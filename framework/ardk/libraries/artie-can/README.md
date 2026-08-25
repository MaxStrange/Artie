# Artie CAN Library

The Artie CAN Library is a C/C++ and Python library for sending and receiving Artie CAN protocol frames.
For gritty details on the various forms of the Artie CAN protocol,
see [the Artie CAN protocol document](../../../../docs/specifications/CANProtocol.md). That document
describes the protocol in detail. This document on the other hand, describes the software library
that implements the protocol.

## General Architecture

This library is meant to run both on an OS and in a bare-metal embedded context, so it is
entirely heapless (except for the UDP multicast backend, which is used in testing). This means that
structs used by the library are managed by the caller and their lifetime must last the entire
lifetime of the library (until deinitialization, if ever). This is called out in any API documentation
as appropriate.

The general architecture of the library is this:

* Lowest level: backend (transport layer) - the library is meant to work over CAN bus,
  but for testing, using UDP multicast is awfully convenient. Additionally, every device
  has a different way to interact with a CAN bus. Some microcontrollers have a CAN peripheral,
  while others make use of an external SPI to CAN translator (such as the ubiquitous MCP 2515).
  Therefore, we provide a couple of backends that we use in Artie reference implementations,
  and custom backends are easy enough to supply to the library.
* Next layer up: protocol state machines - the Artie CAN protocol is really several different
  protocols that are all meant to be run on the same CAN bus without interfering with one another.
  This means that a single CAN node could be listening for messages that make use of different
  protocols while also sending messages over yet another protocol. Each sub protocol needs its
  own state machine.
* Highest layer: API - the Artie CAN library is quite complicated under the hood, but it is meant
  to be very easy to use. The API layer provides a small set of useful functions that should enable
  pretty much any use case the Artie CAN protocol allows.

## API

The C API is documented with [Doxygen](https://www.doxygen.nl/) comments on the headers in `include/`.
Running `build_and_test_c.ps1` (which drives the same CMake build described below) regenerates the
HTML docs at `build/docs/html/index.html` any time Doxygen is installed and on `PATH`; if Doxygen
isn't found, doc generation is silently skipped and the rest of the build proceeds as normal. This
is currently a manual, local step only - it is not yet wired into the wider Docker-based build system.

The gist of it is that you configure a context struct with the various options for the various
versions of the protocol you are interested in - for example, if you want to make use of the RTACP
(real-time Artie CAN protocol) and the RPCACP (remote procedure call Artie CAN protocol),
you would configure the context struct with the various options required by those protocols,
such as the functions that are exposed over RPC.

Next, you configure a handle struct, which consumes the context struct and is where you choose
the backend implementation (the transport layer) - how do we get the frames out onto the CAN bus?

You then call the artie_can_init function with the configured handle to finalize initialization
of the library. After that, frames will come in asynchronously when received, which will trigger
a callback that you supplied during the initialization steps. Sending frames on the other hand,
is synchronous.

## Examples

The snippets below are adapted from the library's own test suite (`tests/test_rtacp.c`,
`tests/test_bwacp.c`, `tests/test_psacp.c`, and `tests/test_rpcacp.c`), which is the most
up-to-date, exercised reference for how to drive each protocol. They use the UDP multicast
backend, since that's what the tests use to simulate a CAN bus on localhost; a real device would
use `artie_can_init_context_mcp2515()` (or a custom backend) instead of
`artie_can_init_context_udp_mcast()`, but everything above the backend is identical. Error
checking is trimmed for readability - real code should check the return value of every call, as
the tests do.

### Common setup

Every protocol builds on the same pattern: a context and a backend handle per node, a transport
(backend) configured on the context, one or more protocols configured on the same context, and
then `artie_can_init()` to tie it all together and start receiving. Here, two nodes are set up to
talk over UDP multicast; the protocol-specific context initialization (`artie_can_init_context_rtacp()`,
`_bwacp()`, `_psacp()`, `_rpcacp()`) is shown separately in each section below since a single node's
context can be configured for more than one protocol at once.

