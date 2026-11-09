import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// On-device progress for the first offline build; not synced across devices.
class StudyProgress extends ChangeNotifier {
  final SharedPreferences _prefs;
  StudyProgress(this._prefs);

  bool isRead(String lessonId) => _prefs.getBool('read:' + lessonId) ?? false;
  int? bestScore(String lessonId) => _prefs.getInt('best:' + lessonId);

  Future<void> markRead(String lessonId) async {
    await _prefs.setBool('read:' + lessonId, true);
    notifyListeners();
  }

  Future<void> saveQuiz(String lessonId, int correct) async {
    final previous = bestScore(lessonId) ?? -1;
    if (correct > previous) {
      await _prefs.setInt('best:' + lessonId, correct);
      notifyListeners();
    }
  }

  int completedIn(List<String> lessonIds) =>
      lessonIds.where(isRead).length;
}
