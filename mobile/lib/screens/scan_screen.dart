import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:provider/provider.dart';

import '../core/app_state.dart';
import 'label_screen.dart';
import 'product_screen.dart';

/// On-device barcode scanning (EAN-13/8, UPC-A/E). Offline scans are queued for sync.
class ScanScreen extends StatefulWidget {
  const ScanScreen({super.key});

  @override
  State<ScanScreen> createState() => _ScanScreenState();
}

class _ScanScreenState extends State<ScanScreen> {
  final controller = MobileScannerController(
    formats: const [BarcodeFormat.ean13, BarcodeFormat.ean8, BarcodeFormat.upcA, BarcodeFormat.upcE],
    detectionSpeed: DetectionSpeed.noDuplicates,
  );
  bool _busy = false;
  final _manual = TextEditingController();

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
                if (v != null) _open(v);
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
                width: 280,
                height: 140,
                decoration: BoxDecoration(border: Border.all(color: const Color(0xFF5EEAD4), width: 4), borderRadius: BorderRadius.circular(18)),
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
