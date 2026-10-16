"""Exercise the runner with a local fake Ark; never contact a model."""
import csv
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

spec = importlib.util.spec_from_file_location("benchmark", Path(__file__).resolve().parents[1] / "run_benchmark.py")
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)

FAKE_ARK = '''
from pathlib import Path
import json
import shutil
import sys
import time

root = Path(__file__).resolve().parent
mode = json.loads((root / 'config/config.json').read_text()).get('test_mode', 'success')
if mode == 'error':
    print('model unavailable', file=sys.stderr)
    raise SystemExit(1)
if mode == 'timeout':
    time.sleep(10)
workspace = root / 'ark-workspace'
shutil.copytree(sys.argv[1], workspace)
if mode != 'missing':
    value = 1 if mode in ('fail', 'test-timeout') else 42
    (workspace / 'src/solution.py').write_text(f'def answer():\\n    return {value}\\n')
else:
    (workspace / 'src/solution.py').unlink()
# A fake passing test must not influence the runner's external evaluation.
(workspace / 'tests/test_solution.py').write_text('def test_solution():\\n    assert True\\n')
(root / 'agent_trace.log').write_text('internal trace')
print('Authorize edit? [y/N]: [1] edit_file')
print('[2] finish')
print('Total tokens: 123')
'''


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(benchmark, "ROOT", tmp_path)
    ark = tmp_path / "ark"
    for directory in ("src/ark", "config"):
        (ark / directory).mkdir(parents=True)
    (ark / "run_ark.py").write_text(FAKE_ARK)
    (ark / "src/ark/agentic_loop.py").write_text("# fake Ark\n")
    (ark / "config/config.json").write_text(json.dumps({"openai_model": "fake", "timeout_seconds": 1}))
    (ark / "config/system_prompt.txt").write_text("Fake agent for local testing")
    task = tmp_path / "humaneval_official_workspaces/he_000"
    (task / "src").mkdir(parents=True)
    (task / "tests").mkdir()
    (task / "prompt.txt").write_text("Implement answer")
    (task / "src/__init__.py").touch()
    (task / "tests/__init__.py").touch()
    (task / "src/solution.py").write_text("def answer():\n    pass\n")
    (task / "tests/test_solution.py").write_text("from src.solution import answer\ndef test_solution():\n    assert answer() == 42\n")
    args = SimpleNamespace(ark_dir=ark, python=Path(sys.executable), run_name="test-run",
                           timeout=5, test_timeout=5, check=False, task=None, limit=None)
    return args, task, tmp_path / "results/test-run"


@pytest.mark.parametrize("mode,status,error", [
    ("success", "PASS", "None"),
    ("fail", "FAIL", "AssertionError"),
    ("error", "ERROR", "ArkExitError"),
    ("missing", "ERROR", "MissingSolution"),
    ("timeout", "TIMEOUT", "ArkTimeout"),
])
def test_execution_and_original_tests(setup, mode, status, error):
    args, task, run_dir = setup
    config = args.ark_dir / "config/config.json"
    config.write_text(json.dumps({"openai_model": "fake", "test_mode": mode}))
    if mode == "timeout":
        args.timeout = 0.1
    run_dir.mkdir(parents=True)
    runtime = benchmark.prepare_snapshot(args, run_dir, benchmark.manifest(args, [task]))
    row = benchmark.run_task(args, task, run_dir, runtime)
    assert row["status"] == status
    assert row["error_type"] == error
    assert (task / "src/solution.py").read_text() == "def answer():\n    pass\n"
    assert (run_dir / "workspaces/he_000/tests/test_solution.py").read_text() == (task / "tests/test_solution.py").read_text()
    assert not (args.ark_dir / "ark-workspace").exists()
    assert not (args.ark_dir / "agent_trace.log").exists()
    if mode == "success":
        assert row["tokens"] == 123
        assert row["turns"] == 2
        assert (run_dir / "traces/he_000.agent.log").read_text() == "internal trace"


def test_external_test_timeout(setup):
    args, task, run_dir = setup
    (task / "tests/test_solution.py").write_text("import time\ndef test_solution():\n    time.sleep(10)\n")
    args.test_timeout = 0.1
    run_dir.mkdir(parents=True)
    runtime = benchmark.prepare_snapshot(args, run_dir, benchmark.manifest(args, [task]))
    row = benchmark.run_task(args, task, run_dir, runtime)
    assert (row["status"], row["error_type"]) == ("TIMEOUT", "TestTimeout")


