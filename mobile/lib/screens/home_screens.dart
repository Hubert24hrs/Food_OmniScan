import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api.dart';
import '../core/app_state.dart';
import '../widgets/score_widgets.dart';
import 'explore_hub.dart';
import 'product_screen.dart';
import '../widgets/fresh.dart';
import 'paywall_screen.dart';

class ProductTile extends StatelessWidget {
  const ProductTile({super.key, required this.p, this.subtitle});
  final Map<String, dynamic> p;
  final String? subtitle;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        leading: p['image_url'] != null
            ? ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: Image.network(p['image_url'] as String, width: 48, height: 48, fit: BoxFit.contain,
                    errorBuilder: (_, _, _) => const Icon(Icons.inventory_2_outlined)),
              )
            : const Icon(Icons.inventory_2_outlined),
        title: Text(p['name'] as String? ?? 'Unnamed product', maxLines: 1, overflow: TextOverflow.ellipsis),
        subtitle: Text([p['brand'], subtitle].whereType<String>().join(' · '), maxLines: 1),
        trailing: MiniScore(score: p['score'] as int?, color: p['color'] as String?),
        onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ProductScreen(productId: p['id'] as String))),
      ),
    );
  }
}

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key, required this.onScan, this.onExplore});
  final VoidCallback onScan;
  final VoidCallback? onExplore;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  Future<List<Map<String, dynamic>>>? _recent;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _recent ??= _load();
  }

  Future<List<Map<String, dynamic>>> _load() async {
    final app = context.read<AppState>();
    if (app.signedIn && app.online) {
      try {
        final h = (await app.api.get('/history', query: {'limit': '10'}) as List).cast<Map<String, dynamic>>();
        return h.map((e) => e['product'] as Map<String, dynamic>).toList();
      } on ApiException {
        // fall through to offline cache
      }
    }
    final cached = await app.store.cachedProducts();
    return cached.map((c) {
      final p = c['product'] as Map<String, dynamic>;
      final s = (c['analysis'] as Map)['score'] as Map;
      return {...p, 'score': s['overall'], 'color': s['color']};
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    final t = Theme.of(context).textTheme;
    return Scaffold(
      appBar: AppBar(
        title: const Wordmark(),
        actions: const [UpgradeChip()],
        bottom: const PreferredSize(preferredSize: Size.fromHeight(3), child: FreshStripe()),
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          final f = _load();
          setState(() {
            _recent = f;
          });
          await f;
        },
        child: ListView(padding: const EdgeInsets.all(16), children: [
          Card(
            clipBehavior: Clip.antiAlias,
            child: Stack(children: [
              Positioned(
                right: -24,
                top: -10,
                bottom: -10,
                child: Opacity(opacity: 0.95, child: Image.asset('assets/brand/hero_plate.webp', fit: BoxFit.contain)),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 20, 120, 20),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text("Know what's inside.", style: t.headlineSmall?.copyWith(fontWeight: FontWeight.w800)),
                  const SizedBox(height: 4),
                  Text(app.activeProfile != null ? 'Checking for ${app.activeProfile!['name']}' : 'Scan a barcode or a label',
                      style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant)),
                  const SizedBox(height: 14),
                  FilledButton.icon(onPressed: widget.onScan, icon: const Icon(Icons.qr_code_scanner), label: const Text('Scan a product')),
                ]),
              ),
            ]),
          ),
          const SizedBox(height: 12),
          const UpgradeBanner(),
          const SizedBox(height: 4),
          QuickGrid(onAll: widget.onExplore ?? () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const ExploreScreen()))),
          const SizedBox(height: 16),
          Text('Recent', style: t.titleMedium?.copyWith(fontWeight: FontWeight.w800)),
          FutureBuilder(
            future: _recent,
            builder: (context, snap) {
              if (!snap.hasData) return const Padding(padding: EdgeInsets.all(24), child: Center(child: CircularProgressIndicator()));
              if (snap.data!.isEmpty) return const Padding(padding: EdgeInsets.all(24), child: Text('No scans yet.'));
              return Column(children: [for (final p in snap.data!) ProductTile(p: p)]);
            },
          ),
        ]),
      ),
    );
  }
}

class DiscoverScreen extends StatefulWidget {
  const DiscoverScreen({super.key, this.initialQuery});
  final String? initialQuery;

  @override
  State<DiscoverScreen> createState() => _DiscoverScreenState();
}

class _DiscoverScreenState extends State<DiscoverScreen> {
  late final q = TextEditingController(text: widget.initialQuery ?? '');
  List<Map<String, dynamic>>? results;
  String? error;
  bool busy = false;

  @override
  void initState() {
    super.initState();
    if ((widget.initialQuery ?? '').length >= 2) WidgetsBinding.instance.addPostFrameCallback((_) => _search());
  }

  Future<void> _search() async {
    if (q.text.trim().length < 2) return;
    setState(() {
      busy = true;
      error = null;
    });
    try {
      final r = await context.read<AppState>().api.get('/products/search', query: {'q': q.text.trim()}) as Map<String, dynamic>;
      setState(() => results = (r['results'] as List).cast<Map<String, dynamic>>());
    } on ApiException catch (e) {
      setState(() => error = e.message);
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Discover')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        TextField(
          controller: q,
          textInputAction: TextInputAction.search,
          onSubmitted: (_) => _search(),
          decoration: InputDecoration(
            hintText: 'Search products, brands, barcodes',
            prefixIcon: const Icon(Icons.search),
            suffixIcon: busy ? const Padding(padding: EdgeInsets.all(12), child: CircularProgressIndicator(strokeWidth: 2)) : null,
          ),
        ),
        if (error != null) Padding(padding: const EdgeInsets.only(top: 12), child: Text(error!)),
        if (results != null && results!.isEmpty) const Padding(padding: EdgeInsets.all(24), child: Text('No products found.')),
        for (final p in results ?? []) ProductTile(p: p),
        const Padding(
          padding: EdgeInsets.only(top: 16),
          child: Text('Data from Open Food Facts (ODbL) and USDA FoodData Central.', style: TextStyle(fontSize: 12)),
        ),
      ]),
    );
  }
}
