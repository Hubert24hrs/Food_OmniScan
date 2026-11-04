import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:food_omniscan/core/api.dart';
import 'package:food_omniscan/core/app_state.dart';
import 'package:food_omniscan/core/offline.dart';
import 'package:food_omniscan/core/theme.dart';
import 'package:food_omniscan/screens/assistant_screen.dart';
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
}
