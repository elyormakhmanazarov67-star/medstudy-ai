import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:medstudy_ai/widgets/adaptive_study_navigation.dart';

void main() {
  testWidgets('iPhone uses Cupertino tab bar with four learning tabs',
      (tester) async {
    final taps = <int>[];
    await tester.pumpWidget(MaterialApp(
      theme: ThemeData(platform: TargetPlatform.iOS),
      home: Scaffold(
        bottomNavigationBar:
            AdaptiveStudyNavigation(selectedIndex: 0, onSelected: taps.add),
      ),
    ));

    expect(find.byType(CupertinoTabBar), findsOneWidget);
    expect(find.byType(NavigationBar), findsNothing);
    expect(find.text('Asosiy'), findsOneWidget);
    expect(find.text('Fanlar'), findsOneWidget);
    expect(find.text('Natija'), findsOneWidget);
    expect(find.text('Sozlama'), findsOneWidget);

    await tester.tap(find.text('Fanlar'));
    await tester.pump();
    expect(taps, [1]);
  });

  testWidgets('Android preserves Material navigation', (tester) async {
    final taps = <int>[];
    await tester.pumpWidget(MaterialApp(
      theme: ThemeData(platform: TargetPlatform.android),
      home: Scaffold(
        bottomNavigationBar:
            AdaptiveStudyNavigation(selectedIndex: 1, onSelected: taps.add),
      ),
    ));

    expect(find.byType(CupertinoTabBar), findsNothing);
    expect(find.byType(NavigationBar), findsOneWidget);
    await tester.tap(find.text('Natija'));
    await tester.pump();
    expect(taps, [2]);
  });
}
