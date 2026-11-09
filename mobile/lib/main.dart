import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'models/study_catalog.dart';
import 'mobile_api.dart';
import 'mobile_account.dart';
import 'widgets/authorized_diagram.dart';
import 'widgets/adaptive_study_navigation.dart';
import 'widgets/dental_arch_3d.dart';
import 'models/study_progress.dart';

const green = Color(0xFF20844D);

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final prefs = await SharedPreferences.getInstance();
  runApp(MedStudyRoot(prefs: prefs));
}

class MedStudyRoot extends StatefulWidget {
  final SharedPreferences prefs;
  const MedStudyRoot({super.key, required this.prefs});
  @override
  State<MedStudyRoot> createState() => _MedStudyRootState();
}

class _MedStudyRootState extends State<MedStudyRoot> with WidgetsBindingObserver {
  late bool dark = widget.prefs.getBool('dark_theme') ?? false;
  StudyCatalog? catalog;
  StudyProgress? progress;
  String? accountId;
  Map<String, dynamic>? accountDetails;
  String? notice;
  final GlobalKey<NavigatorState> navigator = GlobalKey<NavigatorState>();
  bool checking = true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    checkAccess();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    progress?.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) checkAccess();
  }

  Future<void> checkAccess() async {
    if (!mounted) return;
    setState(() { checking = true; catalog = null; notice = null; });
    try {
      final account = await MobileApi.me();
      final nextCatalog = await MobileApi.catalog();
      if (!mounted) return;
      final userId = account['id'].toString();
      if (accountId != userId) {
        progress?.dispose();
        progress = StudyProgress(widget.prefs, accountKey: userId);
        accountId = userId;
      }
      setState(() {
        catalog = nextCatalog;
        accountDetails = account;
        checking = false;
      });
      unawaited(progress!.syncWithServer(
        nextCatalog.lessons.map((lesson) => lesson.id),
      ).then((_) {}));
    } on MobileApiException catch (error) {
      if (error.status == 401 || error.status == 403) {
        await MobileApi.clearToken();
      }
      if (!mounted) return;
      navigator.currentState?.popUntil((route) => route.isFirst);
      setState(() { catalog = null; accountDetails = null; checking = false; notice = error.message; });
    } catch (_) {
      if (!mounted) return;
      navigator.currentState?.popUntil((route) => route.isFirst);
      setState(() {
        catalog = null;
        accountDetails = null;
        checking = false;
        notice = 'Serverga ulanib bo‘lmadi. Internetni tekshirib, qayta kiring.';
      });
    }
  }

  void setDark(bool enabled) {
    setState(() => dark = enabled);
    widget.prefs.setBool('dark_theme', enabled);
  }

  ThemeData createTheme(Brightness brightness) => ThemeData(
    useMaterial3: true,
    colorScheme: ColorScheme.fromSeed(seedColor: green, brightness: brightness),
    appBarTheme: AppBarTheme(
      centerTitle: defaultTargetPlatform == TargetPlatform.iOS,
      scrolledUnderElevation: 0,
    ),
    scaffoldBackgroundColor: brightness == Brightness.dark
        ? const Color(0xFF111B14) : const Color(0xFFF2F8F3),
  );

  @override
  Widget build(BuildContext context) => MaterialApp(
    navigatorKey: navigator,
    title: 'MedStudy AI 3.0',
    debugShowCheckedModeBanner: false,
    theme: createTheme(Brightness.light),
    darkTheme: createTheme(Brightness.dark),
    themeMode: dark ? ThemeMode.dark : ThemeMode.light,
    home: checking
      ? const Scaffold(body: Center(child: CircularProgressIndicator()))
      : catalog == null || progress == null
        ? MobileAccountPage(onAuthChanged: checkAccess, notice: notice)
        : HomePage(catalog: catalog!, progress: progress!, dark: dark,
            account: accountDetails ?? const <String, dynamic>{},
            onTheme: setDark, onAuthChanged: checkAccess),
  );
}

