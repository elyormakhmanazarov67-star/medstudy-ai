import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:medstudy_ai/mobile_auth_service.dart';

void main() {
  const server = 'https://medstudy-ai-mobile-staging-staging.up.railway.app';

  test('Native registration POST reaches the staging API directly', () async {
    late http.Request captured;
    final client = MockClient((request) async {
      captured = request;
      return http.Response(
        jsonEncode({'message': 'Ariza qabul qilindi.'}),
        202,
        headers: {'content-type': 'application/json; charset=utf-8'},
      );
    });
    final auth = MobileAuthService(baseUrl: server, client: client);
    await auth.register(
      name: 'Yangi Talaba',
      email: 'NEW@EXAMPLE.ORG',
      password: 'a-long-unique-password',
    );
    expect(captured.method, 'POST');
    expect(captured.url.toString(), server + '/api/mobile/register');
    expect(jsonDecode(captured.body), {
      'email': 'new@example.org',
      'display_name': 'Yangi Talaba',
      'password': 'a-long-unique-password',
    });
    client.close();
  });

  test('Validation errors are reported instead of swallowing the failure', () async {
    final client = MockClient((request) async =>
      http.Response(jsonEncode({'detail': 'Validation error'}), 422));
    final auth = MobileAuthService(baseUrl: server, client: client);
    await expectLater(
      auth.register(name: 'A', email: 'wrong', password: 'short'),
      throwsA(isA<MobileAuthException>().having(
        (e) => e.status, 'status', 422,
      )),
    );
    client.close();
  });

  test('Unapproved accounts cannot log in even with correct password', () async {
    final client = MockClient((request) async =>
      http.Response(jsonEncode({'detail': 'Administrator tasdig‘i kutilmoqda'}), 403));
    final auth = MobileAuthService(baseUrl: server, client: client);
    await expectLater(
      auth.login(email: 'new@example.org', password: 'long-password'),
      throwsA(isA<MobileAuthException>().having(
        (e) => e.status, 'status', 403,
      )),
    );
    client.close();
  });

  test('Missing or non-HTTPS configuration fails visibly', () async {
    final client = MockClient((_) async =>
      throw StateError('A network call should not have happened'));
    final auth = MobileAuthService(baseUrl: '', client: client);
    await expectLater(
      auth.register(name: 'Talaba', email: 'test@example.org',
          password: 'very-long-password'),
      throwsA(isA<MobileAuthException>()),
    );
    final insecure = MobileAuthService(
        baseUrl: 'http://localhost:8000', client: client);
    await expectLater(
      insecure.login(email: 'test@example.org', password: 'password'),
      throwsA(isA<MobileAuthException>()),
    );
    client.close();
  });
}
