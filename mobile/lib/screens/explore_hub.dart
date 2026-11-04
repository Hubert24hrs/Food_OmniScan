import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../core/app_state.dart';
import '../widgets/common.dart';
import '../widgets/fresh.dart';
import 'account_extras.dart';
import 'admin_screens.dart';
import 'assistant_screen.dart';
import 'explore_screens.dart';
import 'home_screens.dart';
import 'kitchen_screens.dart';
import 'label_screen.dart';
import 'more_screens.dart';
import 'recipe_screens.dart';
import 'scan_screen.dart';
import 'paywall_screen.dart';
import '../core/theme.dart';

typedef Feature = (IconData icon, String title, String subtitle, String? plan, Widget Function() screen);

/// Every feature of the app, grouped, so nothing is hidden. Used by the Explore tab and Home.
List<(String, List<Feature>)> featureSections({required bool staff}) => [
      (
        'Scan & find',
        [
          (Icons.qr_code_scanner, 'Scan a barcode', 'Instant score, allergens and ingredients', null, () => const ScanScreen()),
          (Icons.document_scanner_outlined, 'Scan a label', 'Ingredients and Nutrition Facts from a photo', null, () => const LabelScreen()),
          (Icons.search, 'Search products', 'By name, brand, category or barcode', null, () => const DiscoverScreen()),
          (Icons.compare_arrows, 'Compare products', 'Side by side: nutrition, additives, your profile', null, () => const CompareScreen()),
          (Icons.history, 'Scan history', 'Everything you have scanned', null, () => const HistoryScreen()),
          (Icons.favorite_border, 'Saved & trusted', 'Your favourite and trusted products', null, () => const SavedScreen()),
          (Icons.add_box_outlined, 'Add a missing product', 'Photograph it; a moderator reviews it', null, () => const SubmitProductScreen()),
        ],
      ),
      (
        'Eat & track',
        [
          (Icons.restaurant_menu, 'Recipes', 'Nigerian, US and European, checked for your allergies', null, () => const RecipesScreen()),
          (Icons.calendar_month, 'Meal planner', 'Plan the week, AI plans, shopping list', 'Plus', () => const MealPlansScreen()),
          (Icons.auto_awesome, 'Ask the nutrition assistant', 'Grounded answers, in your language', null, () => const AssistantScreen()),
          (Icons.thumb_up_alt_outlined, 'Picked for you', 'Better products in what you buy', 'Plus', () => const RecommendationsScreen()),
          (Icons.emoji_events_outlined, 'Category rankings', 'Best-scoring products per category', null, () => const RankingsScreen()),
        ],
      ),
      (
        'Home & shopping',
        [
          (Icons.checklist, 'Shopping lists', 'Lists from recipes and meal plans', null, () => const ShoppingListsScreen()),
          (Icons.kitchen, 'Pantry', 'What is at home, with expiry reminders', 'Plus', () => const PantryScreen()),
          (Icons.account_balance_wallet_outlined, 'Grocery budget', 'Spending and shopping history', 'Plus', () => const BudgetScreen()),
          (Icons.home_outlined, 'Household', 'Share pantry, lists and budget', 'Family', () => const HouseholdScreen()),
        ],
      ),
      (
        'Know your food',
        [
          (Icons.menu_book_outlined, 'Ingredient encyclopedia', 'What every ingredient and additive does', null, () => const IngredientsScreen()),
          (Icons.public, 'Nigerian foods', 'Dishes and Yoruba, Igbo, Hausa, Pidgin names', null, () => const LocalFoodsScreen()),
          (Icons.science_outlined, 'Food safety research', 'Heavy metals, microplastics, pesticides…', null, () => const SafetyScreen()),
          (Icons.report_gmailerrorred, 'Food recalls', 'Official recalls from FDA, FSA, NAFDAC', null, () => const RecallsScreen()),
          (Icons.school_outlined, 'Learn', 'Short, sourced food guides', null, () => const LearnScreen()),
          (Icons.library_books_outlined, 'Research sources', 'Every study and regulation we cite', null, () => const SourcesScreen()),
        ],
      ),
      (
        'You',
        [
          (Icons.notifications_none, 'Alerts', 'Recalls, allergen and expiry alerts', null, () => const NotificationsScreen()),
          (Icons.tune, 'Notification settings', 'Choose what we tell you about', null, () => const NotificationSettingsScreen()),
          (Icons.workspace_premium_outlined, 'Plans & usage', 'Upgrade, compare plans, see your allowance', null, () => const PaywallScreen()),
          (Icons.lock_outline, 'Privacy & data', 'Export or delete your data', null, () => const PrivacyScreen()),
          if (staff) (Icons.admin_panel_settings_outlined, 'Admin & moderation', 'Products, moderation, content, users', null, () => const AdminScreen()),
        ],
      ),
    ];

class ExploreScreen extends StatelessWidget {
  const ExploreScreen({super.key});