class HomePage extends StatefulWidget {
  final StudyCatalog catalog;
  final StudyProgress progress;
  final Map<String, dynamic> account;
  final bool dark;
  final ValueChanged<bool> onTheme;
  final Future<void> Function() onAuthChanged;
  const HomePage({super.key, required this.catalog, required this.progress,
      required this.account, required this.dark, required this.onTheme,
      required this.onAuthChanged});
  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  int tab = 0;
  @override
  Widget build(BuildContext context) {
    const headings = ['Bosh sahifa', 'Fanlar', 'Natijalar', 'Sozlamalar'];
    return AnimatedBuilder(
      animation: widget.progress,
      builder: (context, _) => Scaffold(
        appBar: AppBar(title: Text(headings[tab],
            style: const TextStyle(fontWeight: FontWeight.bold))),
        bottomNavigationBar: AdaptiveStudyNavigation(
          selectedIndex: tab,
          onSelected: (index) => setState(() => tab = index),
        ),
        body: SafeArea(child: switch (tab) {
          0 => homeContent(),
          1 => subjectList(),
          2 => progressContent(),
          _ => settingsContent(),
        }),
      ),
    );
  }

  List<String> get lessonIds => widget.catalog.subjects
      .expand((s) => s.lessons.map((l) => l.id)).toList();

