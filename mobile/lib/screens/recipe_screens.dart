import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/app_state.dart';
import '../widgets/common.dart';

class RecipesScreen extends StatefulWidget {
  const RecipesScreen({super.key});

  @override
  State<RecipesScreen> createState() => _RecipesScreenState();
}

class _RecipesScreenState extends State<RecipesScreen> {
  String region = '';

  Future<void> _generate() async {
    final ask = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Create a recipe with AI'),
        content: TextField(controller: ask, maxLength: 1000, decoration: const InputDecoration(hintText: 'e.g. a quick dinner with beans and plantain')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Create')),
        ],
      ),
    );
    if (ok != true || ask.text.trim().length < 3 || !mounted) return;
    final app = context.read<AppState>();
    final r = await runAction(context, () => app.api.postSlow('/recipes/generate', {
          'request': ask.text.trim(),
          'profile_id': app.activeProfile?['id'],
          if (region.isNotEmpty) 'region': region,
        }));
    if (r is Map && mounted) {
      Navigator.of(context).push(MaterialPageRoute(builder: (_) => RecipeScreen(recipeId: r['id'] as String)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final signedIn = context.watch<AppState>().signedIn;
    return Scaffold(
      appBar: AppBar(title: const Text('Recipes')),
      floatingActionButton: signedIn
          ? FloatingActionButton.extended(onPressed: _generate, icon: const Icon(Icons.auto_awesome), label: const Text('AI recipe'))
          : null,
      body: Column(children: [
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.all(8),
          child: Row(children: [
            for (final (k, l) in [('', 'All'), ('NG', 'Nigerian'), ('US', 'American'), ('EU', 'European')])
              Padding(
                padding: const EdgeInsets.only(right: 6),
                child: ChoiceChip(label: Text(l), selected: region == k, onSelected: (_) => setState(() => region = k)),
              ),
          ]),
        ),
        Expanded(
          child: ApiView(
            path: '/recipes',
            query: {if (region.isNotEmpty) 'region': region},
            builder: (context, data, _) => ListView(padding: const EdgeInsets.fromLTRB(12, 0, 12, 80), children: [
              for (final r in (data as List).cast<Map<String, dynamic>>())
                Card(
                  child: ListTile(
                    title: Text(r['title'] as String, style: const TextStyle(fontWeight: FontWeight.w700)),
                    subtitle: Text([r['cuisine'], if (r['time_minutes'] != null) '${r['time_minutes']} min', if (r['ai_generated'] == true) 'AI']
                        .whereType<String>()
                        .join(' · ')),
                    onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => RecipeScreen(recipeId: r['id'] as String))),
                  ),
                ),
            ]),
          ),
        ),
      ]),
    );
  }
}

class RecipeScreen extends StatelessWidget {
  const RecipeScreen({super.key, required this.recipeId});
  final String recipeId;

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    final pid = app.activeProfile?['id'] as String?;
    return Scaffold(
      appBar: AppBar(title: const Text('Recipe')),
      body: ApiView(
        path: '/recipes/$recipeId',
        query: {'profile_ids': ?pid},
        builder: (context, r, reload) {
          final compat = r['compatibility'] as Map<String, dynamic>?;
          final nutrition = r['nutrition_per_serving'] as Map<String, dynamic>?;
          return ListView(padding: const EdgeInsets.all(16), children: [
            Text(r['title'] as String, style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800)),
            if (r['description'] != null) Text(r['description'] as String),
            if (r['ai_generated'] == true) const Padding(padding: EdgeInsets.only(top: 6), child: Text('AI-generated recipe', style: TextStyle(fontWeight: FontWeight.w700))),
            if (compat != null)
              Card(
                margin: const EdgeInsets.only(top: 12),
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    for (final p in (compat['profiles'] as List).cast<Map<String, dynamic>>()) ...[
                      Text('${p['profile_name']}: ${p['verdict'] == 'red' ? 'Avoid' : p['verdict'] == 'yellow' ? 'Check' : 'OK'}',
                          style: TextStyle(fontWeight: FontWeight.w800, color: p['verdict'] == 'red' ? Colors.red : null)),
                      for (final reason in (p['reasons'] as List).where((x) => x['severity'] != 'green')) Text('• ${reason['message']}'),
                    ],
                    for (final s in (compat['substitutions'] as List).cast<Map<String, dynamic>>())
                      Text('Swap: ${(s['replace'] as List).join(', ')} → ${s['with']}'),
                    Text(compat['note'] as String, style: const TextStyle(fontSize: 12)),
                  ]),
                ),
              ),
            const SectionHeader('Ingredients'),
            for (final i in (r['ingredients'] as List).cast<Map<String, dynamic>>())
              Text('• ${i['quantity'] != null ? '${i['quantity']} ${i['unit'] ?? ''} ' : ''}${i['name']}${i['note'] != null ? ' (${i['note']})' : ''}'),
            const SizedBox(height: 8),
            if (app.signedIn)
              OutlinedButton.icon(
                onPressed: () => runAction(context, () => app.api.post('/recipes/$recipeId/shopping-list', {}), ok: 'Added to a new shopping list'),
                icon: const Icon(Icons.playlist_add),
                label: const Text('Add ingredients to a shopping list'),
              ),
            const SectionHeader('Method'),
            for (final (i, s) in (r['steps'] as List).indexed) Padding(padding: const EdgeInsets.only(bottom: 6), child: Text('${i + 1}. $s')),
            if (r['preparation_notes'] != null)
              Card(child: Padding(padding: const EdgeInsets.all(12), child: Text('How cooking affects nutrition: ${r['preparation_notes']}'))),
            const SectionHeader('Nutrition per serving'),
            if (nutrition != null) ...[
              Text(nutrition.entries.map((e) => '${e.key.replaceAll('_', ' ')}: ${(e.value as num).round()}').join(' · ')),
              const Text('Rough AI estimate, not a measurement.', style: TextStyle(fontSize: 12)),
            ] else ...[
              const Text("No nutrition values yet. We don't invent numbers."),
              if (app.signedIn)
                TextButton.icon(
                  onPressed: () async {
                    await runAction(context, () => app.api.postSlow('/recipes/$recipeId/nutrition-estimate', {}));
                    await reload();
                  },
                  icon: const Icon(Icons.auto_awesome),
                  label: const Text('Estimate with AI'),
                ),
            ],
          ]);
        },
      ),
    );
  }
}

