/// Works out what a scanned code is, so the scanner can handle every barcode and QR code alike:
/// product barcodes (EAN/UPC/ITF-14/GS1), links, Wi-Fi, phone, email, SMS, map locations, contacts and text.
sealed class ScannedCode {
  const ScannedCode();
}

/// A product identifier (EAN/UPC/GTIN), from a 1D barcode or a GS1 QR / Data Matrix code.
class ProductCode extends ScannedCode {
  const ProductCode(this.gtin);
  final String gtin;
}

/// A Food omniScan shared report link (…/r/TOKEN).
class SharedReportCode extends ScannedCode {
  const SharedReportCode(this.token);
  final String token;
}

/// Any other web link.
class LinkCode extends ScannedCode {
  const LinkCode(this.uri);
  final Uri uri;
}

/// Wi-Fi network details ("WIFI:S:name;T:WPA;P:secret;;").
class WifiCode extends ScannedCode {
  const WifiCode({required this.ssid, this.password, this.security});
  final String ssid;
  final String? password;
  final String? security;
}

/// Something the phone can act on: call, email, text or show on a map.
class ActionCode extends ScannedCode {
  const ActionCode(this.kind, this.uri, this.label);
  final ActionKind kind;
  final Uri uri;

  /// Human-readable target (the number, address or coordinates).
  final String label;
}

enum ActionKind { phone, email, sms, geo }

/// A contact card (vCard or MECARD).
class ContactCode extends ScannedCode {
  const ContactCode(this.name, this.text);
  final String? name;
  final String text;
}

/// Anything else (plain text, store codes, tickets…).
class TextCode extends ScannedCode {
  const TextCode(this.text);
  final String text;
}

final _gtinDigits = RegExp(r'^\d{8}$|^\d{12,14}$');
// GS1 Digital Link: https://brand.example/01/09506000134352/10/ABC  (AI 01 = GTIN)
final _digitalLink = RegExp(r'/01/(\d{8,14})(?:/|$|\?)');
// GS1 element string (GS1 QR / Data Matrix / GS1-128): "(01)09506000134352…" or "0109506000134352…"
final _elementString = RegExp(r'^(?:\]\w\d)?(?:\x1d)?\(?01\)?(\d{14})');

/// Splits "KEY:value;KEY:value;;" (Wi-Fi / MECARD), honouring backslash escapes.
Map<String, String> _fields(String body) {
  final out = <String, String>{};
  final buf = StringBuffer();
  final parts = <String>[];
  for (var i = 0; i < body.length; i++) {
    final c = body[i];
    if (c == r'\' && i + 1 < body.length) {
      buf.write(body[++i]);
    } else if (c == ';') {
      parts.add(buf.toString());
      buf.clear();
    } else {
      buf.write(c);
    }
  }
  if (buf.isNotEmpty) parts.add(buf.toString());
  for (final p in parts) {
    final j = p.indexOf(':');
    if (j > 0) out.putIfAbsent(p.substring(0, j).toUpperCase(), () => p.substring(j + 1));
  }
  return out;
}

ScannedCode classifyCode(String raw) {
  final s = raw.trim();
  final compact = s.replaceAll(' ', '');
  if (_gtinDigits.hasMatch(compact)) return ProductCode(compact);

  final element = _elementString.firstMatch(compact);
  if (element != null) return ProductCode(element.group(1)!);

  final upper = s.toUpperCase();
  if (upper.startsWith('WIFI:')) {
    final f = _fields(s.substring(5));
    final ssid = f['S'];
    if (ssid != null && ssid.isNotEmpty) {
      final pass = f['P'];
      return WifiCode(ssid: ssid, password: pass == null || pass.isEmpty ? null : pass, security: f['T']);
    }
  }
  if (upper.startsWith('BEGIN:VCARD')) {
    final m = RegExp(r'^FN(?:;[^:]*)?:(.+)$', multiLine: true, caseSensitive: false).firstMatch(s);
    return ContactCode(m?.group(1)?.trim(), s);
  }
  if (upper.startsWith('MECARD:')) {
    final n = _fields(s.substring(7))['N'];
    return ContactCode(n?.split(',').reversed.join(' ').trim(), s);
  }
  if (upper.startsWith('MATMSG:')) {
    final f = _fields(s.substring(7));
    final to = f['TO'];
    if (to != null && to.isNotEmpty) {
      final uri = Uri(scheme: 'mailto', path: to, queryParameters: {
        if (f['SUB'] != null) 'subject': f['SUB']!,
        if (f['BODY'] != null) 'body': f['BODY']!,
      });
      return ActionCode(ActionKind.email, uri, to);
    }
  }
  if (upper.startsWith('SMSTO:')) {
    final parts = s.substring(6).split(':');
    final uri = Uri(scheme: 'sms', path: parts.first, queryParameters: parts.length > 1 ? {'body': parts.sublist(1).join(':')} : null);
    return ActionCode(ActionKind.sms, uri, parts.first);
  }

  final uri = Uri.tryParse(s);
  if (uri != null) {
    switch (uri.scheme.toLowerCase()) {
      case 'http' || 'https' when uri.host.isNotEmpty:
        final link = _digitalLink.firstMatch(uri.path.endsWith('/') ? uri.path : '${uri.path}/');
        if (link != null) return ProductCode(link.group(1)!);
        final segs = uri.pathSegments;
        if (segs.length == 2 && segs[0] == 'r' && RegExp(r'^[A-Za-z0-9_-]{8,40}$').hasMatch(segs[1])) {
          return SharedReportCode(segs[1]);
        }
        return LinkCode(uri);
      case 'tel' when uri.path.isNotEmpty:
        return ActionCode(ActionKind.phone, uri, uri.path);
      case 'mailto' when uri.path.isNotEmpty:
        return ActionCode(ActionKind.email, uri, uri.path);
      case 'sms' || 'smsto' when uri.path.isNotEmpty:
        final number = uri.path.split(':').first;
        return ActionCode(ActionKind.sms, Uri(scheme: 'sms', path: number, query: uri.hasQuery ? uri.query : null), number);
      case 'geo' when RegExp(r'^-?\d+(\.\d+)?,-?\d+(\.\d+)?').hasMatch(uri.path):
        final ll = RegExp(r'^-?\d+(\.\d+)?,-?\d+(\.\d+)?').firstMatch(uri.path)!.group(0)!;
        return ActionCode(ActionKind.geo, uri, ll);
    }
  }
  return TextCode(s);
}
