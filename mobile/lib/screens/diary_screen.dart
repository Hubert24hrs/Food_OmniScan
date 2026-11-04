import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../core/api.dart';
import '../core/app_state.dart';
import '../widgets/common.dart';

const _totals = [('Calories', 'energy_kcal', ''), ('Protein', 'protein', 'g'), ('Carbs', 'carbohydrates', 'g'), ('Fat', 'fat', 'g'), ('Fiber', 'fiber', 'g'), ('Sodium', 'sodium_mg', 'mg')];

class DiaryScreen extends StatefulWidget {
  const DiaryScreen({super.key});

  @override
  State<DiaryScreen> createState() => _DiaryScreenState();
}

class _DiaryScreenState extends State<DiaryScreen> {
  Map<String, dynamic>? day;
  String? error;
  bool busy = false;
  DateTime date = DateTime.now();

  String get _day => date.toIso8601String().substring(0, 10);

  Map<String, String> get _q {
    final p = context.read<AppState>().activeProfile;
    return {if (p != null) 'profile_id': p['id'] as String};
  }

  Future<void> _shiftDay(int days) async {
    setState(() => date = date.add(Duration(days: days)));
    await _load();
  }

  Future<void> _targets() async {
    final t = (day?['targets'] as Map<String, dynamic>?) ?? {};
    const fields = [
      ('energy_kcal', 'Calories'),
      ('protein', 'Protein (g)'),
      ('carbohydrates', 'Carbs (g)'),
      ('fat', 'Fat (g)'),
      ('fiber', 'Fiber (g)'),
      ('sodium_mg', 'Sodium (mg)'),
      ('water_ml', 'Water (ml)'),
      ('weight_goal_kg', 'Goal weight (kg)'),
    ];
    final ctrls = {for (final (k, _) in fields) k: TextEditingController(text: t[k] == null ? '' : '${(t[k] as num).round()}')};
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Daily targets'),
        content: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            for (final (k, l) in fields) TextField(controller: ctrls[k], keyboardType: TextInputType.number, decoration: InputDecoration(labelText: l)),
            const SizedBox(height: 6),
            const Text('Defaults are FDA Daily Values for a 2,000-calorie diet. Ideally set these with a health professional.', style: TextStyle(fontSize: 12)),
          ]),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Save')),
        ],
      ),
    );
    if (ok != true || !mounted) return;
    final goals = {for (final e in ctrls.entries) if (double.tryParse(e.value.text) != null) e.key: double.parse(e.value.text)};
    await runAction(context, () => context.read<AppState>().api.put('/diary/goals', {'goals': goals, ..._q}), ok: 'Targets saved');
    await _load();
  }

  Future<void> _weight() async {
    final c = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => AlertDialog(
        title: const Text('Log weight'),
        content: TextField(controller: c, keyboardType: const TextInputType.numberWithOptions(decimal: true), decoration: const InputDecoration(labelText: 'Weight (kg)')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(d, true), child: const Text('Save')),
        ],
      ),
    );
    final w = double.tryParse(c.text);
    if (ok != true || w == null || !mounted) return;
    await runAction(context, () => context.read<AppState>().api.put('/diary/weight', {'weight_kg': w, 'day': _day, ..._q}), ok: 'Weight saved');
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (day == null && error == null) _load();
  }

  Future<void> _load() async {
    final app = context.read<AppState>();
    if (!app.signedIn) return;
    try {
      final d = await app.api.get('/diary', query: {..._q, 'day': _day});
      if (mounted) setState(() => day = d as Map<String, dynamic>);
    } on ApiException catch (e) {
      if (mounted) setState(() => error = e.message);
    }
  }

  Future<void> _add() async {
    final desc = TextEditingController();
    final kcal = TextEditingController();
    var meal = 'snack';
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => StatefulBuilder(
        builder: (c, set) => AlertDialog(
          title: const Text('Log a food'),
          content: Column(mainAxisSize: MainAxisSize.min, children: [
            DropdownButtonFormField<String>(
              initialValue: meal,
              items: [for (final m in ['breakfast', 'lunch', 'dinner', 'snack']) DropdownMenuItem(value: m, child: Text(m))],
              onChanged: (v) => set(() => meal = v ?? 'snack'),
            ),
            TextField(controller: desc, decoration: const InputDecoration(labelText: 'Food (e.g. Jollof rice, 1 cup)')),
            TextField(controller: kcal, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Calories')),
          ]),
          actions: [
            TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancel')),
            FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Log')),
          ],
        ),
      ),
    );
    if (ok != true || desc.text.trim().isEmpty || !mounted) return;
    await runAction(context, () => context.read<AppState>().api.post('/diary/entries', {
          'meal_type': meal,
          'description': desc.text.trim(),
          'energy_kcal': double.tryParse(kcal.text),
          'day': _day,
          ..._q,
        }));
    await _load();
  }

  Future<void> _water(int ml) async {
    await runAction(context, () => context.read<AppState>().api.post('/diary/water', {'ml': ml, 'day': _day, ..._q}));
    await _load();
  }

  Future<void> _mealPhoto() async {
    final photo = await ImagePicker().pickImage(source: ImageSource.camera, maxWidth: 2000, imageQuality: 85);
    if (photo == null || !mounted) return;
    final api = context.read<AppState>().api;
    setState(() => busy = true);
    final r = await runAction(context, () async => api.upload('/analysis/image', fields: {'task': 'meal'}, bytes: await photo.readAsBytes()));
    if (mounted) setState(() => busy = false);
    if (r is! Map || !mounted) return;
    final items = ((r['extracted'] as Map)['items'] as List? ?? []).cast<Map<String, dynamic>>();
    final keep = List<bool>.filled(items.length, true);
    var meal = 'lunch';
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => StatefulBuilder(
        builder: (c, set) => AlertDialog(
          title: const Text('Foods we recognised'),
          content: SizedBox(
            width: double.maxFinite,
            child: ListView(shrinkWrap: true, children: [
              if (items.isEmpty) const Text('No foods recognised. Try a clearer, top-down photo.'),
              for (var i = 0; i < items.length; i++)
                CheckboxListTile(
                  value: keep[i],
                  onChanged: (v) => set(() => keep[i] = v ?? false),
                  title: Text(items[i]['name'] as String),
                  subtitle: Text('~${(items[i]['portion_g'] as num?)?.round() ?? '?'} g · ${(items[i]['energy_kcal'] as num?)?.round() ?? '?'} kcal'),
                ),
              DropdownButtonFormField<String>(
                initialValue: meal,
                decoration: const InputDecoration(labelText: 'Meal'),
                items: [for (final m in ['breakfast', 'lunch', 'dinner', 'snack']) DropdownMenuItem(value: m, child: Text(m))],
                onChanged: (v) => set(() => meal = v ?? 'lunch'),
              ),
              const SizedBox(height: 8),
              const Text('These are AI estimates from a photo, not measurements.', style: TextStyle(fontSize: 12)),
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancel')),
            if (items.isNotEmpty) FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Log as estimates')),
          ],
        ),
      ),
    );
    if (ok != true || !mounted) return;
    num? n(Map m, String k) => m[k] as num?;
    final entries = [
      for (var i = 0; i < items.length; i++)
        if (keep[i])
          {
            'meal_type': meal,
            'description': (items[i]['name'] as String).substring(0, (items[i]['name'] as String).length.clamp(0, 200)),
            'quantity_g': n(items[i], 'portion_g'),
            'energy_kcal': n(items[i], 'energy_kcal'),
            'protein': n(items[i], 'protein_g'),
            'carbohydrates': n(items[i], 'carbs_g'),
            'fat': n(items[i], 'fat_g'),
            'fiber': n(items[i], 'fiber_g'),
            'is_estimate': true,
            'day': _day,
            ..._q,
          }
    ];
    if (entries.isEmpty) return;
    await runAction(context, () => api.post('/diary/entries/bulk', {'entries': entries}), ok: 'Logged ${entries.length} item(s)');
    await _load();
  }

  Future<void> _report(String kind) async {
    final api = context.read<AppState>().api;
    final path = kind == 'insights' ? '/diary/insights' : '/diary/report';
    final query = {...(_q), if (kind != 'insights') 'period': kind};
    await showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (c) => DraggableScrollableSheet(
        expand: false,
        builder: (c, scroll) => FutureBuilder(
          future: api.get(path, query: query),
          builder: (c, snap) {
            if (snap.hasError) return Padding(padding: const EdgeInsets.all(16), child: errorView(snap.error!));
            if (!snap.hasData) return const Center(child: CircularProgressIndicator());
            final r = snap.data as Map<String, dynamic>;
            return ListView(controller: scroll, padding: const EdgeInsets.all(16), children: [
              if (kind == 'insights') ...[
                const Text('Your food patterns', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
                for (final i in (r['insights'] as List).cast<Map<String, dynamic>>()) Card(child: Padding(padding: const EdgeInsets.all(12), child: Text(i['message'] as String))),
                Text(r['disclaimer'] as String, style: const TextStyle(fontSize: 12)),
              ] else ...[
                Text('${r['days_logged']} of ${r['days_in_period']} days logged', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
                if (r['averages'] != null)
                  for (final (l, k, u) in _totals)
                    ListTile(dense: true, title: Text(l), trailing: Text('${((r['averages'] as Map)[k] as num).round()}$u / ${((r['targets'] as Map)[k] as num).round()}$u')),
                if ((r['top_foods'] as List).isNotEmpty) Text('Most logged: ${(r['top_foods'] as List).map((f) => f['name']).join(', ')}'),
              ],
            ]);
          },
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    if (!app.signedIn) return const Scaffold(body: Center(child: Text('Sign in on the Profile tab to use the diary.')));
    final totals = day?['totals'] as Map<String, dynamic>?;
    final targets = (day?['targets'] as Map<String, dynamic>?) ?? {};
    final water = day?['water'] as Map<String, dynamic>?;
    final micros = day?['micros'] as Map<String, dynamic>?;
    return Scaffold(
      appBar: AppBar(title: const Text('Food diary'), actions: [
        IconButton(tooltip: 'Previous day', icon: const Icon(Icons.chevron_left), onPressed: () => _shiftDay(-1)),
        TextButton(
          onPressed: () async {
            final d = await showDatePicker(context: context, initialDate: date, firstDate: DateTime(2024), lastDate: DateTime.now().add(const Duration(days: 7)));
            if (d != null) {
              setState(() => date = d);
              await _load();
            }
          },
          child: Text(_day == DateTime.now().toIso8601String().substring(0, 10) ? 'Today' : _day.substring(5)),
        ),
        IconButton(tooltip: 'Next day', icon: const Icon(Icons.chevron_right), onPressed: () => _shiftDay(1)),
        PopupMenuButton<String>(
          tooltip: 'More',
          icon: const Icon(Icons.more_vert),
          onSelected: (v) => v == 'targets' ? _targets() : _weight(),
          itemBuilder: (_) => const [
            PopupMenuItem(value: 'targets', child: Text('Daily targets')),
            PopupMenuItem(value: 'weight', child: Text('Log weight')),
          ],
        ),
        PopupMenuButton<String>(
          tooltip: 'Reports',
          icon: const Icon(Icons.insights),
          onSelected: _report,
          itemBuilder: (_) => const [
            PopupMenuItem(value: 'week', child: Text('Weekly report')),
            PopupMenuItem(value: 'month', child: Text('Monthly report')),
            PopupMenuItem(value: 'insights', child: Text('Insights')),
          ],
        ),
      ]),
      floatingActionButton: FloatingActionButton.extended(onPressed: _add, icon: const Icon(Icons.add), label: const Text('Log food')),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.fromLTRB(16, 16, 16, 90), children: [
          if (error != null) Text(error!),
          if (totals != null)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Wrap(spacing: 18, runSpacing: 12, children: [
                  for (final (l, k, u) in _totals)
                    SizedBox(
                      width: 90,
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(l, style: const TextStyle(fontSize: 12)),
                        Text('${(totals[k] as num).round()}$u', style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800)),
                        if (targets[k] != null) ...[
                          LinearProgressIndicator(value: ((totals[k] as num) / (targets[k] as num)).clamp(0, 1).toDouble()),
                          Text('of ${(targets[k] as num).round()}', style: const TextStyle(fontSize: 11)),
                        ],
                      ]),
                    ),
                ]),
              ),
            ),
          if (water != null)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(children: [
                    const Icon(Icons.water_drop_outlined),
                    const SizedBox(width: 8),
                    Text('${water['total_ml']} ml of ${(targets['water_ml'] as num?)?.round() ?? 2000} ml', style: const TextStyle(fontWeight: FontWeight.w700)),
                  ]),
                  Wrap(spacing: 8, children: [for (final ml in [250, 500]) OutlinedButton(onPressed: () => _water(ml), child: Text('+$ml ml'))]),
                ]),
              ),
            ),
          Card(
            child: ListTile(
              leading: busy ? const SizedBox(width: 24, height: 24, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.photo_camera_outlined),
              title: const Text('Log a meal from a photo'),
              subtitle: const Text('AI recognises dishes (including jollof, egusi, moi moi) and estimates calories. You review before logging.'),
              onTap: busy ? null : _mealPhoto,
            ),
          ),
          if (day?['micros_locked'] == true)
            const UpgradeNotice(message: 'Track vitamins and minerals from the products you log.', tier: 'plus')
          else if (micros != null && micros.isNotEmpty) ...[
            const SectionHeader('Vitamins & minerals'),
            for (final m in micros.values.cast<Map<String, dynamic>>())
              ListTile(dense: true, title: Text(m['label'] as String), trailing: Text('${m['amount']} ${m['unit']} · ${m['pct_dv']}%')),
          ],
          SectionHeader(_day == DateTime.now().toIso8601String().substring(0, 10) ? 'Logged today' : 'Logged on $_day'),
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
