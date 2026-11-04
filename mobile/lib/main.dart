import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'core/app_state.dart';
import 'core/theme.dart';
import 'screens/account_screens.dart';
import 'screens/diary_screen.dart';
import 'screens/explore_hub.dart';
import 'screens/home_screens.dart';
import 'screens/scan_screen.dart';
import 'widgets/fresh.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(ChangeNotifierProvider(create: (_) => AppState()..init(), child: const FoodOmniScanApp()));
}

class FoodOmniScanApp extends StatelessWidget {
  const FoodOmniScanApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Food omniScan',
      debugShowCheckedModeBanner: false,
      theme: buildTheme(Brightness.light),
      darkTheme: buildTheme(Brightness.dark),
      home: const Shell(),
    );
  }
}

/// Bottom navigation: Home, Discover, Scan (prominent), Diary, Profile.
class Shell extends StatefulWidget {
  const Shell({super.key});

  @override
  State<Shell> createState() => _ShellState();
}

class _ShellState extends State<Shell> {
  int index = 0;

  @override
  Widget build(BuildContext context) {
    final pages = [
      HomeScreen(onScan: () => setState(() => index = 2), onExplore: () => setState(() => index = 1)),
      const ExploreScreen(),
      const ScanScreen(),
      const DiaryScreen(),
      const ProfileScreen(),
    ];
    return Scaffold(
      body: IndexedStack(index: index, children: [for (var i = 0; i < pages.length; i++) i == index || i != 2 ? pages[i] : const SizedBox()]),
      floatingActionButtonLocation: FloatingActionButtonLocation.centerDocked,
      floatingActionButton: Semantics(
        button: true,
        label: 'Scan',
        child: PulsingScanButton(onPressed: () => setState(() => index = 2)),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: index,
        onDestinationSelected: (i) => setState(() => index = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.home_outlined), selectedIcon: Icon(Icons.home_rounded), label: 'Home'),
          NavigationDestination(icon: Icon(Icons.explore_outlined), selectedIcon: Icon(Icons.explore), label: 'Explore'),
          NavigationDestination(icon: SizedBox(width: 24), label: 'Scan'),
          NavigationDestination(icon: Icon(Icons.edit_note), selectedIcon: Icon(Icons.edit_note_rounded), label: 'Diary'),
          NavigationDestination(icon: Icon(Icons.person_outline), selectedIcon: Icon(Icons.person_rounded), label: 'Profile'),
        ],
      ),
    );
  }
}
