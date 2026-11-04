import 'package:flutter/material.dart';
import 'package:google_mlkit_text_recognition/google_mlkit_text_recognition.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../core/api.dart';
import '../core/app_state.dart';
import '../widgets/analysis_view.dart';

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

  Future<void> _capture(TextEditingController target) async {
    final photo = await ImagePicker().pickImage(source: ImageSource.camera, maxWidth: 2400, imageQuality: 90);
    if (photo == null) return;
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
        const Text('Text is read on your device. Check and correct it before analyzing.'),
        const SizedBox(height: 12),
        _Section(title: 'Ingredients', controller: ingredients, onCapture: busy ? null : () => _capture(ingredients)),
        const SizedBox(height: 12),
        _Section(title: 'Nutrition Facts', controller: nutrition, onCapture: busy ? null : () => _capture(nutrition)),
        SwitchListTile(value: beverage, onChanged: (v) => setState(() => beverage = v), title: const Text('This is a beverage')),
        FilledButton(onPressed: busy ? null : _analyze, child: Text(busy ? 'Working…' : 'Analyze')),
        if (error != null) Padding(padding: const EdgeInsets.only(top: 12), child: Text(error!, style: const TextStyle(color: Colors.red))),
        if (result != null) ...[const SizedBox(height: 16), AnalysisView(analysis: result!)],
      ]),
    );
  }
}

class _Section extends StatelessWidget {
  const _Section({required this.title, required this.controller, required this.onCapture});
  final String title;
  final TextEditingController controller;
  final VoidCallback? onCapture;

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
          TextField(controller: controller, maxLines: 6, minLines: 3, decoration: InputDecoration(hintText: '$title text')),
        ]),
      ),
    );
  }
}
