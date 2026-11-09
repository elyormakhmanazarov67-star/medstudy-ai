import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

import 'mobile_auth_service.dart';

const _server = String.fromEnvironment('MEDSTUDY_API_URL');
const _secure = FlutterSecureStorage();

class MobileAccountPage extends StatefulWidget {
  final Future<void> Function()? onAuthChanged;
  final String? notice;
  const MobileAccountPage({super.key, this.onAuthChanged, this.notice});

  @override
  State<MobileAccountPage> createState() => _MobileAccountPageState();
}

class _MobileAccountPageState extends State<MobileAccountPage> {
  final formKey = GlobalKey<FormState>();
  final email = TextEditingController();
  final password = TextEditingController();
  final name = TextEditingController();
  final client = http.Client();

  late final MobileAuthService auth =
      MobileAuthService(baseUrl: _server, client: client);

  bool register = false;
  bool busy = false;
  bool pendingSubmitted = false;
  bool showPassword = false;
  String message = '';
  Map<String, dynamic>? profile;

  @override
  void initState() {
    super.initState();
    checkSession();
  }

  @override
  void dispose() {
    email.dispose();
    password.dispose();
    name.dispose();
    client.close();
    super.dispose();
  }

  Future<void> checkSession() async {
    if (_server.isEmpty) return;
    final token = await _secure.read(key: 'mobile_access_token');
    if (token == null) return;
    try {
      final response = await client.get(
        Uri.parse(_server.replaceAll(RegExp(r"/+$"), "") + '/api/mobile/me'),
        headers: {'Authorization': 'Bearer ' + token},
      ).timeout(const Duration(seconds: 12));
      if (response.statusCode == 200 && mounted) {
        setState(() {
          profile = jsonDecode(utf8.decode(response.bodyBytes))
              as Map<String, dynamic>;
        });
      } else if (response.statusCode == 401) {
        await _secure.delete(key: 'mobile_access_token');
      }
    } catch (_) {
      if (mounted) {
        setState(() => message =
            'Serverga ulanib bo‘lmadi. Internet aloqasini tekshiring.');
      }
    }
  }

  String? validateEmail(String? value) {
    final input = (value ?? '').trim();
    if (!RegExp(r'^[^\s@]+@[^\s@]+\.[^\s@]+$').hasMatch(input)) {
      return 'To‘g‘ri email manzilini kiriting.';
    }
    return null;
  }

  String? validatePassword(String? value) {
    final input = value ?? '';
    if (input.isEmpty) return 'Parolni kiriting.';
    if (register && input.length < 12) {
      return 'Parol kamida 12 belgidan iborat bo‘lsin.';
    }
    if (input.length > 128) return 'Parol juda uzun.';
    return null;
  }

