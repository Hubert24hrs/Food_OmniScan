import 'package:flutter/material.dart';

import '../core/theme.dart';

bool _reduceMotion(BuildContext context) => MediaQuery.maybeDisableAnimationsOf(context) ?? false;

/// Colourful rounded tile with an icon that gently floats; `index` picks the colour pair.
class IconTile extends StatefulWidget {
  const IconTile({super.key, required this.icon, this.index = 0, this.size = 44});
  final IconData icon;
  final int index;
  final double size;

  @override
  State<IconTile> createState() => _IconTileState();
}

class _IconTileState extends State<IconTile> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(vsync: this, duration: const Duration(milliseconds: 2200));

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_reduceMotion(context)) {
      _c.stop();
    } else if (!_c.isAnimating) {
      // Stagger neighbours so the tiles don't bob in unison.
      _c.value = (widget.index * 0.23) % 1;
      _c.repeat(reverse: true);
    }
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final (bg, fg) = Brand.tiles[widget.index % Brand.tiles.length];
    final dark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      width: widget.size,
      height: widget.size,
      decoration: BoxDecoration(color: dark ? fg.withValues(alpha: 0.18) : bg, borderRadius: BorderRadius.circular(widget.size * 0.3)),
      child: AnimatedBuilder(
        animation: _c,
        builder: (context, child) => Transform.translate(
          offset: Offset(0, -3 * Curves.easeInOut.transform(_c.value)),
          child: child,
        ),
        child: Icon(widget.icon, color: dark ? Color.lerp(fg, Colors.white, 0.35) : fg, size: widget.size * 0.52),
      ),
    );
  }
}

/// Primary scan button with a soft breathing pulse and a scan line sweeping across the icon.
class PulsingScanButton extends StatefulWidget {
  const PulsingScanButton({super.key, required this.onPressed});
  final VoidCallback onPressed;

  @override
  State<PulsingScanButton> createState() => _PulsingScanButtonState();
}

class _PulsingScanButtonState extends State<PulsingScanButton> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(vsync: this, duration: const Duration(milliseconds: 2400));

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_reduceMotion(context)) {
      _c.stop();
    } else if (!_c.isAnimating) {
      _c.repeat();
    }
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return AnimatedBuilder(
      animation: _c,
      builder: (context, _) {
        final t = _c.value;
        final pulse = 1 + 0.04 * Curves.easeInOut.transform(t < 0.5 ? t * 2 : (1 - t) * 2);
        return Stack(alignment: Alignment.center, children: [
          // Expanding ring
          Opacity(
            opacity: (1 - t).clamp(0, 1) * 0.5,
            child: Container(
              width: 76 + 22 * t,
              height: 76 + 22 * t,
              decoration: BoxDecoration(borderRadius: BorderRadius.circular(28), border: Border.all(color: cs.primary, width: 2)),
            ),
          ),
          Transform.scale(
            scale: pulse,
            child: Material(
              color: cs.primary,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(26)),
              child: InkWell(
                borderRadius: BorderRadius.circular(26),
                onTap: widget.onPressed,
                child: SizedBox(
                  width: 76,
                  height: 76,
                  child: Stack(alignment: Alignment.center, children: [
                    Icon(Icons.qr_code_scanner, size: 36, color: cs.onPrimary),
                    Positioned(
                      top: 18 + 38 * Curves.easeInOut.transform(t < 0.5 ? t * 2 : (1 - t) * 2),
                      child: Container(width: 40, height: 2.5, decoration: BoxDecoration(color: const Color(0xFFFEF08A), borderRadius: BorderRadius.circular(2))),
                    ),
                  ]),
                ),
              ),
            ),
          ),
        ]);
      },
    );
  }
}

/// Thin produce-label stripe (green / yellow / orange / red) used under headers.
class FreshStripe extends StatelessWidget {
  const FreshStripe({super.key});

  @override
  Widget build(BuildContext context) => const SizedBox(
        height: 3,
        child: Row(children: [
          Expanded(flex: 10, child: ColoredBox(color: Brand.greenBright)),
          Expanded(flex: 4, child: ColoredBox(color: Color(0xFFEAB308))),
          Expanded(flex: 3, child: ColoredBox(color: Brand.orange)),
          Expanded(flex: 3, child: ColoredBox(color: Brand.tomato)),
        ]),
      );
}

/// App icon + "Food omniScan" wordmark in brand colours.
class Wordmark extends StatelessWidget {
  const Wordmark({super.key});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Row(mainAxisSize: MainAxisSize.min, children: [
      ClipRRect(
        borderRadius: BorderRadius.circular(8),
        child: Image.asset('assets/brand/app_icon_256.png', width: 32, height: 32, semanticLabel: 'Food omniScan logo'),
      ),
      const SizedBox(width: 10),
      // Shrinks rather than overflowing when the app bar also shows actions on a narrow phone.
      Flexible(
        child: FittedBox(
          fit: BoxFit.scaleDown,
          alignment: Alignment.centerLeft,
          child: Text.rich(TextSpan(children: [
            TextSpan(text: 'Food ', style: TextStyle(color: cs.onSurface)),
            TextSpan(text: 'omni', style: TextStyle(color: cs.primary)),
            TextSpan(text: 'Scan', style: TextStyle(color: cs.secondary)),
          ]), style: const TextStyle(fontSize: 21, fontWeight: FontWeight.w800), maxLines: 1),
        ),
      ),
    ]);
  }
}