```c
#include "artie_can.h"

artie_can_context_t node1_context, node2_context;
artie_can_backend_t node1, node2;
artie_can_udp_mcast_context_t node1_udp_ctx, node2_udp_ctx;

// Both nodes join the same multicast group/port to simulate a shared CAN bus.
artie_can_init_context_udp_mcast(&node1_context, &node1_udp_ctx, "239.0.0.1", 5000);
artie_can_init_context_udp_mcast(&node2_context, &node2_udp_ctx, "239.0.0.1", 5000);

// ... protocol-specific context setup goes here, e.g. artie_can_init_context_rtacp() ...

// rx_callback is invoked whenever a frame relevant to this node is received; get_current_time_ms
// is a user-supplied function returning a monotonically increasing millisecond counter.
artie_can_init(&node1_context, &node1, ARTIE_CAN_BACKEND_UDP_MCAST, rx_callback_node1, get_current_time_ms);
artie_can_init(&node2_context, &node2, ARTIE_CAN_BACKEND_UDP_MCAST, rx_callback_node2, get_current_time_ms);

// Somewhere in your main loop (or a dedicated thread/task - see artie_can_tick()'s documentation
// for the threading rules), call artie_can_tick() on each node's handle as often as possible:
artie_can_tick(&node1);
artie_can_tick(&node2);
```

### RTACP (Real Time Artie CAN Protocol)

RTACP is for small, real-time messages sent either to a specific node or broadcast to everyone.
Sends are synchronous and (for non-broadcast frames) ACK'd and retried automatically by the
library; received frames show up in your rx_callback as raw `artie_can_frame_t`s, which you parse
into the friendlier `artie_can_frame_rtacp_t` form (see `tests/test_rtacp.c`):

```c
#include "artie_can.h"

// One-time setup, per node, in addition to the common setup above:
artie_can_init_context_rtacp(&node1_context, 0x01); // node1's RTACP source address
artie_can_init_context_rtacp(&node2_context, 0x02); // node2's RTACP source address

// Sending a message from node 1 to node 2:
uint8_t data_bytes[] = {0xDE, 0xAD, 0xBE, 0xEF};
artie_can_frame_rtacp_t rtacp_frame = {
    .ack = false,
    .priority = ARTIE_CAN_FRAME_PRIORITY_RTACP_MEDIUM,
    .source_address = 0x01,
    .target_address = 0x02, // or ARTIE_CAN_RTACP_TARGET_ADDRESS_BROADCAST to send to everyone
    .nbytes = sizeof(data_bytes),
};
memcpy(rtacp_frame.data, data_bytes, sizeof(data_bytes));

artie_can_frame_t frame_to_send;
artie_can_rtacp_init_frame(&frame_to_send, &rtacp_frame);
artie_can_rtacp_send(&node1, &frame_to_send); // blocks until sent and (if not broadcast) ACK'd

// Receiving: node2's rx_callback (registered in artie_can_init above) parses the incoming frame.
void rx_callback_node2(const artie_can_frame_t *frame)
{
    artie_can_frame_rtacp_t received;
    if (artie_can_rtacp_parse_frame(frame, &received) == ARTIE_CAN_ERR_NONE)
    {
        // received.data[0..received.nbytes) is {0xDE, 0xAD, 0xBE, 0xEF}
    }
}
```

### BWACP (Block Write Artie CAN Protocol)

BWACP moves a larger block of data to a single node or to every node matching a class bitmask,
writing it directly into a caller-supplied receive buffer at a given offset - there's no callback
per chunk, just a buffer that fills in as the transfer progresses (see `tests/test_bwacp.c`).
The protocol sets no maximum transfer size; how much a node can receive is simply how big a buffer
it supplies, and `ARTIE_CAN_BWACP_DEFAULT_BUFFER_SIZE` (64 KB) is only a suggested default. A
receiver whose buffer is too small to hold the transfer drops out of it and is left behind:

```c
#include "artie_can.h"

#define RECEIVE_BUFFER_SIZE 65536
static uint8_t node2_receive_buffer[RECEIVE_BUFFER_SIZE];

// One-time setup, in addition to the common setup above:
artie_can_init_context_bwacp(&node1_context, 0x01, ARTIE_CAN_BWACP_CLASS_SBC);
artie_can_init_context_bwacp(&node2_context, 0x02, ARTIE_CAN_BWACP_CLASS_SENSOR);
// Receiving nodes must supply a buffer before any block write can be received:
artie_can_bwacp_set_receive_buffer(&node2_context, node2_receive_buffer, sizeof(node2_receive_buffer));

// Sending a block write from node 1 to every SENSOR-class node, writing starting at offset 0x1000:
uint8_t send_data[] = {0x42};
uint32_t buffer_offset = 0x1000;
artie_can_bwacp_send(&node1, send_data, sizeof(send_data), buffer_offset,
                      ARTIE_CAN_BWACP_MULTICAST_ADDRESS, ARTIE_CAN_BWACP_CLASS_SENSOR,
                      ARTIE_CAN_FRAME_PRIORITY_BWACP_MEDIUM);

// artie_can_bwacp_send() only queues the transfer; keep calling artie_can_tick() on both nodes
// (see the common setup above) until it completes:
while (artie_can_bwacp_is_busy(&node1))
{
    artie_can_tick(&node1);
    artie_can_tick(&node2);
}

// By now, node2_receive_buffer[0x1000] == 0x42.
```

