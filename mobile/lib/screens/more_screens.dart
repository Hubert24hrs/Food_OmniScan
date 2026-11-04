import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/app_state.dart';
import '../core/theme.dart';
import '../widgets/common.dart';
import '../widgets/score_widgets.dart';
import 'home_screens.dart';
import 'product_screen.dart';

void _open(BuildContext context, Widget screen) => Navigator.of(context).push(MaterialPageRoute(builder: (_) => screen));

String _ago(String iso) {
  final d = DateTime.now().difference(DateTime.parse(iso).toLocal());
  if (d.inMinutes < 60) return '${d.inMinutes} min ago';
  if (d.inHours < 24) return '${d.inHours} h ago';
  return '${d.inDays} days ago';
}

class HistoryScreen extends StatelessWidget {
  const HistoryScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Scan history')),
      body: ApiView(
        path: '/history',
        query: const {'limit': '100'},
        signedIn: true,
        builder: (context, data, _) {
          final rows = (data as List).cast<Map<String, dynamic>>();
          if (rows.isEmpty) return const Center(child: Text('No scans yet.'));
          return ListView(padding: const EdgeInsets.all(12), children: [
            for (final h in rows)
              ProductTile(p: h['product'] as Map<String, dynamic>, subtitle: '${_ago(h['last_scanned_at'] as String)} · scanned ${h['scan_count']}×'),
          ]);
        },
      ),
    );
  }
}

class SavedScreen extends StatelessWidget {
  const SavedScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(title: const Text('Saved'), bottom: const TabBar(tabs: [Tab(text: 'Favorites'), Tab(text: 'Trusted')])),
        body: ApiView(
          path: '/favourites',
          signedIn: true,
          builder: (context, data, reload) {
            final rows = (data as List).cast<Map<String, dynamic>>();
            Widget list(String type) {
              final items = rows.where((r) => (r['list_type'] ?? 'favourite') == type).toList();
              if (items.isEmpty) return const Center(child: Text('Nothing saved here yet.'));
              return ListView(padding: const EdgeInsets.all(12), children: [
                for (final r in items) ProductTile(p: r['product'] as Map<String, dynamic>),
              ]);
            }

            return TabBarView(children: [list('favourite'), list('trusted')]);
          },
        ),
      ),
    );
  }
}

class ShoppingListsScreen extends StatefulWidget {
  const ShoppingListsScreen({super.key});

  @override
  State<ShoppingListsScreen> createState() => _ShoppingListsScreenState();
}

class _ShoppingListsScreenState extends State<ShoppingListsScreen> {
  Future<void> Function()? _reload;

  Future<void> _create() async {
    final name = TextEditingController(text: 'Groceries');
    var shared = false;
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => StatefulBuilder(
        builder: (c, set) => AlertDialog(
          title: const Text('New shopping list'),
          content: Column(mainAxisSize: MainAxisSize.min, children: [
            TextField(controller: name, decoration: const InputDecoration(labelText: 'Name')),
            SwitchListTile(value: shared, onChanged: (v) => set(() => shared = v), title: const Text('Share with my household')),
          ]),
          actions: [
            TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancel')),
            FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Create')),
          ],
        ),
      ),
    );
    if (ok != true || name.text.trim().isEmpty || !mounted) return;
    await runAction(context, () => context.read<AppState>().api.post('/shopping-lists', {'name': name.text.trim(), 'shared_with_family': shared}));
    await _reload?.call();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Shopping lists')),
      floatingActionButton: FloatingActionButton(onPressed: _create, tooltip: 'New list', child: const Icon(Icons.add)),
      body: ApiView(
        path: '/shopping-lists',
        signedIn: true,
        builder: (context, data, reload) {
          _reload = reload;
          final lists = (data as List).cast<Map<String, dynamic>>();
          if (lists.isEmpty) return const Center(child: Text('No lists yet. Tap + to make one.'));
          return ListView(padding: const EdgeInsets.all(12), children: [
            for (final l in lists)
              Card(
                child: ListTile(
                  title: Text(l['name'] as String, style: const TextStyle(fontWeight: FontWeight.w700)),
                  subtitle: Text('${(l['items'] as List).where((i) => i['checked'] != true).length} to buy'
                      '${l['household_id'] != null ? ' · shared' : ''}'),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () async {
                    await Navigator.of(context).push(MaterialPageRoute(builder: (_) => ShoppingListScreen(listId: l['id'] as String)));
                    await reload();
                  },
                ),
              ),
          ]);
        },
      ),
    );
  }
}

