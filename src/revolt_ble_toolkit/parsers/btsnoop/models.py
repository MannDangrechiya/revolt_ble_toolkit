"""Domain models for parsed BTSnoop / HCI data.

These types are specific to the BTSnoop parser (as opposed to the
format-agnostic placeholders in :mod:`revolt_ble_toolkit.core.models`)
because their fields only make sense in terms of the HCI/BTSnoop wire
format: connection handles, H4 packet types, ACL boundary flags, etc.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class PacketDirection(Enum):
    """Direction of an HCI packet relative to the host."""

    HOST_TO_CONTROLLER = "host_to_controller"
    CONTROLLER_TO_HOST = "controller_to_host"


class HciPacketType(Enum):
    """HCI packet type, per the H4 UART transport framing indicator byte."""

    COMMAND = 0x01
    ACL_DATA = 0x02
    SCO_DATA = 0x03
    EVENT = 0x04
    ISO_DATA = 0x05
    UNKNOWN = 0x00

    @classmethod
    def from_indicator(cls, indicator: int) -> HciPacketType:
        """Map a raw H4 indicator byte to a member, defaulting to ``UNKNOWN``."""
        try:
            return cls(indicator)
        except ValueError:
            return cls.UNKNOWN


@dataclass(frozen=True, slots=True)
class BtSnoopFileHeader:
    """Parsed BTSnoop file header."""

    identification: bytes
    version: int
    datalink_type: int


@dataclass(frozen=True, slots=True)
class AclHeader:
    """Parsed HCI ACL Data packet header (Bluetooth Core Spec, Vol 2, Part E).

    ``payload`` is the raw data carried by the ACL packet (e.g. an L2CAP
    frame) — it is not decoded further at this stage.
    """

    connection_handle: int
    packet_boundary_flag: int
    broadcast_flag: int
    data_total_length: int
    payload: bytes


@dataclass(frozen=True, slots=True)
class HciPacket:
    """A single parsed HCI packet captured in a BTSnoop log."""

    number: int
    timestamp: datetime
    direction: PacketDirection
    packet_type: HciPacketType
    original_length: int
    included_length: int
    cumulative_drops: int
    data: bytes
    acl: AclHeader | None = None

    @property
    def is_truncated(self) -> bool:
        """True if fewer bytes were captured than the packet's original length."""
        return self.included_length < self.original_length
