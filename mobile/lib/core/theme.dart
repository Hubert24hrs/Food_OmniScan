import 'package:flutter/material.dart';

/// Food omniScan design tokens (mirrors the web app).
class Brand {
  static const teal = Color(0xFF0F766E);
  static const tealDark = Color(0xFF134E4A);
  static const mint = Color(0xFF5EEAD4);
  static const good = Color(0xFF15803D);
  static const warn = Color(0xFFB45309);
  static const bad = Color(0xFFB91C1C);
  static const grey = Color(0xFF64748B);

  static Color scoreColor(String? color) => switch (color) {
        'green' => good,
        'amber' => warn,
        'red' => bad,
        _ => grey,
      };

  static Color verdictColor(String? verdict) => switch (verdict) {
        'green' => good,
        'yellow' => warn,
        'red' => bad,
        _ => grey,
      };

  static String verdictLabel(String? verdict) => switch (verdict) {
        'green' => 'Fits',
        'yellow' => 'Check',
        'red' => 'Avoid',
        _ => 'Unknown',
      };
}

ThemeData buildTheme(Brightness b) {
  final scheme = ColorScheme.fromSeed(seedColor: Brand.teal, brightness: b);
  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    scaffoldBackgroundColor: b == Brightness.light ? const Color(0xFFF6F8F7) : const Color(0xFF0B1412),
    cardTheme: CardThemeData(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
        side: BorderSide(color: scheme.outlineVariant),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
      filled: true,
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(minimumSize: const Size(48, 48), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
    ),
  );
}