  Future<void> _identify(BuildContext context) async {
    final photo = await ImagePicker().pickImage(source: ImageSource.camera, maxWidth: 2000, imageQuality: 85);
    if (photo == null || !context.mounted) return;
    final api = context.read<AppState>().api;
    final r = await runAction(context, () async => api.upload('/analysis/image', fields: {'task': 'front'}, bytes: await photo.readAsBytes()));
    if (r is! Map || !context.mounted) return;
    final x = (r['extracted'] as Map?) ?? {};
    final term = (x['visible_barcode_digits'] as String?) ?? [x['brand'], x['product_name']].whereType<String>().join(' ');
    if (term.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Couldn't read the product name. Try the front of the pack in good light.")));
      return;
    }
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => DiscoverScreen(initialQuery: term)));
  }

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    final staff = app.me?['role'] == 'admin' || app.me?['role'] == 'moderator';
    var n = 0;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Explore'),
        actions: const [UpgradeChip()],
        bottom: const PreferredSize(preferredSize: Size.fromHeight(3), child: FreshStripe()),
      ),
      body: ListView(padding: const EdgeInsets.fromLTRB(12, 12, 12, 100), children: [
        const UpgradeBanner(),
        Row(children: [
          Expanded(
            child: TextField(
              readOnly: true,
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const DiscoverScreen())),
              decoration: const InputDecoration(prefixIcon: Icon(Icons.search), hintText: 'Search products, brands, barcodes'),
            ),
          ),
          const SizedBox(width: 8),
          IconButton.filledTonal(tooltip: 'Identify a product from a photo', onPressed: () => _identify(context), icon: const Icon(Icons.photo_camera_outlined)),
        ]),
        for (final (section, features) in featureSections(staff: staff)) ...[
          SectionHeader(section),
          for (final f in features)
            Card(
              child: ListTile(
                leading: IconTile(icon: f.$1, index: n++),
                title: Row(children: [
                  Flexible(child: Text(f.$2, style: const TextStyle(fontWeight: FontWeight.w700))),
                  if (f.$4 != null) ...[const SizedBox(width: 6), PlanBadge(f.$4!, locked: app.isFree)],
                ]),
                subtitle: Text(f.$3),
                trailing: Icon(f.$4 != null && app.isFree ? Icons.lock_outline : Icons.chevron_right),
                onTap: () => openFeature(context, f.$4, f.$5),
              ),
            ),
        ],
      ]),
    );
  }
}

/// Opens a feature, or the plans first when it needs a plan the user doesn't have.
void openFeature(BuildContext context, String? plan, Widget Function() screen) {
  if (plan != null && context.read<AppState>().isFree) {
    showPaywall(context, tier: plan.toLowerCase(), reason: '${plan == 'Family' ? 'Household sharing' : 'This feature'} is included with $plan.');
    return;
  }
  Navigator.of(context).push(MaterialPageRoute(builder: (_) => screen()));
}

/// "PLUS" / "FAMILY" tag; red with a lock while the user is on the free plan.
class PlanBadge extends StatelessWidget {
  const PlanBadge(this.plan, {super.key, this.locked = false});
  final String plan;
  final bool locked;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
        decoration: BoxDecoration(color: locked ? Brand.tomato : Brand.greenSoft, borderRadius: BorderRadius.circular(6)),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          if (locked) const Padding(padding: EdgeInsets.only(right: 3), child: Icon(Icons.lock, size: 11, color: Colors.white)),
          Text(plan.toUpperCase(),
              style: TextStyle(fontSize: 10, fontWeight: FontWeight.w800, letterSpacing: 0.4, color: locked ? Colors.white : Brand.green)),
        ]),
      );
}

/// Compact grid of the most-used features for the Home screen.
class QuickGrid extends StatelessWidget {
  const QuickGrid({super.key, required this.onAll});
  final VoidCallback onAll;

  @override
  Widget build(BuildContext context) {
    final free = context.watch<AppState>().isFree;
    final items = <(IconData, String, String?, Widget Function())>[
      (Icons.document_scanner_outlined, 'Scan label', null, () => const LabelScreen()),
      (Icons.restaurant_menu, 'Recipes', null, () => const RecipesScreen()),
      (Icons.calendar_month, 'Meal plan', 'Plus', () => const MealPlansScreen()),
      (Icons.checklist, 'Lists', null, () => const ShoppingListsScreen()),
      (Icons.kitchen, 'Pantry', 'Plus', () => const PantryScreen()),
      (Icons.auto_awesome, 'Ask AI', null, () => const AssistantScreen()),
      (Icons.notifications_none, 'Alerts', null, () => const NotificationsScreen()),
      (Icons.favorite_border, 'Saved', null, () => const SavedScreen()),
    ];
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      GridView.count(
        crossAxisCount: 4,
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        mainAxisSpacing: 8,
        crossAxisSpacing: 8,
        childAspectRatio: 0.85,
        children: [
          for (final (i, (icon, label, plan, screen)) in items.indexed)
            InkWell(
              borderRadius: BorderRadius.circular(16),
              onTap: () => openFeature(context, plan, screen),
              child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                Stack(clipBehavior: Clip.none, children: [
                  IconTile(icon: icon, index: i, size: 48),
                  if (plan != null && free)
                    const Positioned(
                      right: -4,
                      top: -4,
                      child: CircleAvatar(radius: 9, backgroundColor: Brand.tomato, child: Icon(Icons.lock, size: 11, color: Colors.white)),
                    ),
                ]),
                const SizedBox(height: 6),
                Text(label, textAlign: TextAlign.center, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
              ]),
            ),
        ],
      ),
      TextButton.icon(onPressed: onAll, icon: const Icon(Icons.apps), label: const Text('See all features')),
    ]);
  }
}