  Future<void> submit() async {
    if (busy) return;
    if (!(formKey.currentState?.validate() ?? false)) return;
    setState(() {
      busy = true;
      message = '';
      pendingSubmitted = false;
    });
    try {
      if (register) {
        await auth.register(
          name: name.text,
          email: email.text,
          password: password.text,
        );
        if (!mounted) return;
        password.clear();
        setState(() {
          register = false;
          pendingSubmitted = true;
          message = 'Ariza serverga yuborildi. Administrator tasdig‘ini kuting. '
              'Agar bu email oldin ro‘yxatdan o‘tgan bo‘lsa, yangi ariza '
              'yaratilmaydi. Avval akkauntga kirib ko‘ring.';
        });
      } else {
        final token = await auth.login(
          email: email.text,
          password: password.text,
        );
        await _secure.write(key: 'mobile_access_token', value: token);
        password.clear();
        await widget.onAuthChanged?.call();
        if (mounted) {
          setState(() => message = 'Akkauntga muvaffaqiyatli kirdingiz.');
        }
      }
    } on MobileAuthException catch (error) {
      if (mounted) setState(() => message = error.message);
    } catch (_) {
      if (mounted) {
        setState(() => message =
            'Kutilmagan xatolik yuz berdi. Internetni tekshiring, '
            'so‘ng qayta urinib ko‘ring.');
      }
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> logout() async {
    if (busy) return;
    setState(() => busy = true);
    try {
      final token = await _secure.read(key: 'mobile_access_token');
      await auth.logout(token);
      await _secure.delete(key: 'mobile_access_token');
      await widget.onAuthChanged?.call();
      if (mounted) {
        setState(() {
          profile = null;
          message = 'Akkauntdan chiqdingiz.';
        });
      }
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  void changeMode() {
    formKey.currentState?.reset();
    password.clear();
    setState(() {
      register = !register;
      pendingSubmitted = false;
      message = '';
    });
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Talaba kabineti')),
    body: ListView(
      padding: const EdgeInsets.all(20),
      children: [
        if (widget.notice != null && widget.notice!.isNotEmpty)
          Card(child: Padding(
            padding: const EdgeInsets.all(12),
            child: Text(widget.notice!),
          )),
        const Icon(Icons.school_outlined,
            color: Color(0xFF20844D), size: 54),
        const SizedBox(height: 16),
        if (profile != null) ...[
          Text('Salom, ' + (profile!['display_name']?.toString() ?? ''),
              style: Theme.of(context).textTheme.headlineSmall),
          Text(profile!['email']?.toString() ?? ''),
          const SizedBox(height: 16),
          const Text('Darslar faqat administrator ruxsat bergan '
              'akkauntga ochiladi.'),
          const SizedBox(height: 16),
          FilledButton(
            onPressed: busy ? null : logout,
            child: const Text('Chiqish'),
          ),
        ] else ...[
          Text(register ? 'Yangi akkaunt yaratish' : 'Akkauntga kirish',
              style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 10),
          const Text('Ro‘yxatdan o‘tish bevosita ilova ichida '
              'amalga oshiriladi. Brauzer yoki Telegram kerak emas.'),
          const SizedBox(height: 18),
          Form(
            key: formKey,
            child: Column(children: [
              if (register) ...[
                TextFormField(
                  controller: name,
                  maxLength: 70,
                  enabled: !busy,
                  textCapitalization: TextCapitalization.words,
                  textInputAction: TextInputAction.next,
                  decoration: const InputDecoration(
                    labelText: 'Ism va familiya',
                    border: OutlineInputBorder(),
                  ),
                  validator: (value) => (value ?? '').trim().length < 2
                      ? 'Ism kamida 2 belgidan iborat bo‘lsin.'
                      : null,
                ),
                const SizedBox(height: 12),
              ],
              TextFormField(
                controller: email,
                enabled: !busy,
                keyboardType: TextInputType.emailAddress,
                textInputAction: TextInputAction.next,
                autocorrect: false,
                decoration: const InputDecoration(
                  labelText: 'Email',
                  border: OutlineInputBorder(),
                ),
                validator: validateEmail,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: password,
                enabled: !busy,
                obscureText: !showPassword,
                enableSuggestions: false,
                autocorrect: false,
                textInputAction: TextInputAction.done,
                onFieldSubmitted: (_) => submit(),
                decoration: InputDecoration(
                  labelText: register
                      ? 'Parol (kamida 12 ta belgi)' : 'Parol',
                  border: const OutlineInputBorder(),
                  suffixIcon: IconButton(
                    tooltip: showPassword
                        ? 'Parolni yashirish' : 'Parolni ko‘rsatish',
                    onPressed: busy ? null : () =>
                        setState(() => showPassword = !showPassword),
                    icon: Icon(showPassword
                        ? Icons.visibility_off_outlined
                        : Icons.visibility_outlined),
                  ),
                ),
                validator: validatePassword,
              ),
            ]),
          ),
          const SizedBox(height: 18),
          FilledButton.icon(
            onPressed: busy ? null : submit,
            icon: Icon(register ? Icons.person_add_alt_1 : Icons.login),
            label: Text(busy ? 'Serverga yuborilmoqda…'
                : (register ? 'Ro‘yxatdan o‘tish' : 'Kirish')),
          ),
          TextButton(
            onPressed: busy ? null : changeMode,
            child: Text(register
                ? 'Akkauntim bor — kirish'
                : 'Yangi akkaunt yaratish'),
          ),
          const SizedBox(height: 8),
          const Text('Talaba uchun ariza yuborilgach, administrator '
              'tasdiqlashi kerak. Tasdiqlanmagan akkaunt '
              'darslarni ocholmaydi.'),
        ],
        if (message.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 16),
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(14),
                child: Row(children: [
                  Icon(pendingSubmitted
                      ? Icons.mark_email_read_outlined
                      : Icons.info_outline),
                  const SizedBox(width: 12),
                  Expanded(child: Text(message)),
                ]),
              ),
            ),
          ),
        if (_server.isEmpty)
          const Padding(
            padding: EdgeInsets.only(top: 12),
            child: Text('Bu APK serverga ulanmagan. '
                'GitHub Actions’dagi oxirgi Android test versiyasini o‘rnating.'),
          ),
      ],
    ),
  );
}
