import 'package:flutter/material.dart';
import '../widgets/common.dart';
import 'recipe_screens.dart';

class RankingsScreen extends StatefulWidget {
  const RankingsScreen({super.key});

  @override
  State<RankingsScreen> createState() => _RankingsScreenState();
}

class _RankingsScreenState extends State<RankingsScreen> {
  String? category;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Category rankings')),
      body: ApiView(
        path: '/categories',
        builder: (context, data, _) {
          final cats = (data as List).cast<Map<String, dynamic>>();
          if (cats.isEmpty) return const Center(child: Text('Rankings appear as products are scanned.'));
          final code = category ?? cats.first['code'] as String;
          return Column(children: [
            Padding(
              padding: const EdgeInsets.all(12),
              child: DropdownButtonFormField<String>(
                initialValue: code,
                isExpanded: true,
                decoration: const InputDecoration(labelText: 'Category'),
                items: [for (final c in cats) DropdownMenuItem(value: c['code'] as String, child: Text('${c['name']} (${c['products']})'))],
                onChanged: (v) => setState(() => category = v),
              ),
            ),
            Expanded(
              child: ApiView(
                path: '/rankings',
                query: {'category': code},
                builder: (context, r, _) {
                  final rows = (r['results'] as List).cast<Map<String, dynamic>>();
                  return ListView(padding: const EdgeInsets.symmetric(horizontal: 12), children: [
                    Text(r['criteria'] as String, style: const TextStyle(fontSize: 12)),
                    for (final p in rows)
                      ListTile(
                        leading: CircleAvatar(child: Text('${p['rank']}')),
                        title: Text(p['name'] as String? ?? 'Unnamed'),
                        subtitle: Text([p['brand'], if (p['rank'] == 1) 'Best in category'].whereType<String>().join(' · ')),
                        trailing: Text('${p['score']}', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
                      ),
                    if (r['locked'] == true)
                      UpgradeNotice(message: 'Showing the top ${rows.length} of ${r['total']}. Full rankings are included with Plus.', tier: 'plus'),
                  ]);
                },
              ),
            ),
          ]);
        },
      ),
    );
  }
}

const _lang = {'pidgin': 'Pidgin', 'yoruba': 'Yoruba', 'igbo': 'Igbo', 'hausa': 'Hausa'};

class LocalFoodsScreen extends StatelessWidget {
  const LocalFoodsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Nigerian foods')),
      body: ApiView(
        path: '/local-foods',
        builder: (context, data, _) {
          final foods = (data['foods'] as List).cast<Map<String, dynamic>>();
          return ListView(padding: const EdgeInsets.all(12), children: [
            for (final f in foods)
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(f['name'] as String, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800)),
                    if ((f['names'] as Map).isNotEmpty)
                      Text((f['names'] as Map).entries.map((e) => '${_lang[e.key] ?? e.key}: ${e.value}').join(' · '),
                          style: const TextStyle(fontSize: 12)),
                    const SizedBox(height: 6),
                    Text(f['description'] as String),
                    const SizedBox(height: 6),
                    Text('Cooking: ${f['preparation']}. ${f['nutrition_notes']}'),
                    if (f['recipe_id'] != null)
                      TextButton(
                        onPressed: () => Navigator.of(context)
                            .push(MaterialPageRoute(builder: (_) => RecipeScreen(recipeId: f['recipe_id'] as String))),
                        child: const Text('See the recipe'),
                      ),
                  ]),
                ),
              ),
            Padding(padding: const EdgeInsets.all(8), child: Text(data['note'] as String, style: const TextStyle(fontSize: 12))),
          ]);
        },
      ),
    );
  }
}

class SafetyScreen extends StatelessWidget {
  const SafetyScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Food safety research')),
      body: ApiView(
        path: '/safety/topics',
        builder: (context, data, _) {
          final r = data['risk_explainer'] as Map<String, dynamic>;
          final topics = (data['topics'] as List).cast<Map<String, dynamic>>();
          return ListView(padding: const EdgeInsets.all(12), children: [
            Card(
              color: Theme.of(context).colorScheme.primaryContainer,
              child: Padding(
                padding: const EdgeInsets.all(14),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  const Text('Hazard, exposure and risk', style: TextStyle(fontWeight: FontWeight.w800)),
                  for (final k in ['hazard', 'exposure', 'risk']) Text(r[k] as String),
                  const SizedBox(height: 6),
                  Text(r['product_rule'] as String, style: const TextStyle(fontWeight: FontWeight.w700)),
                ]),
              ),
            ),
            for (final t in topics)
              Card(
                child: ExpansionTile(
                  title: Text(t['title'] as String, style: const TextStyle(fontWeight: FontWeight.w700)),
                  subtitle: Text(t['summary'] as String, maxLines: 2, overflow: TextOverflow.ellipsis),
                  childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
                  expandedCrossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(t['summary'] as String),
                    const SizedBox(height: 8),
                    const Text('Found in (by food type)', style: TextStyle(fontWeight: FontWeight.w700)),
                    for (final w in t['where_found'] as List) Text('• $w'),
                    const SizedBox(height: 8),
                    const Text('What you can do', style: TextStyle(fontWeight: FontWeight.w700)),
                    for (final w in t['reduce_exposure'] as List) Text('• $w'),
                    const SizedBox(height: 8),
                    for (final s in (t['sources'] as List).cast<Map<String, dynamic>>())
                      Text('${s['title']} · ${s['publisher'] ?? ''} ${s['year'] ?? ''}', style: const TextStyle(fontSize: 12)),
                  ],
                ),
              ),
          ]);
        },
      ),
    );
  }
}

class LearnScreen extends StatelessWidget {
  const LearnScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Learn')),
      body: ApiView(
        path: '/articles',
        builder: (context, data, _) => ListView(padding: const EdgeInsets.all(12), children: [
          for (final a in (data as List).cast<Map<String, dynamic>>())
            Card(
              child: ListTile(
                title: Text(a['title'] as String, style: const TextStyle(fontWeight: FontWeight.w700)),
                subtitle: Text(a['summary'] as String),
                onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ArticleScreen(slug: a['slug'] as String))),
              ),
            ),
        ]),
      ),
    );
  }
}

class ArticleScreen extends StatelessWidget {
  const ArticleScreen({super.key, required this.slug});
  final String slug;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(),
      body: ApiView(
        path: '/articles/$slug',
        builder: (context, a, _) => ListView(padding: const EdgeInsets.all(16), children: [
          Text(a['title'] as String, style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800)),
          const SizedBox(height: 12),
          for (final p in (a['body'] as String).split('\n\n')) Padding(padding: const EdgeInsets.only(bottom: 12), child: Text(p)),
          const SectionHeader('Sources'),
          for (final s in (a['sources'] as List).cast<Map<String, dynamic>>())
            Text('• ${s['title']} (${s['publisher'] ?? ''}${s['year'] != null ? ', ${s['year']}' : ''})', style: const TextStyle(fontSize: 13)),
        ]),
      ),
    );
  }
}
