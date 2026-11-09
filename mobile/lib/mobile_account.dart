import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

const _server = String.fromEnvironment('MEDSTUDY_API_URL');
const _secure = FlutterSecureStorage();

class MobileAccountPage extends StatefulWidget {
  const MobileAccountPage({super.key});

  @override
  State<MobileAccountPage> createState() => _MobileAccountPageState();
}

class _MobileAccountPageState extends State<MobileAccountPage> {
  final email = TextEditingController();
  final password = TextEditingController();
  final name = TextEditingController();
  bool register = false;
  bool busy = false;
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
    super.dispose();
  }

  Future<void> checkSession() async {
    if (_server.isEmpty) return;
    final token = await _secure.read(key: 'mobile_access_token');
    if (token == null) return;
    try {
      final response = await http.get(Uri.parse('${_server.replaceAll(RegExp(r"/+$"), "")}/api/mobile/me'),
        headers: {'Authorization': 'Bearer $token'}).timeout(const Duration(seconds: 12));
      if (response.statusCode == 200 && mounted) {
        setState(() => profile = jsonDecode(response.body) as Map<String, dynamic>);
      } else if (response.statusCode == 401) {
        await _secure.delete(key: 'mobile_access_token');
      }
    } catch (_) {
      if (mounted) setState(() => message = 'Internet aloqasini tekshiring.');
    }
  }

  Future<void> submit() async {
    if (_server.isEmpty || !Uri.tryParse(_server)!.isScheme('https')) {
      setState(() => message = 'HTTPS API manzili sozlanmagan.');
      return;
    }
    setState(() { busy = true; message = ''; });
    try {
      final response = await http.post(Uri.parse('${_server.replaceAll(RegExp(r"/+$"), "")}/api/mobile/${register ? "register" : "login"}'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'email': email.text.trim(),
          'password': password.text,
          if (register) 'display_name': name.text.trim(),
        })).timeout(const Duration(seconds: 15));
      final payload = jsonDecode(response.body) as Map<String, dynamic>;
      if (response.statusCode == 200 && !register) {
        await _secure.write(key: 'mobile_access_token', value: payload['access_token'] as String);
        await checkSession();
        if (mounted) setState(() => message = 'Muvaffaqiyatli kirdingiz.');
      } else if (response.statusCode == 202) {
        if (mounted) setState(() { register = false; message = 'Ariza yuborildi. Administrator tasdig‘ini kuting.'; });
      } else {
        final detail = payload['detail'];
        if (mounted) setState(() => message = detail is String ? detail : 'Ma‘lumotlarni tekshiring.');
      }
    } catch (_) {
      if (mounted) setState(() => message = 'Server bilan aloqa yo‘q.');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> logout() async {
    final token = await _secure.read(key: 'mobile_access_token');
    if (_server.isNotEmpty && token != null) {
      try {
        await http.post(Uri.parse('${_server.replaceAll(RegExp(r"/+$"), "")}/api/mobile/logout'),
          headers: {'Authorization': 'Bearer $token'}).timeout(const Duration(seconds: 8));
      } catch (_) {
        // Best-effort remote logout; local credentials are always removed.
      }
    }
    await _secure.delete(key: 'mobile_access_token');
    if (mounted) setState(() { profile = null; message = 'Chiqildi.'; });
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Talaba kabineti')),
    body: ListView(padding: const EdgeInsets.all(20), children: [
      const Icon(Icons.school_outlined, color: Color(0xFF20844D), size: 54),
      const SizedBox(height: 20),
      if (profile != null) ...[
        Text('Salom, ${profile!['display_name']}', style: Theme.of(context).textTheme.headlineSmall),
        Text('${profile!['email']}'),
        const SizedBox(height: 15),
        const Text('Hozircha darslar offline. Natijalarni serverga uzatish keyingi bosqichda.'),
        const SizedBox(height: 20),
        FilledButton(onPressed: busy ? null : logout, child: const Text('Chiqish')),
      ] else ...[
        Text(register ? 'Ro‘yxatdan o‘tish' : 'Kirish',
          style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 12),
        if (register) TextField(controller: name, maxLength: 70,
          decoration: const InputDecoration(labelText: 'Ism'), textCapitalization: TextCapitalization.words),
        TextField(controller: email, keyboardType: TextInputType.emailAddress,
          autocorrect: false, decoration: const InputDecoration(labelText: 'Email')),
        TextField(controller: password, obscureText: true, enableSuggestions: false, autocorrect: false,
          decoration: const InputDecoration(labelText: 'Parol (kamida 12 belgi)')),
        const SizedBox(height: 18),
        FilledButton(onPressed: busy ? null : submit,
          child: Text(busy ? 'Yuborilmoqda...' : (register ? 'Ariza yuborish' : 'Kirish'))),
        TextButton(onPressed: busy ? null : () => setState(() { register = !register; message = ''; }),
          child: Text(register ? 'Akkauntim bor' : 'Yangi akkaunt yaratish')),
        const Text('Ro‘yxatdan o‘tgan talabani administrator tasdiqlaydi.'),
      ],
      if (message.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 15),
        child: Text(message, textAlign: TextAlign.center)),
      if (_server.isEmpty) const Padding(padding: EdgeInsets.only(top: 12),
        child: Text('API manzili berilmagan. Ilova offline ishlashda davom etadi.')),
    ]),
  );
}
