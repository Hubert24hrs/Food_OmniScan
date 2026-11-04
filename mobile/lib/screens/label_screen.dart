import 'package:flutter/material.dart';
import 'package:google_mlkit_text_recognition/google_mlkit_text_recognition.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../core/api.dart';
import '../core/app_state.dart';
import '../widgets/analysis_view.dart';
import 'assistant_screen.dart' show assistantErrorText;
import 'paywall_screen.dart';

/// Photograph ingredient / nutrition labels, read them on-device with ML Kit,
/// let the user correct the text, then analyze it server-side.
class LabelScreen extends StatefulWidget {
  const LabelScreen({super.key});

  @override
  State<LabelScreen> createState() => _LabelScreenState();
}

class _LabelScreenState extends State<LabelScreen> {
  final ingredients = TextEditingController();
  final nutrition = TextEditingController();
  bool beverage = false;
  bool busy = false;
  String? error;
  Map<String, dynamic>? result;

  /// Which sections were filled by AI, so we can remind the user to check them.
  final aiFilled = <TextEditingController>{};

  Future<void> _choose(TextEditingController target, String task) async {
    final signedIn = context.read<AppState>().signedIn;
    final useAi = await showModalBottomSheet<bool>(
      context: context,
      showDragHandle: true,
      builder: (c) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          ListTile(
            leading: const Icon(Icons.phone_android),
            title: const Text('Read on this phone'),
            subtitle: const Text('Free and private. Works offline.'),
            onTap: () => Navigator.pop(c, false),
          ),
          ListTile(
            enabled: signedIn,
            leading: const Icon(Icons.auto_awesome),
            title: const Text('Read with AI'),
            subtitle: Text(signedIn
                ? 'Better on curved, glossy or small print. Uses 1 AI credit; the photo is sent to Google Gemini.'
                : 'Sign in on the Profile tab to use AI reading.'),
            onTap: () => Navigator.pop(c, true),
          ),
        ]),
      ),
    );
    if (useAi == null) return;
    useAi ? await _captureAi(target, task) : await _capture(target);
  }

  Future<void> _captureAi(TextEditingController target, String task) async {
    final photo = await ImagePicker().pickImage(source: ImageSource.camera, maxWidth: 2000, imageQuality: 85);
    if (photo == null || !mounted) return;
    final api = context.read<AppState>().api;
    setState(() {
      busy = true;
      error = null;
    });
    try {
      final r = await api.upload('/analysis/image', fields: {'task': task}, bytes: await photo.readAsBytes()) as Map<String, dynamic>;
      final x = r['extracted'] as Map<String, dynamic>;
      // The server labels the allergen statements ("Contains: …", "May contain: …") so they keep their meaning.
      final text = task == 'ingredients'
          ? (r['ingredients_text'] as String? ?? x['ingredients_text'] as String? ?? '')
          : (x['panel_text'] as String? ?? '');
      setState(() {
        target.text = text;
        aiFilled.add(target);
      });
      if (mounted && (text.trim().isEmpty || x['legibility'] == 'poor')) {
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text("The AI couldn't read much of this photo. Try more light and fill the frame.")));
      }
    } on ApiException catch (e) {
      setState(() => error = assistantErrorText(e));
      if (mounted) handlePlanError(context, e);
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> _capture(TextEditingController target) async {
    final photo = await ImagePicker().pickImage(source: ImageSource.camera, maxWidth: 2400, imageQuality: 90);
    if (photo == null) return;
    aiFilled.remove(target);
    setState(() => busy = true);
    final recognizer = TextRecognizer(script: TextRecognitionScript.latin);
    try {
      final text = await recognizer.processImage(InputImage.fromFilePath(photo.path));
      target.text = text.text;
      if (text.text.trim().length < 15 && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Very little text found. Try more light, less glare, and fill the frame.')));
      }
    } finally {
      await recognizer.close();
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> _analyze() async {
    setState(() {
      busy = true;
      error = null;
    });
    try {
      final r = await context.read<AppState>().api.post('/analysis/text', {
        'ingredients_text': ingredients.text.trim().isEmpty ? null : ingredients.text,
        'nutrition_text': nutrition.text.trim().isEmpty ? null : nutrition.text,
        'is_beverage': beverage,
      });
      setState(() => result = r as Map<String, dynamic>);
    } on ApiException catch (e) {
      setState(() => error = e.message);
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Scan a label')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        const Text('Photograph each part of the label, then check and correct the text before analyzing.'),
        const SizedBox(height: 12),
        _Section(
            title: 'Ingredients',
            controller: ingredients,
            readByAi: aiFilled.contains(ingredients),
            onCapture: busy ? null : () => _choose(ingredients, 'ingredients')),
        const SizedBox(height: 12),
        _Section(
            title: 'Nutrition Facts',
            controller: nutrition,
            readByAi: aiFilled.contains(nutrition),
            onCapture: busy ? null : () => _choose(nutrition, 'nutrition')),
        SwitchListTile(value: beverage, onChanged: (v) => setState(() => beverage = v), title: const Text('This is a beverage')),
        FilledButton(onPressed: busy ? null : _analyze, child: Text(busy ? 'Working…' : 'Analyze')),
        if (error != null) Padding(padding: const EdgeInsets.only(top: 12), child: Text(error!, style: const TextStyle(color: Colors.red))),
        if (result != null) ...[const SizedBox(height: 16), AnalysisView(analysis: result!)],
      ]),
    );
  }
}

class _Section extends StatelessWidget {
  const _Section({required this.title, required this.controller, required this.onCapture, this.readByAi = false});
  final String title;
  final TextEditingController controller;
  final VoidCallback? onCapture;
  final bool readByAi;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            Expanded(child: Text(title, style: const TextStyle(fontWeight: FontWeight.w800))),
            TextButton.icon(onPressed: onCapture, icon: const Icon(Icons.photo_camera_outlined), label: const Text('Photograph')),
          ]),
          if (readByAi)
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(children: [
                Icon(Icons.auto_awesome, size: 16, color: Theme.of(context).colorScheme.primary),
                const SizedBox(width: 6),
                const Expanded(child: Text('Read by AI. Check it against the package.', style: TextStyle(fontSize: 12))),
              ]),
            ),
          TextField(controller: controller, maxLines: 6, minLines: 3, decoration: InputDecoration(hintText: '$title text')),
        ]),
      ),
    );
  }
}
