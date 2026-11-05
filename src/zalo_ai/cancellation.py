from threading import Event


class CancellationRequested(Exception):
    """Raised when the user asks an active workflow to stop."""


def check_cancellation(cancel_event: Event | None) -> None:
    """Stop at a safe checkpoint when the user has requested cancellation."""
    if cancel_event is not None and cancel_event.is_set():
        raise CancellationRequested("The operation was cancelled.")
