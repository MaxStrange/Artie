"""
RPCACP - remote procedure calls, both the standard ones every node answers and device-specific ones.
"""
import time

import pytest

from artie_can import enums, errors, rpc

from conftest import call_rpc

RPCACP_ONLY = enums.Protocol.RPCACP

INCREMENT = rpc.RpcSignature(
    procedure_id=0x10,
    name="INCREMENT",
    params=(rpc.RpcParam("uint8_t"),),
    returns=rpc.RpcParam("uint8_t"),
    function=lambda value: (value + 1) & 0xFF,
)

SUM3 = rpc.RpcSignature(
    procedure_id=0x11,
    name="SUM3",
    params=(rpc.RpcParam("uint8_t"), rpc.RpcParam("uint16_t"), rpc.RpcParam("int32_t")),
    returns=rpc.RpcParam("int32_t"),
    function=lambda first, second, third: first + second + third,
)

#: Registered but never called with a matching signature - see test_calling_an_unknown_procedure.
UNREGISTERED = rpc.RpcSignature(procedure_id=0x20, name="NOT_THERE", returns=rpc.RpcParam("uint8_t"))


def test_whoami_reports_the_nodes_identity(make_node):
    caller = make_node(0x01, protocols=RPCACP_ONLY)
    make_node(0x02, protocols=RPCACP_ONLY, name="left-eyebrow", firmware_version="1.2.3")

    identity = call_rpc(caller.whoami, 0x02)

    assert identity.node_address == 0x02
    assert identity.node_name == "left-eyebrow"
    assert identity.firmware_version == "1.2.3"


def test_status_reports_uptime(make_node):
    caller = make_node(0x01, protocols=RPCACP_ONLY)
    make_node(0x02, protocols=RPCACP_ONLY)

    status = call_rpc(caller.node_status, 0x02)

    assert status.uptime_ms >= 0
    assert status.error_flags == 0


def test_status_reports_the_error_flags_the_node_set(make_node):
    caller = make_node(0x01, protocols=RPCACP_ONLY)
    answering = make_node(0x02, protocols=RPCACP_ONLY)
    answering.set_status_error_flags(0xABCD)

    assert call_rpc(caller.node_status, 0x02).error_flags == 0xABCD


# LIST is paged: one page describes RPC_LIST_PAGE_SIZE consecutive procedure IDs, so which page a
# procedure appears on follows from its ID. These are two tests rather than one because each LIST
# call is a multi-frame exchange and a node stays busy for a moment after finishing one - asking
# the same node for a second page straight away runs into that.

def test_list_reports_the_standard_procedures(make_node):
    caller = make_node(0x01, protocols=RPCACP_ONLY)
    make_node(0x02, protocols=RPCACP_ONLY)

    listed = call_rpc(caller.list_procedures, 0x02, page=0)

    assert {"WHOAMI", "STATUS", "LIST"} <= {entry.name for entry in listed if entry.registered}


def test_list_reports_the_procedures_a_node_registered(make_node):
    caller = make_node(0x01, protocols=RPCACP_ONLY)
    answering = make_node(0x02, protocols=RPCACP_ONLY)
    answering.register_procedure(INCREMENT)

    listed = call_rpc(
        caller.list_procedures, 0x02, page=INCREMENT.procedure_id // enums.RPC_LIST_PAGE_SIZE
    )

    registered = {entry.procedure_id: entry for entry in listed if entry.registered}
    assert INCREMENT.procedure_id in registered
    assert registered[INCREMENT.procedure_id].name == "INCREMENT"
    assert registered[INCREMENT.procedure_id].param_type_names == ("uint8_t",)


def test_call_returns_what_the_procedure_returned(make_node):
    caller = make_node(0x01, protocols=RPCACP_ONLY)
    answering = make_node(0x02, protocols=RPCACP_ONLY)
    answering.register_procedure(INCREMENT)

    assert call_rpc(caller.call, 0x02, INCREMENT, 41) == 42


def test_call_passes_every_argument_through(make_node):
    caller = make_node(0x01, protocols=RPCACP_ONLY)
    answering = make_node(0x02, protocols=RPCACP_ONLY)
    answering.register_procedure(SUM3)

    assert call_rpc(caller.call, 0x02, SUM3, 1, 1000, -100) == 901


def test_call_of_a_void_procedure_returns_nothing(make_node):
    called_with = []
    record = rpc.RpcSignature(
        procedure_id=0x12,
        name="RECORD",
        params=(rpc.RpcParam("uint8_t"),),
        function=called_with.append,
    )

    caller = make_node(0x01, protocols=RPCACP_ONLY)
    answering = make_node(0x02, protocols=RPCACP_ONLY)
    answering.register_procedure(record)

    assert call_rpc(caller.call, 0x02, record, 9) is None
    assert called_with[-1] == 9


def test_asynchronous_call_returns_before_the_procedure_has_run(make_node):
    ran = []
    background = rpc.RpcSignature(
        procedure_id=0x13,
        name="BACKGROUND",
        params=(rpc.RpcParam("uint8_t"),),
        synchronous=False,
        function=ran.append,
    )

    caller = make_node(0x01, protocols=RPCACP_ONLY)
    answering = make_node(0x02, protocols=RPCACP_ONLY)
    answering.register_procedure(background)

    assert call_rpc(caller.call, 0x02, background, 7) is None

    deadline = time.monotonic() + 10.0
    while not ran and time.monotonic() < deadline:
        time.sleep(0.01)
    assert ran[-1] == 7


def test_calling_an_unknown_procedure_is_rejected_by_the_remote(make_node):
    caller = make_node(0x01, protocols=RPCACP_ONLY)
    make_node(0x02, protocols=RPCACP_ONLY)

    with pytest.raises(errors.RemoteError) as caught:
        call_rpc(caller.call, 0x02, UNREGISTERED, timeout=10.0)

    assert caught.value.errno != 0


def test_a_procedure_that_raises_is_reported_back_to_the_caller(make_node):
    def explode(_value):
        raise RuntimeError("no")

    exploding = rpc.RpcSignature(
        procedure_id=0x14, name="EXPLODE", params=(rpc.RpcParam("uint8_t"),),
        returns=rpc.RpcParam("uint8_t"), function=explode,
    )

    caller = make_node(0x01, protocols=RPCACP_ONLY)
    answering = make_node(0x02, protocols=RPCACP_ONLY)
    answering.register_procedure(exploding)

    with pytest.raises(errors.RemoteError) as caught:
        call_rpc(caller.call, 0x02, exploding, 1, timeout=10.0)

    assert caught.value.errno == enums.RpcErrno.EINVAL


def test_there_is_no_such_thing_as_a_broadcast_call(make_node):
    caller = make_node(0x01, protocols=RPCACP_ONLY)

    with pytest.raises(errors.InvalidArgument):
        caller.call(enums.BROADCAST_ADDRESS, INCREMENT, 1)


def test_registering_needs_something_to_run(make_node):
    answering = make_node(0x01, protocols=RPCACP_ONLY)

    with pytest.raises(errors.InvalidArgument):
        answering.register_procedure(UNREGISTERED)
