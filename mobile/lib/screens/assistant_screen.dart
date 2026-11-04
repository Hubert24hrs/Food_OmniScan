import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api.dart';
import '../core/app_state.dart';

/// Nutrition assistant chat. Answers come from the API, which grounds Gemini on our own
/// product data and cited sources. Conversations stay on the phone; the server doesn't store them.
class AssistantScreen extends StatefulWidget {
  const AssistantScreen({super.key, this.productId, this.productName});
  final String? productId;
  final String? productName;

  @override
  State<AssistantScreen> createState() => _AssistantScreenState();
}

class ChatMessage {
  ChatMessage(this.role, this.content, {this.sources = const []});
  final String role;
  final String content;
  final List<String> sources;
}

class _AssistantScreenState extends State<AssistantScreen> {
  final q = TextEditingController();
  final scroll = ScrollController();
  final msgs = <ChatMessage>[];
  bool busy = false;
  String? error;
  String language = 'en';
  static const _languages = {'en': 'English', 'pcm': 'Pidgin', 'yo': 'Yoruba', 'ig': 'Igbo', 'ha': 'Hausa', 'fr': 'French', 'es': 'Spanish'};

  List<String> get _suggestions => widget.productId != null
      ? ['Why did this product get its score?', 'Is this OK for someone avoiding added sugar?', 'What does each additive do?']
      : ["What's the difference between total and added sugars?", 'Is Red 40 banned anywhere?', 'Give me a high-protein breakfast idea'];

  Future<void> _ask(String question) async {
    question = question.trim();
    if (question.length < 2 || busy) return;
    final app = context.read<AppState>();
    final history = [for (final m in msgs) {'role': m.role, 'content': m.content}];
    setState(() {
      busy = true;
      error = null;
      msgs.add(ChatMessage('user', question));
      q.clear();
    });
    _scrollToEnd();
    try {
      final r = await app.api.postSlow('/assistant/ask', {
        'question': question,
        'product_ids': [if (widget.productId != null) widget.productId],
        'history': history.length > 16 ? history.sublist(history.length - 16) : history,
        if (app.activeProfile != null) 'profile_id': app.activeProfile!['id'],
        'language': language,
      }) as Map<String, dynamic>;
      final sources = [for (final s in (r['sources'] as List? ?? [])) (s as Map)['key'] as String];
      setState(() => msgs.add(ChatMessage('assistant', r['answer'] as String? ?? '', sources: sources)));
    } on ApiException catch (e) {
      setState(() {
        msgs.removeLast();
        q.text = question;
        error = assistantErrorText(e);
      });
    } finally {
      if (mounted) setState(() => busy = false);
      _scrollToEnd();
    }
  }

