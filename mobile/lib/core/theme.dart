import 'package:flutter/material.dart';

/// Food omniScan design tokens (mirrors the web app): bright "fresh market" palette.
/// White surfaces, fresh green primary, tomato red / orange / sunny yellow accents.
class Brand {
  static const green = Color(0xFF15803D);
  static const greenBright = Color(0xFF16A34A);
  static const greenSoft = Color(0xFFDCFCE7);
  static const tomato = Color(0xFFDC2626);
  static const tomatoSoft = Color(0xFFFEE2E2);
  static const orange = Color(0xFFEA580C);
  static const orangeSoft = Color(0xFFFFEDD5);
  static const sun = Color(0xFFA16207);
  static const sunSoft = Color(0xFFFEF9C3);
  static const sky = Color(0xFF0369A1);
  static const skySoft = Color(0xFFE0F2FE);
  static const berry = Color(0xFFBE185D);
  static const berrySoft = Color(0xFFFCE7F3);

  static const good = Color(0xFF15803D);
  static const warn = Color(0xFFC2410C);
  static const bad = Color(0xFFDC2626);
  static const grey = Color(0xFF64748B);

  /// (background, icon) pairs for colourful icon tiles, cycled so neighbours differ.
  static const tiles = [
    (greenSoft, green),
    (tomatoSoft, tomato),
    (orangeSoft, orange),
    (sunSoft, sun),
    (skySoft, sky),
    (berrySoft, berry),
  ];

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
  final light = b == Brightness.light;
  final scheme = ColorScheme.fromSeed(seedColor: Brand.greenBright, brightness: b).copyWith(
    primary: light ? Brand.green : const Color(0xFF4ADE80),
    onPrimary: light ? Colors.white : const Color(0xFF052E16),
    primaryContainer: light ? Brand.greenSoft : const Color(0xFF143420),
    onPrimaryContainer: light ? const Color(0xFF14532D) : const Color(0xFFBBF7D0),
    secondary: light ? Brand.tomato : const Color(0xFFF87171),
    tertiary: light ? Brand.orange : const Color(0xFFFB923C),
    surface: light ? Colors.white : const Color(0xFF141C17),
  );
  final border = light ? const Color(0xFFE3E9DF) : const Color(0xFF273329);
  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    scaffoldBackgroundColor: light ? Colors.white : const Color(0xFF0D1310),
    appBarTheme: AppBarTheme(
      backgroundColor: scheme.surface,
      surfaceTintColor: Colors.transparent,
      titleTextStyle: TextStyle(color: scheme.onSurface, fontSize: 20, fontWeight: FontWeight.w800),
    ),
    cardTheme: CardThemeData(
      elevation: 0,
      color: scheme.surface,
      surfaceTintColor: Colors.transparent,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20), side: BorderSide(color: border)),
    ),
    chipTheme: ChipThemeData(selectedColor: scheme.primaryContainer, side: BorderSide(color: border)),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: scheme.surface,
      indicatorColor: scheme.primaryContainer,
      surfaceTintColor: Colors.transparent,
    ),
    inputDecorationTheme: InputDecorationTheme(
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
      filled: true,
      fillColor: light ? const Color(0xFFF3F7F1) : const Color(0xFF1B251F),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(minimumSize: const Size(48, 48), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
    ),
    floatingActionButtonTheme: FloatingActionButtonThemeData(backgroundColor: scheme.primary, foregroundColor: scheme.onPrimary),
  );
}
