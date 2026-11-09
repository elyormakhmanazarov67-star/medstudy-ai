import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:medstudy_ai/models/study_progress.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('Completed lessons and best scores persist per student account', () async {
    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();
    final first = StudyProgress(prefs, accountKey: '101');
    await first.markRead('anat_1');
    await first.saveQuiz('anat_1', 3);
    await first.saveQuiz('anat_1', 2);

    expect(first.isRead('anat_1'), true);
    expect(first.bestScore('anat_1'), 3);
    expect(prefs.getBool('account:101:read:anat_1'), true);
    expect(prefs.getInt('account:101:best:anat_1'), 3);
    expect(prefs.getBool('read:anat_1'), isNull);
    expect(prefs.getInt('best:anat_1'), isNull);

    final second = StudyProgress(prefs, accountKey: '202');
    expect(second.isRead('anat_1'), false);
    expect(second.bestScore('anat_1'), isNull);
    await second.markRead('anat_2');
    await second.saveQuiz('anat_1', 1);
    expect(first.isRead('anat_2'), false);
    expect(first.bestScore('anat_1'), 3);

    first.dispose();
    second.dispose();
  });
}
