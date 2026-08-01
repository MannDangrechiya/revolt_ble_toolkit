import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_blue_plus/flutter_blue_plus.dart';

import 'constants.dart';
import 'control_characteristic.dart';
import 'raw_packet.dart';

/// Thrown for connection, discovery, write, or authentication failures.
class RevoltBleException implements Exception {
  final String message;
  const RevoltBleException(this.message);

  @override
  String toString() => 'RevoltBleException: $message';
}

/// Live BLE client for the Revolt RV400, using `flutter_blue_plus`.
///
/// Mirrors the Python toolkit's `live.RevoltLiveClient`: scans by advertised
/// name, connects, discovers services, subscribes to every notify-capable
/// characteristic, and exposes every packet exactly as sent/received via
/// [listen] — no telemetry parsing (e.g. battery, temperature) happens here,
/// and never will; that interpretation is entirely up to the app.
///
/// [authenticate]'s PAIR handshake *mechanics* are implemented (write
/// `PAIR<token>#`, wait for an `ACCEPTED` notification) but the token itself
/// is never derived or guessed — callers supply whatever their vehicle
/// expects.
class RevoltBleClient {
  /// Advertised-name substring to scan for (case-insensitive).
  final String nameFilter;

  /// `flutter_blue_plus` requires declaring your license for every
  /// connection. This SDK does not default it — see the `License` enum:
  /// `nonprofit` is for personal/nonprofit/educational use only, and
  /// `commercial` is required for any for-profit use. Get this right.
  final License license;

  final Duration reconnectDelay;

  BluetoothDevice? _device;
  String? _controlCharacteristicUuid;
  final Map<String, BluetoothCharacteristic> _characteristicsByUuid = {};
  bool _closing = false;
  final _packets = StreamController<RawPacket>.broadcast();
  final List<StreamSubscription<dynamic>> _subscriptions = [];

  RevoltBleClient({
    required this.license,
    this.nameFilter = 'RV400',
    this.reconnectDelay = const Duration(seconds: 3),
  });

  bool get isConnected => _device?.isConnected ?? false;

  /// The write+notify characteristic used by [authenticate], once discovered.
  String? get controlCharacteristicUuid => _controlCharacteristicUuid;

  /// Scans for nearby BLE devices whose advertised name matches [nameFilter].
  Future<List<ScanResult>> scan({
    Duration timeout = const Duration(seconds: 10),
  }) async {
    await FlutterBluePlus.startScan(timeout: timeout);
    await FlutterBluePlus.isScanning
        .where((scanning) => scanning == false)
        .first;
    return FlutterBluePlus.lastScanResults
        .where(
          (r) =>
              matchesNameFilter(r.advertisementData.advName, nameFilter) ||
              matchesNameFilter(r.device.platformName, nameFilter),
        )
        .toList();
  }

  /// Connects to [remoteId], or scans and connects to the first name match.
  Future<void> connect([String? remoteId]) async {
    final BluetoothDevice device;
    if (remoteId != null) {
      device = BluetoothDevice(remoteId: DeviceIdentifier(remoteId));
    } else {
      final matches = await scan();
      if (matches.isEmpty) {
        throw RevoltBleException('No BLE device found matching "$nameFilter"');
      }
      device = matches.first.device;
    }
    _closing = false;
    await _connectOnce(device);
  }

  Future<void> _connectOnce(BluetoothDevice device) async {
    try {
      await device.connect(license: license);
    } catch (e) {
      throw RevoltBleException('Failed to connect to ${device.remoteId}: $e');
    }
    _device = device;

    _subscriptions.add(
      device.connectionState.listen((state) {
        if (state == BluetoothConnectionState.disconnected && !_closing) {
          unawaited(_reconnect(device));
        }
      }),
    );

    await _discoverAndSubscribe(device);
  }

