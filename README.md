# AIRTB Project

Multi-agent real-time bidding (RTB) simulation framework for studying **whether existing audience gender-fairness interventions remain effective after AI agents enter the ad auction**.

This document explains how to run experiments locally.

---

## Environment and Dependencies

- **Python**: 3.9–3.12 recommended.
- Create a virtual environment in the project root and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate   # Linux/macOS; Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Main dependencies: `numpy`, `pandas`, `scipy`, `scikit-learn`, `joblib`, `matplotlib`, `python-dotenv`, `pyyaml`. For the full four-group experiments with LLM you also need `openai` and a `.env` file in the project root with `OPENAI_API_KEY`.

---

## Prerequisites (must be ready)

- **Impression pool**: `DATA/impression_pool_original.log.txt` exists (or the same filename under the data root set by `IPINYOU_DATA_ROOT`).
- **CTR models**: Trained models per advertiser under `models/` (e.g. `ctr.joblib`, `bidding.json`).

If not set up yet, see `scripts/create_impression_pool_original.py` and `scripts/train_ctr.py`.

---

## Running experiments

All commands below are run from the **project root**.

**Single full run (4 groups × 2 mechanisms, default seed 42):**

```bash
PYTHONPATH=. python main.py
```

Output goes to `logs/` (e.g. `experiment_report_YYYYMMDD_HHMMSS.json`).

**Reproduce with a specific seed (recommended):**

```bash
PYTHONPATH=. python scripts/run_one_seed.py 2    # seed 2
```

Output: `logs/run_seed2_terminal.log`, `logs/experiment_report_seed2_*.json`.

**Multiple seeds (e.g. 6 seeds):**

```bash
for seed in 2 15 33 38 69 95; do PYTHONPATH=. python scripts/run_one_seed.py $seed; done
```

**Baseline only: 9 DataDriven + GSP vs Constrained (no LLM, quick check):**

```bash
PYTHONPATH=. python run_gender_fairness_experiment.py
```

---

## Documentation

- `FINAL_EXPERIMENT_DESIGN.md` — Experiment design, four groups and mechanisms.
- `GENDER_FAIRNESS_METRICS.md` — Fairness metrics (slift, κ, dTV).
- `ARCHITECTURE.md` — System architecture.
- **LLM experiments**: see `README_LLM_SETUP.md` (API key, verification, FAQ).

---

## Data and reference

Data preprocessing follows [wnzhang/make-ipinyou-data](https://github.com/wnzhang/make-ipinyou-data) to convert iPinYou RTB raw data into a unified format.

