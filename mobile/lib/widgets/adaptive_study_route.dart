import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';

/// Retains one shared Flutter screen tree for Android and iOS, but uses
/// native-feeling iOS slide transitions and the interactive back swipe.
Route<T> adaptiveStudyRoute<T>(BuildContext context, Widget page) {
  if (Theme.of(context).platform == TargetPlatform.iOS) {
    return CupertinoPageRoute<T>(builder: (_) => page);
  }
  return MaterialPageRoute<T>(builder: (_) => page);
}
