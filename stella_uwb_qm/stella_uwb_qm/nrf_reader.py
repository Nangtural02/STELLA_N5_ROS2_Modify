"""Reader that spawns `run_fira_twr` as a subprocess and emits each
`# Ranging Data:` text block (delimited by a blank line) to a callback.

`run_fira_twr -t -1` uses `input("Press <RETURN> to stop")` and does not
emit any ranging data until stdin is a real terminal. We hand it a PTY so
the child blocks on `input()` normally, and on `stop()` we write "\\n" to
the PTY master which returns `input()` cleanly — the child then runs
`ranging_stop` + `session_deinit` before exiting, which is the only path
that avoids the `RxPhyStsFailed` board-state corruption.

For safety (previous invocation crashed, or self-heal path), every spawn
is still preceded by a `reset_device` call, and runtime
`RxPhyStsFailed` messages trigger kill → reset → respawn.
"""

import os
import pty
import shlex
import shutil
import subprocess
import threading
import time

_ERROR_PATTERN = 'RxPhyStsFailed'


class NrfReader(threading.Thread):
    def __init__(
        self,
        port: str,
        role: str,
        on_block,
        logger,
        extra_args: list | None = None,
        binary: str = 'run_fira_twr',
        reset_binary: str = 'reset_device',
        no_ok_timeout_s: float = 10.0,
        stall_timeout_s: float = 10.0,
        post_reset_delay_s: float = 1.0,
        startup_grace_s: float = 3.0,
    ):
        super().__init__(daemon=True)
        self.port = port
        self.role = role
        self._on_block = on_block
        self._logger = logger
        self._extra_args = list(extra_args or [])
        self._binary = binary
        self._reset_binary = reset_binary
        self._no_ok_timeout_s = no_ok_timeout_s
        self._stall_timeout_s = stall_timeout_s
        self._post_reset_delay_s = post_reset_delay_s
        self._startup_grace_s = startup_grace_s
        self._spawn_time = 0.0
        self._running = True
        self._proc: subprocess.Popen | None = None
        self._master_fd: int | None = None
        self._stderr_thread: threading.Thread | None = None
        self._watchdog_thread: threading.Thread | None = None
        self._last_activity = time.monotonic()
        self._last_ok_time = 0.0
        self._reset_triggered = False
        self._reset_missing_warned = False

    def _build_cmd(self) -> list[str]:
        cmd = [self._binary, '-p', self.port, '-t', '-1']
        if self.role == 'controlee':
            cmd.append('--controlee')
        cmd.extend(self._extra_args)
        return cmd

    def _reset_device(self) -> None:
        if shutil.which(self._reset_binary) is None:
            if not self._reset_missing_warned:
                self._logger.warning(
                    f"'{self._reset_binary}' not found on PATH; "
                    'skipping device reset'
                )
                self._reset_missing_warned = True
            return
        cmd = [self._reset_binary, '-p', self.port]
        self._logger.info(f'Resetting QM device: {shlex.join(cmd)}')
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
        except subprocess.TimeoutExpired:
            self._logger.warning('reset_device timed out (>2s)')
            return
        except OSError as e:
            self._logger.warning(f'reset_device failed to execute: {e}')
            return
        if result.returncode != 0:
            stderr = (result.stderr or '').strip()
            self._logger.warning(
                f'reset_device exited {result.returncode}: {stderr}'
            )
        else:
            self._logger.info('reset_device OK')

    def _note_error(self, source: str, text: str) -> None:
        # Trigger a reset only when RxPhyStsFailed has been the ONLY
        # thing we've seen for `no_ok_timeout_s` seconds — i.e. no
        # successful ranging round interleaved. If Ok measurements are
        # still coming through, the stream is fine and we leave it
        # alone.
        now = time.monotonic()
        if now - self._spawn_time < self._startup_grace_s:
            return
        if self._reset_triggered:
            return
        last_good = max(
            self._last_ok_time, self._spawn_time + self._startup_grace_s
        )
        idle = now - last_good
        if idle < self._no_ok_timeout_s:
            return
        self._reset_triggered = True
        self._logger.warning(
            f'{idle:.1f}s without any Ok measurement under '
            f'{_ERROR_PATTERN}; requesting clean shutdown via Enter'
        )
        fd = self._master_fd
        if fd is not None:
            try:
                os.write(fd, b'\n')
            except OSError:
                pass

    def run(self):
        if shutil.which(self._binary) is None:
            self._logger.error(
                f"'{self._binary}' not found on PATH; nRF transport cannot start"
            )
            return

        while self._running:
            self._reset_device()
            if not self._running:
                break
            # Give the board a moment to settle after reset before
            # opening a new session — kicking off run_fira_twr too
            # quickly leaves the radio in a half-initialized state that
            # shows up as a burst of RxPhyStsFailed measurements.
            if self._post_reset_delay_s > 0:
                time.sleep(self._post_reset_delay_s)
            if not self._running:
                break

            cmd = self._build_cmd()
            self._logger.info(f'Starting nRF reader: {shlex.join(cmd)}')

            master_fd, slave_fd = pty.openpty()
            try:
                self._proc = subprocess.Popen(
                    cmd,
                    stdin=slave_fd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    close_fds=True,
                )
            except OSError as e:
                self._logger.warning(f'Failed to spawn {self._binary}: {e}')
                self._proc = None
                try:
                    os.close(slave_fd)
                except OSError:
                    pass
                try:
                    os.close(master_fd)
                except OSError:
                    pass
                if self._running:
                    time.sleep(0.5)
                continue

            try:
                os.close(slave_fd)
            except OSError:
                pass
            self._master_fd = master_fd
            self._spawn_time = time.monotonic()
            self._last_activity = self._spawn_time
            self._last_ok_time = 0.0
            self._reset_triggered = False

            self._start_stderr_drain()
            self._start_watchdog()

            buf: list[str] = []
            try:
                assert self._proc.stdout is not None
                for raw in self._proc.stdout:
                    if not self._running:
                        break
                    self._last_activity = time.monotonic()
                    line = raw.rstrip('\n')
                    stripped = line.strip()
                    if stripped.startswith('status:') and ' Ok ' in stripped:
                        self._last_ok_time = self._last_activity
                    if _ERROR_PATTERN in line:
                        self._note_error('stdout', stripped)
                        # fall through: keep the line so parser sees the
                        # failed-status measurement (maps to status=255)
                    if line.strip() == '':
                        if buf:
                            self._flush_block(buf)
                            buf = []
                        continue
                    buf.append(line)
                if buf:
                    self._flush_block(buf)
                    buf = []
            except Exception as e:
                if self._running:
                    self._logger.warning(f'nRF reader stdout error: {e}')
            finally:
                self._terminate_proc()

            if self._running:
                self._logger.info(
                    'run_fira_twr exited; resetting and restarting'
                )
                time.sleep(0.5)

    def _flush_block(self, buf: list[str]) -> None:
        if not buf:
            return
        if not buf[0].lstrip().startswith('# Ranging Data'):
            return
        block = '\n'.join(buf)
        try:
            self._on_block(block)
        except Exception as e:
            self._logger.warning(f'on_block callback raised: {e}')

    def _start_stderr_drain(self) -> None:
        def _drain():
            if self._proc is None or self._proc.stderr is None:
                return
            try:
                for line in self._proc.stderr:
                    self._last_activity = time.monotonic()
                    text = line.rstrip('\n')
                    if not text:
                        continue
                    if _ERROR_PATTERN in text:
                        self._note_error('stderr', text.strip())
                        continue
                    self._logger.warning(f'[run_fira_twr stderr] {text}')
            except Exception:
                pass

        t = threading.Thread(target=_drain, daemon=True)
        t.start()
        self._stderr_thread = t

    def _start_watchdog(self) -> None:
        """Kill run_fira_twr if neither stdout nor stderr has produced a
        line for `stall_timeout_s`. Handles the case where FT4222 dies
        mid-session: run_fira_twr's worker thread throws IO_ERROR on
        stderr once, then the process hangs in `input()` forever with no
        further output — `proc.poll()` stays None, so the main while
        loop can't detect the stall on its own."""

        proc = self._proc
        if proc is None:
            return

        def _watch():
            while self._running and proc.poll() is None:
                time.sleep(1.0)
                if not self._running:
                    return
                idle = time.monotonic() - self._last_activity
                if idle >= self._stall_timeout_s:
                    self._logger.warning(
                        f'run_fira_twr stalled ({idle:.1f}s without '
                        'output); killing to trigger reset+respawn'
                    )
                    try:
                        proc.kill()
                    except Exception:
                        pass
                    return

        t = threading.Thread(target=_watch, daemon=True)
        t.start()
        self._watchdog_thread = t

    def _send_enter(self) -> bool:
        """Write '\\n' to the child's PTY so `input()` returns. Returns
        True if the write succeeded."""
        fd = self._master_fd
        if fd is None:
            return False
        try:
            os.write(fd, b'\n')
            return True
        except OSError:
            return False

    def _terminate_proc(self) -> None:
        proc = self._proc
        master_fd = self._master_fd
        self._proc = None
        self._master_fd = None

        if proc is not None and proc.poll() is None:
            # Preferred path: inject Enter so the child runs ranging_stop
            # + session_deinit before exiting. This is the only path that
            # leaves the board in a clean state without needing a reset.
            sent_enter = False
            if master_fd is not None:
                try:
                    os.write(master_fd, b'\n')
                    sent_enter = True
                except OSError:
                    pass
            if sent_enter:
                try:
                    proc.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    self._logger.warning(
                        'run_fira_twr did not exit after Enter; terminating'
                    )
            if proc.poll() is None:
                try:
                    proc.terminate()
                    try:
                        proc.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=2)
                except Exception:
                    pass

        if master_fd is not None:
            try:
                os.close(master_fd)
            except OSError:
                pass
        if proc is not None:
            for stream in (proc.stdout, proc.stderr):
                if stream is not None:
                    try:
                        stream.close()
                    except Exception:
                        pass

    def stop(self) -> None:
        self._running = False
        self._terminate_proc()
