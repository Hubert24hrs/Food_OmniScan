import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';

import 'api.dart';

class QueuedScan {
  QueuedScan({required this.clientId, required this.barcode, required this.scannedAt});

  final String clientId;
  final String barcode;
  final DateTime scannedAt;

  Map<String, dynamic> toJson() =>
      {'client_id': clientId, 'barcode': barcode, 'scanned_at': scannedAt.toUtc().toIso8601String()};

  static QueuedScan fromJson(Map<String, dynamic> j) => QueuedScan(
        clientId: j['client_id'] as String,
        barcode: j['barcode'] as String,
        scannedAt: DateTime.parse(j['scanned_at'] as String),
      );
}

/// Offline-first storage: queued scans (synced idempotently via /scans/sync) and a cache of
/// recently viewed product analyses so history works without a connection.
class OfflineStore {
  static const _queueKey = 'omniscan.queue';
  static const _cacheKey = 'omniscan.products';
  static const maxCached = 50;

  Future<List<QueuedScan>> queue() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_queueKey);
    if (raw == null) return [];
    return (jsonDecode(raw) as List).map((e) => QueuedScan.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<void> _saveQueue(List<QueuedScan> q) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_queueKey, jsonEncode(q.map((e) => e.toJson()).toList()));
  }

  Future<QueuedScan> enqueue(String barcode, {DateTime? at}) async {
    final item = QueuedScan(clientId: const Uuid().v4(), barcode: barcode, scannedAt: at ?? DateTime.now());
    final q = await queue();
    await _saveQueue([...q, item].length > 200 ? [...q, item].sublist(1) : [...q, item]);
    return item;
  }

  /// Uploads queued scans. Items the server asks to retry stay queued. Returns number synced.
  Future<int> sync(ApiClient api) async {
    final q = await queue();
    if (q.isEmpty || api.token == null) return 0;
    final res = await api.post('/scans/sync', q.map((e) => e.toJson()).toList()) as Map<String, dynamic>;
    final retry = {
      for (final r in (res['results'] as List).cast<Map<String, dynamic>>())
        if (r['status'] == 'retry_later') r['client_id'] as String
    };
    await _saveQueue(q.where((e) => retry.contains(e.clientId)).toList());
    return q.length - retry.length;
  }

  Future<void> cacheProduct(String id, Map<String, dynamic> payload) async {
    final prefs = await SharedPreferences.getInstance();
    final m = Map<String, dynamic>.from(jsonDecode(prefs.getString(_cacheKey) ?? '{}') as Map);
    m[id] = {'at': DateTime.now().millisecondsSinceEpoch, 'payload': payload};
    final entries = m.entries.toList()
      ..sort((a, b) => ((b.value as Map)['at'] as int).compareTo((a.value as Map)['at'] as int));
    await prefs.setString(_cacheKey, jsonEncode(Map.fromEntries(entries.take(maxCached))));
  }

  Future<Map<String, dynamic>?> cachedProduct(String id) async {
    final prefs = await SharedPreferences.getInstance();
    final m = jsonDecode(prefs.getString(_cacheKey) ?? '{}') as Map<String, dynamic>;
    return (m[id] as Map<String, dynamic>?)?['payload'] as Map<String, dynamic>?;
  }

  Future<List<Map<String, dynamic>>> cachedProducts() async {
    final prefs = await SharedPreferences.getInstance();
    final m = jsonDecode(prefs.getString(_cacheKey) ?? '{}') as Map<String, dynamic>;
    final entries = m.values.cast<Map<String, dynamic>>().toList()
      ..sort((a, b) => (b['at'] as int).compareTo(a['at'] as int));
    return entries.map((e) => e['payload'] as Map<String, dynamic>).toList();
  }
}
