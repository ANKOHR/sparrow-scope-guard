import json
from sparrow_scope_guard.fixtures import generate
from sparrow_scope_guard.cli import load_input
from sparrow_scope_guard.report import render


def test_fixtures_labelled_synthetic(tmp_path):
    generate(tmp_path)
    assert (tmp_path/'records.jsonl').read_text().startswith('# SYNTHETIC')
    for path in tmp_path.glob('*.json'):
        assert json.loads(path.read_text())['synthetic'] is True
    assert all(r['synthetic'] for r in load_input(tmp_path)['provenance'])


def test_report_matches_ground_truth_exact(tmp_path):
    generate(tmp_path)
    expected = json.loads((tmp_path/'expectations.json').read_text())
    actual = load_input(tmp_path)
    rendered = json.loads(render(actual, 'json'))
    for key in ('record_count','flagged_count','unapproved_minutes','new_deliverable_count','hypothetical_exposure_cents'):
        assert actual[key] == expected[key]
        assert rendered[key] == expected[key]
    assert [c['id'] for c in actual['cases']] == expected['flagged_ids']


def test_report_zero_false_positives(tmp_path):
    generate(tmp_path)
    actual = {c['id'] for c in load_input(tmp_path)['cases']}
    planted = {f'engagement-{i:03d}' for i in range(200) if i % 4}
    assert actual-planted == set()
    assert planted-actual == set()
