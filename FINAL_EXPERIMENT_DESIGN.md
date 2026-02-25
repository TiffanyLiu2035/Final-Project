# Experiment design and usage: Does audience gender-fairness intervention remain effective after AI agents enter?

## Research question

**Core question**: AI-assisted bidding is an irreversible trend. This setup simulates an ad auction platform and gradually replaces historically trained agents with AI agents to observe **audience gender-fairness** metrics and study: **After AI agents enter the auction, do existing fairness interventions (platform mechanism + advertiser self-regulation) still work?**

- **Subject**: Audience fairness (gender fairness); data has explicit gender labels.
- **Platform-side**: Constrained Auction Mechanism (fairness constraints on audience gender).
- **Advertiser-side**: Fairness-aware profit-seeking agents (balance exposure distribution and fairness while pursuing profit; analogous to bid reweighting in agent behavior).

---

## Experiment design

### Mechanisms (2)

1. **GSP (Generalized Second Price)** — Second-price auction, **baseline**, no fairness intervention.
2. **Constrained Auction Mechanism** — Platform-level audience gender constraints (e.g. target interval [ℓ, 1−ℓ]; see `mechanisms/constrained_auction.py`).

### Fairness metrics (3)

1. **Selection Lift (slift)** — Fairness improvement: whether constraints improve exposure for disadvantaged groups (gender balance). System-level: **slift** (worst-case) and **slift_weighted** (exposure-weighted). **Experiments and plots use slift_weighted as the core metric.**
2. **Revenue Ratio κ (kappa)** — Efficiency cost: κ = rev_fair / rev_base; how much platform revenue is lost for fairness.
3. **TV-distance (dTV, advertiser displacement)** — System stability: how much fairness intervention perturbs advertiser allocation.

- **slift_weighted (core)**: Closer to 1 = fairer male/female exposure across advertisers; exposure-weighted to avoid small-sample advertisers dragging the score down.
- **κ**: Revenue of the fair mechanism relative to GSP; κ < 1 means revenue cost for fairness.
- **dTV**: Change in advertiser shares of the fair mechanism vs GSP (total variation distance).

Details: `GENDER_FAIRNESS_METRICS.md` and `metrics/gender_fairness_metrics.py`.

### Three agent types (advertisers)

1. **Historically trained**
   - Value and bid only from user labels (including gender); no strategy updates, no fairness awareness, no mechanism learning. Implemented as `DataDrivenAgent`.

2. **Adaptive profit-seeking**
   - Simulates highly adaptive, purely profit-seeking advertisers under AI-assisted bidding. Sole goal: maximize profit; adjust bids from auction feedback; optimize returns across user segments. **Implemented**: `AdaptiveProfitAgent` (Type 2) in `agents/llm_bidding_agent.py`, base_bid × lambda_male/female with LLM-updated coefficients.

3. **Fairness-aware profit-seeking**
   - Studies whether advertiser self-regulation can ease platform fairness pressure and whether it over-corrects when combined with the platform mechanism. Still profit-oriented but also considers exposure distribution vs a fairness target; when a strategy worsens fairness, later updates suppress it. **Implemented**: `FairnessAwareAgent` (Type 3) in `agents/llm_bidding_agent.py`, with slift and compliance threshold in the prompt; LLM outputs lambda to balance fairness and profit.

---

## Four experiment groups

Each group runs **1000** auctions under **GSP or Constrained**, and we compute the three fairness metrics (slift, κ, dTV).

| Group | Agent setup | Purpose |
|-------|-------------|---------|
| **1. Baseline** | 9 historically trained agents | No AI, no fairness awareness; baseline. |
| **2. Profit-seeking** | 9 adaptive profit-seeking AI agents (configurable) | Effect of purely profit-seeking AI on fairness. |
| **3. Fairness-aware** | 9 fairness-aware profit-seeking AI agents (configurable) | Whether advertiser self-regulation (bid reweighting) mitigates or amplifies the platform mechanism. |
| **4. Mixed** | 3 of each type above, 9 total | Fairness and mechanism effectiveness as AI replaces historical agents. |

**Setup**: 2 mechanisms × 4 groups. Each group can run under GSP and Constrained for comparison (slift, κ, dTV).

---

## Expected analysis

1. **Mechanism effectiveness**: How slift, κ, dTV change under the four agent setups (data-trained → profit-seeking → fairness-aware → mixed).
2. **Advertiser self-regulation**: Compare group 3 vs group 2 for mitigation of fairness loss and over-correction when combined with Constrained (e.g. large dTV).
3. **System stability**: Use dTV and κ to assess efficiency–fairness–stability.

---

## Running experiments

### Prerequisites

1. **Trained CTR models**
   ```bash
   PYTHONPATH=. python scripts/train_ctr.py DATA models
   ```

2. **(Optional) LLM API key** (for profit-seeking / fairness-aware LLM agents)
   ```bash
   export OPENAI_API_KEY="sk-your-API-key"
   ```
   See `README_LLM_SETUP.md`.

### Main experiment: 4 groups × 2 mechanisms

```bash
PYTHONPATH=. python main.py
# or
PYTHONPATH=. python -m experiments.experiment_runner
```

Runs groups 1–4 under GSP and Constrained (1000 rounds each); audience gender fairness (slift, κ, dTV). Reports and fairness details in the console and `logs/` (e.g. `experiment_report_YYYYMMDD_HHMMSS.json`).

### Multiple seeds (recommended: at least 5)

```bash
PYTHONPATH=. python scripts/run_experiment_multiple_seeds.py
```

Uses seeds 42–46 by default; reports in `logs/experiment_report_seed{N}_*.json`.

### Simplified: Baseline only (9 DataDriven + GSP vs Constrained)

```bash
PYTHONPATH=. python run_gender_fairness_experiment.py
```

Output: round_history for Baseline (GSP) and Constrained plus **slift, κ, dTV** (console and `logs/`). Does not run groups 2–4 or call the LLM.

---

## Custom configuration

- **Rounds**: Change `TOTAL_ROUNDS` in `experiments/config.py` (default 1000).
- **Random seed**: Default 42; overridden by `scripts/run_experiment_multiple_seeds.py` or env `EXPERIMENT_RANDOM_SEED`.
- **Constrained params**: See `MAX_BID_RATIO`, `MIN_WIN_RATE` in `experiments/config.py`; `fairness_strength`, `penalty_scale` in `run_gender_fairness_experiment.py` (that script only).

---

## Alignment with code and docs

- **Mechanisms**: GSP, Constrained Auction (`mechanisms/`).
- **Metrics**: Selection Lift, Revenue Ratio κ, TV-distance (`GENDER_FAIRNESS_METRICS.md`, `metrics/gender_fairness_metrics.py`).
- **Entry**: Full 4-group × 2-mechanism run: `main.py`; profit-seeking, fairness-aware, and mixed groups are in `experiments/config.py` and `agents/llm_bidding_agent.py`, created by `experiments/agent_factory.py` from config.
