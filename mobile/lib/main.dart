import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'core/app_state.dart';
import 'core/theme.dart';
import 'screens/account_screens.dart';
import 'screens/home_screens.dart';
import 'screens/scan_screen.dart';

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
      HomeScreen(onScan: () => setState(() => index = 2)),
      const DiscoverScreen(),
      const ScanScreen(),
      const DiaryScreen(),
      const ProfileScreen(),
    ];
    return Scaffold(
      body: IndexedStack(index: index, children: [for (var i = 0; i < pages.length; i++) i == index || i != 2 ? pages[i] : const SizedBox()]),
      floatingActionButtonLocation: FloatingActionButtonLocation.centerDocked,
      floatingActionButton: FloatingActionButton.large(
        tooltip: 'Scan',
        onPressed: () => setState(() => index = 2),
        child: const Icon(Icons.qr_code_scanner, size: 36),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: index,
        onDestinationSelected: (i) => setState(() => index = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.home_outlined), label: 'Home'),
          NavigationDestination(icon: Icon(Icons.search), label: 'Discover'),
          NavigationDestination(icon: SizedBox(width: 24), label: 'Scan'),
          NavigationDestination(icon: Icon(Icons.edit_note), label: 'Diary'),
          NavigationDestination(icon: Icon(Icons.person_outline), label: 'Profile'),
        ],
      ),
    );
  }
}
