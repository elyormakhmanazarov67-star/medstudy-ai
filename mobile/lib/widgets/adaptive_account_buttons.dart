import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';

/// Native-feeling iPhone actions without maintaining separate registration
/// logic or changing the working Android Material buttons.
class AdaptiveAccountPrimaryButton extends StatelessWidget {
  final String label;
  final IconData icon;
  final VoidCallback? onPressed;

  const AdaptiveAccountPrimaryButton({
    super.key,
    required this.label,
    required this.icon,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    if (Theme.of(context).platform == TargetPlatform.iOS) {
      final materialTheme = Theme.of(context);
      return CupertinoTheme(
        data: CupertinoThemeData(primaryColor: materialTheme.colorScheme.primary),
        child: SizedBox(
          width: double.infinity,
          child: CupertinoButton.filled(
            onPressed: onPressed,
            child: Row(
              mainAxisSize: MainAxisSize.min,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(icon, size: 20),
                const SizedBox(width: 8),
                Flexible(child: Text(label)),
              ],
            ),
          ),
        ),
      );
    }
    return FilledButton.icon(
      onPressed: onPressed,
      icon: Icon(icon),
      label: Text(label),
    );
  }
}

class AdaptiveAccountSecondaryButton extends StatelessWidget {
  final String label;
  final VoidCallback? onPressed;

  const AdaptiveAccountSecondaryButton({
    super.key,
    required this.label,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    if (Theme.of(context).platform == TargetPlatform.iOS) {
      return CupertinoTheme(
        data: CupertinoThemeData(primaryColor: Theme.of(context).colorScheme.primary),
        child: CupertinoButton(
          onPressed: onPressed,
          child: Text(label),
        ),
      );
    }
    return TextButton(onPressed: onPressed, child: Text(label));
  }
}