def test_resume_and_reject_changed_ark(setup, monkeypatch):
    args, task, run_dir = setup
    monkeypatch.setattr(benchmark, "parse_args", lambda argv: args)
    monkeypatch.setattr(benchmark, "preflight", lambda args: [task])
    assert benchmark.main([]) == 0
    with (run_dir / "results.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 1 and rows[0]["status"] == "PASS"
    def unexpected_run(*args):
        pytest.fail("A completed task must not execute again")
    monkeypatch.setattr(benchmark, "run_task", unexpected_run)
    assert benchmark.main([]) == 0
    (args.ark_dir / "config/system_prompt.txt").write_text("Changed prompt")
    assert benchmark.main([]) == 1
    with (run_dir / "results.csv").open() as stream:
        assert len(list(csv.DictReader(stream))) == 1


def test_check_creates_no_results(setup, monkeypatch):
    args, task, run_dir = setup
    args.check = True
    monkeypatch.setattr(benchmark, "parse_args", lambda argv: args)
    assert benchmark.main([]) == 0
    assert not run_dir.parent.exists()


def test_unknown_task_and_missing_key(setup, monkeypatch):
    args, task, _ = setup
    args.task = ["he_999"]
    with pytest.raises(ValueError, match="desconhecidas"):
        benchmark.preflight(args)
    args.task = None
    (args.ark_dir / "config/config.json").write_text(json.dumps({
        "openai_model": "fake", "timeout_seconds": 1, "openai_api_key_env": "ARK_BENCHMARK_TEST_KEY"}))
    monkeypatch.delenv("ARK_BENCHMARK_TEST_KEY", raising=False)
    with pytest.raises(ValueError, match="ARK_BENCHMARK_TEST_KEY"):
        benchmark.preflight(args)


def test_default_selection_includes_all_tasks(setup):
    args, first, _ = setup
    import shutil
    for number in range(1, 164):
        shutil.copytree(first, first.parent / f"he_{number:03d}")
    assert len(benchmark.preflight(args)) == 164
    args.limit = 10
    assert len(benchmark.preflight(args)) == 10


@pytest.mark.parametrize("config", [
    {}, {"openai_model": "fake"},
    {"openai_model": "", "timeout_seconds": 1},
    {"openai_model": "fake", "timeout_seconds": -1},
    {"openai_model": "fake", "timeout_seconds": "bad"},
    {"openai_model": "fake", "timeout_seconds": 1, "openai_api_key_env": 123},
])
def test_invalid_model_config_rejected_before_run(setup, config):
    args, _, _ = setup
    (args.ark_dir / "config/config.json").write_text(json.dumps(config))
    with pytest.raises(ValueError, match="config"):
        benchmark.preflight(args)


def test_empty_system_prompt_rejected_before_run(setup):
    args, _, _ = setup
    (args.ark_dir / "config/system_prompt.txt").write_text(" \n")
    with pytest.raises(ValueError, match="prompt"):
        benchmark.preflight(args)


def test_partial_csv_never_skips_unfinished_task(setup, monkeypatch):
    args, task, run_dir = setup
    run_dir.mkdir(parents=True)
    benchmark.prepare_snapshot(args, run_dir, benchmark.manifest(args, [task]))
    (run_dir / "results.csv").write_text(
        ",".join(benchmark.FIELDS) + "\nhe_000,PASS\n")
    monkeypatch.setattr(benchmark, "parse_args", lambda argv: args)
    monkeypatch.setattr(benchmark, "preflight", lambda args: [task])
    assert benchmark.main([]) == 1


def test_task_change_after_manifest_is_rejected(setup):
    args, task, run_dir = setup
    run_dir.mkdir(parents=True)
    runtime = benchmark.prepare_snapshot(args, run_dir, benchmark.manifest(args, [task]))
    (task / "prompt.txt").write_text("Changed after manifest")
    with pytest.raises(ValueError, match="tarefa"):
        benchmark.run_task(args, task, run_dir, runtime)


def test_old_trace_is_not_reused_on_interrupted_retry(setup):
    args, task, run_dir = setup
    (args.ark_dir / "config/config.json").write_text(json.dumps({"test_mode": "error"}))
    run_dir.mkdir(parents=True)
    runtime = benchmark.prepare_snapshot(args, run_dir, benchmark.manifest(args, [task]))
    trace_dir = run_dir / "traces"
    trace_dir.mkdir()
    (trace_dir / "he_000.agent.log").write_text("previous interrupted attempt")
    (trace_dir / "he_000.pytest.log").write_text("previous interrupted attempt")
    row = benchmark.run_task(args, task, run_dir, runtime)
    assert row["status"] == "ERROR"
    assert not (trace_dir / "he_000.agent.log").exists()
    assert not (trace_dir / "he_000.pytest.log").exists()


def test_atomic_csv_preserves_previous_results_on_write_failure(setup, monkeypatch):
    _, _, run_dir = setup
    run_dir.mkdir(parents=True)
    path = run_dir / "results.csv"
    benchmark.write_results(path, [])
    before = path.read_bytes()
    def fail_replace(*args):
        raise OSError("simulated interrupted publication")
    monkeypatch.setattr(benchmark.os, "replace", fail_replace)
    with pytest.raises(OSError):
        benchmark.write_results(path, [{"task_id": "he_000", "status": "PASS"}])
    assert path.read_bytes() == before
    assert not list(run_dir.glob(".results-*.tmp"))


def test_lock_blocks_concurrent_same_run(setup, monkeypatch):
    args, task, run_dir = setup
    monkeypatch.setattr(benchmark, "parse_args", lambda argv: args)
    monkeypatch.setattr(benchmark, "preflight", lambda args: [task])
    run_dir.mkdir(parents=True)
    with (run_dir / ".lock").open("a") as lock:
        benchmark.fcntl.flock(lock, benchmark.fcntl.LOCK_EX | benchmark.fcntl.LOCK_NB)
        assert benchmark.main([]) == 1
    assert not (run_dir / "manifest.json").exists()


def test_keyboard_interrupt_resumes_only_pending_tasks(setup, monkeypatch):
    import shutil
    args, task, run_dir = setup
    second = task.parent / "he_001"
    shutil.copytree(task, second)
    monkeypatch.setattr(benchmark, "parse_args", lambda argv: args)
    monkeypatch.setattr(benchmark, "preflight", lambda args: [task, second])
    actual = benchmark.run_task
    def interrupted(args, task, run_dir, runtime):
        if task.name == "he_001":
            raise KeyboardInterrupt
        return actual(args, task, run_dir, runtime)
    monkeypatch.setattr(benchmark, "run_task", interrupted)
    assert benchmark.main([]) == 130
    assert [row["task_id"] for row in benchmark.read_results(run_dir / "results.csv", [task, second])] == ["he_000"]
    called = []
    def resumed(args, task, run_dir, runtime):
        called.append(task.name)
        return actual(args, task, run_dir, runtime)
    monkeypatch.setattr(benchmark, "run_task", resumed)
    assert benchmark.main([]) == 0
    assert called == ["he_001"]
    assert len(benchmark.read_results(run_dir / "results.csv", [task, second])) == 2


def test_timeout_kills_child_processes(tmp_path):
    import time
    marker = tmp_path / "orphan.txt"
    child = f"import time; from pathlib import Path; time.sleep(0.6); Path({str(marker)!r}).write_text('orphan')"
    parent = f"import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',{child!r}]); print('child started',flush=True); time.sleep(10)"
    code, stdout, _, timed_out = benchmark.execute([sys.executable, "-c", parent], tmp_path, 0.3)
    assert timed_out and code != 0 and "child started" in stdout
    time.sleep(0.7)
    assert not marker.exists()


@pytest.mark.parametrize("change", ["duplicate", "unknown", "bad_status", "false_pass"])
def test_csv_rejects_inconsistent_rows(setup, change):
    _, task, run_dir = setup
    run_dir.mkdir(parents=True)
    row = dict(zip(benchmark.FIELDS, ["he_000", "PASS", 1, 2, 3, "None", 0, 0]))
    if change == "unknown":
        row["task_id"] = "he_999"
    elif change == "bad_status":
        row["status"] = "OK"
    elif change == "false_pass":
        row["ark_exit_code"] = 1
    rows = [row, row] if change == "duplicate" else [row]
    path = run_dir / "results.csv"
    benchmark.write_results(path, rows)
    with pytest.raises(ValueError, match="CSV"):
        benchmark.read_results(path, [task])


def test_bundled_test_suites_have_no_missing_global_helpers():
    import builtins
    import symtable
    def referenced(table):
        refs = {s.get_name() for s in table.get_symbols() if s.is_global() and s.is_referenced()}
        for child in table.get_children():
            refs.update(referenced(child))
        return refs
    root = Path(__file__).resolve().parents[1] / "humaneval_official_workspaces"
    tasks = sorted(root.glob("he_*"))
    assert [p.name for p in tasks] == [f"he_{i:03d}" for i in range(164)]
    for task in tasks:
        path = task / "tests/test_solution.py"
        table = symtable.symtable(path.read_text(), str(path), "exec")
        defined = {s.get_name() for s in table.get_symbols()
                   if s.is_assigned() or s.is_imported() or s.is_namespace()}
        missing = referenced(table) - defined - set(dir(builtins)) - {"__file__", "__name__"}
        assert not missing, f"{task.name}: imports ausentes: {sorted(missing)}"
