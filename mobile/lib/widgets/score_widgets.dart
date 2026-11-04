import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../core/theme.dart';

class ScoreRing extends StatelessWidget {
  const ScoreRing({super.key, required this.score, required this.color, required this.label, this.size = 120});

  final int? score;
  final String? color;
  final String label;
  final double size;

  @override
  Widget build(BuildContext context) {
    final c = Brand.scoreColor(color);
    return Semantics(
      label: score == null ? 'Score: $label' : 'Score $score out of 100, $label',
      child: SizedBox(
        width: size,
        height: size,
        child: CustomPaint(
          painter: _RingPainter((score ?? 0) / 100, c, Theme.of(context).colorScheme.surfaceContainerHighest),
          child: Center(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              Text(score?.toString() ?? '?',
                  style: TextStyle(fontSize: size * 0.3, fontWeight: FontWeight.w800, color: c, height: 1)),
              Text(score == null ? 'no score' : '/ 100', style: Theme.of(context).textTheme.labelSmall),
            ]),
          ),
        ),
      ),
    );
  }
}

class _RingPainter extends CustomPainter {
  _RingPainter(this.pct, this.color, this.track);
  final double pct;
  final Color color;
  final Color track;

  @override
  void paint(Canvas canvas, Size size) {
    final stroke = size.width * 0.1;
    final rect = Offset.zero & size;
    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = stroke
      ..strokeCap = StrokeCap.round;
    canvas.drawArc(rect.deflate(stroke / 2), 0, 2 * math.pi, false, paint..color = track);
    canvas.drawArc(rect.deflate(stroke / 2), -math.pi / 2, 2 * math.pi * pct.clamp(0, 1), false, paint..color = color);
  }

  @override
  bool shouldRepaint(_RingPainter old) => old.pct != pct || old.color != color;
}

class MiniScore extends StatelessWidget {
  const MiniScore({super.key, required this.score, required this.color});
  final int? score;
  final String? color;

  @override
  Widget build(BuildContext context) {
    final c = Brand.scoreColor(color);
    return Container(
      width: 44,
      height: 44,
      alignment: Alignment.center,
      decoration: BoxDecoration(shape: BoxShape.circle, border: Border.all(color: c, width: 3)),
      child: Text(score?.toString() ?? '?', style: TextStyle(fontWeight: FontWeight.w800, color: c)),
    );
  }
}

class VerdictChip extends StatelessWidget {
  const VerdictChip({super.key, required this.verdict, this.name});
  final String verdict;
  final String? name;

  @override
  Widget build(BuildContext context) {
    final c = Brand.verdictColor(verdict);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(color: c.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(99)),
      child: Text('${name != null ? '$name: ' : ''}${Brand.verdictLabel(verdict)}',
          style: TextStyle(color: c, fontWeight: FontWeight.w700)),
    );
  }
}

class Pill extends StatelessWidget {
  const Pill(this.text, {super.key, this.color});
  final String text;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final c = color ?? Brand.grey;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(color: c.withValues(alpha: 0.14), borderRadius: BorderRadius.circular(99)),
      child: Text(text, style: TextStyle(color: c, fontSize: 12, fontWeight: FontWeight.w600)),
    );
  }
}
