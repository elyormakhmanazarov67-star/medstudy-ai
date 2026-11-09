"""Staging displays local anatomy diagrams for all 14 lessons, not only anat_10."""
import json
from pathlib import Path
from xml.etree import ElementTree
ROOT=Path(__file__).resolve().parents[1]
STATIC=ROOT/'app'/'static'

def test_all_14_anatomy_diagrams_and_ui_buttons():
    lessons=json.loads((ROOT/'content'/'lessons.json').read_text(encoding='utf-8'))
    anatomy=next(s for s in lessons['subjects'] if s['id']=='odam_anatomiyasi_1')
    manifest=json.loads((STATIC/'illustrations'/'catalog.json').read_text(encoding='utf-8'))
    js=(STATIC/'app.js').read_text(encoding='utf-8')
    assert len(anatomy['lessons'])==14
    assert {l['id'] for l in anatomy['lessons']}==set(manifest)
    assert "case 'visual':if(state.lesson)showVisualLesson()" in js
    for key in manifest:
        assert key in js
        svg=STATIC/manifest[key]['src'].removeprefix('/static/')
        assert svg.is_file()
        assert ElementTree.parse(svg).getroot().tag.endswith('svg')
    html=(STATIC/'index.html').read_text(encoding='utf-8')
    assert 'app.js?v=1.0.6' in html
