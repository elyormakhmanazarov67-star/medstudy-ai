"""Coverage for the 31 original Preklinik illustration guides."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "app" / "static" / "illustrations" / "preklinik"


def test_preklinik_31_lessons_have_distinct_illustrated_guides():
    data = json.loads((ROOT / "content" / "lessons.json").read_text(encoding="utf-8"))
    subject = next(x for x in data["subjects"] if x["id"] == "stom_prerest")
    lesson_ids = {l["id"] for l in subject["lessons"]}
    guides = json.loads((ASSETS / "catalog.json").read_text(encoding="utf-8"))
    assert len(lesson_ids) == len(guides) == 31
    assert set(guides) == lesson_ids

    used_src = set()
    for key, entry in guides.items():
        assert entry["title"] and entry["alt"] and entry["notice"]
        assert "Soddalashtirilgan" in entry["notice"]
        assert len(entry["facts"]) == 3
        assert all(len(fact) == 2 and all(isinstance(item, str) and item.strip() for item in fact)
                   for fact in entry["facts"])
        src = entry["src"]
        assert src == "/static/illustrations/preklinik/" + key + ".svg"
        assert src not in used_src
        used_src.add(src)
        raw = (ASSETS / (key + ".svg")).read_text(encoding="utf-8")
        doc = ET.fromstring(raw)
        assert doc.tag == "{http://www.w3.org/2000/svg}svg"
        assert doc.attrib["role"] == "img"
        assert entry["title"] in "".join(doc.itertext())
        assert "http://" not in raw and "<script" not in raw
    assert len(list(ASSETS.glob("*.svg"))) == 31


def test_preklinik_visual_action_is_isolated_to_its_subject():
    script = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
    assert "l.subject_id==='stom_prerest'?" in script
    assert "case 'preklinik-visual':await showPreklinikVisual();break;" in script
    assert "lesson.subject_id!=='stom_prerest'" in script
    assert "data-action=\"anatomy-visual\"" in script
