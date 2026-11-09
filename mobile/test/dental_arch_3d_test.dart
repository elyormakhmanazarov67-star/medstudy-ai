import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:medstudy_ai/widgets/dental_arch_3d.dart';

void main() {
  testWidgets('MedStudy AI 3.0 dental arch can rotate and reset',
      (tester) async {
    await tester.pumpWidget(const MaterialApp(home: DentalArch3DPage()));
    expect(find.text('MedStudy AI 3.0 · 3D'), findsOneWidget);
    expect(find.byKey(const Key('dental-arch-3d')), findsOneWidget);
    final original = tester.widget<Text>(find.textContaining('Burilish:')).data;

    await tester.drag(find.byKey(const Key('dental-arch-3d')),
        const Offset(75, 12));
    await tester.pumpAndSettle();
    final rotated = tester.widget<Text>(find.textContaining('Burilish:')).data;
    expect(rotated, isNot(original));

    await tester.tap(find.text('Qayta'));
    await tester.pumpAndSettle();
    final afterReset = tester.widget<Text>(find.textContaining('Burilish:')).data;
    expect(afterReset, original);
  });
}
