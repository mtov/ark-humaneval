# HumanEval with the Current Ark

Run the 164 tasks included in this project using the Ark code and configuration
in `../ark`. Supports macOS and Linux with Python 3.11 or later.

## Task Prompt Format

Each `prompt.txt` contains a single instruction naming the target function and
its source file. For example, `he_032/prompt.txt` contains:

```text
Implement find_zero in src/solution.py according to its docstring.
```

The prompt does not repeat the source code, specification, examples, or test
instructions. Ark reads the function and its specification from `src/solution.py`.
Source files, helper functions, specification text, and tests are unchanged.
In `he_115`, the existing specification string follows a local import, so Python
does not expose it as `__doc__`; the text remains available in the function body.

The previous evaluations in `results/piloto-real/` and `results/avaliacao-01/`
used prompts that included source code. Their artifacts and manifests are
preserved. **Use a new run name for the generic prompts**: the old runs cannot
be resumed with changed task files. The examples below use
`generic-prompts-pilot` and `generic-prompts-01` to keep the new evaluations
separate from the previous results.

## How to Run the Benchmark

Run the following commands in a terminal from this project's root directory.
The project expects this directory layout:

```text
ark-project/
├── ark/              # Your current Ark checkout, including config/ and .venv/
└── human-eval-all/    # This project
```

### 1. Open the Project Directory

On this machine:

```bash
cd /Users/mtov/ark-project/human-eval-all
```

The runner automatically uses `../ark/.venv/bin/python`. You do not need to
activate the virtual environment or install a second copy of Ark in this project.
If Ark's environment does not exist yet, follow [Environment Setup](#environment-setup).

### 2. Set the API Key in Your Terminal

The current configuration reads the key from `OPENAI_API_KEY`:

```bash
export OPENAI_API_KEY="your-api-key"
```

Replace `your-api-key` with your actual key. This setting applies to the current
terminal and its child processes. Set it again if you open another terminal to
start the benchmark.

The model and endpoint are defined in `../ark/config/config.json`.
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
../ark/.venv/bin/python run_benchmark.py --run-name generic-prompts-pilot --task he_000
```

This command makes real model requests. Wait for the task to finish.
A successful pilot reports `PASS` and a `1/1 PASS` summary.
Results are saved in `results/generic-prompts-pilot/`.

If the task reports `ERROR`, `FAIL`, or `TIMEOUT`, inspect the CSV and the files in
`results/generic-prompts-pilot/traces/` before starting the full run. To repeat the pilot
after a failure has been recorded, choose another name, such as `generic-prompts-pilot-02`.

### 5. Run All 164 Tasks

```bash
../ark/.venv/bin/python run_benchmark.py --run-name generic-prompts-01
```

**This command runs the full benchmark.** Without `--task` or `--limit`, it
selects all 164 tasks and runs them sequentially, from `he_000` to `he_163`.
You do not need to respond to edit confirmations: the runner supplies `y`
automatically. `ARK_AUTO_APPROVE` is not required.

The terminal shows each task as it starts and its result when it finishes.
Detailed logs are saved after the task runs; they are not streamed live.
At the end, the terminal reports the number and proportion of tasks with `PASS`.

The full run uses `results/generic-prompts-01/`, separate from the pilot. To inspect
the CSV in another terminal, open this project's root directory and run:

```bash
cat results/generic-prompts-01/results.csv
```

Each task's final code is saved in `results/generic-prompts-01/workspaces/`, and its
logs are saved in `results/generic-prompts-01/traces/`.

### 6. Stop or Resume a Run

To stop, press **Ctrl+C** in the terminal running the benchmark. To resume,
set the API key in your terminal and repeat **the same command with the same options**:

```bash
../ark/.venv/bin/python run_benchmark.py --run-name generic-prompts-01
```

Tasks already recorded in the CSV, including failures and timeouts, are skipped.
A task interrupted by Ctrl+C remains pending and will run again.

To start a new evaluation from scratch, choose another name:

```bash
../ark/.venv/bin/python run_benchmark.py --run-name generic-prompts-02
```

Keep Ark, the tasks, and the options unchanged when resuming a run.
If you change Ark's code or configuration, the runner, the tasks, the environment,
or the time limits, use a new run name.

## Environment Setup

**If `../ark/.venv/bin/python` already works, you do not need to recreate the environment.**
If it does not exist yet, create it using Python 3.11 or later from this project's
root directory:

```bash
python3 -m venv ../ark/.venv
../ark/.venv/bin/python -m pip install -r ../ark/requirements.txt
```

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
mixing versions. The runner does not record the API key. Ark's configuration and
traces are copied in full and may contain endpoint information.

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
cd results/generic-prompts-01/workspaces/he_000
../../../../../ark/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_solution.py
```

## Runner Tests

```bash
../ark/.venv/bin/python -m pytest -q -p no:cacheprovider tests
```

These tests use a simulated agent without making model requests.
The detailed review report is available in [VERIFICACAO.md](VERIFICACAO.md) (in Portuguese).

## Uploading Results to GitHub

The `.gitignore` allows tracking each run's artifacts: `results.csv`,
`manifest.json`, `traces/`, and `workspaces/`. Runtime copies in `runtime/`,
lock files, and caches remain excluded.

When creating the repository, `git add .` already includes these results.
To upload new evaluations after the repository has been created and connected
to GitHub, run the following from the project root:

```bash
git add .gitignore results/
git status
git commit -m "Add Ark evaluation results"
git push
```

## Cleanup Performed

The duplicate `ark_latest/` code, the Linux `venv_ark_latest/` environment,
previous results, traces, workspaces, and their ZIP archives were removed.
The old runner was replaced with `run_benchmark.py`. The task generator was also
removed: all 164 tasks are already included, and running them does not require
the `human_eval` package. Internal task Git repositories and unnecessary caches
were removed; prompts, source files, and tests were preserved.
