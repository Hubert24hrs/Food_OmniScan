import 'package:flutter/material.dart';

import '../core/theme.dart';
import 'score_widgets.dart';

const _compLabel = {
  'nutrition': 'Nutrition',
  'ingredients': 'Ingredients & additives',
  'processing': 'Processing',
  'dietary_suitability': 'Dietary suitability',
  'product_concerns': 'Product-specific concerns',
};

/// Renders the API's `analysis` object. Critical allergen alerts always come first.
class AnalysisView extends StatelessWidget {
  const AnalysisView({super.key, required this.analysis});
  final Map<String, dynamic> analysis;

  @override
  Widget build(BuildContext context) {
    final score = analysis['score'] as Map<String, dynamic>;
    final compat = (analysis['compatibility'] as List? ?? []).cast<Map<String, dynamic>>();
    final alerts = [
      for (final c in compat)
        for (final a in (c['critical_allergen_alerts'] as List).cast<Map<String, dynamic>>()) '${c['profile_name']}: ${a['message']}'
    ];
    final recalls = (analysis['recalls'] as List? ?? []).cast<Map<String, dynamic>>();
    final comps = (score['components'] as Map<String, dynamic>);
    final allergens = (analysis['allergens'] as List).cast<Map<String, dynamic>>();
    final ingredients = (analysis['ingredients'] as List).cast<Map<String, dynamic>>();
    final t = Theme.of(context).textTheme;

    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      if (alerts.isNotEmpty)
        _Banner(
          color: Brand.bad,
          icon: Icons.report_rounded,
          title: 'Allergen alert',
          lines: [...alerts, 'Always check the physical package.'],
        ),
      for (final r in recalls)
        _Banner(color: Brand.bad, icon: Icons.gpp_maybe, title: 'Active recall', lines: ['${r['authority']}: ${r['title']}. ${r['reason']}']),
      if (compat.isNotEmpty)
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('For your profiles', style: t.titleMedium?.copyWith(fontWeight: FontWeight.w800)),
              const SizedBox(height: 8),
              for (final c in compat) ...[
                VerdictChip(verdict: c['verdict'] as String, name: c['profile_name'] as String),
                const SizedBox(height: 6),
                for (final r in (c['reasons'] as List).cast<Map<String, dynamic>>().where((r) => r['severity'] != 'green').take(6))
                  Padding(
                    padding: const EdgeInsets.only(bottom: 4),
                    child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Icon(Icons.circle, size: 8, color: Brand.verdictColor(r['severity'] as String)),
                      const SizedBox(width: 8),
                      Expanded(child: Text(r['message'] as String)),
                    ]),
                  ),
              ],
              Text(compat.first['disclaimer'] as String, style: t.bodySmall),
            ]),
          ),
        ),
      Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              ScoreRing(score: score['overall'] as int?, color: score['color'] as String?, label: score['label'] as String),
              const SizedBox(width: 16),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(score['label'] as String, style: t.headlineSmall?.copyWith(fontWeight: FontWeight.w800)),
                  const SizedBox(height: 6),
                  Wrap(spacing: 6, runSpacing: 6, children: [
                    Pill('${score['confidence']} confidence'),
                    if (comps['processing']['nova_group'] != null)
                      Pill('NOVA ${comps['processing']['nova_group']}${comps['processing']['nova_source'] == 'estimated' ? ' (est.)' : ''}',
                          color: comps['processing']['nova_group'] == 4 ? Brand.bad : Brand.warn),
                  ]),
                  if (score['insufficient_data'] == true)
                    Padding(
                      padding: const EdgeInsets.only(top: 8),
                      child: Text("Not enough data for an overall score. We don't guess.", style: t.bodySmall),
                    ),
                ]),
              ),
            ]),
            for (final cap in (score['caps_applied'] as List).cast<Map<String, dynamic>>())
              Padding(padding: const EdgeInsets.only(top: 8), child: Text('• ${cap['reason']}', style: t.bodySmall)),
            const SizedBox(height: 8),
            for (final e in comps.entries) _ComponentTile(name: _compLabel[e.key] ?? e.key, c: e.value as Map<String, dynamic>),
            const SizedBox(height: 8),
            Text(score['disclaimer'] as String, style: t.bodySmall),
          ]),
        ),
      ),
      Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('Allergens', style: t.titleMedium?.copyWith(fontWeight: FontWeight.w800)),
            const SizedBox(height: 8),
            for (final a in allergens.where((a) => a['regulated_in_region'] == true || a['status'] == 'contains' || a['status'] == 'may_contain'))
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 3),
                child: Row(children: [
                  Expanded(child: Text(a['name'] as String)),
                  Pill(
                    switch (a['status']) {
                      'contains' => 'Contains',
                      'may_contain' => 'May contain',
                      'unknown' => 'Unknown',
                      _ => 'Not detected',
                    },
                    color: switch (a['status']) {
                      'contains' => Brand.bad,
                      'may_contain' => Brand.warn,
                      'unknown' => Brand.grey,
                      _ => Brand.good,
                    },
                  ),
                ]),
              ),
            const SizedBox(height: 6),
            Text('"Not detected" means not found in the listed ingredients. It isn\'t a guarantee.', style: t.bodySmall),
          ]),
        ),
      ),
      if (ingredients.isNotEmpty)
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Ingredients', style: t.titleMedium?.copyWith(fontWeight: FontWeight.w800)),
              for (final i in ingredients.where((i) => i['is_group'] != true))
                Padding(
                  padding: EdgeInsets.only(left: 12.0 * (i['depth'] as int), top: 6),
                  child: Row(children: [
                    Expanded(
                      child: Text(
                        i['ingredient'] == null
                            ? '${i['text']} (not in database yet)'
                            : '${i['ingredient']['name']}${i['ingredient']['e_number'] != null ? ' · ${i['ingredient']['e_number']}' : ''}',
                      ),
                    ),
                    if (i['ingredient'] != null && i['ingredient']['concern_level'] != 'neutral')
                      Pill(i['ingredient']['concern_level'] as String,
                          color: switch (i['ingredient']['concern_level']) {
                            'concern' => Brand.bad,
                            'caution' => Brand.warn,
                            'beneficial' => Brand.good,
                            _ => Brand.grey,
                          }),
                  ]),
                ),
            ]),
          ),
        ),
      if (analysis['contaminant_testing'] != null)
        Padding(
          padding: const EdgeInsets.all(12),
          child: Text(analysis['contaminant_testing']['message'] as String, style: t.bodySmall),
        ),
    ]);
  }
}

