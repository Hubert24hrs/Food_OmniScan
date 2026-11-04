import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api.dart';
import '../core/app_state.dart';

String _restrictions(Map<String, dynamic> p) {
  final items = [...(p['allergens'] as List).map((a) => a['code'] as String), ...(p['diets'] as List).cast<String>()];
  return items.isEmpty ? 'No restrictions set' : items.join(', ');
}

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  final email = TextEditingController();
  final password = TextEditingController();
  final name = TextEditingController();
  bool registerMode = false;
  bool consent = true;
  bool busy = false;
  String? error;

  Future<void> _submit() async {
    setState(() {
      busy = true;
      error = null;
    });
    final app = context.read<AppState>();
    try {
      if (registerMode) {
        await app.register(email.text.trim(), password.text, name.text.trim(), consent);
      } else {
        await app.login(email.text.trim(), password.text);
      }
    } on ApiException catch (e) {
      setState(() => error = e.message);
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    if (!app.signedIn) {
      return Scaffold(
        appBar: AppBar(title: Text(registerMode ? 'Create account' : 'Sign in')),
        body: ListView(padding: const EdgeInsets.all(16), children: [
          if (registerMode) TextField(controller: name, decoration: const InputDecoration(labelText: 'Name')),
          const SizedBox(height: 8),
          TextField(controller: email, keyboardType: TextInputType.emailAddress, autofillHints: const [AutofillHints.email], decoration: const InputDecoration(labelText: 'Email')),
          const SizedBox(height: 8),
          TextField(controller: password, obscureText: true, decoration: const InputDecoration(labelText: 'Password')),
          if (registerMode)
            CheckboxListTile(
              value: consent,
              onChanged: (v) => setState(() => consent = v ?? false),
              title: const Text('Store my allergy & diet info to personalize results (sensitive health data)'),
            ),
          if (registerMode) const Text('By creating an account you agree to the Terms and Privacy Policy. Not medical advice.', style: TextStyle(fontSize: 12)),
          if (error != null) Padding(padding: const EdgeInsets.only(top: 8), child: Text(error!, style: const TextStyle(color: Colors.red))),
          const SizedBox(height: 12),
          FilledButton(onPressed: busy ? null : _submit, child: Text(registerMode ? 'Create account' : 'Sign in')),
          TextButton(onPressed: () => setState(() => registerMode = !registerMode), child: Text(registerMode ? 'I have an account' : 'Create an account')),
        ]),
      );
    }
    final me = app.me!;
    return Scaffold(
      appBar: AppBar(title: const Text('Profile')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        ListTile(title: Text(me['display_name'] as String? ?? me['email'] as String), subtitle: Text('${me['email']} · ${me['tier']} plan')),
        const Divider(),
        const Text('Eater profiles', style: TextStyle(fontWeight: FontWeight.w800)),
        RadioGroup<String>(
          groupValue: app.activeProfile?['id'] as String?,
          onChanged: (v) => app.setActiveProfile(v!),
          child: Column(children: [
            for (final p in app.profiles)
              RadioListTile<String>(
                value: p['id'] as String,
                title: Text(p['name'] as String),
                subtitle: Text(_restrictions(p)),
              ),
          ]),
        ),
        const Padding(
          padding: EdgeInsets.symmetric(vertical: 8),
          child: Text('Edit allergies, diets, family members, data export and account deletion in the web app (Profile).', style: TextStyle(fontSize: 12)),
        ),
        OutlinedButton.icon(onPressed: app.logout, icon: const Icon(Icons.logout), label: const Text('Sign out')),
      ]),
    );
  }
}
