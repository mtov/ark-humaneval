# Hidden evaluation of the generic-prompt run

Evaluated on October 16, 2026, without generating new solutions or calling a model.
Source run: `results/generic-prompts-01` (`gpt-6-luna`).

## Results

| Measurement | Result |
| --- | --- |
| Tasks evaluated | 164 |
| Visible tests | 164 PASS, 0 FAIL |
| Additional hidden tests | 161 PASS, 3 FAIL |
| Combined task approval | **161/164 — 98.17%** |
| Hidden cases available | 121,129 |
| Hidden cases actually checked | 118,481 |
| Candidate timeouts / evaluator errors | 0 / 0 |
| Independent reference validation | 164/164 PASS on visible and hidden suites |
| Local regression tests | 43 PASS |

The evaluator stops at the first hidden failure for each task, which explains
why fewer than 121,129 cases were executed against the candidate solutions.
Task-level approval requires all selected hidden cases to pass; this is not a
claim that every remaining solution is universally correct.

## Confirmed failures

| Task | Function | New input | Expected | Actual |
| --- | --- | --- | --- | --- |
| `he_076` | `is_simple_power` | `(16, -2)` | `True` | `False` |
| `he_109` | `move_one_ball` | `[2, 1, 3]` | `False` | `True` |
| `he_145` | `order_by_points` | `[1, -1]` | `[-1, 1]` | `[1, -1]` |

- **he_076:** the implementation rejects negative bases, but `(-2)**4 == 16`.
  The specification and upstream input contract do not restrict the base to positive values.
- **he_109:** counting internal descents is insufficient for cyclic sorting;
  none of the rotations of `[2, 1, 3]` are sorted.
- **he_145:** the implementation memorized three visible input/output pairs and
  uses an incorrect general rule for signed digit sums. The new pair exposes it.

The latter two failures were detected by small targeted cases. The first was
found among the additional upstream inputs. These are correctness findings;
only `he_145` has confirmed explicit memorization of whole visible inputs.

## Oracle review

A preliminary check identified apparent failures in `he_091` and `he_141` that
were actually upstream oracle defects: the standalone sentence `I` and an
accented filename initial, respectively. Both original and corrected upstream
references share these defects. The final suite excludes all cases violating
the corresponding independently checked specification rules: one case for
`he_091`, four for `he_141`. These are not counted as candidate failures.

Fifteen decimal-rounding cases were also excluded because converting the input
to binary floating point changes its mathematically correct rounded value.
Remaining reference disagreements, invalid inputs, and slow or exceptional
oracle computations are documented in `evaluation/manifest.json`.

This review illustrates why agreement with a reference implementation alone is
not sufficient. The exclusions were applied systematically to the entire affected
task suites, not only to the first candidate mismatch. The references were then
revalidated and the complete candidate evaluation was repeated.

## Artifacts and reproduction

- [Task-level results](evaluation_results/generic-prompts-01/results.csv)
- [Summary](evaluation_results/generic-prompts-01/summary.json)
- [Evaluation manifest](evaluation_results/generic-prompts-01/manifest.json)
- [Reference validation](evaluation_results/reference-validation/summary.json)
- [Suite methodology, provenance, licenses and limitations](evaluation/README.md)

```bash
../ark/.venv/bin/python evaluate_solutions.py --validate-references
../ark/.venv/bin/python evaluate_solutions.py --run results/generic-prompts-01
```

Repeating the same commands resumes/skips completed work. To rerun every task,
choose a new `--output` directory. Changed inputs or evaluator versions cannot be
mixed into an existing report.

The original run's results and all supplied task files were preserved by hash.
Hidden assets were never copied into the Ark workspaces. This separation is a
workflow boundary, not an operating-system sandbox or a claim of dataset secrecy.