class _ComponentTile extends StatelessWidget {
  const _ComponentTile({required this.name, required this.c});
  final String name;
  final Map<String, dynamic> c;

  @override
  Widget build(BuildContext context) {
    final assessed = c['assessed'] == true;
    final s = c['score'] as int?;
    final color = !assessed || s == null ? Brand.grey : s >= 50 ? Brand.good : s >= 35 ? Brand.warn : Brand.bad;
    final adj = (c['adjustments'] as List).cast<Map<String, dynamic>>();
    final notes = (c['notes'] as List).cast<String>();
    return ExpansionTile(
      tilePadding: EdgeInsets.zero,
      title: Text('$name · ${c['weight']}%', style: const TextStyle(fontWeight: FontWeight.w600)),
      subtitle: LinearProgressIndicator(value: assessed && s != null ? s / 100 : 0, color: color, minHeight: 6),
      trailing: Text(assessed && s != null ? '$s' : 'n/a', style: TextStyle(color: color, fontWeight: FontWeight.w700)),
      children: [
        for (final a in adj)
          ListTile(
            dense: true,
            contentPadding: EdgeInsets.zero,
            leading: Text('${(a['points'] as num) > 0 ? '+' : ''}${a['points']}',
                style: TextStyle(fontWeight: FontWeight.w800, color: (a['points'] as num) < 0 ? Brand.bad : Brand.good)),
            title: Text(a['reason'] as String),
            subtitle: Text([a['evidence_type'], ...(a['source_keys'] as List)].join(' · ')),
          ),
        for (final n in notes) ListTile(dense: true, contentPadding: EdgeInsets.zero, leading: const Icon(Icons.info_outline, size: 18), title: Text(n)),
      ],
    );
  }
}

class _Banner extends StatelessWidget {
  const _Banner({required this.color, required this.icon, required this.title, required this.lines});
  final Color color;
  final IconData icon;
  final String title;
  final List<String> lines;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      liveRegion: true,
      child: Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.12),
          border: Border.all(color: color, width: 2),
          borderRadius: BorderRadius.circular(18),
        ),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(icon, color: color),
          const SizedBox(width: 10),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(title, style: TextStyle(color: color, fontWeight: FontWeight.w800, fontSize: 17)),
              for (final l in lines) Text(l, style: TextStyle(color: color)),
            ]),
          ),
        ]),
      ),
    );
  }
}
