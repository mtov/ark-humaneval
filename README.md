# HumanEval with the Current Ark

Run the 164 tasks included in this project using the Ark code and configuration
in `../ark`. Requires macOS or Linux and Python 3.11 or later.
The runner targets the Ark layout described below; compatibility with future Ark
changes must be checked before a new run.

There are two stages:

1. **Generate solutions:** `run_benchmark.py` calls Ark and evaluates its output
   with the visible tests. This stage makes model requests.
2. **Evaluate saved solutions:** `evaluate_solutions.py` runs visible and hidden
   tests offline, without model requests or repairs.

## Task Prompt Format

Each `prompt.txt` contains a single instruction naming the target function and
its source file. For example, `he_032/prompt.txt` contains:

```text
Implement find_zero in src/solution.py according to its docstring.
```

The prompt does not repeat the source code, specification, examples, or test
instructions. Ark reads the function and its specification from `src/solution.py`.
Changing the prompt format did not change source files, helper functions,
specification text, or tests.
In `he_115`, the existing specification string follows a local import, so Python
does not expose it as `__doc__`; the text remains available in the function body.

The previous evaluations in `results/piloto-real/` and `results/avaliacao-01/`
used prompts that included source code. Their artifacts and manifests are
preserved. **Use a new run name for the generic prompts**: the old runs cannot
be resumed with changed task files. The completed generic-prompt evaluation is
preserved in
`results/generic-prompts-01/`. The generation examples below use `benchmark-pilot-01`
and `benchmark-01` for new runs. If either name already exists locally, choose
an unused name and use it consistently.

## How to Run the Benchmark

Run the following commands in a terminal from this project's root directory.
The project expects this directory layout:

```text
ark-project/
├── ark/              # Your current Ark checkout, including config/ and .venv/
└── human-eval-all/    # This project
```

### 1. Open the Project Directory

Use your local checkout path. On this machine:

```bash
cd /Users/mtov/ark-project/human-eval-all
```

The runner automatically uses `../ark/.venv/bin/python`. You do not need to
activate the virtual environment or install a second copy of Ark in this project.
If Ark's environment does not exist yet, follow [Environment Setup](#environment-setup).

### 2. Set the API Key in Your Terminal

The supplied Ark configuration reads the key from `OPENAI_API_KEY`:

```bash
export OPENAI_API_KEY="your-api-key"
```

Replace `your-api-key` with your actual key. This setting applies to the current
terminal and its child processes. Set it again if you open another terminal to
start the benchmark.

The model and endpoint are defined in `../ark/config/config.json`.
If `openai_api_key_env` names a different variable, export that variable instead.
The system prompt comes from `../ark/config/system_prompt.txt`. The runner copies
this configuration at the start of each run, so make any changes before starting.

### 3. Check the Environment

```bash
../ark/.venv/bin/python run_benchmark.py --check
```

The output should identify your Ark checkout, Python, the configured model,
**164 tasks**, and the key as **present** (`presente`). This command does not call
the API or create results. It validates local files and configuration, but does
not verify whether the key is valid or whether the API provides access to the model.

### 4. Run One Task as a Pilot

```bash
../ark/.venv/bin/python run_benchmark.py --run-name benchmark-pilot-01 --task he_000
```

This command makes real model requests. Wait for the task to finish.
A successful pilot reports `PASS` and a `1/1 PASS` summary.
Results are saved in `results/benchmark-pilot-01/`.

If the task reports `ERROR`, `FAIL`, or `TIMEOUT`, inspect the CSV and the files in
`results/benchmark-pilot-01/traces/` before starting the full run. To repeat the pilot
after a failure has been recorded, choose another name, such as `benchmark-pilot-02`.

### 5. Run All 164 Tasks

```bash
../ark/.venv/bin/python run_benchmark.py --run-name benchmark-01
```

**This command runs the full benchmark.** Without `--task` or `--limit`, it
selects all 164 tasks and runs them sequentially, from `he_000` to `he_163`.
You do not need to respond to edit confirmations: the runner supplies `y`
automatically. `ARK_AUTO_APPROVE` is not required.

The terminal shows each task as it starts and its result when it finishes.
Detailed logs are saved after the task runs; they are not streamed live.
At the end, the terminal reports the number and proportion of tasks with `PASS`.

The full run uses `results/benchmark-01/`, separate from the pilot. To inspect
the CSV in another terminal, open this project's root directory and run:

```bash
cat results/benchmark-01/results.csv
```

