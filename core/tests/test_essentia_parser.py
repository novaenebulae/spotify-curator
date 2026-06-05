from __future__ import annotations

import json
from pathlib import Path

from app.audio.essentia_parser import parse_essentia_json


def test_parse_essentia_fixture() -> None:
    fixture = Path(__file__).parent / "fixtures" / "essentia_lowlevel_sample.json"
    data = json.loads(fixture.read_text(encoding="utf-8"))
    parsed = parse_essentia_json(data)
    assert parsed.bpm == 120.5
    assert parsed.key == 0
    assert parsed.mode == 1
    assert parsed.loudness == -8.2
    assert parsed.mfcc


def test_parse_essentia_full_rhythm_profile() -> None:
    fixture = Path(__file__).parent / "fixtures" / "essentia_lowlevel_full_sample.json"
    data = json.loads(fixture.read_text(encoding="utf-8"))
    parsed = parse_essentia_json(data)
    assert parsed.bpm == 120.5
    assert parsed.bpm_confidence == 0.91
    assert parsed.onset_rate == 2.4
    assert parsed.raw_summary["perceptual_tempo"] == 118.0
    assert parsed.raw_summary["beats_loudness"] == 0.42
