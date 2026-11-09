import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../mobile_api.dart';

/// Account-scoped on-device progress with best-effort server synchronization.
/// Local writes always complete even if the network is unavailable.
class StudyProgress extends ChangeNotifier {
  final SharedPreferences _prefs;
  final String accountKey;
  StudyProgress(this._prefs, {required this.accountKey});

  String key(String label, String id) => 'account:' + accountKey + ':' + label + ':' + id;

  bool isRead(String lessonId) => _prefs.getBool(key('read', lessonId)) ?? false;
  int? bestScore(String lessonId) => _prefs.getInt(key('best', lessonId));

  Future<void> markRead(String lessonId) async {
    await _prefs.setBool(key('read', lessonId), true);
    notifyListeners();
    await _push(lessonId);
  }

  Future<void> saveQuiz(String lessonId, int correct) async {
    if (correct < 0) return;
    final previous = bestScore(lessonId) ?? -1;
    if (correct > previous) {
      await _prefs.setInt(key('best', lessonId), correct);
      notifyListeners();
    }
    await _push(lessonId);
  }

  Future<void> _push(String lessonId) async {
    try {
      await MobileApi.putProgress(
        lessonId: lessonId,
        read: isRead(lessonId),
        bestScore: bestScore(lessonId),
      );
    } catch (_) {
      // The previous staging server does not yet have /progress.
      // Keep local progress; retry the upload on the next successful sync.
    }
  }

  Future<bool> syncWithServer(Iterable<String> lessonIds) async {
    try {
      final allowed = lessonIds.toSet();
      final serverItems = await MobileApi.getProgress();
      final remoteById = <String, Map<String, dynamic>>{};
      for (final item in serverItems) {
        final id = item['lesson_id'];
        if (id is String && allowed.contains(id)) remoteById[id] = item;
      }
      var changed = false;
      for (final lessonId in allowed) {
        final remote = remoteById[lessonId];
        final remoteRead = remote?['read'] == true;
        final rawScore = remote?['best_score'];
        final remoteScore = rawScore is int && rawScore >= 0 ? rawScore : null;
        final localRead = isRead(lessonId);
        final localScore = bestScore(lessonId);
        if (remoteRead && !localRead) {
          await _prefs.setBool(key('read', lessonId), true);
          changed = true;
        }
        if (remoteScore != null && (localScore == null || remoteScore > localScore)) {
          await _prefs.setInt(key('best', lessonId), remoteScore);
          changed = true;
        }
      }
      if (changed) notifyListeners();

      // Merge uses monotonic "read OR" and "maximum score" semantics.
      // Upload only the local values missing from the server.
      for (final lessonId in allowed) {
        final remote = remoteById[lessonId];
        final read = isRead(lessonId);
        final score = bestScore(lessonId);
        final remoteScore = remote?['best_score'];
        final remoteRead = remote?['read'] == true;
        if ((read && !remoteRead) ||
            (score != null && (remoteScore is! int || score > remoteScore))) {
          await _push(lessonId);
        }
      }
      return true;
    } catch (_) {
      return false; // Offline and pre-v3 servers retain on-device progress.
    }
  }

  int completedIn(List<String> lessonIds) => lessonIds.where(isRead).length;
}
