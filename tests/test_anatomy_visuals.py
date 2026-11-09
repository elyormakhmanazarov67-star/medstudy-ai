"""All 14 anatomy lessons have separate offline visual guides."""
import json
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
VISUALS = ROOT / "app" / "static" / "illustrations"


def test_all_anatomy_lessons_have_local_illustrations():
    with (ROOT / "content" / "lessons.json").open(encoding="utf-8") as f:
        curriculum = json.load(f)
    anatomy = next(s for s in curriculum["subjects"] if s["id"] == "odam_anatomiyasi_1")
    lesson_ids = {lesson["id"] for lesson in anatomy["lessons"]}
    with (VISUALS / "catalog.json").open(encoding="utf-8") as f:
        visual_index = json.load(f)
    assert len(lesson_ids) == 14
    assert set(visual_index) == lesson_ids
    assert len({entry["src"] for entry in visual_index.values()}) == 14

    for lesson in anatomy["lessons"]:
        entry = visual_index[lesson["id"]]
        assert entry["title"] and entry["alt"]
        assert entry["src"].startswith("/static/illustrations/")
        assert len(entry["facts"]) >= 4
        path = ROOT / "app" / entry["src"].lstrip("/")
        assert path.is_file(), path
        image = ElementTree.parse(path).getroot()
        assert image.tag == "{http://www.w3.org/2000/svg}svg"
        assert image.attrib["viewBox"] == "0 0 900 565"
        for latin, explanation in entry["facts"]:
            assert latin and explanation
            assert latin in path.read_text(encoding="utf-8")


def test_anatomy_visual_button_does_not_depend_on_paid_ai():
    js = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
    assert "l.subject_id==='odam_anatomiyasi_1'" in js
    assert "case 'anatomy-visual':await showPresetAnatomyVisual()" in js
    assert "ANATOMY_VISUAL_URL='/static/illustrations/catalog.json'" in js
    assert "case 'anatomy-image':resetAnatomyImage()" in js
