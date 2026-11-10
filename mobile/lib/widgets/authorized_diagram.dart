import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import '../mobile_api.dart';

class AuthorizedDiagram extends StatefulWidget {
  final String lessonId;
  const AuthorizedDiagram({super.key, required this.lessonId});

  @override
  State<AuthorizedDiagram> createState() => _AuthorizedDiagramState();
}

class _AuthorizedDiagramState extends State<AuthorizedDiagram> {
  late Future<String> svg;
  @override
  void initState() {
    super.initState();
    svg = MobileApi.diagram(widget.lessonId);
  }

  @override
  Widget build(BuildContext context) => FutureBuilder<String>(
    future: svg,
    builder: (context, snapshot) {
      if (snapshot.connectionState != ConnectionState.done) {
        return const SizedBox(height: 180, child: Center(child: CircularProgressIndicator()));
      }
      if (snapshot.hasError || !snapshot.hasData) {
        return const Padding(
          padding: EdgeInsets.all(16),
          child: Text('Rasmni ochish uchun administrator ruxsati va internet kerak.'),
        );
      }
      return SvgPicture.string(snapshot.data!, height: 300);
    },
  );
}
