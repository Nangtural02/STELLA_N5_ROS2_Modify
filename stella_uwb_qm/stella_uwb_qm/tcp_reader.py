import socket
import threading
import time


class TcpReader(threading.Thread):
    def __init__(self, host: str, port: int, on_line, logger):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self._on_line = on_line
        self._logger = logger
        self._running = True
        self._sock = None

    def run(self):
        while self._running:
            try:
                self._sock = socket.create_connection(
                    (self.host, self.port), timeout=5
                )
                self._logger.info(
                    f'Connected to {self.host}:{self.port}'
                )
                f = self._sock.makefile('r', encoding='utf-8', errors='ignore')
                while self._running:
                    line = f.readline()
                    if not line:
                        break
                    line = line.strip()
                    if line:
                        self._on_line(line)
            except (OSError, ConnectionRefusedError) as e:
                if self._running:
                    self._logger.warning(
                        f'TCP connection error ({self.host}:{self.port}): {e}'
                    )
            finally:
                self._close_socket()

            if self._running:
                time.sleep(2)

    def stop(self):
        self._running = False
        self._close_socket()

    def _close_socket(self):
        if self._sock:
            try:
                self._sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
