"""Serial reader thread for UWB devices."""
import threading
import time

import serial


class SerialReader(threading.Thread):
    """Reads lines from a serial port in a background thread.

    Calls `on_line(line)` for each non-empty line received.
    Automatically reconnects on serial errors.
    """

    def __init__(self, port: str, baud_rate: int, on_line, logger):
        super().__init__(daemon=True)
        self.port = port
        self.baud_rate = baud_rate
        self._on_line = on_line
        self._logger = logger
        self._running = True
        self._ser = None
        self._ready = threading.Event()

    def run(self):
        while self._running:
            try:
                if self._ser is None:
                    self._ser = serial.Serial(self.port, self.baud_rate, timeout=1)
                    self._logger.info(f'Connected to {self.port}')
                    self._ready.set()

                line = self._ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    self._on_line(line)

            except serial.SerialException:
                self._ready.clear()
                if self._ser:
                    self._ser.close()
                self._ser = None
                if self._running:
                    self._logger.warn(
                        f'{self.port} disconnected. Retrying...',
                        throttle_duration_sec=5.0,
                    )
                    time.sleep(2)
            except Exception as e:
                self._logger.warn(f'{self.port} error: {e}')

        self._ready.clear()
        if self._ser and self._ser.is_open:
            self._ser.close()

    def stop(self):
        self._running = False

    def send(self, data: str):
        """Send a command string to the device."""
        if self._ready.wait(timeout=1.0) and self._ser and self._ser.is_open:
            self._ser.write(data.encode('utf-8'))
        else:
            self._logger.warn(f'{self.port} not ready, cannot send')