class ShoppingListScreen extends StatefulWidget {
  const ShoppingListScreen({super.key, required this.listId});
  final String listId;

  @override
  State<ShoppingListScreen> createState() => _ShoppingListScreenState();
}

class _ShoppingListScreenState extends State<ShoppingListScreen> {
  Map<String, dynamic>? list;
  final add = TextEditingController();

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final lists = (await context.read<AppState>().api.get('/shopping-lists') as List).cast<Map<String, dynamic>>();
    if (mounted) setState(() => list = lists.firstWhere((l) => l['id'] == widget.listId, orElse: () => {}));
  }

  Future<void> _do(Future<dynamic> Function() call) async {
    final r = await runAction(context, call);
    if (r is Map && mounted) setState(() => list = r.cast<String, dynamic>());
  }

  @override
  Widget build(BuildContext context) {
    final api = context.read<AppState>().api;
    final l = list;
    return Scaffold(
      appBar: AppBar(title: Text(l?['name'] as String? ?? 'List'), actions: [
        if (l != null && l.isNotEmpty)
          IconButton(
            tooltip: 'Delete list',
            icon: const Icon(Icons.delete_outline),
            onPressed: () async {
              await runAction(context, () => api.delete('/shopping-lists/${widget.listId}'));
              if (context.mounted) Navigator.pop(context);
            },
          ),
      ]),
      body: l == null
          ? const Center(child: CircularProgressIndicator())
          : ListView(padding: const EdgeInsets.all(12), children: [
              Row(children: [
                Expanded(child: TextField(controller: add, decoration: const InputDecoration(hintText: 'Add an item'), onSubmitted: (_) => _addItem(api))),
                const SizedBox(width: 8),
                IconButton.filled(onPressed: () => _addItem(api), icon: const Icon(Icons.add), tooltip: 'Add'),
              ]),
              const SizedBox(height: 8),
              for (final i in (l['items'] as List? ?? []).cast<Map<String, dynamic>>())
                CheckboxListTile(
                  value: i['checked'] == true,
                  onChanged: (v) => _do(() => api.patch('/shopping-lists/${widget.listId}/items/${i['id']}', {'checked': v})),
                  title: Text(i['text'] as String,
                      style: TextStyle(decoration: i['checked'] == true ? TextDecoration.lineThrough : null)),
                  subtitle: i['quantity'] != null ? Text(i['quantity'] as String) : null,
                  secondary: IconButton(
                    tooltip: 'Remove',
                    icon: const Icon(Icons.close),
                    onPressed: () => _do(() => api.delete('/shopping-lists/${widget.listId}/items/${i['id']}')),
                  ),
                ),
            ]),
    );
  }

  Future<void> _addItem(dynamic api) async {
    final text = add.text.trim();
    if (text.isEmpty) return;
    add.clear();
    await _do(() => api.post('/shopping-lists/${widget.listId}/items', {'text': text}));
  }
}

class NotificationsScreen extends StatelessWidget {
  const NotificationsScreen({super.key});

  static IconData _icon(String kind) => switch (kind) {
        'recall' => Icons.report_gmailerrorred,
        'allergen_alert' => Icons.warning_amber_rounded,
        'ingredient_alert' => Icons.visibility_outlined,
        'expiry' => Icons.kitchen,
        'weekly_report' => Icons.insights,
        'tip' => Icons.lightbulb_outline,
        'household' => Icons.home_outlined,
        _ => Icons.notifications_none,
      };