Each task's final code is saved in `results/benchmark-01/workspaces/`, and its
logs are saved in `results/benchmark-01/traces/`.

### 6. Stop or Resume a Run

To stop, press **Ctrl+C** in the terminal running the benchmark. To resume,
set the API key in your terminal and repeat **the same command with the same options**:

```bash
../ark/.venv/bin/python run_benchmark.py --run-name benchmark-01
```

Tasks already recorded in the CSV, including failures and timeouts, are skipped.
A task interrupted by Ctrl+C remains pending and will run again.

To start a new evaluation from scratch, choose another name:

```bash
../ark/.venv/bin/python run_benchmark.py --run-name benchmark-02
```

Keep Ark, the tasks, and the options unchanged when resuming a run.
If you change Ark's code or configuration, the runner, the tasks, the environment,
or the time limits, use a new run name.

## Environment Setup

**If `--check` succeeds and the required key is present, skip environment setup.**
If the virtual environment does not exist yet, create it using Python 3.11 or
later from this project's root directory. If it already exists but lacks the
required packages, run only the `pip install` command:

```bash
python3 -m venv ../ark/.venv
../ark/.venv/bin/python -m pip install -r ../ark/requirements.txt
```

Ark must provide `run_ark.py`, `src/ark/agentic_loop.py`,
`config/config.json`, and `config/system_prompt.txt`. Installing the requirements
does not create these files; use your existing Ark checkout.

The tasks are already included. You do not need to generate the workspaces or
install the `human_eval` package.

## Other Run Options

```bash
# Run only the first ten tasks
../ark/.venv/bin/python run_benchmark.py --run-name piloto-10 --limit 10

# Select specific tasks
../ark/.venv/bin/python run_benchmark.py --run-name selecao --task he_000 --task he_065

# Increase the time limits for a new run
../ark/.venv/bin/python run_benchmark.py --run-name avaliacao-longa --timeout 3600 --test-timeout 60

# Check another checkout or Python environment
python3 run_benchmark.py --ark-dir /path/to/ark --python /path/to/venv/bin/python --check

# Show all options
../ark/.venv/bin/python run_benchmark.py --help
```

| Option | Purpose | Default |
| --- | --- | --- |
| `--run-name` | Run name; reuse it to resume | Unique name with a UTC timestamp |
| `--task` | Select one task; can be repeated | All tasks |
| `--limit` | Select only the first N tasks | No limit |
| `--timeout` | Total time limit for the Ark process per task, in seconds | 1800 |
| `--test-timeout` | Time limit for external evaluation per task, in seconds | 30 |
| `--ark-dir` | Directory containing Ark's code and configuration | `../ark` |
| `--python` | Python executable for Ark and evaluation | `<ark-dir>/.venv/bin/python` |
| `--check` | Check the environment without calling the API | Disabled |

The timeout for each model request remains the one configured in Ark.
`--timeout` limits **the entire Ark run for a task**, including requests and
internal tests. A timeout or Ctrl+C also terminates the task's child processes.

## Troubleshooting

| Situation | What to do |
| --- | --- |
| `Defina a variável OPENAI_API_KEY` (set the OPENAI_API_KEY variable) | Run `export` in the same terminal that will start the benchmark. |
| Missing Python executable or invalid environment | Follow the environment setup instructions or specify `--python`. |
| Pilot reports `ERROR` | Read the `.console.log` and `.agent.log` files, when available; check Ark's configuration and model access. |
| Task reports `FAIL` | Read the `.pytest.log` file; the solution failed external evaluation. |
| Task reports `TIMEOUT` | Check `error_type` in the CSV to distinguish an Ark timeout from a test timeout. |
| Message saying Ark, tasks, environment, or options have changed | Use a different `--run-name` to start a run with the current inputs. |
| Run is already active | Wait for or stop the process using that name; use another name for an independent run. |

## Isolation and Results

Each run receives a copy of the current Ark Python code and its two configuration
files. This copy runs in `results/<run-name>/runtime/`, allowing the runner to use
the current version without overwriting `../ark/ark-workspace` or
`../ark/agent_trace.log`. Each new run captures the contents of `../ark` again.

```text
.
├── run_benchmark.py
├── humaneval_official_workspaces/   # 164 supplied tasks
├── tests/test_benchmark.py          # Local runner tests; no API requests
└── results/<run-name>/              # Generated during execution
    ├── manifest.json
    ├── results.csv
    ├── traces/
    │   ├── he_000.console.log       # Ark stdout and stderr
    │   ├── he_000.agent.log         # Internal trace, when produced
    │   └── he_000.pytest.log        # External evaluation, when performed
    ├── workspaces/he_000/           # Final code with the original tests
    └── runtime/                    # Executable copy of Ark
```

