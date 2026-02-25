# Gender-based Fairness Metrics

**Purpose**: Define and document this project’s gender-based fairness metrics (formulas, interpretation, usage, and return fields) so that experiment design, reports, and plots consistently use **slift_weighted** as the main fairness metric. Implementation: `metrics/gender_fairness_metrics.py`.

**Convention**: Experiments and plots use slift_weighted (exposure-weighted average) as the core fairness metric.

## Overview

`metrics/gender_fairness_metrics.py` implements the three core fairness metrics from the paper plus **impression_ratio** (Leveling Down detection) from Baumann et al. (2024). All are based on **impression user gender (male/female)**, not agent budget group.

## Core metrics

### 1. Selection Lift (slift)

**Per-advertiser**:
- `E_i,m`, `E_i,f`, `E_i,total`: male/female impressions and total
- `q_i,m`, `q_i,f`: male/female proportions
- `slift_i = min(q_i,m, q_i,f) / max(q_i,m, q_i,f)`, range [0, 1]
- **`q_f_minus_q_m = q_i,f − q_i,m`** (signed, for plotting and direction)
  - **&lt; 0**: male-biased
  - **&gt; 0**: female-biased

**System-level** (only advertisers with `E_i,total >= min_impressions_threshold`, default 10):
- **`slift`** (worst-case): `slift = min_i slift_i`, in [0, 1], consistent with the paper.
- **`slift_weighted`** (weighted average): `sum(slift_i * E_i,total) / sum(E_i,total)`, so a few small advertisers (e.g. only 2 wins, same gender) do not drag the system score to 0.

**Interpretation**:
- Higher `slift` / `slift_weighted` (closer to 1) means fairer; `q_f_minus_q_m` near 0 means balanced male/female exposure for that advertiser.
- You can set `min_impressions_threshold=0` at init to disable the threshold (all advertisers with any impressions participate in system slift).

### 2. Revenue Ratio κ (kappa)

**Formula**: `κ = rev_fair / rev_base`

Where:
- `rev_fair = Σ payment` (total revenue under the fair mechanism)
- `rev_base = Σ payment` (total revenue under the baseline mechanism)

**Requirement**: Baseline and fair must use the **same set of impressions** (unknown gender already filtered).

**Interpretation**: Change in revenue of the fair mechanism relative to baseline.
- `κ = 1.0`: same revenue
- `κ > 1.0`: fair mechanism yields higher revenue
- `κ < 1.0`: fair mechanism yields lower revenue

### 3. Advertiser Displacement dTV

**Formula**:
- For each advertiser i:
  - `s_i = (E_i,m + E_i,f) / Σ_k(E_k,m + E_k,f)` (share of total wins)
- `dTV = 0.5 * Σ_i |s_i^base - s_i^fair|`

**Interpretation**: Change in advertiser shares under the fair mechanism vs baseline (total variation distance).
- Range: [0, 1]
- `0.0` = identical share distribution
- `1.0` = completely different share distribution

### 4. Impression Ratio (Leveling Down, Baumann et al. 2024)

**Formula**: `impression_ratio = total_impressions_fair / total_impressions_base`

Where `total_impressions` is the **number of all valid rounds** (rounds included in fairness stats, excluding skipped and unknown gender).

**Interpretation**: Detects “Leveling Down”—fairness interventions reducing total impressions.
- **&lt; 1.0**: fair mechanism shrinks the market (total impressions drop)
- **≈ 1.0**: market size stable
- **&gt; 1.0**: more valid rounds on the fair side (only possible if the two runs use different impression sequences)

**Note**: Only provided in the return value of `compute_with_baseline(...)`. Single-run `compute(...)` returns `total_impressions` (= valid_rounds), which you can use to compute this when comparing to a baseline.

## Usage

### Standalone (slift only)

```python
from metrics.gender_fairness_metrics import GenderFairnessMetrics

metrics = GenderFairnessMetrics()
result = metrics.compute(round_history)

print(f"slift: {result['slift']}")
print(f"per_advertiser: {result['per_advertiser']}")
```

### With baseline (κ, dTV, impression_ratio)

```python
fair_result = metrics.compute(fair_round_history)
baseline_result = metrics.compute(baseline_round_history)

# compute_with_baseline computes κ, dTV, impression_ratio (Leveling Down)
full_result = metrics.compute_with_baseline(
    fair_round_history,
    baseline_round_history
)

print(f"slift: {full_result['slift']}")
print(f"kappa: {full_result['kappa']}")
print(f"dTV: {full_result['dTV']}")
print(f"impression_ratio: {full_result['impression_ratio']}")  # < 1.0 indicates Leveling Down
```

## Return fields

### Core metrics
- `slift`: system-level selection lift, worst-case min_i slift_i (float)
- `slift_weighted`: exposure-weighted system slift (float); None when no advertiser meets the threshold
- `kappa`: revenue ratio (float, requires baseline)
- `dTV`: advertiser displacement (float, requires baseline)
- **`impression_ratio`**: total_impressions_fair / total_impressions_base (only from `compute_with_baseline`), for Leveling Down (Baumann et al. 2024)
- `slift_details`: includes `min_impressions_threshold`, `advertisers_excluded_by_threshold`, `slift_weighted`, etc.

### Per-advertiser details
- `per_advertiser`: Dict[advertiser_name, Dict]
  - `E_i,m`, `E_i,f`, `E_i,total`: male/female impressions and total
  - `q_i,m`, `q_i,f`: male/female proportions
  - `slift_i`: per-advertiser selection lift, [0, 1]
  - **`q_f_minus_q_m`**: signed q_f − q_m; &lt;0 male-biased, &gt;0 female-biased (for plotting)

### Auxiliary (by gender)
- `exposure_by_gender`: {"male": int, "female": int}
- `exposure_share_by_gender`: {"male": float, "female": float}
- `win_rate_by_gender`: {"male": float, "female": float} (matches code return fields)

### Other
- `total_payment`: total payment amount
- `payments_by_advertiser`: total payment per advertiser
- `valid_rounds`: number of valid rounds (excluding skipped and unknown gender)
- **`total_impressions`**: same as `valid_rounds`; used to compute `impression_ratio` (Leveling Down)
- `skipped_rounds`: number of skipped rounds (unknown gender)
- `total_rounds`: total number of rounds

## Notes

1. **Impression gender**:
   - Prefer `impression["user_type"]` or `impression["gender"]`
   - Otherwise try sparse feature matrix (iPinYou: 10110=male, 10111=female)
   - Custom `extract_gender_fn` is supported

2. **Skipped rounds**:
   - Rounds with `skipped=True` are skipped
   - Rounds where gender is not 'male' or 'female' are skipped
   - Baseline and fair must use the same set of impressions

3. **Per-advertiser stats**:
   - If `E_i,m + E_i,f = 0`, `q_i,m`, `q_i,f`, `slift_i`, `q_f_minus_q_m` are `None`
   - System-level slift only includes advertisers with `E_i,total >= min_impressions_threshold` (default 10). Use `GenderFairnessMetrics(data_root=..., min_impressions_threshold=0)` to disable the threshold.
