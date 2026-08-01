/// Flutter BLE client SDK for the Revolt RV400.
///
/// Talks the same protocol the Python toolkit (`revolt_ble_toolkit.live`)
/// reverse-engineered and reconnects/exposes packets the same way — but
/// never parses telemetry. `value` bytes are always handed back raw;
/// interpreting them (battery, temperature, GPS, ...) is left to the app.
library;

export 'package:flutter_blue_plus/flutter_blue_plus.dart' show License;

export 'src/constants.dart';
export 'src/control_characteristic.dart';
export 'src/raw_packet.dart';
export 'src/revolt_ble_client.dart';
