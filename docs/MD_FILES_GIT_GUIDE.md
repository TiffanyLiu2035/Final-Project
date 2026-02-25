# Which MD files to commit to GitHub

## Recommended to always commit (core docs)

| File | Description |
|------|-------------|
| `README.md` | Project entry and main instructions for running experiments |
| `README_LLM_SETUP.md` | LLM API setup; linked from README |
| `FINAL_EXPERIMENT_DESIGN.md` | Experiment design; linked from README |
| `GENDER_FAIRNESS_METRICS.md` | Fairness metrics; linked from README |
| `ARCHITECTURE.md` | System architecture; linked from README |

These five match the main workflow and doc index; **commit all of them**.

---

## Recommended to commit (help understanding/repro)

| File | Description |
|------|-------------|
| `AGENT_TUNING.md` | Agent tuning (yaml, personas, etc.) for others to tweak experiments |
| `AGENT_DEGREE_DIFFERENCES.md` | Explains differences between the three agent types |
| `EXPERIMENT_RECORDS.md` | Describes what goes in `logs/` and traceability |
| `docs/CTR_VALIDATION_VERIFICATION.md` | Useful for CTR validation and training repro |
| `archive/README.md` | Explains the archive directory to avoid using old code by mistake |

Safe to commit with the project; skipping them does not affect “can run”.

---

## Recommended not to commit (omit or .gitignore)

| Location | Description |
|----------|-------------|
| **All `.md` under logs/** | e.g. `logs/formal_experiment/*.md`, `logs/summary_last6_metrics.md`, `logs/three_metrics_tables.md`, `logs/AUCTION_ROUNDS_USER_INFO_README.md` — mostly one-off experiment reports that change with runs; not ideal for the repo |
| **models/ctr_validation_report.md** | Training output, tied to specific data/models; usually not committed |

**Either approach is fine:**

1. **Don’t add**: Don’t `git add` these before committing; or  
2. **Use .gitignore**: Add `logs/` (and optionally `models/` if you don’t want to commit model artifacts) to `.gitignore` so nothing under those dirs is committed.

---

## Summary

- **Commit**: `README.md`, `README_LLM_SETUP.md`, `FINAL_EXPERIMENT_DESIGN.md`, `GENDER_FAIRNESS_METRICS.md`, `ARCHITECTURE.md`
- **Optional but recommended**: `AGENT_TUNING.md`, `AGENT_DEGREE_DIFFERENCES.md`, `EXPERIMENT_RECORDS.md`, `docs/CTR_VALIDATION_VERIFICATION.md`, `archive/README.md`
- **Skip**: All `.md` under `logs/`, `models/ctr_validation_report.md`; add `logs/` to `.gitignore` to avoid accidental commit