  Widget homeContent() {
    final count = widget.progress.completedIn(lessonIds);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Container(
        padding: const EdgeInsets.all(22),

        decoration: BoxDecoration(
          gradient: const LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Color(0xFF0C3829), Color(0xFF166B3D), Color(0xFF2B9860)],
          ),
          boxShadow: [
            BoxShadow(
              color: const Color(0xFF166B3D).withValues(alpha: 0.23),
              blurRadius: 20,
              offset: const Offset(0, 10),
            ),
          ],
          borderRadius: BorderRadius.circular(22),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('MEDSTUDY AI 3.0 · BETA', style: TextStyle(color: Color(0xFFBCEBCB),
              letterSpacing: 2, fontWeight: FontWeight.bold)),
          const SizedBox(height: 12),
          const Text('Bilim sari har kuni bir qadam',
              style: TextStyle(fontSize: 24, color: Colors.white, fontWeight: FontWeight.bold)),
          const SizedBox(height: 10),
          const Text('Tibbiyot talabalari uchun o‘quv ilovasi',
              style: TextStyle(color: Colors.white70)),
          const SizedBox(height: 18),
          LinearProgressIndicator(
            value: widget.catalog.lessonCount == 0 ? 0 : count / widget.catalog.lessonCount,
            color: const Color(0xFFBCEBCB), backgroundColor: const Color(0xFF438D63)),
          const SizedBox(height: 7),
          Text('O‘qilgan dars: ' + count.toString() + ' / ' +
              widget.catalog.lessonCount.toString(),
              style: const TextStyle(color: Colors.white)),
        ]),
      ),
      const SizedBox(height: 22),
      Card(
        clipBehavior: Clip.antiAlias,
        child: ListTile(
          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          leading: const CircleAvatar(
            backgroundColor: Color(0xFFDEF8E9),
            child: Icon(Icons.threed_rotation, color: Color(0xFF166B3D)),
          ),
          title: const Text('3D stomatologiya', style: TextStyle(fontWeight: FontWeight.bold)),
          subtitle: const Text('Interaktiv tish qatori maketi · Aylantirish va kattalashtirish'),
          trailing: const Icon(Icons.arrow_forward_ios, size: 18),
          onTap: () => Navigator.push(context,
            MaterialPageRoute<void>(builder: (_) => const DentalArch3DPage())),
        ),
      ),
      const SizedBox(height: 22),
      const Text('Fanlar', style: TextStyle(fontSize: 21, fontWeight: FontWeight.bold)),
      const SizedBox(height: 12),
      ...widget.catalog.subjects.map(subjectTile),
      const SizedBox(height: 12),
      const Text('Eslatma: ayrim darslar mutaxassis tekshiruviga muhtoj. Klinik maslahat emas.',
          style: TextStyle(fontSize: 12)),
    ]);
  }

  Widget subjectList() => ListView(padding: const EdgeInsets.all(16), children: [
    Text(widget.catalog.subjects.length.toString() + ' fan · ' +
        widget.catalog.lessonCount.toString() + ' dars · ' +
        widget.catalog.questionCount.toString() + ' savol'),
    const SizedBox(height: 18),
    ...widget.catalog.subjects.map(subjectTile),
  ]);

  Widget subjectTile(StudySubject subject) {
    final completed = widget.progress.completedIn(
        subject.lessons.map((l) => l.id).toList());
    return Card(child: ListTile(
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      leading: const CircleAvatar(child: Icon(Icons.auto_stories_outlined)),
      title: Text(subject.title, style: const TextStyle(fontWeight: FontWeight.bold)),
      subtitle: Text(subject.lessons.length.toString() + ' mavzu · ' +
          completed.toString() + ' o‘qilgan'),
      trailing: const Icon(Icons.chevron_right),
      onTap: () => Navigator.push(context, MaterialPageRoute<void>(
          builder: (_) => SubjectPage(subject: subject, progress: widget.progress))),
    ));
  }

  Widget progressContent() => ListView(padding: const EdgeInsets.all(16), children: [
    const Text('Mening natijalarim',
        style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
    const SizedBox(height: 8),
    const Text('Natijalar hozircha faqat shu telefonda saqlanadi.'),
    const SizedBox(height: 15),
    ...widget.catalog.subjects.map((s) {
      final completed = widget.progress.completedIn(s.lessons.map((l) => l.id).toList());
      return Card(child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(s.title, style: const TextStyle(fontWeight: FontWeight.bold)),
          const SizedBox(height: 10),
          LinearProgressIndicator(value: s.lessons.isEmpty ? 0 : completed / s.lessons.length),
          const SizedBox(height: 7),
          Text(completed.toString() + ' / ' + s.lessons.length.toString() + ' mavzu'),
          ...s.lessons.where((l) => widget.progress.bestScore(l.id) != null).map((l) =>
            Padding(padding: const EdgeInsets.only(top: 7),
              child: Text(l.title + ': ' +
                  widget.progress.bestScore(l.id).toString() + ' / ' +
                  l.questions.length.toString(),
                  maxLines: 2, overflow: TextOverflow.ellipsis))),
        ]),
      ));
    }),
  ]);

  Widget settingsContent() => ListView(padding: const EdgeInsets.all(16), children: [
    Card(child: ListTile(
      leading: const CircleAvatar(child: Icon(Icons.person)),
      title: Text(widget.account['display_name']?.toString() ?? 'Talaba'),
      subtitle: Text(widget.account['email']?.toString() ?? ''),
    )),
    Card(child: ListTile(
      leading: const Icon(Icons.person_outline),
      title: const Text('Talaba kabineti'),
      subtitle: const Text('Ro‘yxatdan o‘tish yoki akkauntga kirish'),
      trailing: const Icon(Icons.chevron_right),
      onTap: () => Navigator.push(context, MaterialPageRoute<void>(builder: (_) => MobileAccountPage(onAuthChanged: widget.onAuthChanged))),
    )),
    Card(child: SwitchListTile(
      title: const Text('Qora-yashil rejim'),
      subtitle: const Text('Oq-yashil yoki qora-yashil dizayn'),
      secondary: const Icon(Icons.dark_mode_outlined),
      value: widget.dark,
      onChanged: widget.onTheme,
    )),
    Card(child: ListTile(
      leading: Icon(Theme.of(context).platform == TargetPlatform.iOS
          ? Icons.phone_iphone_outlined : Icons.phone_android_outlined),
      title: const Text('MedStudy AI 3.0 · Beta'),
      subtitle: const Text('Android · 3D ta’lim · AI Ustoz va Pro keyingi bosqichda.'),
    )),
    const Card(child: ListTile(
      leading: Icon(Icons.privacy_tip_outlined),
      title: Text('Maxfiylik'),
      subtitle: Text('Natijalar qurilmada saqlanadi; server sinxronizatsiyasi beta bosqichida.'),
    )),
  ]);
}

