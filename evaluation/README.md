# Hidden evaluation suite

This directory is used only by the offline evaluator. It is outside all task
workspaces and is never passed to Ark. The visible tests remain unchanged.

## Scope and provenance

The suite covers all 164 tasks with **121,129 additional cases**. It uses the
`plus_input` cases from **HumanEval+ v0.1.10**, together with targeted new cases
for cyclic sorting, bracket nesting, and signed digit-sum sorting. It is a local,
conservative derivative, **not an official HumanEval+ score**.

Sources:

- [EvalPlus](https://github.com/evalplus/evalplus), source revision
  `26d6d00bb1fd0fa37f39c99d5290da67891d1c5e`.
- [HumanEval+ v0.1.10 data](https://github.com/evalplus/humanevalplus_release/releases/download/v0.1.10/HumanEvalPlus.jsonl.gz).
- [Original HumanEval data](https://github.com/openai/human-eval/blob/master/data/HumanEval.jsonl.gz).

The compressed upstream archives are vendored in `vendor/`, with their license
texts. HumanEval is MIT-licensed; EvalPlus is Apache-2.0-licensed. The corrected
reference implementations are derived from these projects. See
`vendor/HumanEval-LICENSE` and `vendor/EvalPlus-LICENSE` for the full terms.
The manifest pins both downloaded archives by SHA-256, including the content
of the original HumanEval archive fetched from its upstream `master` branch.

## How cases were selected and checked

1. Match every target function and specification to the supplied task.
2. Remove exact duplicates, upstream base inputs, and literal `candidate(...)`
   inputs identifiable in the visible tests. Original randomly generated tests
   may cover overlapping values; complete disjointness cannot be guaranteed.
3. Validate new inputs against the upstream task contracts.
4. Compute expected results from the corrected upstream reference, independently
   of Ark's generated code. Cross-check with the original OpenAI reference.
   The two upstream versions share ancestry; their agreement is useful but is
   not a proof of correctness.
5. Exclude cases on reference disagreement, exception, non-finite output, or
   timeout. Exclusion counts and sample reasons are recorded for every task in
   `manifest.json`. Targeted cases were informed by the earlier audit. A preliminary
   candidate evaluation also exposed shared reference defects in `he_091` and
   `he_141`; specification filters were then applied to all cases in those tasks.
   Expected outputs were never taken from Ark's solutions. See the
   [oracle review](../HIDDEN_EVALUATION_REPORT.md#oracle-review) for the sequence
   of corrections. This is not a blind held-out evaluation.
6. Check the reference implementations against the existing visible tests.
7. Run the references through the actual hidden evaluator, including encoding,
   copying, time limits, and comparison rules. All 164 references pass both suites.

Inputs and order use a fixed seed, `20261016`. The committed suite and its hashes
are the reproducible evaluation artifact. Rebuilding can exclude different cases
if reference computations exceed the construction time budget on another machine;
that produces a different manifest and requires a new evaluation output directory.
The old recursive Fibonacci/FibFib references are memoized without changing their
recurrences. Randomized reference code is seeded during construction.

Large exact outputs may be stored as SHA-256 digests with a preview. Full outputs
are retained for floating-point comparisons, so numerical tolerances are preserved.

## Interpretation decisions

| Task or issue | Evaluation rule |
| --- | --- |
| `he_020`: multiple equally close pairs | Accept any valid closest pair drawn from two input positions; do not demand the particular pair chosen by the reference. |
| `he_032`: multiple polynomial roots | Accept any finite real result whose polynomial residual is at most `1e-4`; roots are not compared for equality. |
| Floating-point outputs | Relative tolerance `1e-7`; absolute tolerance from HumanEval+, or `1e-6` if not specified. Container types are preserved. |
| `he_099`: decimal rounding | Exclude 15 cases where binary floating-point conversion disagrees with exact decimal rounding. Do not penalize exact decimal implementations. |
| `he_091`: a sentence containing only `I` | Exclude one case where both references contradict the rule that a sentence starting with the word `I` is counted. |
| `he_141`: ASCII filename rules | Exclude four cases where both references contradict the explicit `a-z`/`A-Z` and `0-9` requirements. Unicode classification must not create a false failure. |
| `he_116`: contradictory negative-number example | Additional inputs follow the upstream contract of non-negative integers. Existing visible tests remain unchanged. |
| `he_132`: ambiguous bracket wording | Keep only cases where the original and corrected references agree. Disputed cases are excluded rather than used to lower a score. |
| `he_039`: small valid domain | The original visible inputs cover 1–10. The suite retains one independently cross-checked new input; a slow/disputed reference calculation is excluded. Coverage is intentionally limited here. |

These decisions and the exclusion policy make this a conservative test suite.
Passing it provides additional evidence, not a guarantee of general correctness.

## Layout

```text
evaluation/
├── manifest.json          # Counts, exclusions, provenance and file hashes
├── hidden/he_000.json.gz  # Inputs and precomputed expected results (164 files)
├── references/he_000.py   # Independent reference code (164 files)
├── hidden_worker.py       # Separate-process checker
├── support.py             # Serialization and correctness predicates
└── vendor/                # Pinned upstream data and licenses
```

The committed suite is ready to use. Rebuilding overwrites its cases, references,
and manifest; preserve the current version first if needed. Rebuild offline,
from the project root, using an environment with Pytest:

```bash
../ark/.venv/bin/python build_hidden_suite.py
```

Then validate the references:

```bash
../ark/.venv/bin/python evaluate_solutions.py --validate-references \
  --output evaluation_results/reference-validation-v2
```

Use an unused output name for a fresh validation; a completed output with
identical inputs skips recorded tasks. Verify `overall: {"PASS": 164}` in the
summary before interpreting candidate scores. If the suite or evaluator changes,
preserve the old report and choose a fresh `--output` again.

## Isolation boundary

Neither hidden cases nor reference code are copied into task workspaces,
`results/<run>/runtime/`, or model prompts. Only after generation has finished does
`evaluate_solutions.py` run the visible and hidden suites in separate processes
against temporary copies of the saved source code. It checks source hashes before
and after evaluation. It never calls Ark or requests a correction.

"Hidden" means **not supplied to the agent during this experiment**. HumanEval+
is public data, and these files can also be committed to the repository. This is
not an operating-system sandbox: arbitrary Python code with filesystem access
could try to inspect evaluator files. Adversarial secrecy would require a
separate host/container with restricted mounts and credentials. The current
workflow tests ordinary generated solutions, not hostile code.
