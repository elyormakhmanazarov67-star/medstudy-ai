import 'dart:math' as math;
import 'package:flutter/material.dart';

/// Gesture-controlled 3D dental-arch schematic drawn locally in Flutter.
/// The model is intentionally stylized, NOT clinically accurate.
class DentalArch3DPage extends StatefulWidget {
  const DentalArch3DPage({super.key});
  @override
  State<DentalArch3DPage> createState() => _DentalArch3DPageState();
}

class _DentalArch3DPageState extends State<DentalArch3DPage> {
  double yaw = -0.25;
  double pitch = -0.42;
  double zoom = 1;
  double initialZoom = 1;

  void reset() => setState(() {
    yaw = -0.25;
    pitch = -0.42;
    zoom = 1;
  });

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('MedStudy AI 3.0 · 3D')),
    body: ListView(padding: const EdgeInsets.all(16), children: [
      Text('Tish qatori · 3D', style: Theme.of(context).textTheme.headlineSmall),
      const SizedBox(height: 6),
      const Text('Barmoq bilan modelni aylantiring. Ikki barmoq bilan kattalashtiring.'),
      const SizedBox(height: 16),
      ClipRRect(
        borderRadius: BorderRadius.circular(24),
        child: Semantics(
          label: 'Aylantiriladigan uch o‘lchovli tish qatori sxemasi',
          child: GestureDetector(
            behavior: HitTestBehavior.opaque,
            onDoubleTap: reset,
            onScaleStart: (_) => initialZoom = zoom,
            onScaleUpdate: (details) => setState(() {
              yaw += details.focalPointDelta.dx * 0.009;
              pitch = (pitch - details.focalPointDelta.dy * 0.009)
                  .clamp(-1.12, 0.48);
              zoom = (initialZoom * details.scale).clamp(0.65, 1.7);
            }),
            child: AspectRatio(
              aspectRatio: 1.16,
              child: CustomPaint(
                key: const Key('dental-arch-3d'),
                painter: _DentalArchPainter(yaw: yaw, pitch: pitch, zoom: zoom),
              ),
            ),
          ),
        ),
      ),
      const SizedBox(height: 12),
      Row(children: [
        const Icon(Icons.threed_rotation, color: Color(0xFF20844D)),
        const SizedBox(width: 8),
        Expanded(child: Text('Burilish: ' +
          (yaw * 180 / math.pi).round().toString() + '° · ' +
          'Masshtab: ' + (zoom * 100).round().toString() + '%')),
        TextButton.icon(
          onPressed: reset,
          icon: const Icon(Icons.restart_alt),
          label: const Text('Qayta'),
        ),
      ]),
      const SizedBox(height: 12),
      Card(child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('O‘quv maketi', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 6),
          const Text('Bu interaktiv 3D sxema tish qatorining umumiy shaklini '
            'ko‘rsatadi. Tishlar soni, o‘lchamlari va joylashuvi soddalashtirilgan. '
            'Diagnostika yoki klinik qaror uchun foydalanmang. '
            'Keyinchalik tasdiqlangan anatomik 3D modellar qo‘shiladi.'),
        ]),
      )),
    ]),
  );
}

class _Pt {
  final double x, y, z;
  const _Pt(this.x, this.y, this.z);
}
class _Face {
  final List<_Pt> vertices;
  final Color color;
  const _Face(this.vertices, this.color);
}
class _ProjectedFace {
  final List<Offset> points;
  final Color color;
  final double depth;
  const _ProjectedFace(this.points, this.color, this.depth);
}

class _DentalArchPainter extends CustomPainter {
  final double yaw, pitch, zoom;
  const _DentalArchPainter({required this.yaw, required this.pitch, required this.zoom});

  _Pt _turn(_Pt p) {
    final x1 = p.x * math.cos(yaw) + p.z * math.sin(yaw);
    final z1 = -p.x * math.sin(yaw) + p.z * math.cos(yaw);
    return _Pt(x1,
      p.y * math.cos(pitch) - z1 * math.sin(pitch),
      p.y * math.sin(pitch) + z1 * math.cos(pitch));
  }

  Offset _project(_Pt p, Size size) {
    final perspective = 370 / (370 - p.z);
    final scale = size.shortestSide / 265 * zoom;
    return Offset(
      size.width / 2 + p.x * scale * perspective,
      size.height * 0.52 + p.y * scale * perspective,
    );
  }

  void _prism(List<_Face> faces, _Pt center,
      double width, double depth, double top, double bottom,
      Color side, Color topColor) {
    final x = center.x, z = center.z, w = width / 2, d = depth / 2;
    final a = _Pt(x-w,top,z-d), b = _Pt(x+w,top,z-d);
    final c = _Pt(x+w,top,z+d), e = _Pt(x-w,top,z+d);
    final f = _Pt(x-w,bottom,z-d), g = _Pt(x+w,bottom,z-d);
    final h = _Pt(x+w,bottom,z+d), i = _Pt(x-w,bottom,z+d);
    faces.addAll([
      _Face([a,b,c,e],topColor),
      _Face([e,c,h,i],side),
      _Face([a,b,g,f],side.withValues(alpha: 0.78)),
      _Face([a,e,i,f],side.withValues(alpha: 0.90)),
      _Face([b,c,h,g],side.withValues(alpha: 0.74)),
      _Face([f,g,h,i],side.withValues(alpha: 0.70)),
    ]);
  }

  List<_Face> _geometry() {
    final faces = <_Face>[];
    const count = 14;
    for (var index=0; index<count; index++) {
      final t = 0.09 + (math.pi - 0.18) * index / (count - 1);
      final x = 91 * math.cos(t);
      final z = 78 * math.sin(t) - 22;
      final front = (index - (count - 1) / 2).abs() < 3.5;
      final width = front ? 13.0 : 17.0;
      _prism(faces,_Pt(x,0,z),width+3,20,14,33,
        const Color(0xFFB66A79),const Color(0xFFE79DAA));
      _prism(faces,_Pt(x,0,z),width,front ? 15 : 19,-13,16,
        const Color(0xFFE3EADD),const Color(0xFFFFFFEE));
    }
    return faces;
  }

  @override
  void paint(Canvas canvas, Size size) {
    canvas.drawRect(Offset.zero & size, Paint()
      ..shader = const LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [Color(0xFF0E2C22), Color(0xFF183C32), Color(0xFF081A18)],
      ).createShader(Offset.zero & size));
    canvas.drawCircle(
      Offset(size.width*0.5,size.height*0.5),
      size.shortestSide*0.42,
      Paint()..color=const Color(0xFF5BCB87).withValues(alpha:0.10));
    final projected = <_ProjectedFace>[];
    for (final face in _geometry()) {
      final turned = face.vertices.map(_turn).toList(growable:false);
      projected.add(_ProjectedFace(
        turned.map((p)=>_project(p,size)).toList(growable:false),
        face.color,
        turned.map((p)=>p.z).reduce((a,b)=>a+b)/turned.length,
      ));
    }
    projected.sort((a,b)=>a.depth.compareTo(b.depth));
    for (final face in projected) {
      final path = Path()..addPolygon(face.points,true);
      canvas.drawPath(path,Paint()..color=face.color);
      canvas.drawPath(path,Paint()
        ..color=const Color(0xFF214036).withValues(alpha:0.55)
        ..strokeWidth=0.65
        ..style=PaintingStyle.stroke);
    }
  }

  @override
  bool shouldRepaint(covariant _DentalArchPainter old) =>
    old.yaw!=yaw || old.pitch!=pitch || old.zoom!=zoom;
}
