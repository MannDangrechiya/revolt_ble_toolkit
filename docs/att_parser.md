# Module 2: ATT Parser

Decodes ATT (Attribute Protocol) PDUs out of `HciPacket` objects produced by
[Module 1](hci_parser.md). Only the opcodes below are detected — anything
else is silently skipped. GATT-level meaning (services, characteristics) is
a later milestone; this module only decodes ATT's own wire format.

## Usage

```python
from revolt_ble_toolkit.parsers.btsnoop import BtSnoopHciParser
from revolt_ble_toolkit.parsers.att import AttParser, AttOpcode

hci_packets = BtSnoopHciParser().parse_file("btsnoop_hci.log")

for att in AttParser().parse(hci_packets):
    print(att.opcode, att.connection_handle, att.attribute_handle, att.value)
```

## Detected opcodes

| Opcode | Value | `attribute_handle` | `value` | `exchanged_mtu` |
|---|---|---|---|---|
| Exchange MTU Request | `0x02` | — | — | ✓ |
| Exchange MTU Response | `0x03` | — | — | ✓ |
| Read Request | `0x0A` | ✓ | — | — |
| Read Response | `0x0B` | — | ✓ | — |
| Write Request | `0x12` | ✓ | ✓ | — |
| Write Command | `0x52` | ✓ | ✓ | — |
| Handle Value Notification | `0x1B` | ✓ | ✓ | — |
| Handle Value Indication | `0x1D` | ✓ | ✓ | — |

`AttPacket` also carries `hci_number`, `timestamp`, `direction`, and
`connection_handle` from the underlying `HciPacket`/`AclHeader`, so a caller
doesn't need to cross-reference back to the HCI layer.

## How it finds ATT

An ACL packet's payload is an L2CAP frame: 2-byte length + 2-byte channel ID
(little-endian), then the data. ATT always uses fixed channel ID `0x0004`.
The parser reads that header, checks the channel ID, and treats the first
byte of what follows as the ATT opcode.

## Known limitation

One ACL packet is assumed to be one complete L2CAP PDU — continuation
fragments (for ATT PDUs too large for a single ACL packet, e.g. long reads)
aren't reassembled. Fine for the opcodes above in typical captures; add
per-connection-handle fragment buffering (keyed off `packet_boundary_flag`)
if that shows up.

## Out of scope

- Reports/summaries over decoded ATT traffic (next milestone)
- GATT semantics (service/characteristic/descriptor interpretation)
- ATT opcodes beyond the list above (e.g. Find Information, error responses)
- L2CAP fragment reassembly