The manifest records paths, Python/Pytest/OpenAI client versions, options, and
hashes of the runner, Ark code and configuration, and selected task files.
If these inputs change, resuming is rejected: choose another run name to avoid
mixing versions. The runner does not intentionally write the environment
variable holding the API key. Ark's configuration and traces are copied in full; inspect the files
before publishing them, since their contents depend on Ark and your configuration.

The CSV is saved after each task and contains:

| Field | Contents |
| --- | --- |
| `task_id` | Identifier from `he_000` to `he_163` |
| `status` | `PASS`, `FAIL`, `ERROR`, or `TIMEOUT` |
| `time_seconds` | Ark process duration, excluding external evaluation |
| `tokens` | Total reported by Ark; empty if unavailable |
| `turns` | Numbered actions printed to the console |
| `error_type` | Error category, if any |
| `ark_exit_code` | Ark process exit code |
| `test_exit_code` | External evaluation exit code, when performed |

Each save replaces the entire CSV atomically. Before resuming, the runner
validates the header and every record. Incomplete, duplicate, or inconsistent
rows stop execution with a message rather than silently skipping tasks.

`PASS` requires both a zero exit code from Ark and successful external evaluation.
Ark execution errors receive `ERROR`; solutions that fail evaluation receive
`FAIL`. The command returns zero when the run finishes, even if some tasks fail;
check the summary and CSV. Runner errors return 1; Ctrl+C returns 130.

External evaluation uses a copy of the **original tests** and the `src/` directory
produced by the agent. Agent changes to the tests do not enter this evaluation.
Input files are checked against the manifest hashes before each task and after
copying. Ark receives this verified copy. Execution does not modify the supplied
tasks. Tests remain visible to the agent while solving the task; this is not an
evaluation with hidden tests.

The supplied task packaging had incomplete imports in the tests for `he_032`,
`he_038`, and `he_050`. Imports for the helper functions `poly`, `encode_cyclic`,
and `encode_shift` were added, respectively. The assertions were preserved.

To manually check a saved solution, start from the project root:

```bash
(
  cd results/benchmark-01/workspaces/he_000
  ../../../../../ark/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_solution.py
)
```

The subshell keeps your terminal in the project root for subsequent commands.

## Hidden-Test Evaluation

The generation runner's `results.csv` reports **visible-test results only**.
Use the offline evaluator to check whether saved solutions also pass additional
tests that were not supplied to Ark. It does not call a model, change the saved
solutions, or let Ark repair a failing solution.

The suite covers all **164 tasks with 121,129 additional cases**, using pinned
HumanEval+ inputs and reference implementations, plus targeted edge cases.
See [evaluation/README.md](evaluation/README.md) for sources, licenses, excluded
cases, numerical tolerances, ambiguous specifications, and isolation limits.
This is a local derivative, not an official HumanEval+ score.

The committed reports record **164/164 visible passes** and **161/164 combined
passes (98.17%)** for `generic-prompts-01`. The hidden failures are `he_076`,
`he_109`, and `he_145`. Of the 121,129 available cases, 118,481 were checked
against these solutions because checking stops at the first failure per task.

To read the existing report without executing tests:

```bash
cat evaluation_results/generic-prompts-01/summary.json
```

To perform a fresh evaluation, use unused output directories. From the project
root, first validate the references through both suites:

```bash
../ark/.venv/bin/python evaluate_solutions.py --validate-references \
  --output evaluation_results/reference-review-01
cat evaluation_results/reference-review-01/summary.json
```

Check that the summary contains `"tasks": 164` and `"overall": {"PASS": 164}`.
A zero exit code alone does not establish that the references passed. Then
evaluate the saved generic-prompt run, without generating new solutions:

```bash
../ark/.venv/bin/python evaluate_solutions.py --run results/generic-prompts-01 \
  --output evaluation_results/generic-prompts-review-01
cat evaluation_results/generic-prompts-review-01/summary.json
```

The completed reevaluation and its reviewed failure cases are summarized in
[HIDDEN_EVALUATION_REPORT.md](HIDDEN_EVALUATION_REPORT.md).

For a future benchmark run, run the generation command first and invoke this
evaluator only after generation has finished. For example, after completing
`benchmark-01`:

```bash
../ark/.venv/bin/python evaluate_solutions.py --run results/benchmark-01
```