To send to one specific node instead of a whole class, pass that node's address as
`target_address` and any value for `target_class` (it's ignored for non-multicast sends).

### PSACP (Pub/Sub Artie CAN Protocol)

PSACP is fire-and-forget publish/subscribe: nodes subscribe to topics, and a publish is delivered
to every subscriber of that topic (topic `0x00` is broadcast to all subscribers). There's no ACK
and no retry - if you need guaranteed delivery, use RTACP or BWACP instead (see `tests/test_psacp.c`):

```c
#include "artie_can.h"

#define TOPIC_TEMPERATURE 0x0CU

// One-time setup, in addition to the common setup above:
artie_can_init_context_psacp(&node1_context, 0x01);
artie_can_init_context_psacp(&node2_context, 0x02);
artie_can_psacp_subscribe(&node2_context, TOPIC_TEMPERATURE); // node1 does not subscribe

// Publishing from node 1:
artie_can_frame_psacp_t psacp_frame = {
    .high_priority = false,
    .priority = ARTIE_CAN_FRAME_PRIORITY_PSACP_MEDIUM_LOW,
    .source_address = 0x01,
    .topic = TOPIC_TEMPERATURE,
    .nbytes = 1,
    .data = {0xA5},
};
artie_can_frame_t frame_to_send;
artie_can_psacp_init_frame(&frame_to_send, &psacp_frame);
artie_can_psacp_publish(&node1, &frame_to_send); // fire-and-forget; no ACK

// Receiving: node2's rx_callback parses the incoming frame and checks the topic if needed.
void rx_callback_node2(const artie_can_frame_t *frame)
{
    artie_can_frame_psacp_t received;
    if (artie_can_psacp_parse_frame(frame, &received) == ARTIE_CAN_ERR_NONE)
    {
        // received.topic == TOPIC_TEMPERATURE, received.data[0] == 0xA5
    }
}

// Later, if node2 no longer cares about this topic:
artie_can_psacp_unsubscribe(&node2_context, TOPIC_TEMPERATURE);
```

### RPCACP (Remote Procedure Call Artie CAN Protocol)

RPCACP lets one node invoke a procedure registered on another node and (for synchronous
procedures) get its return value back, with arguments and return values packed as MsgPack.
Every node automatically answers three standard procedures - `ARTIE_CAN_RPC_ID_WHOAMI`,
`ARTIE_CAN_RPC_ID_STATUS`, and `ARTIE_CAN_RPC_ID_LIST` - and can additionally register its own
device-specific procedures (IDs `0x10`-`0x7F`) (see `tests/test_rpcacp.c`):

```c
#include "artie_can.h"

// One-time setup, in addition to the common setup above:
artie_can_init_context_rpcacp(&node1_context, 0x01, 0x01, "node1", "1.0.0");
artie_can_init_context_rpcacp(&node2_context, 0x02, 0x01, "node2", "1.0.0");

// A device-specific procedure that increments a uint8_t and returns it. Every registered
// procedure has this signature; arguments are decoded into `params` and the result is written
// into `return_buffer`.
static void *increment_u8(const void **params, uint8_t param_count, void *return_buffer, size_t return_buffer_size)
{
    uint8_t value;
    memcpy(&value, params[0], sizeof(value));
    value = (uint8_t)(value + 1);
    memcpy(return_buffer, &value, sizeof(value));
    return return_buffer;
}

// Registering it on node 2 requires describing its signature so both sides agree on wire layout:
artie_can_rpc_param_descriptor_t return_desc = { .type_name = "uint8_t", .offset_in_msgpack = 0, .optional = false };
artie_can_rpc_signature_t increment_sig = {
    .procedure_id = 0x10,
    .name = "INCREMENT",
    .synchronous = true,
    .param_count = 1,
    .params = {{ .type_name = "uint8_t", .offset_in_msgpack = 0, .optional = false }},
    .function = increment_u8,
    .return_descriptor = &return_desc,
    .return_size = sizeof(uint8_t),
};
artie_can_rpcacp_register_procedure(&node2, &increment_sig);

// Calling it from node 1. artie_can_rpcacp_call() returns immediately; the exchange is driven to
// completion by repeated artie_can_tick() calls (see the common setup above).
uint8_t arg = 41;
artie_can_rpc_value_t args[1] = {{ .data = &arg, .size = sizeof(arg) }};
artie_can_rpcacp_call(&node1, 0x02, &increment_sig, args, 1);
while (artie_can_rpcacp_is_busy(&node1))
{
    artie_can_tick(&node1);
    artie_can_tick(&node2);
}

uint8_t result = 0;
if (artie_can_rpcacp_get_last_error(&node1, NULL) == ARTIE_CAN_ERR_NONE)
{
    artie_can_rpcacp_get_result(&node1, &increment_sig, &result, sizeof(result)); // result == 42
}

// Calling a standard procedure (no registration needed - it's answered internally) works the
// same way, e.g. asking node 2 who it is:
artie_can_rpc_signature_t whoami_sig = { .procedure_id = ARTIE_CAN_RPC_ID_WHOAMI, .name = "WHOAMI", .synchronous = true };
artie_can_rpcacp_call(&node1, 0x02, &whoami_sig, NULL, 0);
// ... drive event loops until artie_can_rpcacp_is_busy(&node1) is false, as above ...
artie_can_whoami_response_t whoami;
artie_can_rpcacp_get_whoami_result(&node1, &whoami); // whoami.node_name == "node2", etc.
```

## Python API

The `artie_can` Python package wraps the C library. It is built with
[CFFI](https://cffi.readthedocs.io/) in API mode, which means the declarations in `build_ffi.py`
are compiled against the real headers - struct sizes, field offsets and enum values all come from
the C compiler, so the bindings cannot silently drift out of step with the library the way a
hand-written `ctypes` mirror would. The C sources are compiled straight into the extension module,
so an installed `artie_can` is self-contained: no shared library to locate at import time, and no
CMake needed to install.

```bash
pip install -e .            # needs a C compiler; everything else is in pyproject.toml
python build_ffi.py         # optional: compile the bindings alone, into build-python/
```

### The Node

Everything goes through `Node`, which owns a transport, the protocols you enable, and the threads
that keep them running. The C library requires that `artie_can_tick()` be called constantly and
that every other entry point be called from that same thread; the node does both for you on a
worker thread, so the methods below are ordinary blocking calls. Received frames are parsed on a
second thread and handed to a callback or a queue, so nothing of yours runs in the library's
interrupt-context receive callback.

```python
from artie_can import backends, enums, node

bus = dict(group="239.0.0.1", port=5000)
with node.Node(backends.UdpMulticastBackend(**bus), address=0x01) as sender, \
     node.Node(backends.UdpMulticastBackend(**bus), address=0x02) as receiver:
    sender.rtacp_send(0x02, b"\xde\xad\xbe\xef", priority=enums.Priority.MEDIUM)
    print(receiver.receive_rtacp(timeout=1.0).data.hex())
```

A node takes part only in the protocols you ask for, and the methods for the others raise
`InvalidArgument`:

```python
my_node = node.Node(
    backends.UdpMulticastBackend(**bus),
    address=0x02,
    protocols=enums.Protocol.RTACP | enums.Protocol.PSACP | enums.Protocol.BWACP | enums.Protocol.RPCACP,
    node_class=enums.NodeClass.SENSOR,
    name="left-eyebrow",          # reported by WHOAMI
    firmware_version="1.0.0",
)
```

Pass `on_rtacp=`, `on_psacp=` or `on_frame=` to have messages delivered to a callback instead of
queued for `receive_rtacp()` / `receive_psacp()` / `receive_frame()`. Callbacks run on the node's
dispatcher thread, one at a time, in arrival order, and must not call back into the same node.

### Each protocol

```python
# RTACP - small real-time messages. Unicast waits for the ACK; broadcast does not.
my_node.rtacp_send(0x02, b"\x01\x02")
my_node.rtacp_send(enums.BROADCAST_ADDRESS, b"\x01\x02")
message = my_node.receive_rtacp(timeout=1.0)

# PSACP - fire-and-forget pub/sub.
my_node.subscribe(0x0C)
my_node.publish(0x0C, b"\xa5", high_priority=False)
message = my_node.receive_psacp(timeout=1.0)

# BWACP - bulk block writes into the receivers' block buffers.
my_node.block_write(payload, offset=0x1000, target_class=enums.NodeClass.SENSOR)
my_node.block_write(payload, offset=0, target_address=0x02)
received = bytes(my_node.block_buffer[0x1000:0x1000 + len(payload)])

# RPCACP - remote procedure calls.
print(my_node.whoami(0x02), my_node.node_status(0x02), my_node.list_procedures(0x02, page=0))
```

Device-specific procedures are described by an `RpcSignature` that both ends share. Parameter
types are named with the same strings the C library matches on; the primitives marshal to and from
Python values automatically, and anything else (`"array<uint8_t, 4>"`, `"struct pose"`) is passed
through as raw `bytes` of a size you declare.

```python
from artie_can import rpc

INCREMENT = rpc.RpcSignature(
    procedure_id=0x10,
    name="INCREMENT",
    params=(rpc.RpcParam("uint8_t"),),
    returns=rpc.RpcParam("uint8_t"),
    function=lambda value: (value + 1) & 0xFF,   # only the answering node needs this
)

answering_node.register_procedure(INCREMENT)
assert calling_node.call(0x02, INCREMENT, 41) == 42
```

A registered procedure runs on the answering node's worker thread and must not call back into that
node. Raising from it is reported to the caller as a `RemoteError` carrying EINVAL.

### Errors

Every failure is an `ArtieCanError` subclass - `Timeout`, `Busy`, `NoResponse`, `RemoteError` and
so on - carrying the library's full `ErrorFlag` mask, since the C API reports failures as a bit
mask that can have more than one bit set.

Two behaviours are worth knowing about:

* A `Timeout` from `rtacp_send()` means the ACK did not arrive within RTACP's 10 ms budget,
  **not** that the message was lost. The frame is usually delivered and it is the ACK that came
  back late, so treat it as "delivery unconfirmed" and only retry if the receiver tolerates
  duplicates.
* RPC calls retry themselves, within their timeout, while the far end answers that it is busy.
  A node stays busy for a short while after the caller already has its result, so back-to-back
  calls run into this constantly; because that rejection means the procedure definitely did not
  run, repeating the request is safe. Pass `retry_if_busy=False` to get the `RemoteError`
  instead. Nothing else is retried - a timeout leaves it unknown whether the remote ran the
  procedure, so that one is always yours to decide about.

### Backends

`UdpMulticastBackend` simulates a bus over UDP multicast, which is what the tests and local
development use. `Mcp2515Backend` drives a real bus through an MCP2515, and takes two callables
from you - one to clock a byte over SPI and return the byte clocked back, one to drive chip
select - since the library has no way to reach your SPI peripheral itself.

## Testing

There are two suites, and they test different things.

The **unit tests** (`tests/`) are Unity tests that stand several nodes up inside a single process
on the UDP multicast backend. Run them locally with `build_and_test_c.ps1`, or in a container via
`artie-tool test artie-can-unit-tests`. Because every node shares one process, frames never actually
leave it - what these cover is the protocol state machines.

The **integration tests** (`itest/`) close that gap by putting each node in its own container, so
frames really do cross a network. `itest/itest_node.c` builds a single binary with two roles: a
long-lived `peer` that answers whatever it is sent (echoing RTACP frames, acknowledging PSACP
publishes and completed BWACP blocks, and servicing an ECHO RPC), and a one-shot `driver` that runs
one scenario, decides pass/fail, and prints `ITEST <scenario>:PASS`. Docker compose hosts two peers
(addresses `0x02` and `0x03`) and each test step runs a driver as node `0x01`:

```bash
artie-tool test can-integration-tests
```

To drive it by hand instead - useful when adding a scenario:

```bash
docker network create can-itest
docker run -d --name can-itest-node-2 --network can-itest <image> \
    /artie-can/build/itest/itest_node --role peer --address 0x02
docker run -d --name can-itest-node-3 --network can-itest <image> \
    /artie-can/build/itest/itest_node --role peer --address 0x03
docker run --rm --network can-itest <image> \
    /artie-can/build/itest/itest_node --role driver --address 0x01 --scenario rtacp-unicast
```

Two things to know before adding scenarios. Every node needs a **unique address**, because the UDP
multicast backend filters out its own traffic by comparing each frame's source address to its own -
two nodes sharing an address silently discard each other's frames. And each scenario needs its own
**payload marker**, because the peers outlive every individual test while the task streams their
logs from container start, so a marker reused across scenarios could match the wrong test's line.

`itest_node` is deliberately not registered with CTest, so `ctest` still runs only the unit tests.

## Integrating

To integrate the Artie CAN Library into an application, there are several ways to do it depending
on the programming language and the hardware.

From Python, install this directory as a package and use `artie_can.node.Node` - see
[the Python API section](#python-api) above. It is not yet wired into Artie Tool or the base
image's Python environment.

From C, build the library with CMake and link against `artie_can` (shared) or `artie_can_static`,
with `include/`, `include/backend/`, `include/protocol/` and `include/util/` on the include path.
On an MCU, compile the sources directly into your firmware instead and supply a backend - see
`artie_can_init_custom()`.
