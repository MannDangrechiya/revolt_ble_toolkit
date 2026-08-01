"""Decodes ATT PDUs out of parsed HCI ACL packets.

An ACL packet's payload is an L2CAP frame: 2-byte length + 2-byte channel ID
(little-endian), then that many bytes of data. ATT uses the fixed channel ID
0x0004. The first byte of an ATT PDU is its opcode.

Only the opcodes listed in :class:`AttOpcode` are surfaced; anything else
(other ATT opcodes, other L2CAP channels, non-ACL packets) is skipped.
"""

from __future__ import annotations

import struct
from collections.abc import Iterable, Iterator

from revolt_ble_toolkit.parsers.att.models import AttOpcode, AttPacket
from revolt_ble_toolkit.parsers.btsnoop.models import HciPacket, HciPacketType

_ATT_CID = 0x0004
_L2CAP_HEADER_LENGTH = 4


class AttParser:
    """Parses ATT PDUs out of a stream of already-parsed :class:`HciPacket`."""

    def parse(self, hci_packets: Iterable[HciPacket]) -> Iterator[AttPacket]:
        for packet in hci_packets:
            if packet.packet_type is not HciPacketType.ACL_DATA or packet.acl is None:
                continue

            # ponytail: assumes one ACL packet = one complete L2CAP PDU (no
            # reassembly of continuation fragments). Fine for typical small
            # ATT PDUs; add per-handle fragment buffering if long
            # reads/writes that span multiple ACL packets show up.
            l2cap = packet.acl.payload
            if len(l2cap) < _L2CAP_HEADER_LENGTH:
                continue

            length, cid = struct.unpack("<HH", l2cap[:_L2CAP_HEADER_LENGTH])
            if cid != _ATT_CID:
                continue

            att_pdu = l2cap[_L2CAP_HEADER_LENGTH : _L2CAP_HEADER_LENGTH + length]
            if not att_pdu:
                continue

            try:
                opcode = AttOpcode(att_pdu[0])
            except ValueError:
                continue

            yield AttPacket(
                hci_number=packet.number,
                timestamp=packet.timestamp,
                direction=packet.direction,
                connection_handle=packet.acl.connection_handle,
                opcode=opcode,
                parameters=att_pdu[1:],
            )
