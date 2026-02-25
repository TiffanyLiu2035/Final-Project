# Gender-based Fairness Metrics

**文档作用**：定义并说明本项目中基于性别的公平性指标（公式、含义、使用方法与返回字段），供实验设计、实验报告与绘图统一以 **slift_weighted** 为核心公平性指标时参考。对应实现见 `metrics/gender_fairness_metrics.py`。

**约定**：实验与绘图统一以 slift_weighted（按曝光加权的平均值）作为核心公平性指标。

## 概述

`metrics/gender_fairness_metrics.py` 实现了论文中的三个核心公平性指标，以及基于 Baumann et al. (2024) 的 **impression_ratio**（Leveling Down 检测），均基于 **impression user gender (male/female)** 维度，而非 agent budget group。

## 核心指标

### 1. Selection Lift (slift)

**Per-advertiser**:
- `E_i,m`, `E_i,f`, `E_i,total`：男女曝光数及总和
- `q_i,m`, `q_i,f`：男女比例
- `slift_i = min(q_i,m, q_i,f) / max(q_i,m, q_i,f)`，范围 [0, 1]
- **`q_f_minus_q_m = q_i,f − q_i,m`**（有符号，便于画图与方向性）  
  - **&lt; 0**：偏向男性  
  - **&gt; 0**：偏向女性  

**系统级**（仅统计 `E_i,total >= min_impressions_threshold` 的广告主，默认阈值 10）:
- **`slift`**（worst-case）：`slift = min_i slift_i`，保持 [0, 1]，与论文一致。
- **`slift_weighted`**（加权平均）：`sum(slift_i * E_i,total) / sum(E_i,total)`，避免个别小广告主（如只赢 2 次且全为同一性别）把系统得分拉低到 0。

**含义**:
- `slift` / `slift_weighted` 越接近 1 越公平；`q_f_minus_q_m` 接近 0 表示该广告主男女曝光比例均衡。
- 初始化时可设 `min_impressions_threshold=0` 表示不设阈值（所有有曝光的广告主都参与系统 slift）。

### 2. Revenue Ratio κ (kappa)

**公式**: `κ = rev_fair / rev_base`

其中:
- `rev_fair = Σ payment` (fair mechanism 的总收入)
- `rev_base = Σ payment` (baseline mechanism 的总收入)

**要求**: baseline 和 fair 必须使用**同一批 impressions**（unknown gender 已过滤）

**含义**: 衡量公平机制相对于 baseline 的收入变化
- `κ = 1.0`: 收入相同
- `κ > 1.0`: fair 机制收入更高
- `κ < 1.0`: fair 机制收入更低

### 3. Advertiser Displacement dTV

**公式**:
- 对每个 advertiser i:
  - `s_i = (E_i,m + E_i,f) / Σ_k(E_k,m + E_k,f)` (整体胜出份额)
- `dTV = 0.5 * Σ_i |s_i^base - s_i^fair|`

**含义**: 衡量 fair 机制相对于 baseline 的 advertiser 份额变化（total variation distance）
- 范围: [0, 1]
- `0.0` = 份额分布完全相同
- `1.0` = 份额分布完全不同

### 4. Impression Ratio（Leveling Down, Baumann et al. 2024）

**公式**: `impression_ratio = total_impressions_fair / total_impressions_base`

其中 `total_impressions` 为**所有 valid rounds 的数量**（即参与公平性统计的有效轮数，排除 skipped 与 unknown gender）。

**含义**: 检测「Leveling Down」效应——为公平而导致总展示量下降。
- **&lt; 1.0**：公平机制导致市场萎缩（总展示量下降）
- **≈ 1.0**：市场容量保持稳定
- **&gt; 1.0**：fair 侧有效轮数多于 baseline（仅在两轮使用不同 impression 序列时可能出现）

