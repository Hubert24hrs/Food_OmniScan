import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

/// API base URL. Override at build time:
///   flutter run --dart-define=API_URL=https://api.foodomniscan.app/api/v1
/// Default targets a local API from the Android emulator (10.0.2.2 = host machine).
const apiUrl = String.fromEnvironment('API_URL', defaultValue: 'http://10.0.2.2:8010/api/v1');

class ApiException implements Exception {
  ApiException(this.status, this.message, {this.code, this.detail});
  final int status;
  final String message;
  final String? code;
  final Object? detail;

  bool get isNetwork => status == 0;

  @override
  String toString() => message;
}

/// Thin JSON client. Secrets never live in the app: only the user's session token.
/// Production builds should keep the token in flutter_secure_storage (Keychain/Keystore).
class ApiClient {
  ApiClient({http.Client? client, this.baseUrl = apiUrl}) : _http = client ?? http.Client();

  final http.Client _http;
  final String baseUrl;
  String? _token;
  static const _tokenKey = 'omniscan.token';

  String? get token => _token;

  Future<void> loadToken() async {
    final prefs = await SharedPreferences.getInstance();
    _token = prefs.getString(_tokenKey);
  }

  Future<void> setToken(String? token) async {
    _token = token;
    final prefs = await SharedPreferences.getInstance();
    if (token == null) {
      await prefs.remove(_tokenKey);
    } else {
      await prefs.setString(_tokenKey, token);
    }
  }

  Future<dynamic> get(String path, {Map<String, String>? query}) => _send('GET', path, query: query);
  Future<dynamic> post(String path, [Object? body]) => _send('POST', path, body: body);
  Future<dynamic> put(String path, Object? body) => _send('PUT', path, body: body);
  Future<dynamic> patch(String path, Object? body) => _send('PATCH', path, body: body);
  Future<dynamic> delete(String path, [Object? body]) => _send('DELETE', path, body: body);

  Future<dynamic> _send(String method, String path, {Object? body, Map<String, String>? query}) async {
    final uri = Uri.parse('$baseUrl$path').replace(queryParameters: query);
    final req = http.Request(method, uri);
    if (_token != null) req.headers['Authorization'] = 'Bearer $_token';
    if (body != null) {
      req.headers['Content-Type'] = 'application/json';
      req.body = jsonEncode(body);
    }
    http.Response res;
    try {
      res = await http.Response.fromStream(await _http.send(req).timeout(const Duration(seconds: 25)));
    } catch (_) {
      throw ApiException(0, "Can't reach Food omniScan. Check your connection.", code: 'network_error');
    }
    if (res.statusCode == 204 || res.body.isEmpty) return null;
    final data = jsonDecode(utf8.decode(res.bodyBytes));
    if (res.statusCode >= 400) {
      final d = data is Map ? data['detail'] : null;
      var message = 'Request failed (${res.statusCode})';
      String? code;
      if (d is String) message = d;
      if (d is Map) {
        code = d['code'] as String?;
        message = (d['message'] as String?) ?? message;
      }
      if (res.statusCode == 401) await setToken(null);
      throw ApiException(res.statusCode, message, code: code, detail: d);
    }
    return data;
  }
}
