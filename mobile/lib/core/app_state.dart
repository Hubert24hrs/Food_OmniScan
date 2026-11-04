import 'dart:async';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/foundation.dart';

import 'api.dart';
import 'offline.dart';

class AppState extends ChangeNotifier {
  AppState({ApiClient? api, OfflineStore? store}) : api = api ?? ApiClient(), store = store ?? OfflineStore();

  final ApiClient api;
  final OfflineStore store;
  Map<String, dynamic>? me;
  List<Map<String, dynamic>> profiles = [];
  bool loading = true;
  bool online = true;
  int queued = 0;
  StreamSubscription<List<ConnectivityResult>>? _conn;

  bool get signedIn => me != null;

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
    } else {
      try {
        me = await api.get('/me') as Map<String, dynamic>;
        profiles = (await api.get('/profiles') as List).cast<Map<String, dynamic>>();
      } on ApiException catch (e) {
        if (!e.isNetwork) {
          me = null;
          profiles = [];
        }
      }
    }
    loading = false;
    notifyListeners();
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
    notifyListeners();
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