  void _scrollToEnd() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (scroll.hasClients) scroll.animateTo(scroll.position.maxScrollExtent, duration: const Duration(milliseconds: 250), curve: Curves.easeOut);
    });
  }

  @override
  void dispose() {
    q.dispose();
    scroll.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(title: const Text('Nutrition assistant'), actions: [
        PopupMenuButton<String>(
          tooltip: 'Answer language',
          initialValue: language,
          onSelected: (v) => setState(() => language = v),
          itemBuilder: (_) => [for (final e in _languages.entries) PopupMenuItem(value: e.key, child: Text(e.key == 'en' ? e.value : '${e.value} (Plus)'))],
          child: Padding(padding: const EdgeInsets.symmetric(horizontal: 12), child: Row(children: [const Icon(Icons.translate), const SizedBox(width: 4), Text(_languages[language]!)])),
        ),
      ]),
      body: !app.signedIn
          ? const Center(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: Text('Sign in on the Profile tab to ask the nutrition assistant.', textAlign: TextAlign.center),
              ),
            )
          : Column(children: [
              Expanded(
                child: ListView(controller: scroll, padding: const EdgeInsets.all(16), children: [
                  if (widget.productName != null)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: Chip(avatar: const Icon(Icons.inventory_2_outlined, size: 18), label: Text('Asking about ${widget.productName}')),
                    ),
                  if (msgs.isEmpty) ...[
                    const Text('Answers use our product data and cited sources. General information, not medical advice.'),
                    const SizedBox(height: 12),
                    Row(children: [Icon(Icons.auto_awesome, size: 18, color: cs.primary), const SizedBox(width: 6), const Text('Try asking:', style: TextStyle(fontWeight: FontWeight.w700))]),
                    const SizedBox(height: 8),
                    for (final s in _suggestions)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: OutlinedButton(
                          style: OutlinedButton.styleFrom(alignment: Alignment.centerLeft, padding: const EdgeInsets.all(14)),
                          onPressed: busy ? null : () => _ask(s),
                          child: Text(s),
                        ),
                      ),
                  ],
                  for (final m in msgs) MessageBubble(message: m),
                  if (busy) const Padding(padding: EdgeInsets.all(8), child: Text('Thinking…')),
                  if (error != null) Padding(padding: const EdgeInsets.only(top: 8), child: Text(error!, style: TextStyle(color: cs.error))),
                ]),
              ),
              SafeArea(
                top: false,
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(12, 4, 12, 8),
                  child: Column(mainAxisSize: MainAxisSize.min, children: [
                    Row(children: [
                      Expanded(
                        child: TextField(
                          controller: q,
                          maxLength: 2000,
                          minLines: 1,
                          maxLines: 4,
                          textInputAction: TextInputAction.send,
                          onSubmitted: _ask,
                          decoration: const InputDecoration(hintText: 'Ask about ingredients, nutrients, swaps…', counterText: ''),
                        ),
                      ),
                      const SizedBox(width: 8),
                      IconButton.filled(tooltip: 'Send', onPressed: busy ? null : () => _ask(q.text), icon: const Icon(Icons.send)),
                    ]),
                    const SizedBox(height: 4),
                    Text("Conversations aren't stored on our servers. Questions are processed by Google Gemini.",
                        style: Theme.of(context).textTheme.bodySmall),
                  ]),
                ),
              ),
            ]),
    );
  }
}

/// Plain-language text for the assistant and AI photo errors the API can return.
String assistantErrorText(ApiException e) {
  switch (e.code) {
    case 'quota_exceeded':
      return "${e.message} Upgrade your plan for more, or try again next month.";
    case 'ai_not_configured':
      return "The AI features aren't switched on for this server yet.";
    case 'ai_failed':
      return '${e.message} Please try again in a moment.';
  }
  if (e.status == 401) return 'Your session ended. Sign in again on the Profile tab.';
  return e.message;
}

class MessageBubble extends StatelessWidget {
  const MessageBubble({super.key, required this.message});
  final ChatMessage message;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final mine = message.role == 'user';
    return Align(
      alignment: mine ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        constraints: BoxConstraints(maxWidth: MediaQuery.sizeOf(context).width * 0.85),
        decoration: BoxDecoration(
          color: mine ? cs.primary : cs.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(18),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          SelectableText(plainText(message.content), style: TextStyle(color: mine ? cs.onPrimary : cs.onSurface)),
          if (message.sources.isNotEmpty) ...[
            const SizedBox(height: 6),
            Wrap(spacing: 4, runSpacing: 4, children: [
              for (final s in message.sources)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(color: cs.surface, borderRadius: BorderRadius.circular(99)),
                  child: Text(s, style: Theme.of(context).textTheme.labelSmall),
                ),
            ]),
          ],
          if (!mine) ...[
            const SizedBox(height: 6),
            Text('AI-generated · check the label · not medical advice', style: Theme.of(context).textTheme.labelSmall),
          ],
        ]),
      ),
    );
  }

  /// The model answers in light Markdown; show it as clean text with bullet dots.
  static String plainText(String s) => s
      .replaceAllMapped(RegExp(r'\*\*(.+?)\*\*'), (m) => m[1]!)
      .replaceAllMapped(RegExp(r'^(\s*)[*-] ', multiLine: true), (m) => '${m[1]}• ');
}
