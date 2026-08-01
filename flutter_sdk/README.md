# revolt_ble_sdk

Flutter BLE client SDK for the Revolt RV400. Built on
[`flutter_blue_plus`](https://pub.dev/packages/flutter_blue_plus); mirrors the
Python toolkit's `revolt_ble_toolkit.live.RevoltLiveClient` — same protocol,
same reconnect behavior, same raw-packets-only philosophy.

**This SDK never parses telemetry.** `RawPacket.value` is always the exact
bytes sent or received. Battery, temperature, GPS, ride mode — interpreting
any of that is the app's job, not the SDK's.

## ⚠️ License requirement

`flutter_blue_plus` requires declaring a license on every connection. This
SDK does **not** default it for you:

```dart
RevoltBleClient(license: License.nonprofit)   // personal / nonprofit / educational use only
RevoltBleClient(license: License.commercial)  // any for-profit use — this is a paid license
```

Get this right for your use case — see the `License` enum's docs and
`flutter_blue_plus`'s own LICENSE file for details.

## Usage

```dart
import 'package:revolt_ble_sdk/revolt_ble_sdk.dart';

final client = RevoltBleClient(license: License.nonprofit);

await client.connect();               // scans for "RV400", connects to the first match
// or: await client.connect(knownMacAddress);

final accepted = await client.authenticate(yourToken); // caller supplies the token — never guessed

client.listen().listen((RawPacket packet) {
  print(packet); // raw bytes, whatever characteristic they came from
});

await client.write(client.controlCharacteristicUuid!, utf8.encode('LOCATION#'));

await client.disconnect();
```

## API

- `connect([remoteId])` — scan-and-connect (by advertised name, default
  `"RV400"`) or connect directly to a known address.
- `authenticate(token)` — writes `PAIR<token>#`, waits for an `ACCEPTED`
  notification. Returns `true`/`false`.
- `listen()` — a broadcast `Stream<RawPacket>` of every notification *and*
  write, exactly as sent/received.
- `write(characteristicUuid, data)` — write raw bytes to any discovered
  characteristic.
- `disconnect()` — disconnects and stops auto-reconnect.

Reconnects automatically on unexpected disconnect (fixed 3s retry delay, no
backoff cap or max-attempts limit — tune `reconnectDelay` if needed).
