"""
Error codes and exceptions for the Artie CAN library.

The C library reports failures as a bit mask (see `include/err.h`), because a single operation can
fail more than one way at a time - an `artie_can_tick()` that drives four protocol state machines
ORs together whatever each of them reported. :class:`ErrorFlag` preserves that mask, and
:func:`check` turns a non-zero mask into the most specific exception it can while keeping the full
mask available on the exception for callers that care.
"""
from __future__ import annotations

import enum

from ._artie_can import lib

__all__ = [
    "ErrorFlag",
    "ArtieCanError",
    "InvalidArgument",
    "Timeout",
    "NoData",
    "SendFailed",
    "ReceiveFailed",
    "InitFailed",
    "CloseFailed",
    "NodeClosed",
    "Busy",
    "NoSpace",
    "InternalError",
    "DriverError",
    "NoResponse",
    "RemoteError",
    "check",
]


class ErrorFlag(enum.IntFlag):
    """The Artie CAN error codes, as a bit mask. ``NONE`` (zero) means success."""

    NONE = 0
    INVALID_ARG = lib.ARTIE_CAN_ERR_INVALID_ARG
    TIMEOUT = lib.ARTIE_CAN_ERR_TIMEOUT
    NO_DATA = lib.ARTIE_CAN_ERR_NO_DATA
    SEND_FAIL = lib.ARTIE_CAN_ERR_SEND_FAIL
    RECEIVE_FAIL = lib.ARTIE_CAN_ERR_RECEIVE_FAIL
    INIT_FAIL = lib.ARTIE_CAN_ERR_INIT_FAIL
    CLOSE_FAIL = lib.ARTIE_CAN_ERR_CLOSE_FAIL
    CLOSED = lib.ARTIE_CAN_ERR_CLOSED
    SEND_BUSY = lib.ARTIE_CAN_ERR_SEND_BUSY
    NO_SPACE = lib.ARTIE_CAN_ERR_NO_SPACE
    INTERNAL = lib.ARTIE_CAN_ERR_INTERNAL
    DRIVER = lib.ARTIE_CAN_ERR_DRIVER
    NO_RESPONSE = lib.ARTIE_CAN_ERR_NO_RESPONSE

    @property
    def retriable(self) -> bool:
        """True if every flag set here is one the library considers worth retrying.

        Mirrors ``ARTIE_CAN_ERR_ONLY_RETRIABLE`` from ``err.h``.
        """
        return bool(self) and not (self & ~_RETRIABLE_MASK)


_RETRIABLE_MASK = (
    ErrorFlag.TIMEOUT | ErrorFlag.SEND_BUSY | ErrorFlag.NO_SPACE | ErrorFlag.NO_RESPONSE
)


class ArtieCanError(Exception):
    """Base class for every failure reported by the Artie CAN library.

    :ivar flags: The full :class:`ErrorFlag` mask the library reported.
    :ivar operation: The library call that failed, for context in the message.
    """

    def __init__(self, message: str, flags: ErrorFlag = ErrorFlag.NONE, operation: str = ""):
        self.flags = ErrorFlag(flags)
        self.operation = operation
        if operation:
            message = f"{operation}: {message}"
        if self.flags:
            message = f"{message} (flags={self.flags!r})"
        super().__init__(message)


class InvalidArgument(ArtieCanError, ValueError):
    """An argument was rejected by the library (``ARTIE_CAN_ERR_INVALID_ARG``)."""


class Timeout(ArtieCanError, TimeoutError):
    """An operation did not complete in time (``ARTIE_CAN_ERR_TIMEOUT``)."""


class NoData(ArtieCanError):
    """There was nothing to read (``ARTIE_CAN_ERR_NO_DATA``)."""


class SendFailed(ArtieCanError):
    """A frame could not be put on the bus (``ARTIE_CAN_ERR_SEND_FAIL``)."""


class ReceiveFailed(ArtieCanError):
    """A frame could not be read off the bus (``ARTIE_CAN_ERR_RECEIVE_FAIL``)."""


class InitFailed(ArtieCanError):
    """The backend could not be brought up (``ARTIE_CAN_ERR_INIT_FAIL``)."""


class CloseFailed(ArtieCanError):
    """The backend could not be shut down cleanly (``ARTIE_CAN_ERR_CLOSE_FAIL``)."""


class NodeClosed(ArtieCanError):
    """The node has already been closed (``ARTIE_CAN_ERR_CLOSED``)."""


class Busy(ArtieCanError):
    """The bus or a protocol state machine is busy with an earlier operation.

    Corresponds to ``ARTIE_CAN_ERR_SEND_BUSY``.
    """


class NoSpace(ArtieCanError):
    """A buffer was too small for the data (``ARTIE_CAN_ERR_NO_SPACE``)."""


class InternalError(ArtieCanError):
    """The library hit a state it considers a bug (``ARTIE_CAN_ERR_INTERNAL``)."""


class DriverError(ArtieCanError):
    """The backend driver failed talking to the hardware (``ARTIE_CAN_ERR_DRIVER``)."""


class NoResponse(ArtieCanError):
    """An expected ACK or reply never arrived (``ARTIE_CAN_ERR_NO_RESPONSE``)."""


class RemoteError(ArtieCanError):
    """A remote node NACK'd an RPC request.

    :ivar errno: The errno-style byte the remote reported (see :class:`artie_can.RpcErrno`).
    """

    def __init__(self, message: str, errno: int, flags: ErrorFlag = ErrorFlag.NONE, operation: str = ""):
        self.errno = errno
        super().__init__(message, flags, operation)


# Ordered lowest-bit-first, so the exception chosen for a compound mask is the one for the most
# fundamental failure in it.
_EXCEPTIONS: tuple[tuple[ErrorFlag, type[ArtieCanError], str], ...] = (
    (ErrorFlag.INVALID_ARG, InvalidArgument, "invalid argument"),
    (ErrorFlag.TIMEOUT, Timeout, "operation timed out"),
    (ErrorFlag.NO_DATA, NoData, "no data available"),
    (ErrorFlag.SEND_FAIL, SendFailed, "failed to send frame"),
    (ErrorFlag.RECEIVE_FAIL, ReceiveFailed, "failed to receive frame"),
    (ErrorFlag.INIT_FAIL, InitFailed, "failed to initialize backend"),
    (ErrorFlag.CLOSE_FAIL, CloseFailed, "failed to close backend"),
    (ErrorFlag.CLOSED, NodeClosed, "backend is closed"),
    (ErrorFlag.SEND_BUSY, Busy, "bus is busy"),
    (ErrorFlag.NO_SPACE, NoSpace, "no space left in buffer"),
    (ErrorFlag.INTERNAL, InternalError, "internal library error"),
    (ErrorFlag.DRIVER, DriverError, "backend driver error"),
    (ErrorFlag.NO_RESPONSE, NoResponse, "no response received"),
)


def to_exception(code: int, operation: str = "") -> ArtieCanError | None:
    """Build the exception for an error mask, or return None if the mask is ``NONE``."""
    flags = ErrorFlag(code)
    if not flags:
        return None
    for flag, exception_type, message in _EXCEPTIONS:
        if flags & flag:
            return exception_type(message, flags, operation)
    return ArtieCanError("unrecognized error code", flags, operation)


def check(code: int, operation: str = "") -> None:
    """Raise the matching :class:`ArtieCanError` if ``code`` is not ``ARTIE_CAN_ERR_NONE``."""
    error = to_exception(code, operation)
    if error is not None:
        raise error
