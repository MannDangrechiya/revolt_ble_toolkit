# Module 1: BTSnoop HCI Parser

Parses Android `btsnoop_hci.log` capture files into typed Python objects.
No protocol analysis above HCI is performed — ACL payloads (L2CAP/ATT/GATT)
are kept as raw bytes for a later milestone.

## Usage

```python
from revolt_ble_toolkit.parsers.btsnoop import BtSnoopHciParser, HciPacketType

parser = BtSnoopHciParser()

# Inspect just the file header, without parsing every record.
header = parser.read_header("btsnoop_hci.log")
print(header.version, header.datalink_type)

# Stream every packet, in file order.
for packet in parser.parse_file("btsnoop_hci.log"):
    print(packet.number, packet.timestamp, packet.direction, packet.packet_type)
    if packet.packet_type is HciPacketType.ACL_DATA and packet.acl is not None:
        print("  handle:", packet.acl.connection_handle)
```

`parse_file` is a generator — packets are yielded one at a time rather than
loaded into memory all at once, so it scales to large capture files.

## What gets parsed

For every packet:

| Field | Description |
|---|---|
| `number` | 1-indexed sequence number, in file order |
| `timestamp` | `datetime` (UTC), converted from the BTSnoop epoch |
| `direction` | `PacketDirection.HOST_TO_CONTROLLER` or `.CONTROLLER_TO_HOST` |
| `packet_type` | `HciPacketType.COMMAND` / `ACL_DATA` / `SCO_DATA` / `EVENT` / `ISO_DATA` / `UNKNOWN` |
| `original_length` | Length of the packet as originally captured |
| `included_length` | Length actually present in the file (may be less, if truncated) |
| `is_truncated` | `True` if `included_length < original_length` |
| `cumulative_drops` | Packets dropped before this one, per the BTSnoop record header |
| `data` | Raw record bytes, including the leading H4 packet-type indicator |

Additionally, for ACL Data packets (`packet.acl`, otherwise `None`):

| Field | Description |
|---|---|
| `connection_handle` | 12-bit connection handle |
| `packet_boundary_flag` | 2-bit PB flag (fragmentation state) |
| `broadcast_flag` | 2-bit BC flag |
| `data_total_length` | Declared length of `payload` |
| `payload` | Raw ACL data (an L2CAP frame) — **not decoded** |

Command, Event, SCO, and ISO packets are surfaced as `HciPacket` too, just
without a type-specific header parsed out yet.

## Format notes (the non-obvious parts)

- **Mixed byte order.** The BTSnoop file header and each 24-byte record
  header are big-endian. The HCI packet bytes they wrap are little-endian,
  per the Bluetooth Core Specification. Getting this backwards silently
  produces wrong-looking-but-plausible connection handles.
- **Timestamp epoch.** BTSnoop timestamps are microseconds since
  `0000-01-01T00:00:00Z`, not the Unix epoch. Converting requires
  subtracting a fixed offset (`BTSNOOP_EPOCH_OFFSET_USEC` in
  [`constants.py`](../src/revolt_ble_toolkit/parsers/btsnoop/constants.py))
  before adding the result to `1970-01-01`.
- **Direction bit.** Record header flag bit 0: `0` = sent (host → controller),
  `1` = received (controller → host). "Sent"/"received" are relative to the
  host, which is why this parser exposes the less ambiguous
  `HOST_TO_CONTROLLER` / `CONTROLLER_TO_HOST` instead.
- **The H4 indicator, not the flags, determines packet type.** The record
  header's flag bit 1 only distinguishes "data" from "command/event"
  broadly; the actual packet type comes from the first byte of `data` (the
  H4 UART indicator: `0x01` Command, `0x02` ACL, `0x03` SCO, `0x04` Event,
  `0x05` ISO).
- **Truncated captures are tolerated, not fatal.** If `included_length` is
  legitimately less than `original_length` (the OS/tooling only captured a
  prefix), that's normal and reflected in `is_truncated`. It's only a
  `ParsingError` if the file itself doesn't contain the bytes a record's
  own header says it should.

## Error handling

`BtSnoopHciParser` raises `revolt_ble_toolkit.core.exceptions.ParsingError`
for structural problems: a missing/wrong identification pattern, an
unsupported version, or a file that ends in the middle of a record header
or a record's data. A malformed ACL header (fewer than 4 bytes after the H4
indicator) is logged as a warning and leaves `packet.acl` as `None` rather
than raising, since it doesn't prevent the rest of the file from being read.

## Out of scope (future milestones)

- Decoding ACL payloads as L2CAP, then ATT/GATT
- Type-specific headers for Command/Event/SCO/ISO packets
- Reassembling fragmented ACL packets (using `packet_boundary_flag`)
