"""Reconstructs the GATT hierarchy (services/characteristics/descriptors)
from GATT discovery ATT PDUs.

GATT discovery runs over three ATT PDU types:

- Read By Group Type Response (0x11): primary service handle ranges + UUID.
- Read By Type Response (0x09): characteristic declarations (handle,
  properties, value handle, UUID) — assumes the request was for the
  Characteristic Declaration UUID (0x2803), as real discovery does.
- Find Information Response (0x05): descriptor handles + UUIDs.

Attribute handles are only unique per connection, so records are grouped by
`connection_handle` before characteristics/descriptors are matched to the
service/characteristic whose handle range contains them. Values are not
interpreted here (e.g. what a CCCD's bytes mean) — that's a later milestone.
"""

from __future__ import annotations

import struct
import uuid as uuid_lib
from collections.abc import Iterable
from dataclasses import dataclass, field

from revolt_ble_toolkit.analyzers.gatt.models import (
    Characteristic,
    CharacteristicProperty,
    Descriptor,
    Service,
)
from revolt_ble_toolkit.parsers.att import AttOpcode, AttPacket


def _parse_uuid(data: bytes) -> str:
    if len(data) == 2:
        return f"{int.from_bytes(data, 'little'):04x}"
    if len(data) == 16:
        return str(uuid_lib.UUID(bytes=bytes(reversed(data))))
    return data.hex()  # ponytail: unexpected length, show raw hex rather than guessing


@dataclass
class _ServiceBuilder:
    start_handle: int
    end_handle: int
    uuid: str


@dataclass
class _CharacteristicBuilder:
    declaration_handle: int
    value_handle: int
    uuid: str
    properties: CharacteristicProperty
    descriptors: list[Descriptor] = field(default_factory=list)


class GattAnalyzer:
    """Builds the GATT object model out of a stream of decoded ATT PDUs."""

    def analyze(self, att_packets: Iterable[AttPacket]) -> list[Service]:
        services: dict[int, list[_ServiceBuilder]] = {}
        chars: dict[int, list[_CharacteristicBuilder]] = {}
        descs: dict[int, list[Descriptor]] = {}

        for att in att_packets:
            conn = att.connection_handle
            if att.opcode is AttOpcode.READ_BY_GROUP_TYPE_RESPONSE:
                services.setdefault(conn, []).extend(self._parse_services(att.parameters))
            elif att.opcode is AttOpcode.READ_BY_TYPE_RESPONSE:
                chars.setdefault(conn, []).extend(self._parse_characteristics(att.parameters))
            elif att.opcode is AttOpcode.FIND_INFORMATION_RESPONSE:
                descs.setdefault(conn, []).extend(self._parse_descriptors(att.parameters))

        result: list[Service] = []
        for conn, conn_services in services.items():
            conn_chars = sorted(chars.get(conn, []), key=lambda c: c.declaration_handle)
            conn_descs = sorted(descs.get(conn, []), key=lambda d: d.handle)
            for svc in sorted(conn_services, key=lambda s: s.start_handle):
                svc_chars = [
                    c
                    for c in conn_chars
                    if svc.start_handle <= c.declaration_handle <= svc.end_handle
                ]
                for i, ch in enumerate(svc_chars):
                    upper = (
                        svc_chars[i + 1].declaration_handle - 1
                        if i + 1 < len(svc_chars)
                        else svc.end_handle
                    )
                    ch.descriptors = [
                        d for d in conn_descs if ch.declaration_handle < d.handle <= upper
                    ]
                result.append(
                    Service(
                        connection_handle=conn,
                        start_handle=svc.start_handle,
                        end_handle=svc.end_handle,
                        uuid=svc.uuid,
                        characteristics=tuple(
                            Characteristic(
                                declaration_handle=c.declaration_handle,
                                value_handle=c.value_handle,
                                uuid=c.uuid,
                                properties=c.properties,
                                descriptors=tuple(c.descriptors),
                            )
                            for c in svc_chars
                        ),
                    )
                )
        return result

    @staticmethod
    def _parse_services(data: bytes) -> list[_ServiceBuilder]:
        if not data:
            return []
        entry_length = data[0]
        if entry_length <= 0:
            return []
        body = data[1:]
        results = []
        for i in range(0, len(body) - entry_length + 1, entry_length):
            entry = body[i : i + entry_length]
            start_handle, end_handle = struct.unpack("<HH", entry[:4])
            results.append(
                _ServiceBuilder(
                    start_handle=start_handle, end_handle=end_handle, uuid=_parse_uuid(entry[4:])
                )
            )
        return results

    @staticmethod
    def _parse_characteristics(data: bytes) -> list[_CharacteristicBuilder]:
        if not data:
            return []
        entry_length = data[0]
        if entry_length <= 0:
            return []
        body = data[1:]
        results = []
        for i in range(0, len(body) - entry_length + 1, entry_length):
            entry = body[i : i + entry_length]
            decl_handle, properties, value_handle = struct.unpack("<HBH", entry[:5])
            results.append(
                _CharacteristicBuilder(
                    declaration_handle=decl_handle,
                    value_handle=value_handle,
                    uuid=_parse_uuid(entry[5:]),
                    properties=CharacteristicProperty(properties),
                )
            )
        return results

    @staticmethod
    def _parse_descriptors(data: bytes) -> list[Descriptor]:
        if not data:
            return []
        uuid_length = 2 if data[0] == 1 else 16
        entry_length = 2 + uuid_length
        body = data[1:]
        results = []
        for i in range(0, len(body) - entry_length + 1, entry_length):
            entry = body[i : i + entry_length]
            (handle,) = struct.unpack("<H", entry[:2])
            results.append(Descriptor(handle=handle, uuid=_parse_uuid(entry[2:])))
        return results
