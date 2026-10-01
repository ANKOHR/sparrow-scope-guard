import json
from sparrow_scope_guard.core import analyze
from sparrow_scope_guard.fixtures import fixture_records
from sparrow_scope_guard.report import render


def test_report_carries_provenance_banner():
    records = fixture_records(2)
    records[0].update(synthetic=False, source='henry_entered')
    for fmt in ('md','json'):
        out = render(analyze(records,'2026-09-30'), fmt)
        assert 'Data provenance: 1 synthetic fixture records; 1 real records' in out
        assert 'henry_entered' in out
        assert 'engagement-001' in out


def test_hypothetical_figures_labelled():
    result = analyze(fixture_records(), '2026-09-30')
    assert 'hypothetical_exposure_cents' in result
    assert 'Not measured' in result['savings']
    for fmt in ('md','json'):
        assert 'hypothetical' in render(result, fmt).lower()


def test_handles_unicode_and_long_inputs():
    r = fixture_records(2)[1]
    r['client'] = '客户 café '+ 'x'*9000 + r' C:\Users\henry\data'
    result = analyze([r], '2026-09-30')
    assert json.loads(render(result,'json'))['cases'][0]['client'] == r['client']


def test_no_em_dashes_in_outputs():
    result = analyze(fixture_records(), '2026-09-30')
    for fmt in ('md','json'):
        assert chr(0x2014) not in render(result,fmt)
