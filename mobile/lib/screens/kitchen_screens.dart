import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/app_state.dart';
import '../widgets/common.dart';

class PantryScreen extends StatefulWidget {
  const PantryScreen({super.key});

  @override
  State<PantryScreen> createState() => _PantryScreenState();
}

class _PantryScreenState extends State<PantryScreen> {
  Future<void> Function()? _reload;

  Future<void> _add() async {
    final name = TextEditingController();
    DateTime? expires;
    var location = 'cupboard';
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => StatefulBuilder(
        builder: (c, set) => AlertDialog(
          title: const Text('Add to pantry'),
          content: Column(mainAxisSize: MainAxisSize.min, children: [
            TextField(controller: name, decoration: const InputDecoration(labelText: 'Item')),
            DropdownButtonFormField<String>(
              initialValue: location,
              decoration: const InputDecoration(labelText: 'Where'),
              items: const [
                DropdownMenuItem(value: 'fridge', child: Text('Fridge')),
                DropdownMenuItem(value: 'freezer', child: Text('Freezer')),
                DropdownMenuItem(value: 'cupboard', child: Text('Cupboard')),
              ],
              onChanged: (v) => set(() => location = v ?? 'cupboard'),
            ),
            TextButton.icon(
              icon: const Icon(Icons.event),
              label: Text(expires == null ? 'Expiry date (optional)' : 'Expires ${expires!.toIso8601String().substring(0, 10)}'),
              onPressed: () async {
                final d = await showDatePicker(
                    context: c, firstDate: DateTime.now().subtract(const Duration(days: 30)), lastDate: DateTime.now().add(const Duration(days: 1500)));
                if (d != null) set(() => expires = d);
              },
            ),
          ]),
          actions: [
            TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancel')),
            FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Add')),
          ],
        ),
      ),
    );
    if (ok != true || name.text.trim().isEmpty || !mounted) return;
    await runAction(context, () => context.read<AppState>().api.post('/pantry', {
          'name': name.text.trim(),
          'location': location,
          'expires_on': expires?.toIso8601String().substring(0, 10),
        }));
    await _reload?.call();
  }

  @override
  Widget build(BuildContext context) {
    final api = context.read<AppState>().api;
    return Scaffold(
      appBar: AppBar(title: const Text('Pantry')),
      floatingActionButton: FloatingActionButton(onPressed: _add, tooltip: 'Add item', child: const Icon(Icons.add)),
      body: ApiView(
        path: '/pantry',
        signedIn: true,
        builder: (context, data, reload) {
          _reload = reload;
          final items = (data as List).cast<Map<String, dynamic>>();
          if (items.isEmpty) return const Center(child: Text('Nothing in your pantry yet.'));
          return ListView(padding: const EdgeInsets.fromLTRB(8, 8, 8, 80), children: [
            for (final i in items)
              Card(
                child: ListTile(
                  title: Text(i['name'] as String),
                  subtitle: Text([
                    i['location'],
                    if (i['expires_on'] != null) 'best before ${i['expires_on']}',
                    if (i['shared'] == true) 'shared',
                  ].whereType<String>().join(' · ')),
                  leading: Icon(Icons.circle,
                      size: 14,
                      color: switch (i['status']) {
                        'expired' => Colors.red,
                        'soon' => Colors.orange,
                        'ok' => Colors.green,
                        _ => Colors.grey,
                      }),
                  trailing: Row(mainAxisSize: MainAxisSize.min, children: [
                    IconButton(
                      tooltip: 'Used up',
                      icon: const Icon(Icons.check),
                      onPressed: () async {
                        await runAction(context, () => api.patch('/pantry/${i['id']}', {'used_up': true}));
                        await reload();
                      },
                    ),
                    IconButton(
                      tooltip: 'Delete',
                      icon: const Icon(Icons.delete_outline),
                      onPressed: () async {
                        await runAction(context, () => api.delete('/pantry/${i['id']}'));
                        await reload();
                      },
                    ),
                  ]),
                ),
              ),
          ]);
        },
      ),
    );
  }
}

class BudgetScreen extends StatelessWidget {
  const BudgetScreen({super.key});

  Future<void> _log(BuildContext context, String currency, Future<void> Function() reload) async {
    final name = TextEditingController();
    final price = TextEditingController();
    final store = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Log a purchase'),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(controller: name, decoration: const InputDecoration(labelText: 'Item')),
          TextField(controller: price, keyboardType: TextInputType.number, decoration: InputDecoration(labelText: 'Price ($currency)')),
          TextField(controller: store, decoration: const InputDecoration(labelText: 'Store')),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Log')),
        ],
      ),
    );
    final p = double.tryParse(price.text);
    if (ok != true || name.text.trim().isEmpty || p == null || !context.mounted) return;
    await runAction(context, () => context.read<AppState>().api.post('/purchases', {
          'name': name.text.trim(),
          'price': p,
          'currency': currency,
          'store': store.text.trim().isEmpty ? null : store.text.trim(),
        }));
    await reload();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Grocery budget')),
      body: ApiView(
        path: '/budget',
        signedIn: true,
        builder: (context, s, reload) {
          final cur = s['currency'] as String;
          final budget = s['budget'] as num?;
          return ListView(padding: const EdgeInsets.all(12), children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(s['month'] as String),
                  Text('$cur ${(s['spent'] as num).toStringAsFixed(2)}${budget != null ? ' of ${budget.toStringAsFixed(2)}' : ' spent'}',
                      style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800)),
                  if (budget != null && budget > 0) ...[
                    const SizedBox(height: 8),
                    LinearProgressIndicator(value: ((s['spent'] as num) / budget).clamp(0, 1).toDouble()),
                  ],
                  for (final e in (s['by_store'] as Map).entries) Text('${e.key}: $cur ${(e.value as num).toStringAsFixed(2)}'),
                ]),
              ),
            ),
            FilledButton.icon(onPressed: () => _log(context, cur, reload), icon: const Icon(Icons.add), label: const Text('Log a purchase')),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: () async {
                final c = TextEditingController(text: budget?.toString() ?? '');
                final ok = await showDialog<bool>(
                  context: context,
                  builder: (d) => AlertDialog(
                    title: const Text('Monthly grocery budget'),
                    content: TextField(controller: c, keyboardType: TextInputType.number, decoration: InputDecoration(labelText: 'Amount ($cur)')),
                    actions: [
                      TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Cancel')),
                      FilledButton(onPressed: () => Navigator.pop(d, true), child: const Text('Save')),
                    ],
                  ),
                );
                final v = double.tryParse(c.text);
                if (ok != true || v == null || !context.mounted) return;
                await runAction(context, () => context.read<AppState>().api.put('/budget', {'monthly_amount': v, 'currency': cur}), ok: 'Budget saved');
                await reload();
              },
              icon: const Icon(Icons.savings_outlined),
              label: Text(budget == null ? 'Set a monthly budget' : 'Change monthly budget'),
            ),
            const SectionHeader('Shopping history'),
            ApiView(
              path: '/purchases',
              builder: (context, data, reloadHistory) => Column(children: [
                if ((data as List).isEmpty) const Text('No purchases logged yet.'),
                for (final p in data.cast<Map<String, dynamic>>())
                  ListTile(
                    dense: true,
                    title: Text(p['name'] as String),
                    subtitle: Text('${p['purchased_on']}${p['store'] != null ? ' · ${p['store']}' : ''}'),
                    trailing: Text('${p['currency']} ${(p['price'] as num).toStringAsFixed(2)}'),
                  ),
              ]),
            ),
          ]);
        },
      ),
    );
  }
}
