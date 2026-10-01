import json
import time
import pytest
from sparrow_scope_guard.cli import main
from sparrow_scope_guard.fixtures import generate


def test_run_completes_on_fixture(tmp_path, capsys):
    generate(tmp_path/'input')
    start = time.perf_counter()
    assert main(['run','--input',str(tmp_path/'input'),'--state',str(tmp_path/'result.json')]) == 0
    assert main(['report','--state',str(tmp_path/'result.json')]) == 0
    assert time.perf_counter()-start < 5
    assert 'Data provenance' in capsys.readouterr().out


def test_empty_input_renders_without_traceback(tmp_path, capsys):
    assert main(['run','--input',str(tmp_path),'--state',str(tmp_path/'state.json')]) == 0
    assert main(['report','--state',str(tmp_path/'state.json')]) == 0
    assert 'Records: 0' in capsys.readouterr().out


@pytest.mark.parametrize('filename,content,error', [('bad.jsonl','{bad\n','ParseError'),
    ('bad.csv','bad,csv','SchemaError'), ('bad.yaml','bad: [','SchemaError')])
def test_malformed_input_named_error(tmp_path, capsys, filename, content, error):
    (tmp_path/filename).write_text(content)
    assert main(['audit','--input',str(tmp_path),'--as-of','2026-09-30']) == 2
    output = capsys.readouterr().err
    assert error in output and filename in output and 'line 1' in output
    assert 'Traceback' not in output


def test_determinism_byte_identical(tmp_path):
    generate(tmp_path/'input')
    for name in ('a','b'):
        assert main(['run','--input',str(tmp_path/'input'),'--state',str(tmp_path/f'{name}.json')]) == 0
        assert main(['report','--format','md','--state',str(tmp_path/f'{name}.json'),'--out',str(tmp_path/f'{name}.md')]) == 0
    for suffix in ('json','md'):
        assert (tmp_path/f'a.{suffix}').read_bytes() == (tmp_path/f'b.{suffix}').read_bytes()


def test_cli_smoke_all_subcommands(tmp_path, capsys):
    assert main(['fixtures','--out',str(tmp_path/'input')]) == 0
    assert main(['run','--input',str(tmp_path/'input'),'--state',str(tmp_path/'state.json')]) == 0
    for cmd in ('audit','quote'):
        assert main([cmd,'--input',str(tmp_path/'input')]) == 0
    assert main(['quote','--input',str(tmp_path/'input'),'--id','engagement-001']) == 0
    for fmt in ('md','json'):
        assert main(['report','--format',fmt,'--state',str(tmp_path/'state.json')]) == 0
    for cmd in ('fixtures','run','report','audit','quote'):
        with pytest.raises(SystemExit) as exc:
            main([cmd,'--help'])
        assert exc.value.code == 0


def test_missing_input_and_write_failure(tmp_path, capsys):
    assert main(['audit','--input',str(tmp_path/'missing')]) == 2
    assert 'MissingInput' in capsys.readouterr().err
    generate(tmp_path/'input')
    state = tmp_path/'state.json'
    assert main(['run','--input',str(tmp_path/'input'),'--state',str(state)]) == 0
    target = tmp_path/'blocked'
    target.mkdir()
    before = set(tmp_path.iterdir())
    assert main(['report','--state',str(state),'--out',str(target)]) == 2
    assert 'WriteError' in capsys.readouterr().err
    assert set(tmp_path.iterdir()) == before


def test_schema_error_lists_field_and_line(tmp_path, capsys):
    generate(tmp_path)
    path = tmp_path/'records.jsonl'
    lines = path.read_text().splitlines()
    record = json.loads(lines[1])
    record['requested_minutes'] = -1
    lines[1] = json.dumps(record)
    path.write_text('\n'.join(lines))
    assert main(['audit','--input',str(tmp_path)]) == 2
    error = capsys.readouterr().err
    assert 'requested_minutes' in error and 'line 2' in error