  @override
  Widget build(BuildContext context) {
    final api = context.read<AppState>().api;
    return Scaffold(
      appBar: AppBar(title: const Text('Alerts')),
      body: ApiView(
        path: '/notifications',
        signedIn: true,
        builder: (context, data, reload) {
          final rows = (data as List).cast<Map<String, dynamic>>();
          if (rows.isEmpty) return const Center(child: Text('No alerts. Recalls and allergen alerts show up here.'));
          return ListView(padding: const EdgeInsets.all(12), children: [
            for (final n in rows)
              Card(
                child: ListTile(
                  leading: Icon(_icon(n['kind'] as String), color: n['kind'] == 'recall' || n['kind'] == 'allergen_alert' ? Brand.tomato : Brand.green),
                  title: Text(n['title'] as String, style: TextStyle(fontWeight: n['read'] == true ? FontWeight.w500 : FontWeight.w800)),
                  subtitle: Text('${n['body']}\n${_ago(n['created_at'] as String)}'),
                  isThreeLine: true,
                  onTap: () async {
                    if (n['read'] != true) await runAction(context, () => api.post('/notifications/${n['id']}/read'));
                    final pid = (n['data'] as Map?)?['product_id'] as String?;
                    if (pid != null && context.mounted) _open(context, ProductScreen(productId: pid));
                    await reload();
                  },
                ),
              ),
          ]);
        },
      ),
    );
  }
}

const _concernColor = {'beneficial': Brand.good, 'neutral': Brand.grey, 'caution': Brand.warn, 'concern': Brand.bad};

class IngredientsScreen extends StatefulWidget {
  const IngredientsScreen({super.key});

  @override
  State<IngredientsScreen> createState() => _IngredientsScreenState();
}

class _IngredientsScreenState extends State<IngredientsScreen> {
  String q = '';

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Ingredient encyclopedia')),
      body: Column(children: [
        Padding(
          padding: const EdgeInsets.all(12),
          child: TextField(
            decoration: const InputDecoration(prefixIcon: Icon(Icons.search), hintText: 'Search e.g. Red 40, E621, palm oil'),
            textInputAction: TextInputAction.search,
            onSubmitted: (v) => setState(() => q = v.trim()),
          ),
        ),
        Expanded(
          child: ApiView(
            path: '/ingredients',
            query: {'limit': '100', if (q.isNotEmpty) 'q': q},
            builder: (context, data, _) => ListView(padding: const EdgeInsets.symmetric(horizontal: 12), children: [
              for (final i in (data['items'] as List).cast<Map<String, dynamic>>())
                ListTile(
                  leading: Icon(Icons.circle, size: 12, color: _concernColor[i['concern_level']] ?? Brand.grey),
                  title: Text(i['name'] as String),
                  subtitle: Text('${i['category']} · ${i['concern_level']}'),
                  onTap: () => _open(context, IngredientScreen(slug: i['slug'] as String)),
                ),
            ]),
          ),
        ),
      ]),
    );
  }
}

class IngredientScreen extends StatelessWidget {
  const IngredientScreen({super.key, required this.slug});
  final String slug;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(),
      body: ApiView(
        path: '/ingredients/$slug',
        builder: (context, i, _) => ListView(padding: const EdgeInsets.all(16), children: [
          Text(i['name'] as String, style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800)),
          Wrap(spacing: 6, children: [
            Chip(label: Text(i['category'] as String)),
            if (i['e_number'] != null) Chip(label: Text(i['e_number'] as String)),
            Chip(
              label: Text(i['concern_level'] as String),
              backgroundColor: (_concernColor[i['concern_level']] ?? Brand.grey).withValues(alpha: 0.15),
            ),
          ]),
          if (i['function'] != null) Text('What it does: ${i['function']}'),
          const SizedBox(height: 8),
          if (i['plain_language'] != null) Text(i['plain_language'] as String),
          if (i['concern_summary'] != null) ...[const SectionHeader('What the evidence says'), Text(i['concern_summary'] as String)],
          if ((i['regulatory_notes'] as List).isNotEmpty) ...[
            const SectionHeader('Regulation'),
            for (final n in (i['regulatory_notes'] as List).cast<Map<String, dynamic>>()) Text('• ${n['jurisdiction']}: ${n['note']}'),
          ],
          if ((i['sources'] as List).isNotEmpty) ...[
            const SectionHeader('Sources'),
            for (final s in (i['sources'] as List).cast<Map<String, dynamic>>())
              Text('• ${s['title']} (${s['publisher'] ?? ''}${s['year'] != null ? ', ${s['year']}' : ''})', style: const TextStyle(fontSize: 13)),
          ],
          if (i['verification_status'] != 'verified')
            const Padding(padding: EdgeInsets.only(top: 12), child: Text('Pending editorial verification.', style: TextStyle(fontSize: 12))),
        ]),
      ),
    );
  }
}

