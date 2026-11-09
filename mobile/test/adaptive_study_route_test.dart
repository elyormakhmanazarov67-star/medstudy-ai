import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:medstudy_ai/widgets/adaptive_study_route.dart';

void main() {
  testWidgets('iPhone pages use Cupertino push transitions', (tester) async {
    Route<void>? pushed;
    await tester.pumpWidget(MaterialApp(
      theme: ThemeData(platform: TargetPlatform.iOS),
      home: Builder(builder: (context) => Scaffold(
        body: TextButton(
          onPressed: () {
            pushed = adaptiveStudyRoute<void>(
              context,
              const Scaffold(body: Center(child: Text('Dars'))),
            );
            Navigator.of(context).push(pushed!);
          },
          child: const Text('Open'),
        ),
      )),
    ));
    await tester.tap(find.text('Open'));
    await tester.pumpAndSettle();
    expect(pushed, isA<CupertinoPageRoute<void>>());
    expect(find.text('Dars'), findsOneWidget);
  });

  testWidgets('Android pages keep Material push transitions', (tester) async {
    Route<void>? pushed;
    await tester.pumpWidget(MaterialApp(
      theme: ThemeData(platform: TargetPlatform.android),
      home: Builder(builder: (context) => Scaffold(
        body: TextButton(
          onPressed: () {
            pushed = adaptiveStudyRoute<void>(
              context,
              const Scaffold(body: Center(child: Text('Dars'))),
            );
            Navigator.of(context).push(pushed!);
          },
          child: const Text('Open'),
        ),
      )),
    ));
    await tester.tap(find.text('Open'));
    await tester.pumpAndSettle();
    expect(pushed, isA<MaterialPageRoute<void>>());
    expect(find.text('Dars'), findsOneWidget);
  });
}
