import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../mobile_api.dart';

/// A separate "Rasm orqali tushuntirish" page for each Preklinik topic.
/// All illustration metadata and SVG bytes are fetched from an authenticated
/// endpoint, not embedded in the installed Android APK.
class PreklinikVisualPage extends StatefulWidget {
  final String lessonId;
  const PreklinikVisualPage({super.key, required this.lessonId});

  @override
  State<PreklinikVisualPage> createState() => _PreklinikVisualPageState();
}

class _PreklinikVisualPageState extends State<PreklinikVisualPage> {
  late Future<Map<String, dynamic>> guide;

  @override
  void initState() {
    super.initState();
    guide = MobileApi.preklinikVisual(widget.lessonId);
  }

  void retry() => setState(() {
    guide = MobileApi.preklinikVisual(widget.lessonId);
  });

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Rasm orqali tushuntirish')),
    body: FutureBuilder<Map<String, dynamic>>(
      future: guide,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError || snapshot.data == null) {
          return Center(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.image_not_supported_outlined, size: 48),
                  const SizedBox(height: 12),
                  const Text(
                    'Rasmni yuklab bo‘lmadi. Internetni va kirish huquqini tekshiring.',
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 12),
                  OutlinedButton.icon(
                    onPressed: retry,
                    icon: const Icon(Icons.refresh),
                    label: const Text('Qayta urinish'),
                  ),
                ],
              ),
            ),
          );
        }
        final data = snapshot.data!;
        final facts = data['facts'] is List ? data['facts'] as List : const [];
        final svg = data['svg']?.toString() ?? '';
        if (svg.isEmpty || facts.isEmpty) {
          return const Center(child: Text('Ushbu mavzuning rasmi topilmadi.'));
        }
        return ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(
              data['title']?.toString() ?? 'Mavzu sxemasi',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 12),
            Card(
              clipBehavior: Clip.antiAlias,
              child: Padding(
                padding: const EdgeInsets.all(10),
                child: Semantics(
                  label: data['alt']?.toString() ?? 'O‘quv sxemasi',
                  child: SvgPicture.string(
                    svg,
                    fit: BoxFit.contain,
                    placeholderBuilder: (_) =>
                        const Center(child: CircularProgressIndicator()),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 12),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Rasmdagi asosiy tushunchalar',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 8),
                    for (var index = 0; index < facts.length; index++)
                      if (facts[index] is List && (facts[index] as List).length == 2)
                        Padding(
                          padding: const EdgeInsets.symmetric(vertical: 11),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              CircleAvatar(
                                radius: 16,
                                child: Text((index + 1).toString()),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      facts[index][0].toString(),
                                      style: const TextStyle(
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                    const SizedBox(height: 4),
                                    Text(facts[index][1].toString()),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ),
                  ],
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 16),
              child: Text(
                data['notice']?.toString() ??
                    'Soddalashtirilgan o‘quv sxemasi.',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ),
          ],
        );
      },
    ),
  );
}
