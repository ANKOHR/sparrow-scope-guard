import copy
import pytest
from sparrow_scope_guard.core import analyze, SchemaError
from sparrow_scope_guard.fixtures import fixture_records


def test_fixture_ground_truth_matches_hand_computed():
    r = analyze(fixture_records(), "2026-09-30")
    assert (r['record_count'], r['flagged_count'], r['unapproved_minutes'],
            r['new_deliverable_count'], r['hypothetical_exposure_cents']) == (200, 150, 3000, 100, 300000)


@pytest.mark.parametrize('field,value', [('requested_minutes', -1), ('hourly_rate_cents', True),
    ('date', '2026-10-01'), ('client', 'x'*10001), ('requested_minutes', 100000001),
    ('approved_deliverables', ['a', 'a']), ('synthetic', 'true'), ('source', 'unknown')])
def test_rejects_adversarial_values(field, value):
    r = fixture_records(1)[0]
    r[field] = value
    with pytest.raises(SchemaError, match=field):
        analyze([r], '2026-09-30')


def test_duplicate_ids():
    r = fixture_records(1)[0]
    with pytest.raises(SchemaError, match='duplicate'):
        analyze([r, copy.deepcopy(r)], '2026-09-30')


def test_corrupted_input_changes_computed_figures():
    records = fixture_records()
    before = analyze(records, '2026-09-30')
    records[0]['requested_minutes'] = 180
    after = analyze(records, '2026-09-30')
    assert after['flagged_count'] == before['flagged_count'] + 1
    assert after['hypothetical_exposure_cents'] == before['hypothetical_exposure_cents'] + 6000


def test_rounding_and_unpriced_deliverables():
    r = fixture_records(1)[0]
    r.update(requested_minutes=121, hourly_rate_cents=30)
    assert analyze([r], '2026-09-30')['hypothetical_exposure_cents'] == 1
    r.update(requested_minutes=0, requested_deliverables=['draft', 'extra'])
    result = analyze([r], '2026-09-30')
    assert result['flagged_count'] == 1
    assert result['hypothetical_exposure_cents'] == 0


def test_five_handwritten_records():
    base = dict(client='Synthetic handwritten example', synthetic=True, source='synthetic_fixture', date='2026-09-30',
                approved_minutes=60, hourly_rate_cents=6000, approved_deliverables=['draft'])
    records = [dict(base, id=id, requested_minutes=minutes, requested_deliverables=items)
               for id, minutes, items in [('a',60,['draft']), ('b',90,['draft']),
                ('c',60,['draft','revision']), ('d',120,['draft','revision']), ('e',30,[])]]
    r = analyze(records, '2026-09-30')
    assert (r['flagged_count'], r['unapproved_minutes'], r['new_deliverable_count'], r['hypothetical_exposure_cents']) == (3,90,2,9000)


def test_rejects_em_dash_input_with_named_field():
    r = fixture_records(1)[0]
    r['client'] = 'client' + chr(0x2014) + 'name'
    with pytest.raises(SchemaError, match='client: unsupported U\\+2014'):
        analyze([r], '2026-09-30')
