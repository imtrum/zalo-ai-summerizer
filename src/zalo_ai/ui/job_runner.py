"""Run UI jobs in background threads and deliver events on the Tk thread."""

import logging
import queue
import threading
from collections.abc import Callable
from threading import Event

from zalo_ai.common.cancellation import CancellationRequested


Job = Callable[[Callable[[str], None], Event], object]


class JobRunner:
    """Manage job state and dispatch worker results through callbacks."""

    def __init__(
        self,
        on_status: Callable[[str], None],
        on_log: Callable[[str], None],
        on_result: Callable[[str, object], None],
        on_error: Callable[[str, Exception], None],
        on_cancelled: Callable[[str, Exception], None],
        set_busy: Callable[[bool], None],
        schedule: Callable[[Callable[[], None]], None],
    ) -> None:
        self.on_status = on_status
        self.on_log = on_log
        self.on_result = on_result
        self.on_error = on_error
        self.on_cancelled = on_cancelled
        self.set_busy = set_busy
        self.schedule = schedule
        self.busy = False
        self.cancel_event: Event | None = None
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()

    def start(self, kind: str, label: str, job: Job) -> None:
        if self.busy:
            return
        self.busy = True
        cancel_event = threading.Event()
        self.cancel_event = cancel_event
        self.on_status(label)
        self.set_busy(True)

        def report(message: str) -> None:
            if not cancel_event.is_set():
                self.events.put(("status", message))

        def worker() -> None:
            try:
                result = job(report, cancel_event)
            except CancellationRequested as error:
                self.events.put(("cancelled", (kind, error)))
            except Exception as error:
                logging.getLogger(__name__).exception("Background UI action failed.")
                self.events.put(("error", (kind, error)))
            else:
                self.events.put(("result", (kind, result)))

        threading.Thread(target=worker, daemon=True).start()

    def cancel(self) -> None:
        if not self.busy or self.cancel_event is None:
            return
        if self.cancel_event.is_set():
            return
        self.cancel_event.set()
        self.set_busy(True)
        self.on_status("Cancellation requested; waiting for the current step.")
        self.on_log("Cancellation requested.")

    def drain(self) -> None:
        while True:
            try:
                event, payload = self.events.get_nowait()
            except queue.Empty:
                break
            if event == "status":
                if self.cancel_event is None or not self.cancel_event.is_set():
                    message = str(payload)
                    self.on_status(message)
                    self.on_log(message)
                continue
            kind, result = payload
            self.busy = False
            self.cancel_event = None
            self.set_busy(False)
            if event == "error":
                self.on_error(kind, result)
            elif event == "cancelled":
                self.on_cancelled(kind, result)
            else:
                self.on_result(kind, result)
        self.schedule(self.drain)
