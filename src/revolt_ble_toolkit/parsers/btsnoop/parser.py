"""Parser for Android BTSnoop HCI capture logs (``btsnoop_hci.log``).

A BTSnoop file is a 16-byte file header followed by a sequence of records,
each a 24-byte header plus variable-length packet data. File and record
headers are big-endian. The packet data is exactly what the H4 UART
transport carries between host and controller: a 1-byte packet-type
indicator followed by the HCI packet itself, whose multi-byte fields
(handles, opcodes, lengths) are little-endian per the Bluetooth Core
Specification.

Only the ACL Data packet header is decoded in this milestone (connection
handle, boundary/broadcast flags). Its payload — an L2CAP frame — is kept
as raw bytes and is not decoded (ATT/GATT analysis is a later milestone).
Command, Event, SCO, and ISO packets are still surfaced as :class:`HciPacket`
instances, just without a type-specific header parsed out.
"""

from __future__ import annotations

import struct
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import BinaryIO

from revolt_ble_toolkit.config.logging_config import get_logger
from revolt_ble_toolkit.core.exceptions import ParsingError
from revolt_ble_toolkit.parsers.btsnoop import constants as c
from revolt_ble_toolkit.parsers.btsnoop.models import (
    AclHeader,
    BtSnoopFileHeader,
    HciPacket,
    HciPacketType,
    PacketDirection,
)

logger = get_logger(__name__)

_UNIX_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


class BtSnoopHciParser:
    """Parses Android BTSnoop HCI capture logs into :class:`HciPacket` objects."""

    def read_header(self, path: str | Path) -> BtSnoopFileHeader:
        """Read and validate just the file header, without parsing any records."""
        path = Path(path)
        with path.open("rb") as stream:
            return self._read_file_header(stream, source=path)

    def parse_file(self, path: str | Path) -> Iterator[HciPacket]:
        """Parse every HCI packet in a BTSnoop capture file, in file order.

        :param path: Path to a ``btsnoop_hci.log`` (or equivalently formatted) file.
        :raises ParsingError: If the file header is invalid, or a record is truncated.
        """
        path = Path(path)
        with path.open("rb") as stream:
            self._read_file_header(stream, source=path)
            yield from self._iter_packets(stream, source=path)

    def _read_file_header(self, stream: BinaryIO, *, source: Path) -> BtSnoopFileHeader:
        header_bytes = stream.read(c.FILE_HEADER_LENGTH)
        if len(header_bytes) < c.FILE_HEADER_LENGTH:
            raise ParsingError(
                f"{source}: file is smaller than the BTSnoop header "
                f"({c.FILE_HEADER_LENGTH} bytes)."
            )

        identification = header_bytes[:8]
        if identification != c.IDENTIFICATION_PATTERN:
            raise ParsingError(f"{source}: not a BTSnoop file (bad identification pattern).")

        version, datalink_type = struct.unpack(">II", header_bytes[8:16])
        if version != c.SUPPORTED_VERSION:
            raise ParsingError(f"{source}: unsupported BTSnoop version {version}.")

        logger.info("Parsed BTSnoop header for %s (datalink_type=%d)", source, datalink_type)
        return BtSnoopFileHeader(
            identification=identification, version=version, datalink_type=datalink_type
        )

    def _iter_packets(self, stream: BinaryIO, *, source: Path) -> Iterator[HciPacket]:
        number = 0
        while True:
            header_bytes = stream.read(c.RECORD_HEADER_LENGTH)
            if not header_bytes:
                return
            if len(header_bytes) < c.RECORD_HEADER_LENGTH:
                raise ParsingError(f"{source}: truncated record header at end of file.")

            original_length, included_length, flags, cumulative_drops, ts_usec = struct.unpack(
                c.RECORD_HEADER_STRUCT, header_bytes
            )

            data = stream.read(included_length)
            if len(data) < included_length:
                raise ParsingError(
                    f"{source}: truncated packet data (expected {included_length} bytes, "
                    f"got {len(data)})."
                )

            number += 1
            try:
                packet = self._build_packet(
                    number=number,
                    original_length=original_length,
                    included_length=included_length,
                    flags=flags,
                    cumulative_drops=cumulative_drops,
                    ts_usec=ts_usec,
                    data=data,
                )
            except OverflowError:
                # A timestamp this far from the real BTSnoop epoch offset can't be
                # represented as a datetime at all; skip just this record rather than
                # aborting a capture that's otherwise fine (same "log and skip"
                # convention as the GATT/ATT malformed-data handling).
                logger.warning(
                    "%s: record #%d has an out-of-range timestamp (ts_usec=%d); skipping it.",
                    source,
                    number,
                    ts_usec,
                )
                continue
            yield packet

    def _build_packet(
        self,
        *,
        number: int,
        original_length: int,
        included_length: int,
        flags: int,
        cumulative_drops: int,
        ts_usec: int,
        data: bytes,
    ) -> HciPacket:
        direction = (
            PacketDirection.CONTROLLER_TO_HOST
            if flags & c.FLAG_DIRECTION_MASK
            else PacketDirection.HOST_TO_CONTROLLER
        )
        packet_type = HciPacketType.from_indicator(data[0]) if data else HciPacketType.UNKNOWN
        acl_header = self._parse_acl_header(data) if packet_type is HciPacketType.ACL_DATA else None

        return HciPacket(
            number=number,
            timestamp=self._to_datetime(ts_usec),
            direction=direction,
            packet_type=packet_type,
            original_length=original_length,
            included_length=included_length,
            cumulative_drops=cumulative_drops,
            data=data,
            acl=acl_header,
        )

    @staticmethod
    def _parse_acl_header(data: bytes) -> AclHeader | None:
        payload = data[1:]  # strip the H4 packet-type indicator byte
        if len(payload) < c.ACL_HEADER_LENGTH:
            logger.warning(
                "ACL packet too short for its header (%d bytes); leaving it unparsed.",
                len(payload),
            )
            return None

        handle_and_flags, data_total_length = struct.unpack("<HH", payload[: c.ACL_HEADER_LENGTH])
        return AclHeader(
            connection_handle=handle_and_flags & c.ACL_HANDLE_MASK,
            packet_boundary_flag=(handle_and_flags >> c.ACL_PB_FLAG_SHIFT) & c.ACL_PB_FLAG_MASK,
            broadcast_flag=(handle_and_flags >> c.ACL_BC_FLAG_SHIFT) & c.ACL_BC_FLAG_MASK,
            data_total_length=data_total_length,
            payload=payload[c.ACL_HEADER_LENGTH :],
        )

    @staticmethod
    def _to_datetime(ts_usec: int) -> datetime:
        unix_usec = ts_usec - c.BTSNOOP_EPOCH_OFFSET_USEC
        return _UNIX_EPOCH + timedelta(microseconds=unix_usec)
