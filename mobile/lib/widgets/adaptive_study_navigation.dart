import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';

/// Keeps Android's Material navigation while giving iPhone users the familiar
/// compact iOS tab bar. Both platforms share the same page state and API.
class AdaptiveStudyNavigation extends StatelessWidget {
  final int selectedIndex;
  final ValueChanged<int> onSelected;

  const AdaptiveStudyNavigation({
    super.key,
    required this.selectedIndex,
    required this.onSelected,
  });

  @override
  Widget build(BuildContext context) {
    if (Theme.of(context).platform == TargetPlatform.iOS) {
      final colors = Theme.of(context).colorScheme;
      return CupertinoTabBar(
        currentIndex: selectedIndex,
        onTap: onSelected,
        activeColor: colors.primary,
        inactiveColor: colors.onSurfaceVariant,
        backgroundColor: colors.surface,
        border: Border(
          top: BorderSide(color: colors.outlineVariant, width: 0.5),
        ),
        items: const [
          BottomNavigationBarItem(
            icon: Icon(CupertinoIcons.house),
            activeIcon: Icon(CupertinoIcons.house_fill),
            label: 'Asosiy',
          ),
          BottomNavigationBarItem(
            icon: Icon(CupertinoIcons.book),
            activeIcon: Icon(CupertinoIcons.book_fill),
            label: 'Fanlar',
          ),
          BottomNavigationBarItem(
            icon: Icon(CupertinoIcons.chart_bar),
            activeIcon: Icon(CupertinoIcons.chart_bar_fill),
            label: 'Natija',
          ),
          BottomNavigationBarItem(
            icon: Icon(CupertinoIcons.gear),
            activeIcon: Icon(CupertinoIcons.gear_solid),
            label: 'Sozlama',
          ),
        ],
      );
    }

    return NavigationBar(
      selectedIndex: selectedIndex,
      onDestinationSelected: onSelected,
      destinations: const [
        NavigationDestination(
          icon: Icon(Icons.home_outlined),
          selectedIcon: Icon(Icons.home),
          label: 'Asosiy',
        ),
        NavigationDestination(
          icon: Icon(Icons.menu_book_outlined),
          selectedIcon: Icon(Icons.menu_book),
          label: 'Fanlar',
        ),
        NavigationDestination(
          icon: Icon(Icons.bar_chart_outlined),
          selectedIcon: Icon(Icons.bar_chart),
          label: 'Natija',
        ),
        NavigationDestination(
          icon: Icon(Icons.settings_outlined),
          selectedIcon: Icon(Icons.settings),
          label: 'Sozlama',
        ),
      ],
    );
  }
}
