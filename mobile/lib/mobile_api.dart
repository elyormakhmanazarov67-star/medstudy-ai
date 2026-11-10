import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'models/study_catalog.dart';

class MobileApiException implements Exception {
  final int? status;
  final String message;
  const MobileApiException(this.message, {this.status});
  @override
  String toString() => message;
}

/// Study requests always require HTTPS and a previously approved account.
class MobileApi {
  static const server = String.fromEnvironment('MEDSTUDY_API_URL');
  static const storage = FlutterSecureStorage();

  static Uri endpoint(String path) {
    final url = Uri.tryParse(server);
    if (url == null || url.scheme != 'https' || url.host.isEmpty ||
        url.userInfo.isNotEmpty || url.hasQuery || url.hasFragment) {
      throw const MobileApiException(
        'Xavfsiz server ulanmagan. Administrator sozlamalarni tekshirsin.',
      );
    }
    return Uri.parse(server.replaceAll(RegExp(r"/+$"), "") + path);
  }

  static Future<String> _get(String path) async {
    final token = await storage.read(key: 'mobile_access_token');
    if (token == null || token.isEmpty) {
      throw const MobileApiException('Ilovadan foydalanish uchun kiring.', status: 401);
    }
    final response = await http.get(endpoint(path), headers: {
      'Authorization': 'Bearer $token',
      'Cache-Control': 'no-store',
    }).timeout(const Duration(seconds: 20));
    if (response.statusCode != 200) {
      throw MobileApiException(
        response.statusCode == 401 || response.statusCode == 403
          ? 'Ruxsat berilmagan yoki sessiya tugagan.'
          : 'Serverdan ma’lumot olib bo‘lmadi.',
        status: response.statusCode,
      );
    }
    return utf8.decode(response.bodyBytes);
  }

  static Future<Map<String, dynamic>> me() async =>
      jsonDecode(await _get('/api/mobile/me')) as Map<String, dynamic>;

  static Future<StudyCatalog> catalog() async =>
      StudyCatalog.fromJson(jsonDecode(await _get('/api/mobile/catalog')) as Map<String, dynamic>);

  static Future<String> diagram(String lessonId) async {
    if (!RegExp(r'^anat_([1-9]|1[0-4])$').hasMatch(lessonId)) {
      throw const MobileApiException('Bunday anatomiya sxemasi yo‘q.');
    }
    return _get('/api/mobile/diagrams/' + lessonId);
  }


  static Future<List<Map<String, dynamic>>> getProgress() async {
    final body = jsonDecode(await _get('/api/mobile/progress'));
    final data = body is Map ? body['items'] : null;
    if (data is! List) {
      throw const MobileApiException('Natijalar formati noto‘g‘ri.');
    }
    return data
        .whereType<Map>()
        .map((item) => Map<String, dynamic>.from(item))
        .toList(growable: false);
  }

  static Future<void> putProgress({
    required String lessonId,
    required bool read,
    int? bestScore,
  }) async {
    final token = await storage.read(key: 'mobile_access_token');
    if (token == null || token.isEmpty) {
      throw const MobileApiException('Ilovadan foydalanish uchun kiring.', status: 401);
    }
    final response = await http.put(
      endpoint('/api/mobile/progress'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
        'Cache-Control': 'no-store',
      },
      body: jsonEncode({
        'lesson_id': lessonId,
        'read': read,
        'best_score': bestScore,
      }),
    ).timeout(const Duration(seconds: 8));
    if (response.statusCode != 200) {
      throw MobileApiException(
        'Natija hozircha telefonda saqlandi.',
        status: response.statusCode,
      );
    }
  }

  static Future<Map<String, dynamic>> preklinikVisual(String lessonId) async {
    if (!RegExp(r'^[a-z0-9_]{1,100}
      storage.delete(key: 'mobile_access_token');
}
).hasMatch(lessonId)) {
      throw const MobileApiException('Ushbu mavzu uchun rasm topilmadi.');
    }
    final response = jsonDecode(
      await _get('/api/mobile/preklinik-visual/' + Uri.encodeComponent(lessonId)),
    );
    if (response is! Map) {
      throw const MobileApiException('Rasm ma’lumotlari noto‘g‘ri.');
    }
    return Map<String, dynamic>.from(response);
  }

  static Future<void> clearToken() async =>
      storage.delete(key: 'mobile_access_token');
}
