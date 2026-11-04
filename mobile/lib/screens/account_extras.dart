import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../core/api.dart';
import '../core/app_state.dart';
import '../core/theme.dart';
import '../widgets/common.dart';
import 'home_screens.dart';
import 'product_screen.dart';

const _severities = ['intolerance', 'mild', 'severe', 'anaphylaxis'];

/// Edit one eater profile: allergies (with severity), diets and avoided ingredients.
class ProfileEditorScreen extends StatefulWidget {
  const ProfileEditorScreen({super.key, required this.profile});
  final Map<String, dynamic> profile;

  @override
  State<ProfileEditorScreen> createState() => _ProfileEditorScreenState();
}

class _ProfileEditorScreenState extends State<ProfileEditorScreen> {
  Map<String, dynamic>? options;
  late final Map<String, String> allergens = {
    for (final a in (widget.profile['allergens'] as List).cast<Map<String, dynamic>>()) a['code'] as String: a['severity'] as String? ?? 'severe',
  };
  late final Set<String> diets = {...(widget.profile['diets'] as List).cast<String>()};
  late final List<String> avoid = [...(widget.profile['avoid'] as List).cast<String>()];
  final avoidInput = TextEditingController();
  bool saving = false;

  @override
  void initState() {
    super.initState();
    context.read<AppState>().api.get('/profiles/options').then((o) {
      if (mounted) setState(() => options = o as Map<String, dynamic>);
    });
  }

  Future<void> _save() async {
    final app = context.read<AppState>();
    final id = widget.profile['id'];
    setState(() => saving = true);
    final ok = await runAction(context, () async {
      await app.api.put('/profiles/$id/allergens', [
        for (final e in allergens.entries) {'code': e.key, 'severity': e.value, 'avoid_traces': true}
      ]);
      await app.api.put('/profiles/$id/diets', diets.toList());
      await app.api.put('/profiles/$id/avoid', avoid);
      return true;
    }, ok: 'Profile saved');
    if (!mounted) return;
    setState(() => saving = false);
    if (ok == true) {
      await app.refresh();
      if (mounted) Navigator.pop(context);
    }
  }

  @override
  Widget build(BuildContext context) {
    final o = options;
    final consent = context.watch<AppState>().me?['consent_health_data'] == true;
    return Scaffold(
      appBar: AppBar(title: Text(widget.profile['name'] as String), actions: [
        TextButton(onPressed: saving || !consent ? null : _save, child: const Text('Save')),
      ]),
      body: !consent
          ? Padding(
              padding: const EdgeInsets.all(24),
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                const Text('To store allergies and diets, allow Food omniScan to keep this health information.'),
                const SizedBox(height: 12),
                FilledButton(
                  onPressed: () async {
                    final app = context.read<AppState>();
                    await runAction(context, () => app.api.patch('/me', {'consent_health_data': true}));
                    await app.refresh();
                  },
                  child: const Text('Allow and continue'),
                ),
              ]),
            )
          : o == null
              ? const Center(child: CircularProgressIndicator())
              : ListView(padding: const EdgeInsets.all(16), children: [
                  const SectionHeader('Allergies & intolerances'),
                  Wrap(spacing: 6, runSpacing: 6, children: [
                    for (final a in (o['allergens'] as List).cast<Map<String, dynamic>>())
                      FilterChip(
                        label: Text(a['name'] as String),
                        selected: allergens.containsKey(a['code']),
                        onSelected: (v) => setState(() => v ? allergens[a['code'] as String] = 'severe' : allergens.remove(a['code'])),
                      ),
                  ]),
                  for (final e in allergens.entries)
                    Row(children: [
                      Expanded(child: Text(((o['allergens'] as List).firstWhere((a) => a['code'] == e.key, orElse: () => {'name': e.key}))['name'] as String)),
                      DropdownButton<String>(
                        value: e.value,
                        items: [for (final s in _severities) DropdownMenuItem(value: s, child: Text(s))],
                        onChanged: (v) => setState(() => allergens[e.key] = v ?? 'severe'),
                      ),
                    ]),
                  const SectionHeader('Diets'),
                  Wrap(spacing: 6, runSpacing: 6, children: [
                    for (final d in (o['diets'] as List).cast<Map<String, dynamic>>())
                      FilterChip(
                        label: Text(d['name'] as String),
                        selected: diets.contains(d['code']),
                        onSelected: (v) => setState(() => v ? diets.add(d['code'] as String) : diets.remove(d['code'])),
                      ),
                  ]),
                  const SectionHeader('Ingredients to avoid (watchlist)'),
                  Row(children: [
                    Expanded(child: TextField(controller: avoidInput, decoration: const InputDecoration(hintText: 'e.g. palm oil, MSG, Red 40'))),
                    IconButton(
                      tooltip: 'Add',
                      icon: const Icon(Icons.add),
                      onPressed: () => setState(() {
                        final t = avoidInput.text.trim();
                        if (t.isNotEmpty && !avoid.contains(t)) avoid.add(t);
                        avoidInput.clear();
                      }),
                    ),
                  ]),
                  Wrap(spacing: 6, children: [for (final t in avoid) InputChip(label: Text(t), onDeleted: () => setState(() => avoid.remove(t)))]),
                  const SizedBox(height: 12),
                  const Text('Products are checked against these on every scan. Not medical advice; always read the label.', style: TextStyle(fontSize: 12)),
                ]),
    );
  }
}

