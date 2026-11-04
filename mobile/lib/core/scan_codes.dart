/// Works out what a scanned code is, so the scanner can handle barcodes and QR codes alike.
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

/// Anything else (Wi-Fi details, plain text, contact cards…).
class TextCode extends ScannedCode {
  const TextCode(this.text);
  final String text;
}

final _gtinDigits = RegExp(r'^\d{8}$|^\d{12,14}$');
// GS1 Digital Link: https://brand.example/01/09506000134352/10/ABC  (AI 01 = GTIN)
final _digitalLink = RegExp(r'/01/(\d{8,14})(?:/|$|\?)');
// GS1 element string as encoded in GS1 QR / Data Matrix: "(01)09506000134352" or "0109506000134352…"
final _elementString = RegExp(r'^(?:\x1d)?\(?01\)?(\d{14})');

ScannedCode classifyCode(String raw) {
  final s = raw.trim();
  final compact = s.replaceAll(' ', '');
  if (_gtinDigits.hasMatch(compact)) return ProductCode(compact);

  final element = _elementString.firstMatch(compact);
  if (element != null) return ProductCode(element.group(1)!);

  final uri = Uri.tryParse(s);
  if (uri != null && (uri.scheme == 'http' || uri.scheme == 'https') && uri.host.isNotEmpty) {
    final link = _digitalLink.firstMatch(uri.path.endsWith('/') ? uri.path : '${uri.path}/');
    if (link != null) return ProductCode(link.group(1)!);
    final segs = uri.pathSegments;
    if (segs.length == 2 && segs[0] == 'r' && RegExp(r'^[A-Za-z0-9_-]{8,40}$').hasMatch(segs[1])) {
      return SharedReportCode(segs[1]);
    }
    return LinkCode(uri);
  }
  return TextCode(s);
}
