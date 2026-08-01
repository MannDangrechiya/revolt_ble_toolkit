import 'constants.dart';

/// A minimal, plugin-independent description of one discovered characteristic.
///
/// Kept separate from `flutter_blue_plus`'s own types so the selection logic
/// in [selectControlCharacteristic] can be unit-tested without a real BLE
/// plugin/platform channel.
class CharacteristicDescriptor {
  final String serviceUuid;
  final String characteristicUuid;
  final bool canWrite;
  final bool canNotify;

  const CharacteristicDescriptor({
    required this.serviceUuid,
    required this.characteristicUuid,
    required this.canWrite,
    required this.canNotify,
  });
}

/// Picks the write+notify control characteristic used for [authenticate]/
/// [write]: prefers the empirically verified
/// [kVehicleControlCharacteristicUuid] and falls back to the first
/// write+notify characteristic within the known
/// [kVehicleControlServiceUuid] if a different firmware doesn't have it.
/// Returns null if neither is found.
String? selectControlCharacteristic(
  List<CharacteristicDescriptor> characteristics,
) {
  CharacteristicDescriptor? fallback;
  for (final c in characteristics) {
    if (c.characteristicUuid.toLowerCase() ==
        kVehicleControlCharacteristicUuid) {
      return c.characteristicUuid;
    }
    if (fallback == null &&
        c.serviceUuid.toLowerCase() == kVehicleControlServiceUuid &&
        c.canWrite &&
        c.canNotify) {
      fallback = c;
    }
  }
  return fallback?.characteristicUuid;
}

/// Whether an advertised device name matches [nameFilter] (case-insensitive
/// substring match), for identifying the RV400 during scanning.
bool matchesNameFilter(String? advertisedName, String nameFilter) {
  if (advertisedName == null || advertisedName.isEmpty) return false;
  return advertisedName.toLowerCase().contains(nameFilter.toLowerCase());
}
