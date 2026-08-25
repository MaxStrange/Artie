"""
Transport backends - how a node's frames actually get onto a bus.

The C library separates the protocol state machines from the transport underneath them, and these
classes are the Python face of that split. Pass one to :class:`~artie_can.Node`; the node owns it
from then on and it cannot be shared between nodes.
"""
from __future__ import annotations

import abc
import traceback
from typing import Callable

from ._artie_can import ffi, lib
from . import enums, errors

__all__ = ["Backend", "UdpMulticastBackend", "Mcp2515Backend"]


class Backend(abc.ABC):
    """Base class for transports. Subclasses configure a node's context for one bus type."""

    #: Which ``artie_can_backend_type_t`` the library should initialize for this transport.
    backend_type: enums.BackendType

    @abc.abstractmethod
    def _configure(self, context) -> None:
        """Point ``context`` at this backend's own context struct.

        Called once, before the protocols are configured and before ``artie_can_init()``. The
        backend must hold on to any cdata it allocates for as long as the node lives.
        """
        pass

class UdpMulticastBackend(Backend):
    """Simulate a CAN bus over UDP multicast.

    Every node that joins the same group and port sees every frame, which is close enough to a
    real CAN bus's broadcast semantics for development, tests, and running Artie nodes across
    containers or a LAN. Not for production hardware.

    :param group: Multicast group address, e.g. ``"239.0.0.1"``.
    :param port: Multicast port. Every node on the same simulated bus must agree on it.
    """

    backend_type = enums.BackendType.UDP_MULTICAST

    def __init__(self, group: str = "239.0.0.1", port: int = 5000):
        self.group = group
        self.port = port
        self._context = None

    def __repr__(self) -> str:
        return f"UdpMulticastBackend(group={self.group!r}, port={self.port})"

    def _configure(self, context) -> None:
        self._context = ffi.new("artie_can_udp_mcast_context_t *")
        errors.check(
            lib.artie_can_init_context_udp_mcast(context, self._context, self.group.encode("utf-8"), self.port),
            "artie_can_init_context_udp_mcast",
        )


class Mcp2515Backend(Backend):
    """Talk to a real CAN bus through an MCP2515 SPI-to-CAN controller.

    The library does not know how to reach your SPI peripheral, so you supply two callables. Both
    are invoked from the library's driver, including from its interrupt path, and both run on
    whichever thread called into the library - keep them short and free of locks that the rest of
    your program might hold.

    :param transfer_byte: ``transfer_byte(value) -> int``. Clock one byte out to the MCP2515 and
        return the byte clocked back in on the same transfer.
    :param select: ``select(active) -> None``. Drive the chip-select line: ``True`` means asserted
        (low). Leave it as a no-op if your SPI peripheral handles CS in hardware.
    :param mode: Which mode to configure the controller into. ``LOOPBACK`` is useful for bringing
        a board up without a second node on the bus.
    :param oscillator_freq_hz: Frequency of the crystal wired to the MCP2515.
    :param buffer_full_pin_0_interrupt: Configure the RX0BF pin as an interrupt output.
    :param buffer_full_pin_1_interrupt: Configure the RX1BF pin as an interrupt output.
    """

    backend_type = enums.BackendType.MCP2515

    def __init__(
        self,
        transfer_byte: Callable[[int], int],
        select: Callable[[bool], None],
        *,
        mode: enums.Mcp2515Mode = enums.Mcp2515Mode.NORMAL,
        oscillator_freq_hz: int = 16_000_000,
        buffer_full_pin_0_interrupt: bool = False,
        buffer_full_pin_1_interrupt: bool = False,
    ):
        self.transfer_byte = transfer_byte
        self.select = select
        self.mode = enums.Mcp2515Mode(mode)
        self.oscillator_freq_hz = oscillator_freq_hz
        self.buffer_full_pin_0_interrupt = buffer_full_pin_0_interrupt
        self.buffer_full_pin_1_interrupt = buffer_full_pin_1_interrupt
        self._context = None
        self._write_byte_callback = None
        self._write_cs_pin_callback = None

    def __repr__(self) -> str:
        return f"Mcp2515Backend(mode={self.mode.name}, oscillator_freq_hz={self.oscillator_freq_hz})"

    def _configure(self, context) -> None:
        self._context = ffi.new("artie_can_mcp2515_context_t *")

        config = ffi.new("driver_mcp2515_config_t *")
        config.bfp0_int_enabled = self.buffer_full_pin_0_interrupt
        config.bfp1_int_enabled = self.buffer_full_pin_1_interrupt
        config.mode = int(self.mode)
        config.oscillator_freq_hz = self.oscillator_freq_hz

        # The driver reads the byte the MCP2515 clocked back out of the context's read_byte field,
        # which is this callback's job to fill in.
        def write_byte(_context, value):
            try:
                self._context.read_byte = self.transfer_byte(value) & 0xFF
                return lib.ARTIE_CAN_ERR_NONE
            except Exception:
                traceback.print_exc()
                return lib.ARTIE_CAN_ERR_DRIVER

        def write_cs_pin(_context, cs_low):
            try:
                self.select(bool(cs_low))
                return lib.ARTIE_CAN_ERR_NONE
            except Exception:
                traceback.print_exc()
                return lib.ARTIE_CAN_ERR_DRIVER

        self._write_byte_callback = ffi.callback("artie_can_write_byte_t", write_byte, error=lib.ARTIE_CAN_ERR_DRIVER)
        self._write_cs_pin_callback = ffi.callback("artie_can_write_cs_pin_t", write_cs_pin, error=lib.ARTIE_CAN_ERR_DRIVER)

        errors.check(
            lib.artie_can_init_context_mcp2515(context, self._context, config, self._write_byte_callback, self._write_cs_pin_callback),
            "artie_can_init_context_mcp2515",
        )
