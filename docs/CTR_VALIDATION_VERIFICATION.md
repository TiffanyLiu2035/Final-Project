# CTR validation: computation and verification

This document confirms that the current CTR validation (AUC, Log Loss) is computed correctly, without data leakage, and consistently with training.

## 1. Data and responsibility split

- **Training set**: `train.yzx.txt`, used only for `model.fit(X_tr, y_tr)`; not used in validation metrics.
- **Validation set**: `validation.yzx.txt` (original test split), used only for `model.evaluate(X_val, y_val)` and reported AUC / Log Loss.
- No overlap: validation does not read `train.yzx.txt`; during training the validation set is used only for evaluation, not fitting.

## 2. Feature dimension alignment

- **During training** (`scripts/train_ctr.py`):
  - Load `train.yzx.txt` first to get `nfeat` (from max feature index in the data).
  - When loading `validation.yzx.txt`, pass **`n_features=nfeat`** explicitly so the validation matrix has the same number of columns as the training set.
- **Evaluation only** (`scripts/evaluate_ctr_validation.py`):
  - Take `n_features_in_` (or `coef_.shape[1]`) from the saved model; when loading `validation.yzx.txt` pass that `nfeat`.
  - If validation feature dim does not match the model, the script raises an error (self-check added) to avoid silent dimension mismatch.

So validation and training use the **same advertiser and featindex** and the same feature space; dimensions are consistent.

## 3. Metric computation (aligned with sklearn)

- **AUC** (`tools/ctr_models.py`):
  - `roc_auc_score(y_true, y_score)` with `y_score = model.predict_proba(X)[:, 1]`.
  - If the validation set has only positive or only negative labels (`y.sum() == 0` or `y.sum() == len(y)`), AUC is undefined; the code returns `nan` and reports it as missing.

- **Log Loss**:
  - `log_loss(y, p)` with probability `p` clipped to `[1e-6, 1-1e-6]` to avoid log(0).
  - Matches sklearn binary log loss.

- **Mean pCTR** (in the report):
  - From `mean_pctr` in `bidding.json` (mean on training set), or if missing, `predict_proba(X_val).mean()` on the validation set.
  - Reference only; not used in AUC/Log Loss.

## 4. Report summary

- **Per-advertiser**: One row per advertiser with `n_test`, `auc`, `logloss`, `mean_pctr`.
- **Summary**:
  - `mean_auc`: average over valid AUCs (skipping nan).
  - `std_auc`: standard deviation of valid AUCs (when ≥2 advertisers).
  - `mean_logloss`: mean logloss over advertisers.
  - `mean_pctr`: mean of per-advertiser mean_pctr.

Values match “compute AUC/Log Loss per advertiser on its validation.yzx.txt, then aggregate”.

## 5. Self-check and reproducibility

- The evaluation script checks: if `X_val.shape[1] != model.n_features_in_` it raises `ValueError` to avoid wrong results from dimension mismatch.
- Running the evaluation script multiple times on the same `validation.yzx.txt` and `ctr.joblib` yields the same report (no randomness).

**Conclusion**: The current CTR validation pipeline is correct in data split, feature alignment, metric definition, and aggregation, and can be used directly for model validation results in the paper.