class SubjectPage extends StatelessWidget {
  final StudySubject subject;
  final StudyProgress progress;
  const SubjectPage({super.key, required this.subject, required this.progress});
  @override
  Widget build(BuildContext context) => AnimatedBuilder(
    animation: progress,
    builder: (context, _) => Scaffold(
      appBar: AppBar(title: Text(subject.title)),
      body: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: subject.lessons.length,
        itemBuilder: (context, i) {
          final lesson = subject.lessons[i];
          return Card(child: ListTile(
            leading: CircleAvatar(child: progress.isRead(lesson.id)
                ? const Icon(Icons.check) : Text((i + 1).toString())),
            title: Text(lesson.title, style: const TextStyle(fontWeight: FontWeight.bold)),
            subtitle: Text(lesson.questions.length.toString() +
                ' test' + (lesson.hasAnatomyDiagram ? ' · rasmli dars' : '')),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => Navigator.push(context, MaterialPageRoute<void>(
                builder: (_) => LessonPage(lesson: lesson, progress: progress))),
          ));
        },
      ),
    ),
  );
}

class LessonPage extends StatelessWidget {
  final StudyLesson lesson;
  final StudyProgress progress;
  const LessonPage({super.key, required this.lesson, required this.progress});
  @override
  Widget build(BuildContext context) => AnimatedBuilder(
    animation: progress,
    builder: (context, _) => Scaffold(
      appBar: AppBar(title: const Text('Dars')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        Text(lesson.title, style: const TextStyle(fontSize: 23, fontWeight: FontWeight.bold)),
        const SizedBox(height: 14),
        if (lesson.needsReview) const Card(child: Padding(
          padding: EdgeInsets.all(14),
          child: Text('Dars matni o‘qituvchi yoki mutaxassis tekshiruviga muhtoj.',
              style: TextStyle(fontSize: 13)),
        )),
        if (lesson.hasAnatomyDiagram) Card(child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('Rasm orqali tushuntirish',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            AuthorizedDiagram(lessonId: lesson.id),
          ]),
        )),
        if (lesson.sections.isEmpty) const Card(child: Padding(
          padding: EdgeInsets.all(16), child: Text('Matn hali kiritilmagan.'),
        )),
        ...lesson.sections.map((section) => Card(child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(section.heading, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold)),
            const SizedBox(height: 10),
            Text(section.body.isEmpty ? 'Matn hali kiritilmagan.' : section.body,
                style: const TextStyle(fontSize: 15, height: 1.5)),
          ]),
        ))),
        const SizedBox(height: 13),
        FilledButton.icon(
          onPressed: () => progress.markRead(lesson.id),
          icon: Icon(progress.isRead(lesson.id) ? Icons.check_circle : Icons.bookmark_add_outlined),
          label: Text(progress.isRead(lesson.id) ? 'O‘qilgan' : 'Darsni o‘qidim'),
        ),
        if (lesson.hasAnatomyDiagram) OutlinedButton.icon(
          onPressed: () => Navigator.push(context,
            MaterialPageRoute<void>(builder: (_) => const DentalArch3DPage())),
          icon: const Icon(Icons.threed_rotation),
          label: const Text('3D tish qatori · O‘quv maketi'),
        ),
        if (lesson.questions.isNotEmpty) OutlinedButton.icon(
          onPressed: () => Navigator.push(context, MaterialPageRoute<void>(
              builder: (_) => QuizPage(lesson: lesson, progress: progress))),
          icon: const Icon(Icons.quiz_outlined),
          label: Text('Testni boshlash · ' + lesson.questions.length.toString()),
        ),
        const SizedBox(height: 20),
      ]),
    ),
  );
}

class QuizPage extends StatefulWidget {
  final StudyLesson lesson;
  final StudyProgress progress;
  const QuizPage({super.key, required this.lesson, required this.progress});
  @override
  State<QuizPage> createState() => _QuizPageState();
}

