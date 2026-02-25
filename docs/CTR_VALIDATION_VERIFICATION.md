# CTR Validation 计算验证说明

本文档确认当前 CTR 验证（AUC、Log Loss）的计算方式正确、无数据泄露、且与训练时一致。

## 1. 数据与职责划分

- **训练集**：`train.yzx.txt`，仅用于 `model.fit(X_tr, y_tr)`，不参与验证指标计算。
- **验证集**：`validation.yzx.txt`（原 test 划分），仅用于 `model.evaluate(X_val, y_val)` 和报告中的 AUC / Log Loss。
- 无交叉：验证阶段不读取 `train.yzx.txt`，训练阶段验证集只用于评估、不用于拟合。

## 2. 特征维度对齐

- **训练时**（`scripts/train_ctr.py`）：  
  - 先从 `train.yzx.txt` 加载得到 `nfeat`（由数据中最大特征索引推断）。  
  - 再加载 `validation.yzx.txt` 时**显式传入** `n_features=nfeat`，保证验证集矩阵列数与训练集一致。  
- **仅评估时**（`scripts/evaluate_ctr_validation.py`）：  
  - 从已保存模型中取 `n_features_in_`（或 `coef_.shape[1]`），再加载 `validation.yzx.txt` 时传入该 `nfeat`。  
  - 若验证集特征维与模型不一致会报错（脚本内已加自检），避免静默维度错位。

因此，验证集与训练集使用**同一广告主、同一 featindex** 下的同一特征空间，维度一致。

## 3. 指标计算（与 sklearn 一致）

- **AUC**（`tools/ctr_models.py`）：  
  - `roc_auc_score(y_true, y_score)`，其中 `y_score = model.predict_proba(X)[:, 1]`。  
  - 若验证集中只有正样本或只有负样本（`y.sum() == 0` 或 `y.sum() == len(y)`），AUC 无定义，返回 `nan` 并在报告中记为缺失。  

- **Log Loss**：  
  - `log_loss(y, p)`，概率 `p` 先裁剪到 `[1e-6, 1-1e-6]`，避免 log(0)。  
  - 与 sklearn 二分类 log loss 定义一致。

- **Mean pCTR**（报告中）：  
  - 来自 `bidding.json` 的 `mean_pctr`（训练集上的均值），或若无则用验证集上的 `predict_proba(X_val).mean()`。  
  - 仅作参考，不参与 AUC/Log Loss 计算。

## 4. 报告汇总

- **Per-advertiser**：每个广告主一条记录，包含 `n_test`、`auc`、`logloss`、`mean_pctr`。  
- **Summary**：  
  - `mean_auc`：对有效 AUC 取平均（跳过 nan）。  
  - `std_auc`：有效 AUC 的标准差（≥2 个广告主时）。  
  - `mean_logloss`：所有广告主 logloss 的均值。  
  - `mean_pctr`：所有广告主 mean_pctr 的均值。  

数值与“每个广告主在各自 validation.yzx.txt 上算 AUC/Log Loss，再汇总”一致。

## 5. 自检与可复现

- 评估脚本中已增加检查：若 `X_val.shape[1] != model.n_features_in_`，会抛出 `ValueError`，避免特征维不一致导致错误结果。  
- 同一组 `validation.yzx.txt` 和 `ctr.joblib` 多次运行评估脚本，得到的报告应一致（无随机性）。  

**结论**：当前 CTR 验证流程在数据划分、特征对齐、指标定义和汇总上均正确，可直接用于论文中的模型验证结果。