**说明**: 仅在 `compute_with_baseline(...)` 的返回结果中提供；`compute(...)` 单次运行结果中有 `total_impressions`（= valid_rounds），可用于与 baseline 对比时计算。

## 使用方法

### 单独计算（仅 slift）

```python
from metrics.gender_fairness_metrics import GenderFairnessMetrics

metrics = GenderFairnessMetrics()
result = metrics.compute(round_history)

print(f"slift: {result['slift']}")
print(f"per_advertiser: {result['per_advertiser']}")
```

### 与 baseline 对比（计算 κ、dTV、impression_ratio）

```python
fair_result = metrics.compute(fair_round_history)
baseline_result = metrics.compute(baseline_round_history)

# 使用 compute_with_baseline 自动计算 κ、dTV、impression_ratio（Leveling Down）
full_result = metrics.compute_with_baseline(
    fair_round_history, 
    baseline_round_history
)

print(f"slift: {full_result['slift']}")
print(f"kappa: {full_result['kappa']}")
print(f"dTV: {full_result['dTV']}")
print(f"impression_ratio: {full_result['impression_ratio']}")  # < 1.0 表示 Leveling Down
```

## 返回字段

### 核心指标
- `slift`: 系统级 selection lift，worst-case min_i slift_i (float)
- `slift_weighted`: 按曝光量加权的系统 slift (float)；无广告主满足阈值时为 None
- `kappa`: Revenue ratio (float, 需要 baseline)
- `dTV`: Advertiser displacement (float, 需要 baseline)
- **`impression_ratio`**: total_impressions_fair / total_impressions_base（仅 `compute_with_baseline` 返回），用于检测 Leveling Down（Baumann et al. 2024）
- `slift_details`: 含 `min_impressions_threshold`、`advertisers_excluded_by_threshold`、`slift_weighted` 等

### Per-advertiser 详细统计
- `per_advertiser`: Dict[advertiser_name, Dict]
  - `E_i,m`, `E_i,f`, `E_i,total`: 男女曝光数及总和
  - `q_i,m`, `q_i,f`: 男女比例
  - `slift_i`: per-advertiser selection lift，[0, 1]
  - **`q_f_minus_q_m`**: 有符号指标 q_f − q_m，&lt;0 偏向男性，&gt;0 偏向女性（便于论文画图）

### 辅助指标（按 gender 统计）
- `exposure_by_gender`: {"male": int, "female": int}
- `exposure_share_by_gender`: {"male": float, "female": float}
- `win_rate_by_gender`: {"male": float, "female": float}（与代码返回字段一致）

### 其他信息
- `total_payment`: 总支付金额
- `payments_by_advertiser`: 每个 advertiser 的支付总额
- `valid_rounds`: 有效轮数（排除 skipped 与 unknown gender）
- **`total_impressions`**: 与 `valid_rounds` 同义，用于计算 `impression_ratio`（Leveling Down）
- `skipped_rounds`: 跳过的轮数（unknown gender）
- `total_rounds`: 总轮数

## 注意事项

1. **Impression Gender 提取**: 
   - 优先从 `impression["user_type"]` 或 `impression["gender"]` 提取
   - 如果没有，尝试从稀疏特征矩阵提取（iPinYou: 10110=male, 10111=female）
   - 可以传入自定义 `extract_gender_fn` 函数

2. **Skipped Rounds**:
   - 自动跳过 `skipped=True` 的轮次
   - 自动跳过 gender 不是 'male' 或 'female' 的轮次
   - baseline 和 fair 必须使用同一批 impressions

3. **Per-advertiser Stats**:
   - 如果 `E_i,m + E_i,f = 0`，`q_i,m`, `q_i,f`, `slift_i`, `q_f_minus_q_m` 为 `None`
   - 系统级 slift 只统计 `E_i,total >= min_impressions_threshold` 的广告主（默认 10），可通过 `GenderFairnessMetrics(data_root=..., min_impressions_threshold=0)` 关闭阈值


