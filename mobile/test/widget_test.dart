import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:food_omniscan/core/api.dart';
import 'package:food_omniscan/core/app_state.dart';
import 'package:food_omniscan/core/offline.dart';
import 'package:food_omniscan/core/scan_codes.dart';
import 'package:food_omniscan/core/theme.dart';
import 'package:food_omniscan/screens/assistant_screen.dart';
import 'package:food_omniscan/screens/diary_screen.dart';
import 'package:food_omniscan/screens/explore_hub.dart';
import 'package:food_omniscan/screens/paywall_screen.dart';
import 'package:food_omniscan/widgets/common.dart';
import 'package:food_omniscan/widgets/fresh.dart';
import 'package:food_omniscan/widgets/analysis_view.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

Map<String, dynamic> analysisFixture({bool allergen = true}) => {
      'score': {
        'methodology_version': '2026.11-us.1',
        'overall': 10,
        'grade': 'poor',
        'color': 'red',
        'label': 'Poor',
        'confidence': 'high',
        'insufficient_data': false,
        'caps_applied': [
          {'code': 'cap.nutrition', 'max': 10, 'reason': 'Poor nutrition limits the overall score.'}
        ],
        'components': {
          'nutrition': {
            'assessed': true,
            'score': 0,
            'weight': 40,
            'adjustments': [
              {'code': 'nutrition.added_sugars', 'points': -60, 'reason': 'Added sugars is high', 'evidence_type': 'product_measurement', 'source_keys': ['fda_21cfr101_9']}
            ],
            'notes': <String>[],
          },
          'processing': {'assessed': true, 'score': 10, 'weight': 15, 'adjustments': [], 'notes': <String>[], 'nova_group': 4, 'nova_source': 'off'},
        },
        'disclaimer': 'Not medical advice.',
      },
      'ingredients': [
        {'text': 'sugar', 'depth': 0, 'is_group': false, 'ingredient': {'name': 'Sugar', 'e_number': null, 'concern_level': 'neutral'}},
        {'text': 'zorbleflux', 'depth': 0, 'is_group': false, 'ingredient': null},
      ],
      'allergens': [
        {'code': 'nuts', 'name': 'Tree nuts', 'status': allergen ? 'contains' : 'not_detected', 'regulated_in_region': true, 'evidence': []},
      ],
      'compatibility': [
        {
          'profile_name': 'Ada',
          'verdict': allergen ? 'red' : 'green',
          'critical_allergen_alerts': allergen
              ? [
                  {'allergen': 'nuts', 'message': 'Contains tree nuts (almond).'}
                ]
              : [],
          'reasons': [],
          'disclaimer': 'Always read the label.',
        }
      ],
    };

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));

  test('score and verdict colors are consistent', () {
    expect(Brand.scoreColor('green'), Brand.good);
    expect(Brand.scoreColor('red'), Brand.bad);
    expect(Brand.scoreColor(null), Brand.grey);
    expect(Brand.verdictLabel('red'), 'Avoid');
  });

  test('offline queue syncs idempotently and keeps retry_later items', () async {
    final store = OfflineStore();
    final a = await store.enqueue('0049000000443');
    final b = await store.enqueue('3017620422003');
    expect((await store.queue()).length, 2);

    late List<dynamic> sent;
    final api = ApiClient(
      baseUrl: 'http://api.test/api/v1',
      client: MockClient((req) async {
        sent = jsonDecode(req.body) as List;
        return http.Response(
            jsonEncode({
              'results': [
                {'client_id': a.clientId, 'status': 'found'},
                {'client_id': b.clientId, 'status': 'retry_later'},
              ]
            }),
            200);
      }),
    );
    await api.setToken('test-token');
    expect(await store.sync(api), 1);
    expect(sent.first['client_id'], a.clientId);
    final left = await store.queue();
    expect(left.single.clientId, b.clientId);
  });

  test('api client surfaces structured error codes', () async {
    final api = ApiClient(
      baseUrl: 'http://api.test/api/v1',
      client: MockClient((_) async => http.Response(
          jsonEncode({'detail': {'code': 'product_not_found', 'message': "We couldn't find this product."}}), 404)),
    );
    expect(
      () => api.get('/products/barcode/0012345678905'),
      throwsA(isA<ApiException>().having((e) => e.code, 'code', 'product_not_found')),
    );
  });

  test('product cache keeps most recent entries', () async {
    final store = OfflineStore();
    await store.cacheProduct('p1', {'product': {'id': 'p1'}});
    await store.cacheProduct('p2', {'product': {'id': 'p2'}});
    expect((await store.cachedProduct('p1'))!['product']['id'], 'p1');
    expect((await store.cachedProducts()).first['product']['id'], 'p2');
  });

  testWidgets('critical allergen banner is shown above the score', (tester) async {
    await tester.pumpWidget(MaterialApp(home: Scaffold(body: SingleChildScrollView(child: AnalysisView(analysis: analysisFixture())))));
    expect(find.text('Allergen alert'), findsOneWidget);
    expect(find.textContaining('Contains tree nuts'), findsWidgets);
    expect(find.text('Avoid', findRichText: true), findsNothing); // verdict chip combines name + label
    expect(find.textContaining('Ada: Avoid'), findsOneWidget);
    expect(find.text('zorbleflux (not in database yet)'), findsOneWidget);
    final bannerY = tester.getTopLeft(find.text('Allergen alert')).dy;
    final scoreY = tester.getTopLeft(find.text('Poor').first).dy;
    expect(bannerY, lessThan(scoreY));
  });

  testWidgets('no banner when allergen not detected', (tester) async {
    await tester.pumpWidget(MaterialApp(home: Scaffold(body: SingleChildScrollView(child: AnalysisView(analysis: analysisFixture(allergen: false))))));
    expect(find.text('Allergen alert'), findsNothing);
    expect(find.textContaining("isn't a guarantee"), findsOneWidget);
  });

  test('photo upload is multipart with the session token', () async {
    late http.BaseRequest seen;
    final api = ApiClient(
      baseUrl: 'http://api.test/api/v1',
      client: MockClient.streaming((req, body) async {
        seen = req;
        final raw = utf8.decode(await body.toBytes(), allowMalformed: true);
        expect(raw, contains('name="task"'));
        expect(raw, contains('name="image"; filename="photo.jpg"'));
        return http.StreamedResponse(Stream.value(utf8.encode(jsonEncode({'extracted': {'panel_text': 'Calories 200'}}))), 200);
      }),
    );
    await api.setToken('test-token');
    final r = await api.upload('/analysis/image', fields: {'task': 'nutrition'}, bytes: [0xFF, 0xD8, 0xFF]) as Map;
    expect(seen.headers['Authorization'], 'Bearer test-token');
    expect(seen.headers['content-type'], startsWith('multipart/form-data'));
    expect(r['extracted']['panel_text'], 'Calories 200');
  });

  test('assistant errors read plainly and markdown is cleaned', () {
    expect(assistantErrorText(ApiException(402, "You've used all 5 ai assistant credits this month on the free plan.", code: 'quota_exceeded')),
        contains('Upgrade your plan'));
    expect(assistantErrorText(ApiException(503, 'x', code: 'ai_not_configured')), contains("aren't switched on"));
    expect(MessageBubble.plainText('* **Milk:** contains\n- Soy'), '• Milk: contains\n• Soy');
  });

  testWidgets('assistant sends the product and shows a grounded answer', (tester) async {
    late Map<String, dynamic> sent;
    final api = ApiClient(
      baseUrl: 'http://api.test/api/v1',
      client: MockClient((req) async {
        sent = jsonDecode(req.body) as Map<String, dynamic>;
        return http.Response(
            jsonEncode({
              'answer': 'It is **high** in added sugar.',
              'sources': [
                {'key': 'fda_5_20_rule', 'title': 'FDA 5/20', 'url': null}
              ],
            }),
            200);
      }),
    );
    final app = AppState(api: api)..me = {'id': 'u1'};
    await tester.pumpWidget(ChangeNotifierProvider.value(
        value: app, child: const MaterialApp(home: AssistantScreen(productId: 'p1', productName: 'Nutella'))));
    expect(find.text('Asking about Nutella'), findsOneWidget);
    await tester.tap(find.text('Why did this product get its score?'));
    await tester.pumpAndSettle();
    expect(sent['product_ids'], ['p1']);
    expect(sent['question'], 'Why did this product get its score?');
    expect(find.text('It is high in added sugar.'), findsOneWidget);
    expect(find.text('fda_5_20_rule'), findsOneWidget);
    expect(find.textContaining('not medical advice'), findsWidgets);
  });

  testWidgets('assistant asks signed-out users to sign in', (tester) async {
    final app = AppState(api: ApiClient(baseUrl: 'http://api.test/api/v1', client: MockClient((_) async => http.Response('{}', 200))));
    await tester.pumpWidget(ChangeNotifierProvider.value(value: app, child: const MaterialApp(home: AssistantScreen())));
    expect(find.textContaining('Sign in on the Profile tab'), findsOneWidget);
  });

  testWidgets('plan errors show an upgrade notice naming the plan', (tester) async {
    final e = ApiException(402, 'Pantry and expiry reminders is included with Plus.', code: 'upgrade_required',
        detail: {'code': 'upgrade_required', 'required_tier': 'plus'});
    expect(e.isPlan, isTrue);
    expect(e.requiredTier, 'plus');
    await tester.pumpWidget(MaterialApp(home: Scaffold(body: errorView(e))));
    expect(find.text('Included with Plus'), findsOneWidget);
    expect(find.byType(UpgradeNotice), findsOneWidget);
  });

  testWidgets('diary shows targets, water and the vitamins upgrade prompt', (tester) async {
    await tester.binding.setSurfaceSize(const Size(500, 2400));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final api = ApiClient(
      baseUrl: 'http://api.test/api/v1',
      client: MockClient((req) async => http.Response(
          jsonEncode({
            'day': '2026-11-04',
            'entries': [
              {'id': 'e1', 'meal_type': 'lunch', 'description': 'Jollof rice', 'energy_kcal': 450, 'is_estimate': true}
            ],
            'totals': {'energy_kcal': 450, 'protein': 10, 'carbohydrates': 80, 'fat': 12, 'fiber': 3, 'sugars': 4, 'sodium_mg': 600,
                       'includes_estimates': true},
            'goals': {},
            'targets': {'energy_kcal': 2000, 'protein': 50, 'carbohydrates': 275, 'fat': 78, 'fiber': 28, 'sodium_mg': 2300, 'water_ml': 2000},
            'water': {'total_ml': 750, 'logs': []},
            'micros': null,
            'micros_locked': true,
          }),
          200)),
    );
    final app = AppState(api: api)..me = {'id': 'u1'};
    await tester.pumpWidget(ChangeNotifierProvider.value(value: app, child: const MaterialApp(home: DiaryScreen())));
    await tester.pumpAndSettle();
    expect(find.text('750 ml of 2000 ml'), findsOneWidget);
    expect(find.text('of 2000'), findsOneWidget);
    expect(find.textContaining('Jollof rice'), findsOneWidget);
    expect(find.text('lunch · estimate'), findsOneWidget);
    expect(find.text('Included with Plus'), findsOneWidget);
  });

  testWidgets('explore lists every feature, and admin tools only for staff', (tester) async {
    await tester.binding.setSurfaceSize(const Size(800, 6000));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final api = ApiClient(baseUrl: 'http://api.test/api/v1', client: MockClient((_) async => http.Response('{}', 200)));
    final app = AppState(api: api)..me = {'id': 'u1', 'role': 'user'};
    await tester.pumpWidget(ChangeNotifierProvider.value(value: app, child: const MaterialApp(home: ExploreScreen())));
    const titles = [
      'Scan a barcode', 'Scan a label', 'Search products', 'Compare products', 'Scan history', 'Saved & trusted', 'Add a missing product',
      'Recipes', 'Meal planner', 'Ask the nutrition assistant', 'Picked for you', 'Category rankings',
      'Shopping lists', 'Pantry', 'Grocery budget', 'Household',
      'Ingredient encyclopedia', 'Nigerian foods', 'Food safety research', 'Food recalls', 'Learn', 'Research sources',
      'Alerts', 'Notification settings', 'Plans & usage', 'Privacy & data',
    ];
    for (final t in titles) {
      expect(find.text(t), findsOneWidget, reason: t);
    }
    expect(find.text('Admin & moderation'), findsNothing);
    app.me = {'id': 'u1', 'role': 'admin'};
    app.notifyListeners();
    await tester.pump();
    expect(find.text('Admin & moderation'), findsOneWidget);
  });

  testWidgets('animated icons stop when the system asks for reduced motion', (tester) async {
    var taps = 0;
    await tester.pumpWidget(MaterialApp(
      home: MediaQuery(
        data: const MediaQueryData(disableAnimations: true),
        child: Scaffold(body: Column(children: [const IconTile(icon: Icons.kitchen), PulsingScanButton(onPressed: () => taps++)])),
      ),
    ));
    await tester.pumpAndSettle(); // would time out if the loops were still running
    await tester.tap(find.byIcon(Icons.qr_code_scanner));
    expect(taps, 1);
  });

  test('scanner understands barcodes, GS1 QR codes, share links and other QR codes', () {
    expect((classifyCode('3017620422003') as ProductCode).gtin, '3017620422003');
    expect((classifyCode('https://id.gs1.org/01/09506000134352/10/ABC') as ProductCode).gtin, '09506000134352');
    expect((classifyCode('https://brand.example/01/00049000000443?lot=7') as ProductCode).gtin, '00049000000443');
    expect((classifyCode('(01)09506000134352(17)271231') as ProductCode).gtin, '09506000134352');
    expect((classifyCode('http://192.168.100.8:3000/r/AbC123xyz_-9') as SharedReportCode).token, 'AbC123xyz_-9');
    final link = classifyCode('http://192.168.100.8:8090/food-omniscan-debug.apk');
    expect(link, isA<LinkCode>());
    expect((link as LinkCode).uri.host, '192.168.100.8');
    expect(classifyCode('hello'), isA<TextCode>());
  });

  test('scanner understands Wi-Fi, phone, email, SMS, map and contact codes', () {
    final wifi = classifyCode(r'WIFI:T:WPA;S:Home\;Net;P:sec:ret;;') as WifiCode;
    expect(wifi.ssid, 'Home;Net');
    expect(wifi.password, 'sec:ret');
    expect(wifi.security, 'WPA');
    final tel = classifyCode('tel:+2348012345678') as ActionCode;
    expect(tel.kind, ActionKind.phone);
    expect(tel.label, '+2348012345678');
    expect((classifyCode('mailto:hello@example.com?subject=Hi') as ActionCode).kind, ActionKind.email);
    final mat = classifyCode('MATMSG:TO:a@example.com;SUB:Hi;BODY:Yo;;') as ActionCode;
    expect(mat.uri.scheme, 'mailto');
    expect(mat.label, 'a@example.com');
    final sms = classifyCode('SMSTO:+15551234567:Hello there') as ActionCode;
    expect(sms.kind, ActionKind.sms);
    expect(sms.uri.queryParameters['body'], 'Hello there');
    expect((classifyCode('geo:6.5244,3.3792?q=Lagos') as ActionCode).label, '6.5244,3.3792');
    expect((classifyCode('BEGIN:VCARD\nVERSION:3.0\nFN:Ada Obi\nEND:VCARD') as ContactCode).name, 'Ada Obi');
    expect((classifyCode('MECARD:N:Obi,Ada;TEL:123;;') as ContactCode).name, 'Ada Obi');
    // 1D codes: ITF-14 case codes and GS1-128 with a symbology prefix are products; store codes are text.
    expect((classifyCode('10012345678902') as ProductCode).gtin, '10012345678902');
    expect((classifyCode(']C10109506000134352') as ProductCode).gtin, '09506000134352');
    expect(classifyCode('ABC-123'), isA<TextCode>());
    expect(classifyCode('2024-01-01'), isA<TextCode>());
  });

  Map<String, dynamic> plan(String tier, num monthly, num? annual) =>
      {'tier': tier, 'monthly_usd': monthly, 'annual_usd': annual, 'features': ['Everything in Free', '$tier feature']};

  ApiClient billingApi() => ApiClient(
        baseUrl: 'http://api.test/api/v1',
        client: MockClient((req) async {
          if (req.url.path.endsWith('/billing/plans')) {
            return http.Response(
                jsonEncode([plan('free', 0, null), plan('plus', 3.99, 39.99), plan('premium', 7.99, 79.99), plan('family', 11.99, 119.99)]), 200);
          }
          if (req.url.path.endsWith('/assistant/ask')) {
            return http.Response(
                jsonEncode({
                  'detail': {'code': 'quota_exceeded', 'required_tier': 'plus', 'message': "You've used all 5 AI questions this month."}
                }),
                402);
          }
          return http.Response('{}', 200);
        }),
      );

  testWidgets('paywall shows the plans with yearly savings and a checkout button', (tester) async {
    await tester.binding.setSurfaceSize(const Size(420, 2400));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final app = AppState(api: billingApi())..me = {'id': 'u1', 'tier': 'free'};
    await tester.pumpWidget(ChangeNotifierProvider.value(
        value: app, child: MaterialApp(builder: (c, child) => MediaQuery(data: MediaQuery.of(c).copyWith(disableAnimations: true), child: child!), home: const PaywallScreen(reason: "You've used all 5 AI questions this month."))));
    await tester.pumpAndSettle();
    expect(find.text('Unlock the full Food omniScan'), findsOneWidget);
    expect(find.text("You've used all 5 AI questions this month."), findsOneWidget);
    expect(find.text('Yearly · save 17%'), findsOneWidget);
    expect(find.text('MOST POPULAR'), findsOneWidget);
    expect(find.text('Get Premium · \$79.99/year'), findsOneWidget);
    await tester.tap(find.text('Plus'));
    await tester.tap(find.text('Monthly'));
    await tester.pump();
    expect(find.text('Get Plus · \$3.99/month'), findsOneWidget);
  });

  testWidgets('running out of AI questions opens the paywall', (tester) async {
    await tester.binding.setSurfaceSize(const Size(420, 1600));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final app = AppState(api: billingApi())..me = {'id': 'u1', 'tier': 'free'};
    await tester.pumpWidget(ChangeNotifierProvider.value(value: app, child: MaterialApp(builder: (c, child) => MediaQuery(data: MediaQuery.of(c).copyWith(disableAnimations: true), child: child!), home: const AssistantScreen())));
    await tester.enterText(find.byType(TextField), 'Is palm oil healthy?');
    await tester.testTextInput.receiveAction(TextInputAction.send);
    await tester.pumpAndSettle();
    expect(find.byType(PaywallScreen), findsOneWidget);
    expect(find.text("You've used all 5 AI questions this month."), findsWidgets);
    Navigator.of(tester.element(find.byType(PaywallScreen))).pop();
    await tester.pumpAndSettle();
    expect(find.byType(PaywallScreen), findsNothing);
  });

  testWidgets('upgrade prompts show for free users and hide for subscribers', (tester) async {
    final app = AppState(api: billingApi())
      ..me = {'id': 'u1', 'tier': 'free'}
      ..usage = {
        'tier': 'free',
        'features': {
          'ai_assistant': {'kind': 'metered', 'label': 'AI nutrition assistant questions', 'limit': 5, 'used': 4},
          'pantry': {'kind': 'access', 'label': 'Pantry', 'limit': 0},
        }
      };
    await tester.pumpWidget(ChangeNotifierProvider.value(
        value: app, child: const MaterialApp(home: Scaffold(body: Column(children: [UpgradeChip(), UpgradeBanner()])))));
    expect(find.text('Go Premium'), findsOneWidget);
    expect(find.text('Get more with Premium'), findsOneWidget);
    expect(find.text('1 of 5 free AI nutrition assistant questions left this month'), findsOneWidget);
    app.me = {'id': 'u1', 'tier': 'premium'};
    app.notifyListeners();
    await tester.pump();
    expect(find.text('Go Premium'), findsNothing);
    expect(find.text('Get more with Premium'), findsNothing);
  });

  testWidgets('app name and Premium button fit side by side on a narrow phone', (tester) async {
    addTearDown(tester.view.reset);
    for (final width in [320.0, 360.0, 412.0]) {
      tester.view.devicePixelRatio = 3;
      tester.view.physicalSize = Size(width * 3, 2400);
      final app = AppState(api: billingApi())..me = {'id': 'u1', 'tier': 'free'};
      await tester.pumpWidget(ChangeNotifierProvider.value(
        value: app,
        child: MaterialApp(home: Scaffold(appBar: AppBar(title: const Wordmark(), actions: const [UpgradeChip()]))),
      ));
      await tester.pump();
      // Any overflow would be reported as a test failure here.
      expect(tester.takeException(), isNull, reason: 'width $width');
      expect(find.text('Premium'), findsOneWidget, reason: 'width $width');
      final name = tester.getRect(find.byType(FittedBox));
      final chip = tester.getRect(find.byType(ActionChip));
      expect(name.right, lessThanOrEqualTo(chip.left), reason: 'name overlaps the button at width $width');
    }
  });

  testWidgets('locked features in Explore open the plans for free users', (tester) async {
    await tester.binding.setSurfaceSize(const Size(800, 6000));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final app = AppState(api: billingApi())..me = {'id': 'u1', 'role': 'user', 'tier': 'free'};
    await tester.pumpWidget(ChangeNotifierProvider.value(value: app, child: MaterialApp(builder: (c, child) => MediaQuery(data: MediaQuery.of(c).copyWith(disableAnimations: true), child: child!), home: const ExploreScreen())));
    await tester.tap(find.text('Pantry'));
    await tester.pumpAndSettle();
    expect(find.byType(PaywallScreen), findsOneWidget);
    expect(find.text('This feature is included with Plus.'), findsOneWidget);
  });
}
