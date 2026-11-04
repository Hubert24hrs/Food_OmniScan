import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../core/app_state.dart';
import '../core/scan_codes.dart';
import '../core/theme.dart';
import '../widgets/common.dart';
import 'label_screen.dart';
import 'product_screen.dart';

/// On-device scanning of product barcodes (EAN-13/8, UPC-A/E) and QR / Data Matrix codes.
/// GS1 product QR codes open the product; Food omniScan share links open the report; other QR codes
/// show their content with Open / Copy. Offline product scans are queued for sync.
class ScanScreen extends StatefulWidget {
  const ScanScreen({super.key});

  @override
  State<ScanScreen> createState() => _ScanScreenState();
}

class _ScanScreenState extends State<ScanScreen> {
  final controller = MobileScannerController(
    formats: const [
      BarcodeFormat.ean13,
      BarcodeFormat.ean8,
      BarcodeFormat.upcA,
      BarcodeFormat.upcE,
      BarcodeFormat.qrCode,
      BarcodeFormat.dataMatrix,
    ],
    detectionSpeed: DetectionSpeed.noDuplicates,
  );
  bool _busy = false;
  final _manual = TextEditingController();

  Future<void> _handle(String raw) async {
    if (_busy) return;
    switch (classifyCode(raw)) {
      case ProductCode(:final gtin):
        await _open(gtin);
      case SharedReportCode(:final token):
        await _pause(() async {
          final r = await runAction(context, () => context.read<AppState>().api.get('/shared/$token'));
          if (r is Map && mounted) {
            await Navigator.of(context).push(MaterialPageRoute(builder: (_) => ProductScreen(initial: r.cast<String, dynamic>())));
          }
        });
      case LinkCode(:final uri):
        await _pause(() => _showLink(uri));
      case TextCode(:final text):
        await _pause(() => _showText(text));
    }
  }

  /// Stop the camera while something else is on screen, then resume.
  Future<void> _pause(Future<void> Function() body) async {
    _busy = true;
    await controller.stop();
    if (mounted) await body();
    _busy = false;
    if (mounted) await controller.start();
  }

  Future<void> _showLink(Uri uri) => showModalBottomSheet<void>(
        context: context,
        showDragHandle: true,
        builder: (c) => SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 0, 20, 16),
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text('This QR code is a link', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
              const SizedBox(height: 4),
              Text('It goes to ${uri.host}. Only open links you trust.'),
              const SizedBox(height: 8),
              SelectableText(uri.toString(), style: const TextStyle(fontSize: 13)),
              const SizedBox(height: 16),
              Row(children: [
                Expanded(
                  child: FilledButton.icon(
                    onPressed: () async {
                      Navigator.pop(c);
                      final ok = await launchUrl(uri, mode: LaunchMode.externalApplication);
                      if (!ok && mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Couldn't open the link.")));
                    },
                    icon: const Icon(Icons.open_in_new),
                    label: const Text('Open link'),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () {
                      Clipboard.setData(ClipboardData(text: uri.toString()));
                      Navigator.pop(c);
                      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Link copied')));
                    },
                    icon: const Icon(Icons.copy),
                    label: const Text('Copy'),
                  ),
                ),
              ]),
            ]),
          ),
        ),
      );

  Future<void> _showText(String text) => showModalBottomSheet<void>(
        context: context,
        showDragHandle: true,
        builder: (c) => SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 0, 20, 16),
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text('Scanned code', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
              const SizedBox(height: 4),
              const Text("This isn't a product barcode. Here's what it contains:"),
              const SizedBox(height: 8),
              SelectableText(text.length > 1000 ? '${text.substring(0, 1000)}…' : text),
              const SizedBox(height: 16),
              OutlinedButton.icon(
                onPressed: () {
                  Clipboard.setData(ClipboardData(text: text));
                  Navigator.pop(c);
                  ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Copied')));
                },
                icon: const Icon(Icons.copy),
                label: const Text('Copy'),
              ),
            ]),
          ),
        ),
      );

  Future<void> _open(String code) async {
    if (_busy) return;
    final digits = code.replaceAll(RegExp(r'\D'), '');
    if (digits.length < 8) return;
    _busy = true;
    final app = context.read<AppState>();
    if (!app.online) {
      await app.queueScan(digits);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Saved $digits. It will sync when you are back online.')));
      }
      _busy = false;
      return;
    }
    await controller.stop();
    if (!mounted) return;
    await Navigator.of(context).push(MaterialPageRoute(builder: (_) => ProductScreen(barcode: digits)));
    _busy = false;
    await controller.start();
  }

  @override
  void dispose() {
    controller.dispose();
    _manual.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    return Scaffold(
      appBar: AppBar(
        title: const Text('Scan'),
        actions: [
          IconButton(
            tooltip: 'Flashlight',
            icon: const Icon(Icons.flashlight_on_outlined),
            onPressed: () => controller.toggleTorch(),
          ),
          IconButton(
            tooltip: 'Scan a label instead',
            icon: const Icon(Icons.document_scanner_outlined),
            onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const LabelScreen())),
          ),
        ],
      ),
      body: Column(children: [
        if (!app.online || app.queued > 0)
          MaterialBanner(
            content: Text(app.online ? '${app.queued} offline scan(s) waiting to sync' : "You're offline. Scans are queued."),
            actions: [TextButton(onPressed: app.online ? app.syncOffline : null, child: const Text('Sync'))],
          ),
        Expanded(
          child: Stack(children: [
            MobileScanner(
              controller: controller,
              onDetect: (capture) {
                final v = capture.barcodes.firstOrNull?.rawValue;
                if (v != null) _handle(v);
              },
              errorBuilder: (context, error) => Center(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Text(
                    error.errorCode == MobileScannerErrorCode.permissionDenied
                        ? 'Camera permission denied. Enable it in Settings or type the barcode below.'
                        : 'Camera unavailable: ${error.errorCode.name}',
                    textAlign: TextAlign.center,
                  ),
                ),
              ),
            ),
            Center(
              child: Container(
                width: 260,
                height: 200,
                decoration: BoxDecoration(border: Border.all(color: Brand.greenBright, width: 4), borderRadius: BorderRadius.circular(20)),
              ),
            ),
            const Positioned(
              left: 0,
              right: 0,
              bottom: 16,
              child: Center(
                child: DecoratedBox(
                  decoration: BoxDecoration(color: Colors.black54, borderRadius: BorderRadius.all(Radius.circular(20))),
                  child: Padding(
                    padding: EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                    child: Text('Point at a barcode or QR code', style: TextStyle(color: Colors.white)),
                  ),
                ),
              ),
            ),
          ]),
        ),
        SafeArea(
          top: false,
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Row(children: [
              Expanded(
                child: TextField(
                  controller: _manual,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(hintText: 'Or type the barcode'),
                  onSubmitted: _open,
                ),
              ),
              const SizedBox(width: 8),
              FilledButton(onPressed: () => _open(_manual.text), child: const Text('Go')),
            ]),
          ),
        ),
      ]),
    );
  }
}
