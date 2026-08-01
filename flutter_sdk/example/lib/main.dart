import 'dart:async';

import 'package:flutter/material.dart';
import 'package:revolt_ble_sdk/revolt_ble_sdk.dart';

void main() {
  runApp(const RevoltDemoApp());
}

class RevoltDemoApp extends StatelessWidget {
  const RevoltDemoApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Revolt BLE Demo',
      themeMode: ThemeMode.dark,
      darkTheme: ThemeData(
        useMaterial3: true,
        brightness: Brightness.dark,
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.teal,
          brightness: Brightness.dark,
        ),
      ),
      home: const HomePage(),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  RevoltBleClient? _client;
  StreamSubscription<RawPacket>? _subscription;
  bool _connected = false;
  bool _connecting = false;
  int _packetCount = 0;
  final List<RawPacket> _notifications = [];

  Future<void> _connect() async {
    setState(() => _connecting = true);
    final client = RevoltBleClient(license: License.nonprofit);
    try {
      await client.connect();
    } on RevoltBleException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.message)));
      setState(() => _connecting = false);
      return;
    }

    _subscription = client
        .listen()
        .where((packet) => packet.direction == PacketDirection.notify)
        .listen((packet) {
          setState(() {
            _notifications.insert(0, packet);
            _packetCount++;
          });
        });

    setState(() {
      _client = client;
      _connected = true;
      _connecting = false;
    });
  }

  Future<void> _disconnect() async {
    await _subscription?.cancel();
    await _client?.disconnect();
    setState(() {
      _client = null;
      _connected = false;
    });
  }

  @override
  void dispose() {
    _subscription?.cancel();
    _client?.disconnect();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Revolt BLE Demo'),
        actions: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8),
            child: Center(child: Chip(label: Text('$_packetCount packets'))),
          ),
        ],
      ),
      body: Column(
        children: [
          _ConnectionBar(
            connected: _connected,
            connecting: _connecting,
            onConnect: _connect,
            onDisconnect: _disconnect,
          ),
          const Divider(height: 1),
          Expanded(
            child: _notifications.isEmpty
                ? Center(
                    child: Text(
                      _connected
                          ? 'Connected. Waiting for notifications...'
                          : 'Not connected. Tap Connect to begin.',
                      style: Theme.of(context).textTheme.bodyLarge,
                    ),
                  )
                : ListView.builder(
                    padding: const EdgeInsets.all(8),
                    itemCount: _notifications.length,
                    itemBuilder: (context, index) =>
                        _PacketTile(packet: _notifications[index]),
                  ),
          ),
        ],
      ),
    );
  }
}

class _ConnectionBar extends StatelessWidget {
  final bool connected;
  final bool connecting;
  final VoidCallback onConnect;
  final VoidCallback onDisconnect;

  const _ConnectionBar({
    required this.connected,
    required this.connecting,
    required this.onConnect,
    required this.onDisconnect,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(12),
      child: Row(
        children: [
          Icon(
            connected ? Icons.bluetooth_connected : Icons.bluetooth_disabled,
            color: connected ? Colors.greenAccent : Colors.redAccent,
          ),
          const SizedBox(width: 8),
          Text(
            connected ? 'Connected' : 'Disconnected',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const Spacer(),
          if (connecting)
            const SizedBox(
              width: 20,
              height: 20,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          else
            FilledButton(
              onPressed: connected ? onDisconnect : onConnect,
              child: Text(connected ? 'Disconnect' : 'Connect'),
            ),
        ],
      ),
    );
  }
}

class _PacketTile extends StatelessWidget {
  final RawPacket packet;

  const _PacketTile({required this.packet});

  static String _time(DateTime t) {
    String pad(int n, [int width = 2]) => n.toString().padLeft(width, '0');
    return '${pad(t.hour)}:${pad(t.minute)}:${pad(t.second)}.${pad(t.millisecond, 3)}';
  }

  static String _hex(List<int> bytes) => bytes
      .map((b) => b.toRadixString(16).padLeft(2, '0'))
      .join(' ')
      .toUpperCase();

  static String _ascii(List<int> bytes) => bytes
      .map((b) => b >= 32 && b < 127 ? String.fromCharCode(b) : '.')
      .join();

  @override
  Widget build(BuildContext context) {
    final monospace = Theme.of(
      context,
    ).textTheme.bodySmall?.copyWith(fontFamily: 'monospace');
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 4),
      child: Padding(
        padding: const EdgeInsets.all(10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(_time(packet.timestamp), style: monospace),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    packet.characteristicUuid,
                    style: monospace,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Text('Hex:   ${_hex(packet.value)}', style: monospace),
            Text('ASCII: ${_ascii(packet.value)}', style: monospace),
          ],
        ),
      ),
    );
  }
}
