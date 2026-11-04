import 'dart:async';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/foundation.dart';

import 'api.dart';
import 'billing.dart';
import 'offline.dart';

class AppState extends ChangeNotifier {
  AppState({ApiClient? api, OfflineStore? store}) : api = api ?? ApiClient(), store = store ?? OfflineStore();

  final ApiClient api;
  final OfflineStore store;
  Map<String, dynamic>? me;

  /// This month's plan usage from /billing/me (null when signed out).
  Map<String, dynamic>? usage;
  List<Map<String, dynamic>> profiles = [];
  bool loading = true;
  bool online = true;
  int queued = 0;
  StreamSubscription<List<ConnectivityResult>>? _conn;

  bool get signedIn => me != null;

  String get tier => (me?['tier'] as String?) ?? 'free';

  /// Signed-out people count as free too: upgrade prompts are shown to everyone not paying.
  bool get isFree => tier == 'free';

  /// Metered features (AI questions, photo reads…) with how many are left this month, lowest first.
  List<({String label, int used, int limit})> get allowances {
    final f = usage?['features'] as Map<String, dynamic>?;
    if (f == null) return [];
    final out = [
      for (final v in f.values.cast<Map<String, dynamic>>())
        if (v['kind'] == 'metered' && v['limit'] is int && (v['limit'] as int) > 0)
          (label: v['label'] as String, used: (v['used'] as int?) ?? 0, limit: v['limit'] as int),
    ];
    out.sort((a, b) => (a.limit - a.used).compareTo(b.limit - b.used));
    return out;
  }

  Map<String, dynamic>? get activeProfile {
    if (profiles.isEmpty) return null;
    return profiles.firstWhere((p) => p['is_active'] == true,
        orElse: () => profiles.firstWhere((p) => p['is_primary'] == true, orElse: () => profiles.first));
  }

  Future<void> init() async {
    await api.loadToken();
    queued = (await store.queue()).length;
    _conn = Connectivity().onConnectivityChanged.listen((r) async {
      online = !r.contains(ConnectivityResult.none);
      if (online) await syncOffline();
      notifyListeners();
    });
    await refresh();
  }

  Future<void> refresh() async {
    if (api.token == null) {
      me = null;
      profiles = [];
      usage = null;
    } else {
      try {
        me = await api.get('/me') as Map<String, dynamic>;
        profiles = (await api.get('/profiles') as List).cast<Map<String, dynamic>>();
      } on ApiException catch (e) {
        if (!e.isNetwork) {
          me = null;
          profiles = [];
          usage = null;
        }
      }
    }
    if (me != null) {
      try {
        usage = await api.get('/billing/me') as Map<String, dynamic>;
      } on ApiException {
        // usage meters are a nice-to-have; never sign someone out over them
      }
    }
    loading = false;
    notifyListeners();
    await StoreBilling.identify(me?['id'] as String?);
  }

  /// Re-read usage after something that spends an allowance (an AI answer, a photo read…).
  Future<void> refreshUsage() async {
    if (!signedIn) return;
    try {
      usage = await api.get('/billing/me') as Map<String, dynamic>;
      notifyListeners();
    } on ApiException {
      // keep the last known numbers
    }
  }

  Future<void> login(String email, String password) async {
    final r = await api.post('/auth/login', {'email': email, 'password': password}) as Map<String, dynamic>;
    await api.setToken(r['access_token'] as String);
    await refresh();
    await syncOffline();
  }

  Future<void> register(String email, String password, String name, bool consentHealth) async {
    final r = await api.post('/auth/register', {
      'email': email,
      'password': password,
      'display_name': name,
      'country': 'US',
      'accept_terms': true,
      'consent_health_data': consentHealth,
    }) as Map<String, dynamic>;
    await api.setToken(r['access_token'] as String);
    await refresh();
  }

  Future<void> logout() async {
    await api.setToken(null);
    me = null;
    profiles = [];
    usage = null;
    notifyListeners();
    await StoreBilling.identify(null);
  }

  Future<void> setActiveProfile(String id) async {
    await api.post('/profiles/$id/activate');
    await refresh();
  }

  Future<int> syncOffline() async {
    try {
      final n = await store.sync(api);
      queued = (await store.queue()).length;
      notifyListeners();
      return n;
    } on ApiException {
      return 0;
    }
  }

  Future<void> queueScan(String barcode) async {
    await store.enqueue(barcode);
    queued = (await store.queue()).length;
    notifyListeners();
  }

  @override
  void dispose() {
    _conn?.cancel();
    super.dispose();
  }
}