No API key is needed for offline evaluation. It uses Python and Pytest; an
alternative environment can be selected with `--python /path/to/venv/bin/python`.
Hidden assets are kept under the separate project-level `evaluation/` directory;
they are never copied into the task or Ark runtime workspaces.

Without `--output`, reports default to `evaluation_results/<source-run-name>/`,
or `evaluation_results/reference-validation/` for reference validation. Reusing
a completed output with identical inputs skips its recorded tasks, including
failures; it does not execute the tests again. Reports are saved separately from
the original benchmark artifacts. The committed report has this layout:

```text
evaluation_results/generic-prompts-01/
├── manifest.json             # Suite, evaluator, environment and solution hashes
├── results.csv               # Separate visible, hidden and combined status
├── summary.json
└── traces/
    ├── he_145.visible.log
    ├── he_145.hidden.log
    └── he_145.hidden.json     # First failing input, expected result and actual result
```

The CSV distinguishes `visible_status`, `hidden_status`, and `overall_status`,
with separate times, exit codes, case counts, and error types. A combined `PASS`
requires both suites to pass. Hidden checking stops at the first failure for
each task, so `hidden_cases_checked` may be less than `hidden_cases_total`.
The command returns zero when evaluation finishes, including runs with failed
solutions: inspect the summary rather than treating the exit code as a pass rate.

Each visible/hidden worker has a 60-second limit; each hidden call and comparison
has a 2-second limit. Set `--timeout` or `--case-timeout` to change them, using a
new output directory. `TIMEOUT` is recorded separately from functional failures.
Repeat the exact command to resume an interrupted evaluation. Changes to code,
cases, environment, source files, task selection, or limits require a new output:

```bash
../ark/.venv/bin/python evaluate_solutions.py --run results/generic-prompts-01 \
  --output evaluation_results/he145-review --task he_145
```

The committed suite is ready to use; rebuilding is optional. Running
`../ark/.venv/bin/python build_hidden_suite.py` overwrites the suite and its
manifest. Construction time limits can change the retained cases on another
machine. Preserve the current suite and reports if you need their exact version,
and validate any rebuilt suite in a fresh output directory before scoring solutions.

The additional inputs come from public data and targeted checks informed by the
audit. A preliminary evaluation also exposed reference defects; the final suite
applies the documented specification filters and was fully reevaluated. This was
not a blind held-out evaluation. Hidden files are excluded from Ark's supplied
workspaces and prompts, but filesystem access is not sandboxed. Coverage varies
by task; `he_039` has only one additional case. Passing the suite provides
evidence of generalization, not a guarantee of correctness for every valid input.

## Local Tests

```bash
../ark/.venv/bin/python -m pytest -q -p no:cacheprovider tests
```

The runner tests use a simulated agent; the evaluator tests check suite integrity,
comparison rules, timeouts, and saved-solution evaluation. They make no model or
network requests.
The detailed review report is available in [VERIFICACAO.md](VERIFICACAO.md) (in Portuguese).

## Uploading Results to GitHub

The `.gitignore` allows tracking each run's artifacts: `results.csv`,
`manifest.json`, `traces/`, and `workspaces/`. Runtime copies in `runtime/`,
lock files, and caches remain excluded.
Offline reports under `evaluation_results/` are also included, except locks and
temporary files. The `evaluation/` directory contains the reproducible suite.

When creating the repository, `git add .` already includes these results.
To upload new evaluations after the repository has been created and connected
to GitHub, run the following from the project root:

```bash
git add .gitignore results/
git status
git commit -m "chore(results): add Ark evaluation results"
git push
```

To include the hidden suite and its reports in a commit:

```bash
git add build_hidden_suite.py evaluate_solutions.py evaluation/ evaluation_results/ tests/ README.md HIDDEN_EVALUATION_REPORT.md .gitignore
git status
git commit -m "feat(eval): add hidden tests and offline solution evaluation"
git push
```

## Cleanup Performed

The duplicate `ark_latest/` code, the Linux `venv_ark_latest/` environment,
obsolete results, traces, workspaces, and ZIP archives were removed during the
initial migration. The historical runs currently under `results/` are retained.
The old runner was replaced with `run_benchmark.py`. The task generator was also
removed: all 164 tasks are already included, and running them does not require
the `human_eval` package. Internal task Git repositories and unnecessary caches
were removed. All 164 tasks remain; prompts were subsequently simplified as
described above, and the three test-helper import fixes are documented under
[Isolation and Results](#isolation-and-results).