class NotificationSettingsScreen extends StatelessWidget {
  const NotificationSettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    final prefs = (app.me?['notification_prefs'] as Map?)?.cast<String, dynamic>() ?? {};
    const items = [
      ('allergen_alerts', 'Allergen alerts when I scan', true),
      ('recalls', "Recalls for products I've scanned", true),
      ('ingredient_alerts', 'Watchlist ingredient alerts (Plus)', true),
      ('expiry', 'Pantry expiry reminders (Plus)', true),
      ('weekly_report', 'Weekly nutrition summary (Plus)', true),
      ('tips', 'A weekly food tip', false),
    ];
    return Scaffold(
      appBar: AppBar(title: const Text('Notifications')),
      body: ListView(children: [
        for (final (key, label, def) in items)
          SwitchListTile(
            value: prefs[key] as bool? ?? def,
            title: Text(label),
            onChanged: (v) async {
              await runAction(context, () => app.api.patch('/me', {'notification_prefs': {key: v}}));
              await app.refresh();
            },
          ),
      ]),
    );
  }
}

class SubmitProductScreen extends StatefulWidget {
  const SubmitProductScreen({super.key, this.barcode});
  final String? barcode;

  @override
  State<SubmitProductScreen> createState() => _SubmitProductScreenState();
}

class _SubmitProductScreenState extends State<SubmitProductScreen> {
  late final barcode = TextEditingController(text: widget.barcode ?? '');
  final name = TextEditingController();
  final brand = TextEditingController();
  final ingredients = TextEditingController();
  final nafdac = TextEditingController();
  final images = <String>[];
  bool busy = false;

  Future<void> _photo() async {
    final photo = await ImagePicker().pickImage(source: ImageSource.camera, maxWidth: 2000, imageQuality: 85);
    if (photo == null || !mounted) return;
    final api = context.read<AppState>().api;
    final r = await runAction(context, () async => api.upload('/uploads', fields: const {}, bytes: await photo.readAsBytes()));
    if (r is Map && mounted) setState(() => images.add(r['image_id'] as String));
  }

