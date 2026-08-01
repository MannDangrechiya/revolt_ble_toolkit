import 'dart:typed_data';

/// Whether a [RawPacket] was received from the device (notify/indicate) or
/// sent to it (write).
enum PacketDirection { notify, write }

/// A single raw BLE packet, exactly as sent or received.
///
/// No telemetry parsing happens here — interpreting [value] (e.g. as a
/// battery percentage) is left entirely to the app. This SDK only exposes
/// what was actually on the wire.
class RawPacket {
  final DateTime timestamp;
  final String characteristicUuid;
  final PacketDirection direction;
  final Uint8List value;

  const RawPacket({
    required this.timestamp,
    required this.characteristicUuid,
    required this.direction,
    required this.value,
  });

  @override
  String toString() =>
      'RawPacket(${direction.name} $characteristicUuid ${value.length}B @ $timestamp)';
}
