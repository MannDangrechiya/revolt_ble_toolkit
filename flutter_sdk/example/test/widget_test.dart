import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:revolt_ble_sdk_example/main.dart';

void main() {
  testWidgets('shows disconnected state and a Connect button on launch', (
    tester,
  ) async {
    await tester.pumpWidget(const RevoltDemoApp());

    expect(find.text('Disconnected'), findsOneWidget);
    expect(find.widgetWithText(FilledButton, 'Connect'), findsOneWidget);
    expect(find.text('0 packets'), findsOneWidget);
    expect(find.text('Not connected. Tap Connect to begin.'), findsOneWidget);
  });

  testWidgets('uses a dark theme', (tester) async {
    await tester.pumpWidget(const RevoltDemoApp());

    final MaterialApp app = tester.widget(find.byType(MaterialApp));
    expect(app.themeMode, ThemeMode.dark);
    expect(app.darkTheme?.brightness, Brightness.dark);
  });
}
