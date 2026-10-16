"""Run the current sibling Ark against the supplied HumanEval workspaces."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent
FIELDS = ["task_id", "status", "time_seconds", "tokens", "turns", "error_type",
          "ark_exit_code", "test_exit_code"]
IGNORE = shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", ".DS_Store", "*.pyc")


def positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("Use um inteiro positivo.")
    return number


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ark-dir", type=Path, default=ROOT.parent / "ark")
    parser.add_argument("--python", type=Path, help="Padrão: <ark-dir>/.venv/bin/python")
    parser.add_argument("--run-name", default=datetime.now(timezone.utc).strftime("run-%Y%m%dT%H%M%S%fZ"),
                        help="Nome da rodada; repita o nome para retomar.")
    parser.add_argument("--task", action="append", help="Ex.: he_000; pode ser repetido.")
    parser.add_argument("--limit", type=positive_int, help="Executar somente as primeiras N tarefas.")
    parser.add_argument("--timeout", type=positive_int, default=1800,
                        help="Limite total do Ark por tarefa em segundos (padrão: 1800).")
    parser.add_argument("--test-timeout", type=positive_int, default=30)
    parser.add_argument("--check", action="store_true", help="Validar ambiente sem chamar a API ou criar resultados.")
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", args.run_name):
        parser.error("--run-name aceita apenas letras, números, hífen e sublinhado.")
    args.ark_dir = args.ark_dir.expanduser().absolute()
    # Keep the venv path: resolving its symlink would bypass the virtual environment.
    args.python = (args.python or args.ark_dir / ".venv/bin/python").expanduser().absolute()
    return args


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ark_files(ark_dir: Path):
    return [ark_dir / "run_ark.py", ark_dir / "config/config.json",
            ark_dir / "config/system_prompt.txt", *sorted((ark_dir / "src").rglob("*.py"))]


def load_config(ark_dir):
    config = json.loads((ark_dir / "config/config.json").read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("config.json deve conter um objeto JSON.")
    model = config.get("openai_model")
    timeout = config.get("timeout_seconds")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("config.json: openai_model deve ser uma string não vazia.")
    if (isinstance(timeout, bool) or not isinstance(timeout, (int, float))
            or not math.isfinite(timeout) or timeout <= 0):
        raise ValueError("config.json: timeout_seconds deve ser um número positivo e finito.")
    for key in ("openai_api_key_env", "openai_base_url"):
        value = config.get(key)
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError(f"config.json: {key} deve ser uma string não vazia ou null.")
    if not (ark_dir / "config/system_prompt.txt").read_text(encoding="utf-8").strip():
        raise ValueError("O prompt de sistema do Ark está vazio.")
    return config


def workspace_hashes(workspace):
    ignored = {".git", "__pycache__", ".pytest_cache"}
    return {str(path.relative_to(workspace)): file_hash(path)
            for path in sorted(workspace.rglob("*")) if path.is_file()
            and not any(part in ignored for part in path.relative_to(workspace).parts)
            and path.name != ".DS_Store" and path.suffix != ".pyc"}


def verify_task(workspace, expected):
    prefix = workspace.name + "/"
    hashes = {key[len(prefix):]: digest for key, digest in expected["task_files_sha256"].items()
              if key.startswith(prefix)}
    if workspace_hashes(workspace) != hashes:
        raise ValueError(f"Os arquivos da tarefa {workspace.name} mudaram após o manifesto; inicie outra rodada.")


def preflight(args):
    for path in ark_files(args.ark_dir):
        if not path.is_file():
            raise ValueError(f"Arquivo do Ark ausente: {path}")
    if not (args.ark_dir / "src/ark/agentic_loop.py").is_file():
        raise ValueError("Diretório do Ark não contém src/ark/agentic_loop.py.")
    probe = subprocess.run(
        [str(args.python), "-c", "import sys,pytest,openai; "
         "assert sys.version_info >= (3,11), 'Python >= 3.11 necessário'; "
         "print(sys.version); print('pytest',pytest.__version__); print('openai',openai.__version__)"],
        capture_output=True, text=True, timeout=30)
    if probe.returncode:
        raise ValueError(f"Ambiente Python inválido:\n{probe.stderr}")
    config = load_config(args.ark_dir)
    key_env = config.get("openai_api_key_env")
    key_present = bool(os.environ.get(key_env or "OPENAI_API_KEY"))
    if key_env and not key_present and not args.check:
        raise ValueError(f"Defina a variável {key_env} antes da execução.")
    available = sorted(p for p in (ROOT / "humaneval_official_workspaces").glob("he_*") if p.is_dir())
    names = {p.name for p in available}
    unknown = set(args.task or []) - names
    if unknown:
        raise ValueError(f"Tarefas desconhecidas: {', '.join(sorted(unknown))}")
    tasks = [p for p in available if not args.task or p.name in args.task]
    if args.limit:
        tasks = tasks[:args.limit]
    if not tasks:
        raise ValueError("Nenhuma tarefa encontrada.")
    for task in tasks:
        for name in ("prompt.txt", "src/solution.py", "tests/test_solution.py"):
                if not (task / name).is_file():
                    raise ValueError(f"Arquivo de tarefa ausente: {task / name}")
        if not (task / "prompt.txt").read_text(encoding="utf-8").strip():
            raise ValueError(f"Prompt da tarefa vazio: {task / 'prompt.txt'}")
    print(f"Ark: {args.ark_dir}\nPython: {args.python}\n{probe.stdout.strip()}", flush=True)
    print(f"Modelo: {config['openai_model']} | Tarefas: {len(tasks)} | "
          f"Chave no ambiente: {'presente' if key_present else 'ausente'}", flush=True)
    return tasks


def execute(command, cwd, timeout, stdin=None):
    """Kill the entire process group on timeout or interruption, including pytest."""
    process = subprocess.Popen(command, cwd=cwd, stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                               env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUNBUFFERED": "1"},
                               start_new_session=True)
    timed_out = False
    try:
        stdout, stderr = process.communicate(stdin, timeout=timeout)
    except (subprocess.TimeoutExpired, KeyboardInterrupt) as exc:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        stdout, stderr = process.communicate()
        if isinstance(exc, KeyboardInterrupt):
            raise
        timed_out = True
    return process.returncode, stdout, stderr, timed_out


def manifest(args, tasks):
    inputs = {str(path.relative_to(args.ark_dir)): file_hash(path) for path in ark_files(args.ark_dir)}
    task_inputs = {f"{task.name}/{relative}": digest for task in tasks
                   for relative, digest in workspace_hashes(task).items()}
    return {"schema_version": 1, "runner_sha256": file_hash(Path(__file__)),
            "ark_dir": str(args.ark_dir), "python": str(args.python),
            "python_environment": subprocess.check_output(
                [str(args.python), "-c", "import sys,pytest,openai; print(sys.version); "
                 "print(pytest.__version__,openai.__version__)"], text=True).strip(),
            "ark_files_sha256": inputs, "task_files_sha256": task_inputs,
            "tasks": [p.name for p in tasks], "timeout": args.timeout,
            "test_timeout": args.test_timeout, "approval": "stdin: yes"}


def prepare_snapshot(args, run_dir, expected):
    metadata = run_dir / "manifest.json"
    if metadata.exists():
        if json.loads(metadata.read_text()) != expected:
            raise ValueError("Ark, tarefas, ambiente ou opções mudaram. Use outro --run-name para uma nova rodada.")
    else:
        if (run_dir / "results.csv").exists():
            raise ValueError("Resultados sem manifest.json; use outro --run-name.")
        metadata.write_text(json.dumps(expected, indent=2, ensure_ascii=False) + "\n")
    runtime = run_dir / "runtime"
    if runtime.exists():
        shutil.rmtree(runtime)
    runtime.mkdir()
    for relative, digest in expected["ark_files_sha256"].items():
        target = runtime / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(args.ark_dir / relative, target)
        if file_hash(target) != digest:
            raise ValueError("Ark mudou durante a preparação; inicie uma nova rodada.")
    return runtime


def run_task(args, task, run_dir, runtime):
    task_id = task.name
    expected = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    verify_task(task, expected)
    trace_dir = run_dir / "traces"
    workspace = run_dir / "workspaces" / task_id
    trace_dir.mkdir(exist_ok=True)
    for suffix in ("console.log", "agent.log", "pytest.log"):
        (trace_dir / f"{task_id}.{suffix}").unlink(missing_ok=True)
    # Never evaluate tests modified by the agent: preserve the original test suite.
    if workspace.exists():
        shutil.rmtree(workspace)
    shutil.copytree(task, workspace, ignore=IGNORE)
    verify_task(workspace, expected)
    agent_workspace = runtime / "ark-workspace"
    if agent_workspace.exists():
        shutil.rmtree(agent_workspace)
    internal_trace = runtime / "agent_trace.log"
    internal_trace.unlink(missing_ok=True)
    start = time.monotonic()
    code, stdout, stderr, timed_out = execute(
        [str(args.python), str(runtime / "run_ark.py"), str(workspace)], runtime,
        args.timeout, "y\n" * 50)
    elapsed = round(time.monotonic() - start, 2)
    (trace_dir / f"{task_id}.console.log").write_text(
        f"=== STDOUT ===\n{stdout}\n=== STDERR ===\n{stderr}", encoding="utf-8")
    if internal_trace.exists():
        shutil.copy2(internal_trace, trace_dir / f"{task_id}.agent.log")
    generated_src = agent_workspace / "src"
    has_solution = (generated_src / "solution.py").is_file()
    if has_solution:
        shutil.rmtree(workspace / "src")
        shutil.copytree(generated_src, workspace / "src", ignore=IGNORE)
    test_code = None
    if timed_out:
        status, error = "TIMEOUT", "ArkTimeout"
    elif code != 0:
        status, error = "ERROR", "ArkExitError"
    elif not has_solution:
        status, error = "ERROR", "MissingSolution"
    else:
        test_code, test_out, test_err, test_timeout = execute(
            [str(args.python), "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_solution.py"],
            workspace, args.test_timeout)
        (trace_dir / f"{task_id}.pytest.log").write_text(test_out + test_err, encoding="utf-8")
        if test_timeout:
            status, error = "TIMEOUT", "TestTimeout"
        elif test_code == 0:
            status, error = "PASS", "None"
        else:
            status = "FAIL"
            error = next((name for name in ("AssertionError", "NameError", "SyntaxError", "ImportError", "TypeError")
                          if name in test_out + test_err), "PytestError")
    match = re.search(r"^Total tokens:\s*(\d+)\s*$", stdout, re.MULTILINE)
    return dict(zip(FIELDS, [task_id, status, elapsed, int(match[1]) if match else "",
                            len(re.findall(r"^(?:Authorize edit\? \[y/N\]: )?\[\d+\] ",
                                           stdout, re.MULTILINE)), error, code, test_code]))


def read_results(path, tasks):
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != FIELDS:
            raise ValueError("CSV inválido: cabeçalho inesperado.")
        rows = list(reader)
    seen = set()
    selected = {task.name for task in tasks}
    for row in rows:
        try:
            if (set(row) != set(FIELDS) or any(value is None for value in row.values())
                    or row["task_id"] not in selected or row["task_id"] in seen
                    or row["status"] not in {"PASS", "FAIL", "ERROR", "TIMEOUT"}):
                raise ValueError
            elapsed = float(row["time_seconds"])
            if not math.isfinite(elapsed) or elapsed < 0 or int(row["turns"]) < 0:
                raise ValueError
            if row["tokens"] and int(row["tokens"]) < 0:
                raise ValueError
            int(row["ark_exit_code"])
            if row["test_exit_code"]:
                int(row["test_exit_code"])
            if row["status"] == "PASS" and (row["ark_exit_code"] != "0" or row["test_exit_code"] != "0"):
                raise ValueError
        except (ValueError, TypeError):
            raise ValueError("CSV inválido: registro incompleto, duplicado ou inconsistente; "
                             "verifique o arquivo antes de retomar.") from None
        seen.add(row["task_id"])
    return rows


def write_results(path, rows):
    """Publish a complete CSV atomically, so an interrupted write cannot skip a task."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, prefix=".results-", suffix=".tmp",
                                         newline="", encoding="utf-8", delete=False) as stream:
            temporary = Path(stream.name)
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv=None):
    args = parse_args(argv)
    try:
        tasks = preflight(args)
        if args.check:
            print("Verificação local concluída; API não consultada e nenhum resultado criado.")
            return 0
        expected = manifest(args, tasks)
        run_dir = ROOT / "results" / args.run_name
        run_dir.mkdir(parents=True, exist_ok=True)
        with (run_dir / ".lock").open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ValueError("Esta rodada já está em execução em outro processo.") from None
            csv_path = run_dir / "results.csv"
            rows = read_results(csv_path, tasks)
            runtime = prepare_snapshot(args, run_dir, expected)
            completed = {row["task_id"] for row in rows}
            print(f"Rodada: {args.run_name}\nResultados: {run_dir}\nJá registradas: {len(completed)}", flush=True)
            if not csv_path.exists():
                write_results(csv_path, rows)
            for index, task in enumerate(tasks, 1):
                if task.name in completed:
                    continue
                print(f"[{index}/{len(tasks)}] {task.name}...", flush=True)
                row = run_task(args, task, run_dir, runtime)
                rows.append(row)
                write_results(csv_path, rows)
                print(f"  {row['status']} | {row['time_seconds']}s | {row['error_type']}", flush=True)
            passed = sum(row["status"] == "PASS" for row in rows)
            print(f"Rodada concluída: {passed}/{len(rows)} PASS ({passed / len(rows):.1%}).", flush=True)
            return 0
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrompido. Retome com o mesmo --run-name e as mesmas opções.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
