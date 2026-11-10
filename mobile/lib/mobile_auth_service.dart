import 'dart:convert';
import 'package:http/http.dart' as http;

/// Native account requests always target the configured HTTPS API.
class MobileAuthException implements Exception {
  final int? status;
  final String message;
  const MobileAuthException(this.message, {this.status});

  @override
  String toString() => message;
}

class MobileAuthService {
  final String baseUrl;
  final http.Client client;

  MobileAuthService({required this.baseUrl, required this.client});

  Uri _url(String path) {
    final parsed = Uri.tryParse(baseUrl);
    if (parsed == null ||
        parsed.scheme != 'https' ||
        parsed.host.isEmpty ||
        parsed.userInfo.isNotEmpty ||
        parsed.hasQuery ||
        parsed.hasFragment) {
      throw const MobileAuthException(
        'Server manzili sozlanmagan. Ilovani yangilang yoki administratorga xabar bering.',
      );
    }
    return Uri.parse(baseUrl.replaceAll(RegExp(r"/+$"), "") + path);
  }

  Future<Map<String, dynamic>> _post(
      String path, Map<String, String> body) async {
    http.Response response;
    try {
      response = await client.post(
        _url(path),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(body),
      ).timeout(const Duration(seconds: 20));
    } on MobileAuthException {
      rethrow;
    } catch (_) {
      throw const MobileAuthException(
        'Serverga ulanib bo‘lmadi. Internetni tekshiring va qayta urinib ko‘ring.',
      );
    }

    Map<String, dynamic> payload = {};
    try {
      payload = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
    } catch (_) {
      // An unexpected HTML / proxy response must not count as success.
      throw MobileAuthException('Server javobi noto‘g‘ri. Keyinroq urinib ko‘ring.',
          status: response.statusCode);
    }
    if (response.statusCode == 429) {
      throw const MobileAuthException(
        'Juda ko‘p urinish. Birozdan keyin qayta urinib ko‘ring.',
        status: 429,
      );
    }
    if (response.statusCode == 422) {
      throw const MobileAuthException(
        'Ism, email yoki parol noto‘g‘ri. Parol kamida 12 belgidan iborat bo‘lsin.',
        status: 422,
      );
    }
    if (response.statusCode == 401) {
      throw const MobileAuthException('Email yoki parol noto‘g‘ri.', status: 401);
    }
    if (response.statusCode == 403) {
      final detail = payload['detail'];
      throw MobileAuthException(
        detail is String ? detail : 'Administrator ruxsati hali berilmagan.',
        status: 403,
      );
    }
    if (response.statusCode >= 400) {
      throw MobileAuthException(
        'Server xatosi (' + response.statusCode.toString() + '). Keyinroq urinib ko‘ring.',
        status: response.statusCode,
      );
    }
    return payload;
  }

  Future<void> register({
    required String name,
    required String email,
    required String password,
  }) async {
    final response = await _post('/api/mobile/register', {
      'display_name': name.trim(),
      'email': email.trim().toLowerCase(),
      'password': password,
    });
    // The server returns HTTP 202 for both newly added and existing emails.
    // Neither case gives access until the administrator approves the account.
    if (response['message'] is! String) {
      throw const MobileAuthException('Ariza javobi tekshirib bo‘lmadi.');
    }
  }

  Future<String> login({
    required String email,
    required String password,
  }) async {
    final response = await _post('/api/mobile/login', {
      'email': email.trim().toLowerCase(),
      'password': password,
    });
    final token = response['access_token'];
    if (token is! String || token.isEmpty) {
      throw const MobileAuthException('Server kirish tokenini bermadi.');
    }
    return token;
  }

  Future<void> logout(String? token) async {
    if (token == null || token.isEmpty) return;
    try {
      await client.post(
        _url('/api/mobile/logout'),
        headers: {'Authorization': 'Bearer $token'},
      ).timeout(const Duration(seconds: 8));
    } catch (_) {
      // Local token gets removed in the UI even if remote logout is unavailable.
    }
  }
}