  Future<void> _submit() async {
    setState(() => busy = true);
    final app = context.read<AppState>();
    final r = await runAction(
      context,
      () => app.api.post('/submissions', {
        'barcode': barcode.text.trim(),
        'name': name.text.trim(),
        if (brand.text.trim().isNotEmpty) 'brand': brand.text.trim(),
        if (ingredients.text.trim().isNotEmpty) 'ingredients_text': ingredients.text.trim(),
        if (nafdac.text.trim().isNotEmpty) 'nafdac_number': nafdac.text.trim(),
        'countries': [app.me?['country'] ?? 'US'],
        'image_ids': images,
      }),
      ok: 'Thanks! A moderator will review your product.',
    );
    if (!mounted) return;
    setState(() => busy = false);
    if (r != null) Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Add a missing product')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        TextField(controller: barcode, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Barcode')),
        const SizedBox(height: 8),
        TextField(controller: name, decoration: const InputDecoration(labelText: 'Product name')),
        const SizedBox(height: 8),
        TextField(controller: brand, decoration: const InputDecoration(labelText: 'Brand')),
        const SizedBox(height: 8),
        TextField(controller: ingredients, maxLines: 4, decoration: const InputDecoration(labelText: 'Ingredients (as printed)')),
        const SizedBox(height: 8),
        TextField(controller: nafdac, decoration: const InputDecoration(labelText: 'NAFDAC number (Nigeria, optional)')),
        const SizedBox(height: 12),
        OutlinedButton.icon(onPressed: images.length >= 6 ? null : _photo, icon: const Icon(Icons.photo_camera_outlined), label: Text('Add photo (${images.length}/6)')),
        const Text('Photograph the front, ingredient list and nutrition panel. Photos are stripped of location data.', style: TextStyle(fontSize: 12)),
        const SizedBox(height: 16),
        FilledButton(onPressed: busy ? null : _submit, child: const Text('Submit for review')),
      ]),
    );
  }
}

class RecallsScreen extends StatelessWidget {
  const RecallsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Food recalls')),
      body: ApiView(
        path: '/recalls',
        builder: (context, data, _) {
          final rows = (data as List).cast<Map<String, dynamic>>();
          if (rows.isEmpty) return const Center(child: Text('No verified recalls right now.'));
          return ListView(padding: const EdgeInsets.all(12), children: [
            for (final r in rows)
              Card(
                child: ListTile(
                  leading: const Icon(Icons.report_gmailerrorred, color: Brand.tomato),
                  title: Text(r['title'] as String, style: const TextStyle(fontWeight: FontWeight.w700)),
                  subtitle: Text('${r['authority']} (${r['jurisdiction']})${r['recall_date'] != null ? ' · ${r['recall_date']}' : ''}\n${r['reason']}'),
                  isThreeLine: true,
                  onTap: r['product_id'] == null
                      ? null
                      : () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ProductScreen(productId: r['product_id'] as String))),
                ),
              ),
          ]);
        },
      ),
    );
  }
}

class SourcesScreen extends StatelessWidget {
  const SourcesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Research & regulatory sources')),
      body: ApiView(
        path: '/sources',
        builder: (context, data, _) => ListView(padding: const EdgeInsets.all(12), children: [
          const Text('Every score deduction cites one of these. Evidence quality is shown honestly.'),
          for (final s in (data as List).cast<Map<String, dynamic>>())
            Card(
              child: ListTile(
                title: Text(s['title'] as String, style: const TextStyle(fontWeight: FontWeight.w700)),
                subtitle: Text('${[s['publisher'], s['year']].whereType<Object>().join(', ')}\n'
                    '${s['source_type']} · ${s['evidence_quality']} evidence${s['verified'] == true ? '' : ' · pending editorial check'}'),
                isThreeLine: true,
              ),
            ),
        ]),
      ),
    );
  }
}

class RecommendationsScreen extends StatelessWidget {
  const RecommendationsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Picked for you')),
      body: ApiView(
        path: '/recommendations',
        signedIn: true,
        builder: (context, r, _) {
          final rows = (r['results'] as List).cast<Map<String, dynamic>>();
          if (rows.isEmpty) return Center(child: Padding(padding: const EdgeInsets.all(24), child: Text(r['note'] as String? ?? 'Nothing yet.')));
          return ListView(padding: const EdgeInsets.all(12), children: [
            const Text('Better-scoring products in the categories you buy, checked against your profile.'),
            for (final p in rows) ProductTile(p: p, subtitle: p['reason'] as String?),
          ]);
        },
      ),
    );
  }
}