  Future<void> _discoverAndSubscribe(BluetoothDevice device) async {
    final services = await device.discoverServices();
    _characteristicsByUuid.clear();

    final descriptors = <CharacteristicDescriptor>[];
    for (final service in services) {
      for (final char in service.characteristics) {
        _characteristicsByUuid[char.characteristicUuid.str] = char;
        descriptors.add(
          CharacteristicDescriptor(
            serviceUuid: service.serviceUuid.str,
            characteristicUuid: char.characteristicUuid.str,
            canWrite:
                char.properties.write || char.properties.writeWithoutResponse,
            canNotify: char.properties.notify || char.properties.indicate,
          ),
        );

        if (char.properties.notify || char.properties.indicate) {
          await char.setNotifyValue(true);
          _subscriptions.add(
            char.onValueReceived.listen((data) {
              _emit(
                RawPacket(
                  timestamp: DateTime.now(),
                  characteristicUuid: char.characteristicUuid.str,
                  direction: PacketDirection.notify,
                  value: Uint8List.fromList(data),
                ),
              );
            }),
          );
        }
      }
    }
    _controlCharacteristicUuid = selectControlCharacteristic(descriptors);
  }

  /// Stream of every raw packet (notify and write), exactly as sent/received.
  Stream<RawPacket> listen() => _packets.stream;

  /// Writes [data] to the characteristic identified by [characteristicUuid].
  Future<void> write(
    String characteristicUuid,
    List<int> data, {
    bool withoutResponse = false,
  }) async {
    if (_device == null || !isConnected) {
      throw const RevoltBleException('Not connected');
    }
    final characteristic = _characteristicsByUuid[characteristicUuid];
    if (characteristic == null) {
      throw RevoltBleException('Unknown characteristic $characteristicUuid');
    }
    await characteristic.write(data, withoutResponse: withoutResponse);
    _emit(
      RawPacket(
        timestamp: DateTime.now(),
        characteristicUuid: characteristicUuid,
        direction: PacketDirection.write,
        value: Uint8List.fromList(data),
      ),
    );
  }

  /// Writes the PAIR handshake and waits for an ACCEPTED notification.
  ///
  /// [token] is supplied by the caller — this does not derive or guess it.
  /// Returns true if ACCEPTED arrived within [timeout], false otherwise.
  Future<bool> authenticate(
    String token, {
    Duration timeout = const Duration(seconds: 5),
  }) async {
    final controlUuid = _controlCharacteristicUuid;
    if (controlUuid == null) {
      throw const RevoltBleException(
        'No write+notify control characteristic discovered',
      );
    }

    final accepted = Completer<bool>();
    final subscription = listen().listen((packet) {
      if (packet.characteristicUuid == controlUuid &&
          utf8.decode(packet.value, allowMalformed: true) ==
              kPairAcceptedResponse) {
        if (!accepted.isCompleted) accepted.complete(true);
      }
    });

    try {
      await write(controlUuid, utf8.encode('PAIR$token#'));
      return await accepted.future.timeout(timeout, onTimeout: () => false);
    } finally {
      await subscription.cancel();
    }
  }

  Future<void> _reconnect(BluetoothDevice device) async {
    // ponytail: fixed-delay infinite retry, no backoff cap. Matches the
    // Python client's identical tradeoff — add exponential backoff + a
    // max-attempts limit if this ever hammers a device that's genuinely
    // gone for good rather than briefly out of range.
    while (!_closing) {
      await Future.delayed(reconnectDelay);
      try {
        await _connectOnce(device);
        return;
      } on RevoltBleException {
        // retry
      }
    }
  }

  void _emit(RawPacket packet) {
    if (!_packets.isClosed) _packets.add(packet);
  }

  /// Disconnects and stops all reconnect attempts.
  Future<void> disconnect() async {
    _closing = true;
    for (final subscription in _subscriptions) {
      await subscription.cancel();
    }
    _subscriptions.clear();
    final device = _device;
    if (device != null) {
      await device.disconnect();
    }
  }
}
