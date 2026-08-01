import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:revolt_ble_sdk/revolt_ble_sdk.dart';

void main() {
  group('matchesNameFilter', () {
    test('matches a case-insensitive substring', () {
      expect(matchesNameFilter('RV400-1234', 'rv400'), isTrue);
      expect(matchesNameFilter('rv400-1234', 'RV400'), isTrue);
    });

    test('rejects a non-matching name', () {
      expect(matchesNameFilter('Some Other Device', 'RV400'), isFalse);
    });

    test('rejects null or empty advertised names', () {
      expect(matchesNameFilter(null, 'RV400'), isFalse);
      expect(matchesNameFilter('', 'RV400'), isFalse);
    });
  });

  group('selectControlCharacteristic', () {
    test('prefers the known control characteristic when present', () {
      final descriptors = [
        const CharacteristicDescriptor(
          serviceUuid: kVehicleControlServiceUuid,
          characteristicUuid: '11111111-2222-3333-4444-555555555555',
          canWrite: true,
          canNotify: true,
        ),
        const CharacteristicDescriptor(
          serviceUuid: kVehicleControlServiceUuid,
          characteristicUuid: kVehicleControlCharacteristicUuid,
          canWrite: true,
          canNotify: true,
        ),
      ];

      expect(
        selectControlCharacteristic(descriptors),
        kVehicleControlCharacteristicUuid,
      );
    });

    test(
      'falls back to the first write+notify characteristic in the known service',
      () {
        const differentUuid = '99999999-8888-7777-6666-555555555555';
        final descriptors = [
          const CharacteristicDescriptor(
            serviceUuid: kVehicleControlServiceUuid,
            characteristicUuid: differentUuid,
            canWrite: true,
            canNotify: true,
          ),
        ];

        expect(selectControlCharacteristic(descriptors), differentUuid);
      },
    );

    test(
      'ignores write-only or notify-only characteristics as fallback candidates',
      () {
        final descriptors = [
          const CharacteristicDescriptor(
            serviceUuid: kVehicleControlServiceUuid,
            characteristicUuid: 'write-only',
            canWrite: true,
            canNotify: false,
          ),
          const CharacteristicDescriptor(
            serviceUuid: kVehicleControlServiceUuid,
            characteristicUuid: 'notify-only',
            canWrite: false,
            canNotify: true,
          ),
        ];

        expect(selectControlCharacteristic(descriptors), isNull);
      },
    );

    test('ignores write+notify characteristics outside the known service', () {
      final descriptors = [
        const CharacteristicDescriptor(
          serviceUuid: 'unrelated-service',
          characteristicUuid: 'unrelated-char',
          canWrite: true,
          canNotify: true,
        ),
      ];

      expect(selectControlCharacteristic(descriptors), isNull);
    });

    test('returns null when no characteristics are given', () {
      expect(selectControlCharacteristic(const []), isNull);
    });
  });

  group('RawPacket', () {
    test('toString includes direction, characteristic, and size', () {
      final packet = RawPacket(
        timestamp: DateTime.utc(2024, 1, 1),
        characteristicUuid: kVehicleControlCharacteristicUuid,
        direction: PacketDirection.notify,
        value: Uint8List.fromList([1, 2, 3]),
      );

      final text = packet.toString();
      expect(text, contains('notify'));
      expect(text, contains(kVehicleControlCharacteristicUuid));
      expect(text, contains('3B'));
    });
  });
}
