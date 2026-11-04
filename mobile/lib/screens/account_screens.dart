import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api.dart';
import '../core/app_state.dart';
import '../widgets/common.dart';
import '../widgets/fresh.dart';
import 'account_extras.dart';
import 'admin_screens.dart';
import 'more_screens.dart';

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
    final staff = me['role'] == 'admin' || me['role'] == 'moderator';
    void go(Widget w) => Navigator.of(context).push(MaterialPageRoute(builder: (_) => w));
    return Scaffold(
      appBar: AppBar(title: const Text('Profile')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        ListTile(
          leading: const IconTile(icon: Icons.person_rounded, index: 0),
          title: Text(me['display_name'] as String? ?? me['email'] as String, style: const TextStyle(fontWeight: FontWeight.w800)),
          subtitle: Text('${me['email']} · ${me['tier']} plan'),
        ),
        const SectionHeader('Who are you checking for?'),
        RadioGroup<String>(
          groupValue: app.activeProfile?['id'] as String?,
          onChanged: (v) => app.setActiveProfile(v!),
          child: Column(children: [
            for (final p in app.profiles)
              RadioListTile<String>(
                value: p['id'] as String,
                title: Text(p['name'] as String),
                subtitle: Text(_restrictions(p)),
                secondary: IconButton(tooltip: 'Edit ${p['name']}', icon: const Icon(Icons.edit_outlined), onPressed: () => go(ProfileEditorScreen(profile: p))),
              ),
          ]),
        ),
        TextButton.icon(
          icon: const Icon(Icons.person_add_alt),
          label: const Text('Add a family member'),
          onPressed: () async {
            final c = TextEditingController();
            final ok = await showDialog<bool>(
              context: context,
              builder: (d) => AlertDialog(
                title: const Text('Add a family member'),
                content: TextField(controller: c, autofocus: true, decoration: const InputDecoration(labelText: 'Name')),
                actions: [
                  TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Cancel')),
                  FilledButton(onPressed: () => Navigator.pop(d, true), child: const Text('Add')),
                ],
              ),
            );
            if (ok != true || c.text.trim().isEmpty || !context.mounted) return;
            await runAction(context, () => app.api.post('/profiles', {'name': c.text.trim()}), ok: 'Added ${c.text.trim()}');
            await app.refresh();
          },
        ),
        const Divider(height: 24),
        for (final (i, (icon, label, screen)) in <(IconData, String, Widget)>[
          (Icons.notifications_none, 'Notifications', const NotificationSettingsScreen()),
          (Icons.workspace_premium_outlined, 'Plans & usage', const PlansScreen()),
          (Icons.home_outlined, 'Household', const HouseholdScreen()),
          (Icons.add_box_outlined, 'Add a missing product', const SubmitProductScreen()),
          (Icons.lock_outline, 'Privacy & data', const PrivacyScreen()),
          if (staff) (Icons.admin_panel_settings_outlined, 'Admin & moderation', const AdminScreen()),
        ].indexed)
          ListTile(leading: IconTile(icon: icon, index: i + 1, size: 38), title: Text(label), trailing: const Icon(Icons.chevron_right), onTap: () => go(screen)),
        const SizedBox(height: 12),
        OutlinedButton.icon(onPressed: app.logout, icon: const Icon(Icons.logout), label: const Text('Sign out')),
      ]),
    );
  }
}
