"""
Python bindings for the Artie CAN library.

The Artie CAN protocol is really four protocols sharing one bus, and this package exposes all of
them through a single :class:`~artie_can.node.Node`:

* **RTACP** - small, latency-sensitive messages to one node or to everyone, ACK'd and retried
  (:meth:`~artie_can.node.Node.rtacp_send`, :meth:`~artie_can.node.Node.receive_rtacp`).
* **PSACP** - fire-and-forget publish/subscribe on numbered topics
  (:meth:`~artie_can.node.Node.publish`, :meth:`~artie_can.node.Node.subscribe`,
  :meth:`~artie_can.node.Node.receive_psacp`).
* **BWACP** - bulk block writes of arbitrary size into a receiver's buffer, bounded only by how
  much the receiver allocated (:meth:`~artie_can.node.Node.block_write`,
  :attr:`~artie_can.node.Node.block_buffer`).
* **RPCACP** - remote procedure calls, including the standard WHOAMI, STATUS and LIST that every
  node answers (:meth:`~artie_can.node.Node.call`, :meth:`~artie_can.node.Node.register_procedure`,
  :meth:`~artie_can.node.Node.whoami`).

A minimal two-node exchange over the UDP multicast transport, which simulates a CAN bus on
localhost::

    from artie_can import backends, node

    bus = dict(group="239.0.0.1", port=5000)
    with node.Node(backends.UdpMulticastBackend(**bus), address=0x01) as sender, \\
         node.Node(backends.UdpMulticastBackend(**bus), address=0x02) as receiver:
        sender.rtacp_send(0x02, b"\\xde\\xad\\xbe\\xef")
        print(receiver.receive_rtacp(timeout=1.0).data.hex())

The node runs the library's event loop for you on its own thread, so methods here are ordinary
blocking calls; see :mod:`artie_can.node` for how that works.
"""
from . import backends, enums, errors, frames, node, rpc

__version__ = "0.1.0"

__all__ = [
    "backends",
    "enums",
    "errors",
    "frames",
    "node",
    "rpc",
    "__version__",
]
