"""
RPC signatures and parameter marshalling.

These are the parts both ends of a call have to agree on, and they are pure Python - no bus
involved. The calls themselves are covered in test_rpcacp.py.
"""
import pytest

from artie_can import enums, errors, rpc

_PRIMITIVE_SAMPLES = {
    "bool": True,
    "int8_t": -8,
    "uint8_t": 200,
    "int16_t": -300,
    "uint16_t": 60000,
    "int32_t": -70000,
    "uint32_t": 4000000000,
    "int64_t": -5000000000,
    "uint64_t": 18000000000000000000,
}


def test_primitive_parameters_survive_the_round_trip():
    for type_name, value in _PRIMITIVE_SAMPLES.items():
        param = rpc.RpcParam(type_name)
        assert param.decode(param.encode(value)) == value, type_name


def test_float_parameters_survive_the_round_trip():
    """Floats keep their native width in memory even though the protocol narrows them on the wire."""
    for type_name, value in (("float", 1.5), ("double", -2.25)):
        param = rpc.RpcParam(type_name)
        assert param.decode(param.encode(value)) == value


def test_float_and_double_are_narrowed_on_the_wire():
    assert rpc.RpcParam("float").native_size == 4
    assert rpc.RpcParam("float").wire_size == 2
    assert rpc.RpcParam("double").native_size == 8
    assert rpc.RpcParam("double").wire_size == 4


def test_out_of_range_value_is_rejected():
    with pytest.raises(errors.InvalidArgument):
        rpc.RpcParam("uint8_t").encode(256)


def test_non_primitive_type_needs_an_explicit_size():
    with pytest.raises(errors.InvalidArgument):
        rpc.RpcParam("struct pose")


def test_non_primitive_type_is_passed_through_as_raw_bytes():
    param = rpc.RpcParam("array<uint8_t, 4>", size=4)

    assert param.encode(b"\x01\x02\x03\x04") == b"\x01\x02\x03\x04"
    assert param.decode(b"\x01\x02\x03\x04") == b"\x01\x02\x03\x04"
    assert not param.is_primitive


def test_raw_value_of_the_wrong_size_is_rejected():
    with pytest.raises(errors.InvalidArgument):
        rpc.RpcParam("array<uint8_t, 4>", size=4).encode(b"\x01\x02")


def test_void_parameter_carries_nothing():
    param = rpc.RpcParam(rpc.VOID)

    assert param.encode(None) == b""
    assert param.decode(b"") is None
    assert param.wire_size == 0


def test_parameters_are_laid_out_back_to_back():
    signature = rpc.RpcSignature(
        0x10, "MIXED",
        params=(rpc.RpcParam("uint8_t"), rpc.RpcParam("uint32_t"), rpc.RpcParam("float")),
    )

    # uint8_t is 1 byte, uint32_t is 4, and float goes on the wire narrowed to 2.
    assert signature.offsets == (0, 1, 5)


def test_signature_rejects_more_parameters_than_the_protocol_carries():
    with pytest.raises(errors.InvalidArgument):
        rpc.RpcSignature(
            0x10, "TOO_MANY",
            params=tuple(rpc.RpcParam("uint8_t") for _ in range(enums.MAX_RPC_PARAMS + 1)),
        )


def test_variable_length_parameter_must_come_last():
    """The library reads such a parameter as 'from my offset to the end', so nothing can follow it."""
    with pytest.raises(errors.InvalidArgument):
        rpc.RpcSignature(
            0x10, "BAD_ORDER",
            params=(rpc.RpcParam("blob", size=8), rpc.RpcParam("uint8_t")),
        )

    # The same two the other way round is fine.
    rpc.RpcSignature(
        0x10, "GOOD_ORDER",
        params=(rpc.RpcParam("uint8_t"), rpc.RpcParam("blob", size=8)),
    )


def test_extra_arguments_are_rejected():
    signature = rpc.RpcSignature(0x10, "ONE_ARG", params=(rpc.RpcParam("uint8_t"),))

    with pytest.raises(errors.InvalidArgument):
        signature.encode_args((1, 2))


def test_missing_required_argument_is_rejected():
    signature = rpc.RpcSignature(
        0x10, "TWO_ARGS", params=(rpc.RpcParam("uint8_t"), rpc.RpcParam("uint8_t"))
    )

    with pytest.raises(errors.InvalidArgument):
        signature.encode_args((1,))


def test_trailing_optional_arguments_may_be_omitted():
    signature = rpc.RpcSignature(
        0x10, "OPTIONAL_TAIL",
        params=(rpc.RpcParam("uint8_t"), rpc.RpcParam("uint8_t", optional=True)),
    )

    assert signature.encode_args((7,)) == [b"\x07"]


def test_procedure_info_reports_unassigned_ids_as_unregistered():
    listed = rpc.ProcedureInfo(0x10, "ECHO", synchronous=True, param_type_names=("uint8_t",))
    empty = rpc.ProcedureInfo(0x11, "UNASSIGNED", synchronous=True, param_type_names=())

    assert listed.registered
    assert not empty.registered
