"""
Error codes and exceptions.

The C library reports failures as a bit mask, and these check that the Python side keeps the whole
mask while still picking a useful exception type out of it.
"""
import pytest

from artie_can import errors

# A bit no error code uses, for checking the fallback path. The highest real flag is NO_RESPONSE
# at 1 << 12.
_UNKNOWN_FLAG = 1 << 20


def test_success_code_is_falsy():
    assert not errors.ErrorFlag.NONE
    assert errors.ErrorFlag(0) == errors.ErrorFlag.NONE


def test_check_returns_quietly_on_success():
    assert errors.check(0, "some_operation") is None


def test_check_raises_the_matching_exception():
    with pytest.raises(errors.Timeout):
        errors.check(errors.ErrorFlag.TIMEOUT, "some_operation")


def test_exception_carries_flags_and_operation():
    with pytest.raises(errors.NoSpace) as caught:
        errors.check(errors.ErrorFlag.NO_SPACE, "artie_can_bwacp_send")

    assert caught.value.flags == errors.ErrorFlag.NO_SPACE
    assert caught.value.operation == "artie_can_bwacp_send"
    assert "artie_can_bwacp_send" in str(caught.value)


def test_compound_mask_picks_the_most_fundamental_failure():
    """A tick that drives four state machines ORs their failures together."""
    mask = errors.ErrorFlag.SEND_FAIL | errors.ErrorFlag.NO_RESPONSE

    with pytest.raises(errors.SendFailed) as caught:
        errors.check(mask)

    # The exception narrows the mask down to one type, but nothing is lost off the exception.
    assert caught.value.flags == mask


def test_unrecognized_code_falls_back_to_the_base_error():
    error = errors.to_exception(_UNKNOWN_FLAG)

    assert type(error) is errors.ArtieCanError
    assert error.flags == errors.ErrorFlag(_UNKNOWN_FLAG)


def test_retriable_only_when_every_flag_is():
    assert (errors.ErrorFlag.TIMEOUT | errors.ErrorFlag.SEND_BUSY).retriable
    assert not (errors.ErrorFlag.TIMEOUT | errors.ErrorFlag.INTERNAL).retriable
    assert not errors.ErrorFlag.NONE.retriable


def test_exceptions_double_as_their_builtin_equivalents():
    """So that callers can catch these with the builtins they already handle."""
    assert issubclass(errors.Timeout, TimeoutError)
    assert issubclass(errors.InvalidArgument, ValueError)
    assert issubclass(errors.ArtieCanError, Exception)


def test_remote_error_carries_the_nodes_errno():
    error = errors.RemoteError("node said no", errno=5, flags=errors.ErrorFlag.INVALID_ARG)

    assert error.errno == 5
    assert error.flags == errors.ErrorFlag.INVALID_ARG
