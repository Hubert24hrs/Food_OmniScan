import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api.dart';
import '../core/app_state.dart';

class DiaryScreen extends StatefulWidget {
  const DiaryScreen({super.key});

  @override
  State<DiaryScreen> createState() => _DiaryScreenState();
}

class _DiaryScreenState extends State<DiaryScreen> {
  Map<String, dynamic>? day;
  String? error;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (day == null && error == null) _load();
  }

  Future<void> _load() async {
    final app = context.read<AppState>();
    if (!app.signedIn) return;
    try {
      final d = await app.api.get('/diary', query: {if (app.activeProfile != null) 'profile_id': app.activeProfile!['id'] as String});
      if (mounted) setState(() => day = d as Map<String, dynamic>);
    } on ApiException catch (e) {
      if (mounted) setState(() => error = e.message);
    }
  }

  Future<void> _add() async {
    final desc = TextEditingController();
    final kcal = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Log a food'),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(controller: desc, decoration: const InputDecoration(labelText: 'Food (e.g. Jollof rice, 1 cup)')),
          const SizedBox(height: 8),
          TextField(controller: kcal, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Calories')),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Log')),
        ],
      ),
    );
    if (ok != true || desc.text.trim().isEmpty || !mounted) return;
    await context.read<AppState>().api.post('/diary/entries', {
      'meal_type': 'snack',
      'description': desc.text.trim(),
      'energy_kcal': double.tryParse(kcal.text),
      'profile_id': context.read<AppState>().activeProfile?['id'],
    });
    await _load();
  }

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    if (!app.signedIn) return const Scaffold(body: Center(child: Text('Sign in on the Profile tab to use the diary.')));
    final totals = day?['totals'] as Map<String, dynamic>?;
    return Scaffold(
      appBar: AppBar(title: const Text('Food diary')),
      floatingActionButton: FloatingActionButton.extended(onPressed: _add, icon: const Icon(Icons.add), label: const Text('Log food')),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.all(16), children: [
          if (error != null) Text(error!),
          if (totals != null)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Wrap(spacing: 18, runSpacing: 8, children: [
                  for (final k in ['energy_kcal', 'protein', 'carbohydrates', 'fat', 'fiber'])
                    Column(children: [
                      Text(k == 'energy_kcal' ? 'kcal' : k, style: const TextStyle(fontSize: 12)),
                      Text('${(totals[k] as num).round()}', style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800)),
                    ]),
                ]),
              ),
            ),
          for (final e in (day?['entries'] as List? ?? []).cast<Map<String, dynamic>>())
            ListTile(
              title: Text(e['description'] as String),
              subtitle: Text('${e['meal_type']}${e['is_estimate'] == true ? ' · estimate' : ''}'),
              trailing: Text('${(e['energy_kcal'] as num?)?.round() ?? '—'} kcal'),
            ),
        ]),
      ),
    );
  }
}

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
