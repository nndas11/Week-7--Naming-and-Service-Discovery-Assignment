import os
import signal
import threading
import time
from typing import Optional

from registry_client import RegistryClient


def build_service_address(port: int, explicit_address: Optional[str] = None) -> str:
    if explicit_address:
        return explicit_address
    pod_ip = os.getenv("POD_IP")
    host = pod_ip if pod_ip else "localhost"
    return f"http://{host}:{port}"


class ServiceRegistrar:
    def __init__(
        self,
        service_name: str,
        address: str,
        registry_url: str,
        heartbeat_interval: int = 10,
    ) -> None:
        self.service_name = service_name
        self.address = address
        self.heartbeat_interval = heartbeat_interval
        self._client = RegistryClient(registry_url=registry_url)
        self._stop_event = threading.Event()
        self._registered = False
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._registered:
            self._client.deregister(self.service_name, self.address)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            if not self._registered:
                self._registered = self._client.register(self.service_name, self.address)
                if not self._registered:
                    time.sleep(1)
                    continue

            heartbeat_ok = self._client.heartbeat(self.service_name, self.address)
            if not heartbeat_ok:
                self._registered = False
                time.sleep(1)
                continue

            self._stop_event.wait(self.heartbeat_interval)


def install_signal_handlers(registrar: ServiceRegistrar) -> None:
    def _shutdown_handler(_sig, _frame):
        registrar.stop()
        raise SystemExit(0)

    signal.signal(signal.SIGINT, _shutdown_handler)
    signal.signal(signal.SIGTERM, _shutdown_handler)
