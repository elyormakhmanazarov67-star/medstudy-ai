import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:medstudy_ai/widgets/adaptive_account_buttons.dart';

void main() {
  testWidgets('iPhone uses Cupertino controls for student account actions',
      (tester) async {
    var submitted = 0;
    var switched = 0;
    await tester.pumpWidget(MaterialApp(
      theme: ThemeData(platform: TargetPlatform.iOS),
      home: Scaffold(
        body: Column(children: [
          AdaptiveAccountPrimaryButton(
            label: 'Ro‘yxatdan o‘tish',
            icon: Icons.person_add,
            onPressed: () => submitted++,
          ),
          AdaptiveAccountSecondaryButton(
            label: 'Akkauntim bor',
            onPressed: () => switched++,
          ),
        ]),
      ),
    ));
    expect(find.byType(CupertinoButton), findsNWidgets(2));
    expect(find.byType(FilledButton), findsNothing);
    await tester.tap(find.text('Ro‘yxatdan o‘tish'));
    await tester.tap(find.text('Akkauntim bor'));
    expect(submitted, 1);
    expect(switched, 1);
  });

  testWidgets('Android retains its Material student account buttons',
      (tester) async {
    var submitted = 0;
    await tester.pumpWidget(MaterialApp(
      theme: ThemeData(platform: TargetPlatform.android),
      home: Scaffold(body: Column(children: [
        AdaptiveAccountPrimaryButton(
          label: 'Kirish', icon: Icons.login,
          onPressed: () => submitted++,
        ),
        const AdaptiveAccountSecondaryButton(
          label: 'Yangi akkaunt yaratish',
          onPressed: null,
        ),
      ])),
    ));
    expect(find.byType(FilledButton), findsOneWidget);
    expect(find.byType(TextButton), findsOneWidget);
    await tester.tap(find.text('Kirish'));
    expect(submitted, 1);
    expect(tester.widget<TextButton>(find.byType(TextButton)).onPressed, isNull);
  });
}