class _QuizPageState extends State<QuizPage> {
  final Map<int, int> selections = {};
  int index = 0;
  bool finished = false;

  int get score => widget.lesson.questions.asMap().entries
      .where((entry) => selections[entry.key] == entry.value.answer).length;

  void finish() {
    setState(() => finished = true);
    widget.progress.saveQuiz(widget.lesson.id, score);
  }

  @override
  Widget build(BuildContext context) {
    final questions = widget.lesson.questions;
    if (questions.isEmpty) {
      return Scaffold(
          appBar: AppBar(title: const Text('Test')),
          body: const Center(child: Text('Bu mavzuda test yo‘q.')));
    }
    return Scaffold(
      appBar: AppBar(title: Text(finished ? 'Test natijasi' : 'Mavzu testi')),
      body: ListView(padding: const EdgeInsets.all(16), children:
          finished ? resultItems(context, questions) : questionItems(context, questions)),
    );
  }

  List<Widget> questionItems(BuildContext context, List<StudyQuestion> questions) {
    final question = questions[index];
    return [
      Text('Savol ' + (index + 1).toString() + ' / ' + questions.length.toString(),
          style: const TextStyle(fontWeight: FontWeight.bold, color: green)),
      const SizedBox(height: 10),
      LinearProgressIndicator(value: (index + 1) / questions.length),
      const SizedBox(height: 24),
      Text(question.prompt, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
      const SizedBox(height: 18),
      ...question.options.asMap().entries.map((choice) {
        final selected = selections[index] == choice.key;
        return Card(child: ListTile(
          onTap: () => setState(() => selections[index] = choice.key),
          leading: Icon(selected ? Icons.radio_button_checked : Icons.radio_button_off),
          selected: selected,
          title: Text(choice.value),
        ));
      }),
      const SizedBox(height: 14),
      FilledButton.icon(
        onPressed: selections[index] == null ? null : () {
          if (index + 1 == questions.length) {
            finish();
          } else {
            setState(() => index++);
          }
        },
        icon: const Icon(Icons.arrow_forward),
        label: Text(index + 1 == questions.length ? 'Natijani ko‘rish' : 'Keyingi savol'),
      ),
      if (index > 0) TextButton(
        onPressed: () => setState(() => index--),
        child: const Text('Oldingi savol'),
      ),
    ];
  }

  List<Widget> resultItems(BuildContext context, List<StudyQuestion> questions) => [
    Card(child: Padding(
      padding: const EdgeInsets.all(24),
      child: Column(children: [
        const Icon(Icons.workspace_premium_outlined, size: 46, color: green),
        Text(score.toString() + ' / ' + questions.length.toString(),
            style: const TextStyle(fontSize: 35, fontWeight: FontWeight.bold)),
        const Text('To‘g‘ri javoblar'),
      ]),
    )),
    const SizedBox(height: 12),
    ...questions.asMap().entries.map((entry) {
      final q = entry.value;
      final isCorrect = selections[entry.key] == q.answer;
      return Card(child: Padding(
        padding: const EdgeInsets.all(15),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Icon(isCorrect ? Icons.check_circle_outline : Icons.cancel_outlined,
                color: isCorrect ? green : Theme.of(context).colorScheme.error),
            const SizedBox(width: 8),
            Expanded(child: Text(q.prompt, style: const TextStyle(fontWeight: FontWeight.bold))),
          ]),
          const SizedBox(height: 8),
          Text('To‘g‘ri javob: ' + q.options[q.answer]),
          if (!isCorrect) Text('Siz tanladingiz: ' +
              q.options[selections[entry.key] ?? 0]),
          if (q.explanation.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(q.explanation, style: const TextStyle(fontSize: 13)),
          ],
        ]),
      ));
    }),
    const SizedBox(height: 13),
    FilledButton.icon(
      icon: const Icon(Icons.refresh),
      label: const Text('Qayta ishlash'),
      onPressed: () => setState(() {
        index = 0;
        selections.clear();
        finished = false;
      }),
    ),
  ];
}
