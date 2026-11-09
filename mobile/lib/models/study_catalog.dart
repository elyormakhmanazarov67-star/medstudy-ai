import 'dart:convert';
import 'package:flutter/services.dart';

/// Offline catalog built from original MedStudy AI study summaries and tests.
class StudyCatalog {
  final List<StudySubject> subjects;
  const StudyCatalog(this.subjects);

  factory StudyCatalog.fromJson(Map<String, dynamic> json) {
    final raw = (json['subjects'] as List<dynamic>? ?? []);
    return StudyCatalog(raw
        .map((item) => StudySubject.fromJson(Map<String, dynamic>.from(item as Map)))
        .toList(growable: false));
  }

  static Future<StudyCatalog> load() async {
    final raw = await rootBundle.loadString('assets/data/lessons.json');
    return StudyCatalog.fromJson(jsonDecode(raw) as Map<String, dynamic>);
  }

  int get lessonCount => subjects.fold(0, (n, s) => n + s.lessons.length);
  int get questionCount => subjects.fold(
      0, (n, s) => n + s.lessons.fold(0, (m, l) => m + l.questions.length));

  Iterable<StudyLesson> get lessons sync* {
    for (final subject in subjects) {
      yield* subject.lessons;
    }
  }
}

class StudySubject {
  final String id;
  final String title;
  final List<StudyLesson> lessons;

  const StudySubject({required this.id, required this.title, required this.lessons});

  factory StudySubject.fromJson(Map<String, dynamic> json) {
    return StudySubject(
      id: (json['id'] ?? '').toString(),
      title: (json['title'] ?? '').toString(),
      lessons: (json['lessons'] as List<dynamic>? ?? [])
          .map((item) => StudyLesson.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList(growable: false),
    );
  }
}

class StudyLesson {
  final String id;
  final String title;
  final String focus;
  final List<StudySection> sections;
  final List<StudyQuestion> questions;
  final String reviewStatus;

  const StudyLesson({
    required this.id,
    required this.title,
    required this.focus,
    required this.sections,
    required this.questions,
    required this.reviewStatus,
  });

  factory StudyLesson.fromJson(Map<String, dynamic> json) {
    return StudyLesson(
      id: (json['id'] ?? '').toString(),
      title: (json['title'] ?? '').toString(),
      focus: (json['focus'] ?? '').toString(),
      sections: (json['sections'] as List<dynamic>? ?? [])
          .map((item) => StudySection.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList(growable: false),
      questions: (json['questions'] as List<dynamic>? ?? [])
          .map((item) => StudyQuestion.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList(growable: false),
      reviewStatus: (json['review_status'] ?? '').toString(),
    );
  }

  bool get hasAnatomyDiagram => RegExp(r'^anat_([1-9]|1[0-4])$').hasMatch(id);
  String get diagramAsset => 'assets/illustrations/' + id + '.svg';
  bool get needsReview => reviewStatus.contains('DRAFT');
}

class StudySection {
  final String heading;
  final String body;

  const StudySection({required this.heading, required this.body});

  factory StudySection.fromJson(Map<String, dynamic> json) {
    return StudySection(
      heading: (json['heading'] ?? '').toString(),
      body: (json['body'] ?? '').toString(),
    );
  }
}

class StudyQuestion {
  final String id;
  final String prompt;
  final List<String> options;
  final int answer;
  final String explanation;

  const StudyQuestion({
    required this.id,
    required this.prompt,
    required this.options,
    required this.answer,
    required this.explanation,
  });

  factory StudyQuestion.fromJson(Map<String, dynamic> json) {
    return StudyQuestion(
      id: (json['id'] ?? '').toString(),
      prompt: (json['q'] ?? '').toString(),
      options: (json['options'] as List<dynamic>? ?? [])
          .map((item) => item.toString()).toList(growable: false),
      answer: (json['answer'] as num?)?.toInt() ?? -1,
      explanation: (json['explanation'] ?? '').toString(),
    );
  }
}