class MealPlansScreen extends StatefulWidget {
  const MealPlansScreen({super.key});

  @override
  State<MealPlansScreen> createState() => _MealPlansScreenState();
}

class _MealPlansScreenState extends State<MealPlansScreen> {
  final _key = GlobalKey();

  Future<void> _generate() async {
    var days = 3;
    var region = 'NG';
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => StatefulBuilder(
        builder: (c, set) => AlertDialog(
          title: const Text('Plan with AI'),
          content: Column(mainAxisSize: MainAxisSize.min, children: [
            DropdownButtonFormField<int>(
              initialValue: days,
              decoration: const InputDecoration(labelText: 'Days'),
              items: [for (var d = 1; d <= 7; d++) DropdownMenuItem(value: d, child: Text('$d'))],
              onChanged: (v) => set(() => days = v ?? 3),
            ),
            DropdownButtonFormField<String>(
              initialValue: region,
              decoration: const InputDecoration(labelText: 'Cuisine'),
              items: const [
                DropdownMenuItem(value: 'NG', child: Text('Nigerian')),
                DropdownMenuItem(value: 'US', child: Text('American')),
                DropdownMenuItem(value: 'EU', child: Text('European')),
              ],
              onChanged: (v) => set(() => region = v ?? 'NG'),
            ),
            const SizedBox(height: 8),
            const Text('Follows your profile\'s allergies and diets. Included with Premium.', style: TextStyle(fontSize: 12)),
          ]),
          actions: [
            TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancel')),
            FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Create')),
          ],
        ),
      ),
    );
    if (ok != true || !mounted) return;
    final app = context.read<AppState>();
    final r = await runAction(context, () => app.api.postSlow('/meal-plans/generate', {
          'days': days,
          'region': region,
          'profile_id': app.activeProfile?['id'],
        }));
    if (r is Map && mounted) {
      await Navigator.of(context).push(MaterialPageRoute(builder: (_) => MealPlanScreen(planId: r['id'] as String)));
      setState(() {});
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Meal planner')),
      floatingActionButton: FloatingActionButton.extended(onPressed: _generate, icon: const Icon(Icons.auto_awesome), label: const Text('Plan with AI')),
      body: ApiView(
        key: _key,
        path: '/meal-plans',
        signedIn: true,
        builder: (context, data, _) {
          final plans = (data as List).cast<Map<String, dynamic>>();
          if (plans.isEmpty) return const Center(child: Text('No meal plans yet.'));
          return ListView(padding: const EdgeInsets.all(12), children: [
            for (final p in plans)
              Card(
                child: ListTile(
                  title: Text(p['name'] as String),
                  subtitle: Text('${(p['days'] as List).length} day(s)'),
                  onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => MealPlanScreen(planId: p['id'] as String))),
                ),
              ),
          ]);
        },
      ),
    );
  }
}

class MealPlanScreen extends StatelessWidget {
  const MealPlanScreen({super.key, required this.planId});
  final String planId;

  @override
  Widget build(BuildContext context) {
    final app = context.read<AppState>();
    return Scaffold(
      appBar: AppBar(title: const Text('Meal plan'), actions: [
        IconButton(
          tooltip: 'Make a shopping list',
          icon: const Icon(Icons.playlist_add),
          onPressed: () => runAction(context, () => app.api.post('/meal-plans/$planId/shopping-list', {}), ok: 'Shopping list created'),
        ),
      ]),
      body: ApiView(
        path: '/meal-plans/$planId',
        builder: (context, p, _) => ListView(padding: const EdgeInsets.all(12), children: [
          Text(p['name'] as String, style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800)),
          for (final d in (p['days'] as List).cast<Map<String, dynamic>>())
            Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('Day ${d['day']}', style: const TextStyle(fontWeight: FontWeight.w800)),
                  for (final m in (d['meals'] as List).cast<Map<String, dynamic>>())
                    ListTile(
                      dense: true,
                      contentPadding: EdgeInsets.zero,
                      title: Text(m['title'] as String),
                      subtitle: Text('${m['meal_type']}${m['estimated_kcal'] != null ? ' · ~${(m['estimated_kcal'] as num).round()} kcal (estimate)' : ''}'),
                      trailing: m['recipe_id'] != null ? const Icon(Icons.chevron_right) : null,
                      onTap: m['recipe_id'] == null
                          ? null
                          : () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => RecipeScreen(recipeId: m['recipe_id'] as String))),
                    ),
                ]),
              ),
            ),
        ]),
      ),
    );
  }
}