/// Export my data (copied to the clipboard as JSON) and delete my account.
class PrivacyScreen extends StatelessWidget {
  const PrivacyScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final app = context.read<AppState>();
    return Scaffold(
      appBar: AppBar(title: const Text('Privacy & data')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        ListTile(
          leading: const Icon(Icons.download_outlined),
          title: const Text('Export my data'),
          subtitle: const Text('Copies everything we store about you as JSON.'),
          onTap: () async {
            final r = await runAction(context, () => app.api.get('/me/export'));
            if (r == null) return;
            await Clipboard.setData(ClipboardData(text: const JsonEncoder.withIndent('  ').convert(r)));
            if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Your data was copied to the clipboard.')));
          },
        ),
        SwitchListTile(
          value: app.me?['consent_health_data'] == true,
          title: const Text('Store allergy & diet information'),
          subtitle: const Text('Turning this off deletes stored allergies, diets and avoid lists.'),
          onChanged: (v) async {
            await runAction(context, () => app.api.patch('/me', {'consent_health_data': v}));
            await app.refresh();
          },
        ),
        ListTile(
          leading: const Icon(Icons.block),
          title: const Text('Blocked reviewers'),
          subtitle: const Text("People whose reviews you don't see."),
          trailing: const Icon(Icons.chevron_right),
          onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const BlockedReviewersScreen())),
        ),
        const Divider(height: 32),
        ListTile(
          leading: const Icon(Icons.delete_forever_outlined, color: Brand.tomato),
          title: const Text('Delete my account', style: TextStyle(color: Brand.tomato)),
          subtitle: const Text('Permanent. Type DELETE to confirm.'),
          onTap: () async {
            final c = TextEditingController();
            final ok = await showDialog<bool>(
              context: context,
              builder: (d) => AlertDialog(
                title: const Text('Delete account permanently?'),
                content: TextField(controller: c, decoration: const InputDecoration(hintText: 'Type DELETE')),
                actions: [
                  TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Cancel')),
                  FilledButton(style: FilledButton.styleFrom(backgroundColor: Brand.tomato), onPressed: () => Navigator.pop(d, true), child: const Text('Delete')),
                ],
              ),
            );
            if (ok != true || c.text != 'DELETE' || !context.mounted) return;
            try {
              await app.api.delete('/me', {'confirm': 'DELETE'});
              await app.logout();
              if (context.mounted) Navigator.of(context).popUntil((r) => r.isFirst);
            } on ApiException catch (e) {
              if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
            }
          },
        ),
      ]),
    );
  }
}

class BlockedReviewersScreen extends StatelessWidget {
  const BlockedReviewersScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final app = context.read<AppState>();
    return Scaffold(
      appBar: AppBar(title: const Text('Blocked reviewers')),
      body: ApiView(
        path: '/me/blocks',
        builder: (context, data, reload) {
          final rows = (data as List).cast<Map<String, dynamic>>();
          if (rows.isEmpty) return const Center(child: Padding(padding: EdgeInsets.all(24), child: Text("You haven't blocked anyone.")));
          return ListView(children: [
            for (final (i, b) in rows.indexed)
              ListTile(
                leading: const Icon(Icons.person_off_outlined),
                title: Text('Blocked reviewer ${i + 1}'),
                subtitle: Text('Since ${(b['created_at'] as String).substring(0, 10)}'),
                trailing: TextButton(
                  onPressed: () async {
                    await runAction(context, () => app.api.delete('/me/blocks/${b['id']}'), ok: 'Unblocked');
                    await reload();
                  },
                  child: const Text('Unblock'),
                ),
              ),
          ]);
        },
      ),
    );
  }
}