/// Pick 2-6 products from history and saved items, then compare them side by side.
class CompareScreen extends StatefulWidget {
  const CompareScreen({super.key, this.initial = const []});
  final List<String> initial;

  @override
  State<CompareScreen> createState() => _CompareScreenState();
}

class _CompareScreenState extends State<CompareScreen> {
  late final Set<String> picked = {...widget.initial};
  Map<String, dynamic>? result;
  bool busy = false;

  Future<void> _compare() async {
    setState(() => busy = true);
    final app = context.read<AppState>();
    final r = await runAction(context, () => app.api.post('/compare', {
          'product_ids': picked.toList(),
          if (app.activeProfile != null) 'profile_ids': [app.activeProfile!['id']],
        }));
    if (!mounted) return;
    setState(() {
      busy = false;
      if (r is Map) result = r.cast<String, dynamic>();
    });
  }

  @override
  Widget build(BuildContext context) {
    if (result != null) return _CompareResult(result: result!, onBack: () => setState(() => result = null));
    return Scaffold(
      appBar: AppBar(title: const Text('Compare products')),
      floatingActionButton: picked.length >= 2
          ? FloatingActionButton.extended(onPressed: busy ? null : _compare, icon: const Icon(Icons.compare_arrows), label: Text('Compare ${picked.length}'))
          : null,
      body: ApiView(
        path: '/history',
        query: const {'limit': '50'},
        signedIn: true,
        builder: (context, data, _) {
          final rows = (data as List).cast<Map<String, dynamic>>();
          if (rows.isEmpty) return const Center(child: Text('Scan a few products first, then compare them here.'));
          return ListView(padding: const EdgeInsets.fromLTRB(12, 12, 12, 90), children: [
            const Text('Pick 2 to 6 products you have scanned.'),
            for (final h in rows)
              CheckboxListTile(
                value: picked.contains((h['product'] as Map)['id']),
                onChanged: (v) => setState(() {
                  final id = (h['product'] as Map)['id'] as String;
                  if (v == true && picked.length < 6) {
                    picked.add(id);
                  } else {
                    picked.remove(id);
                  }
                }),
                title: Text((h['product'] as Map)['name'] as String? ?? 'Unnamed'),
                subtitle: Text((h['product'] as Map)['brand'] as String? ?? ''),
                secondary: MiniScore(score: (h['product'] as Map)['score'] as int?, color: (h['product'] as Map)['color'] as String?),
              ),
          ]);
        },
      ),
    );
  }
}

class _CompareResult extends StatelessWidget {
  const _CompareResult({required this.result, required this.onBack});
  final Map<String, dynamic> result;
  final VoidCallback onBack;

  @override
  Widget build(BuildContext context) {
    final products = (result['products'] as List).cast<Map<String, dynamic>>();
    final rows = (result['rows'] as List).cast<Map<String, dynamic>>();
    final best = result['best'] as Map<String, dynamic>?;
    return Scaffold(
      appBar: AppBar(title: const Text('Comparison'), leading: BackButton(onPressed: onBack)),
      body: ListView(padding: const EdgeInsets.all(12), children: [
        if (best != null)
          Card(
            color: Brand.greenSoft,
            child: ListTile(leading: const Icon(Icons.emoji_events_outlined, color: Brand.green), title: Text('Best for ${best['objective']}: ${best['name']}')),
          ),
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: DataTable(
            columns: [
              const DataColumn(label: Text('')),
              for (final p in products) DataColumn(label: SizedBox(width: 110, child: Text((p['product'] as Map)['name'] as String? ?? '', maxLines: 2))),
            ],
            rows: [
              DataRow(cells: [const DataCell(Text('Score')), for (final p in products) DataCell(Text('${p['score'] ?? '?'}'))]),
              for (final r in rows)
                DataRow(cells: [
                  DataCell(Text('${r['label']}${r['unit'] != null && r['unit'] != '' ? ' (${r['unit']})' : ''}')),
                  for (final v in r['values'] as List) DataCell(Text(v == null ? '—' : v is List ? v.join(', ') : '$v')),
                ]),
            ],
          ),
        ),
        for (final n in (result['notes'] as List? ?? [])) Padding(padding: const EdgeInsets.only(top: 6), child: Text('$n', style: const TextStyle(fontSize: 12))),
      ]),
    );
  }
}

