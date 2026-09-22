import threading
import time

from harness import network_status


class ReconnectWatcher:
    """Poll connectivity and reconcile once after an offline-to-online edge."""

    def __init__(
        self,
        rw_conn,
        ro_conn,
        verifier,
        ledger,
        reconcile,
        interval=2.0,
    ):
        self.rw_conn = rw_conn
        self.ro_conn = ro_conn
        self.verifier = verifier
        self.ledger = ledger
        self.reconcile = reconcile
        self.interval = interval
        self._stop = threading.Event()
        self._reconciled = threading.Event()
        self._thread = threading.Thread(
            target=self._watch,
            name="veritas-reconnect-watcher",
            daemon=True,
        )

    def start(self):
        self._thread.start()

    def wait_for_reconciliation(self, timeout=None):
        return self._reconciled.wait(timeout)

    def stop(self):
        self._stop.set()
        self._thread.join()

    def _watch(self):
        was_online = network_status.is_online()
        while not self._stop.wait(self.interval):
            online = network_status.is_online()
            if not was_online and online:
                print(
                    f"RECONNECT WATCHER: connectivity restored at "
                    f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}"
                )
                reconciled = self.reconcile(
                    self.rw_conn, self.ro_conn, self.verifier, self.ledger
                )
                print(f"RECONNECT WATCHER: reconciled {reconciled}")
                self._reconciled.set()
                return
            was_online = online
