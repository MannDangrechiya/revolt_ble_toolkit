"""Binary layout constants for the BTSnoop file format and HCI framing.

Reference: the BTSnoop file format specification (as implemented by Android's
Bluetooth stack and read by Wireshark's ``btsnoop`` dissector). File and
record headers are big-endian; the encapsulated HCI packet bytes are
little-endian, per the Bluetooth Core Specification.
"""

from __future__ import annotations

# --- File header (16 bytes, big-endian) -----------------------------------

IDENTIFICATION_PATTERN = b"btsnoop\x00"
FILE_HEADER_LENGTH = 16  # 8 (identification) + 4 (version) + 4 (datalink type)
SUPPORTED_VERSION = 1

# --- Record header (24 bytes, big-endian) ---------------------------------
#
# Original Length (u32), Included Length (u32), Flags (u32),
# Cumulative Drops (u32), Timestamp Microseconds (i64).

RECORD_HEADER_LENGTH = 24
RECORD_HEADER_STRUCT = ">IIIIq"

# Flags bit 0: 0 = sent (host -> controller), 1 = received (controller -> host).
FLAG_DIRECTION_MASK = 0b01

# --- Timestamp epoch --------------------------------------------------------
#
# BTSnoop timestamps are microseconds since 0000-01-01T00:00:00Z. This is the
# offset, in microseconds, between that epoch and the Unix epoch
# (1970-01-01T00:00:00Z): subtract it from a record's timestamp to get
# microseconds since the Unix epoch.

BTSNOOP_EPOCH_OFFSET_USEC = 0x00E03AB44A676000

# --- H4 UART transport packet-type indicator ------------------------------
#
# The first byte of every record's data is the H4 packet-type indicator, as
# used by the real UART transport between host and controller.

H4_COMMAND = 0x01
H4_ACL_DATA = 0x02
H4_SCO_DATA = 0x03
H4_EVENT = 0x04
H4_ISO_DATA = 0x05

# --- HCI ACL Data packet header (4 bytes, little-endian) -------------------
#
# Bluetooth Core Specification, Vol 2, Part E: 12-bit connection handle,
# 2-bit packet-boundary flag, 2-bit broadcast flag, packed little-endian into
# 2 bytes, followed by a little-endian 2-byte data length.

ACL_HEADER_LENGTH = 4
ACL_HANDLE_MASK = 0x0FFF
ACL_PB_FLAG_SHIFT = 12
ACL_PB_FLAG_MASK = 0b11
ACL_BC_FLAG_SHIFT = 14
ACL_BC_FLAG_MASK = 0b11