class HouseholdScreen extends StatefulWidget {
  const HouseholdScreen({super.key});

  @override
  State<HouseholdScreen> createState() => _HouseholdScreenState();
}

class _HouseholdScreenState extends State<HouseholdScreen> {
  @override
  Widget build(BuildContext context) {
    final app = context.read<AppState>();
    return Scaffold(
      appBar: AppBar(title: const Text('Household')),
      body: ApiView(
        path: '/household',
        signedIn: true,
        builder: (context, d, reload) {
          final h = d['household'] as Map<String, dynamic>?;
          final invites = (d['invites'] as List).cast<Map<String, dynamic>>();
          final owner = h != null && h['owner_user_id'] == app.me?['id'];
          return ListView(padding: const EdgeInsets.all(12), children: [
            const Text('Share a pantry, shopping lists and a grocery budget with the people you live with. Diaries and health profiles stay private.'),
            for (final i in invites)
              Card(
                child: ListTile(
                  title: Text('Invite to ${i['household']}'),
                  trailing: FilledButton(
                    onPressed: () async {
                      await runAction(context, () => app.api.post('/household/invites/${i['id']}/accept'), ok: 'Joined');
                      await reload();
                    },
                    child: const Text('Join'),
                  ),
                ),
              ),
            if (h != null) ...[
              SectionHeader(h['name'] as String),
              for (final m in (h['members'] as List).cast<Map<String, dynamic>>())
                ListTile(
                  title: Text(m['name'] as String? ?? m['email'] as String),
                  subtitle: Text('${m['email']} · ${m['role'] == 'owner' ? 'owner' : m['status']}'),
                  trailing: owner || m['email'] == app.me?['email']
                      ? TextButton(
                          onPressed: () async {
                            await runAction(context, () => app.api.delete('/household/members/${m['id']}'));
                            await reload();
                          },
                          child: Text(m['email'] == app.me?['email'] ? (m['role'] == 'owner' ? 'Close' : 'Leave') : 'Remove'),
                        )
                      : null,
                ),
              if (owner)
                OutlinedButton.icon(
                  icon: const Icon(Icons.person_add_alt),
                  label: const Text('Invite by email'),
                  onPressed: () async {
                    final email = await _ask(context, 'Invite by email', 'Email address');
                    if (email == null || !context.mounted) return;
                    await runAction(context, () => app.api.post('/household/invite', {'email': email}), ok: 'Invite sent');
                    await reload();
                  },
                ),
            ] else if (d['can_create'] == true)
              FilledButton.icon(
                icon: const Icon(Icons.add_home_outlined),
                label: const Text('Create a household'),
                onPressed: () async {
                  final name = await _ask(context, 'Household name', 'e.g. Our home');
                  if (name == null || !context.mounted) return;
                  await runAction(context, () => app.api.post('/household', {'name': name}));
                  await reload();
                },
              )
            else
              const UpgradeNotice(message: 'Household sharing is part of the Family plan. Someone on Family can also invite you.', tier: 'family'),
          ]);
        },
      ),
    );
  }
}

Future<String?> _ask(BuildContext context, String title, String hint) async {
  final c = TextEditingController();
  final ok = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: TextField(controller: c, autofocus: true, decoration: InputDecoration(hintText: hint)),
      actions: [
        TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Cancel')),
        FilledButton(onPressed: () => Navigator.pop(d, true), child: const Text('OK')),
      ],
    ),
  );
  return ok == true && c.text.trim().isNotEmpty ? c.text.trim() : null;
}
