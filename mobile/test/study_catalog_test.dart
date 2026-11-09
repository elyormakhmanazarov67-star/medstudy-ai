import 'dart:convert';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:medstudy_ai/models/study_catalog.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('Restored curriculum contains 81 lessons and 631 questions', () async {
    final raw = await rootBundle.loadString('assets/data/lessons.json');
    final catalog = StudyCatalog.fromJson(jsonDecode(raw) as Map<String, dynamic>);
    expect(catalog.subjects.length, 6);
    expect(catalog.lessonCount, 81);
    expect(catalog.questionCount, 631);
    final anatomy = catalog.subjects.firstWhere((x) => x.id == 'odam_anatomiyasi_1');
    expect(anatomy.lessons.length, 14);
    expect(anatomy.lessons.every((lesson) => lesson.hasAnatomyDiagram), isTrue);
    expect(catalog.subjects.every((s) => s.lessons.every((l) => l.questions.every(
      (q) => q.answer >= 0 && q.answer < q.options.length))), isTrue);
  });
}
