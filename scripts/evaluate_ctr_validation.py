#!/usr/bin/env python3
"""
Evaluate existing CTR models on validation.yzx.txt without retraining; write validation report.
Usage (from project root): PYTHONPATH=. python scripts/evaluate_ctr_validation.py [data_root] [model_root]
Default: data_root=ExperimentConfig.DATA_ROOT, model_root=models
"""
import os
import sys
import json
import math
import argparse
import numpy as np
from datetime import datetime

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.chdir(_root)

from tools.ipinyou_loader import load_yzx_as_csr
from tools.ctr_models import CTRModel


def get_n_features_from_model(model: CTRModel) -> int:
    """Get feature dimension from loaded model (same as at train time)."""
    if hasattr(model.model, "n_features_in_") and model.model.n_features_in_ is not None:
        return int(model.model.n_features_in_)
    if hasattr(model.model, "coef_") and model.model.coef_ is not None:
        return int(model.model.coef_.shape[1])
    return None


def evaluate_one(adv_id: str, data_root: str, model_root: str) -> dict:
    """Load model and validation data, evaluate and return one record."""
    model_path = os.path.join(model_root, adv_id, "ctr.joblib")
    test_path = os.path.join(data_root, adv_id, "validation.yzx.txt")
    bidding_path = os.path.join(model_root, adv_id, "bidding.json")

    if not os.path.isfile(model_path):
        return None
    if not os.path.isfile(test_path):
        return None

    model = CTRModel.load(model_path)
    nfeat = get_n_features_from_model(model)
    if nfeat is None:
        X_val, y_val, z_val, nfeat = load_yzx_as_csr(test_path)
    else:
        X_val, y_val, z_val, _ = load_yzx_as_csr(test_path, n_features=nfeat)

    # Validation feature dim must match model
    if X_val.shape[1] != nfeat:
        raise ValueError(f"{adv_id}: validation X has {X_val.shape[1]} features, model expects {nfeat}. Check that validation.yzx.txt uses the same featindex as training.")
    auc, ll = model.evaluate(X_val, y_val)
    mean_pctr = None
    n_train = None
    if os.path.isfile(bidding_path):
        with open(bidding_path, "r") as f:
            bid_cfg = json.load(f)
        mean_pctr = bid_cfg.get("mean_pctr")
        n_train = bid_cfg.get("n_train")
    if mean_pctr is None:
        mean_pctr = float(model.predict_proba(X_val).mean())

    auc_val = None if (isinstance(auc, float) and math.isnan(auc)) else round(float(auc), 6)
    return {
        "adv_id": adv_id,
        "n_train": n_train,
        "n_test": int(len(y_val)),
        "auc": auc_val,
        "logloss": round(float(ll), 6),
        "mean_pctr": round(float(mean_pctr), 6),
        "model_type": getattr(model, "model_type", "sgd_log"),
    }


def write_reports(model_root: str, results: list):
    """Write ctr_validation_report.json and ctr_validation_report.md."""
    os.makedirs(model_root, exist_ok=True)
    valid_aucs = [r["auc"] for r in results if r.get("auc") is not None]
    summary = {
        "n_advertisers": len(results),
        "mean_auc": round(float(np.mean(valid_aucs)), 6) if valid_aucs else None,
        "std_auc": round(float(np.std(valid_aucs)), 6) if len(valid_aucs) > 1 else None,
        "mean_logloss": round(float(np.mean([r["logloss"] for r in results])), 6),
        "mean_pctr": round(float(np.mean([r["mean_pctr"] for r in results])), 6),
    }
    report = {
        "timestamp": datetime.now().isoformat(),
        "note": "Validation on validation.yzx.txt without retraining",
        "validation_data": "validation.yzx.txt (held-out)",
        "per_advertiser": results,
        "summary": summary,
    }
    json_path = os.path.join(model_root, "ctr_validation_report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"Validation report (JSON): {json_path}")

    md_path = os.path.join(model_root, "ctr_validation_report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# CTR Model Validation Report (for Paper)\n\n")
        f.write("Models were evaluated on held-out `validation.yzx.txt` **without retraining**.\n\n")
        f.write("## Per-Advertiser Results\n\n")
        f.write("| Advertiser ID | Train size | Test size | AUC | Log Loss | Mean pCTR |\n")
        f.write("|---------------|------------|-----------|-----|----------|----------|\n")
        for r in results:
            ntr = r.get("n_train") if r.get("n_train") is not None else "—"
            auc_str = f"{r['auc']:.4f}" if r.get("auc") is not None else "—"
            f.write(f"| {r['adv_id']} | {ntr} | {r['n_test']} | {auc_str} | {r['logloss']:.4f} | {r['mean_pctr']:.6f} |\n")
        f.write("\n## Summary\n\n")
        f.write(f"- **Number of advertisers:** {summary['n_advertisers']}\n")
        if summary["mean_auc"] is not None:
            std_str = f" ± {summary['std_auc']:.4f}" if summary.get("std_auc") is not None else ""
            f.write(f"- **Mean AUC (test):** {summary['mean_auc']:.4f}{std_str}\n")
        f.write(f"- **Mean Log Loss (test):** {summary['mean_logloss']:.4f}\n")
        f.write(f"- **Mean pCTR:** {summary['mean_pctr']:.6f}\n")
    print(f"Validation report (Markdown, for paper): {md_path}")


def main():
    ap = argparse.ArgumentParser(description="Evaluate trained CTR models on validation.yzx.txt and write validation report.")
    ap.add_argument("data_root", nargs="?", default=None, help="Data root (advertiser subdirs with validation.yzx.txt). Default: from ExperimentConfig.DATA_ROOT")
    ap.add_argument("model_root", nargs="?", default="models", help="Model root (default: models)")
    args = ap.parse_args()

    data_root = args.data_root
    if not data_root:
        try:
            from experiments.config import ExperimentConfig
            data_root = ExperimentConfig.DATA_ROOT
        except Exception:
            print("Error: need data_root or set ExperimentConfig.DATA_ROOT.", file=sys.stderr)
            sys.exit(1)
    if not os.path.isdir(data_root):
        print(f"Error: data_root not a directory: {data_root}", file=sys.stderr)
        sys.exit(1)

    model_root = args.model_root
    if not os.path.isdir(model_root):
        print(f"Error: model_root not a directory: {model_root}", file=sys.stderr)
        sys.exit(1)

    # Use same advertiser list as config; skip if no model for an advertiser
    try:
        from experiments.config import ExperimentConfig
        adv_ids = ExperimentConfig.ADVERTISER_IDS
    except Exception:
        adv_ids = sorted(d for d in os.listdir(model_root) if os.path.isdir(os.path.join(model_root, d)))

    results = []
    for adv_id in adv_ids:
        rec = evaluate_one(adv_id, data_root, model_root)
        if rec is None:
            print(f"Skip {adv_id}: missing ctr.joblib or validation.yzx.txt")
            continue
        results.append(rec)
        print(f"{adv_id}: Test={rec['n_test']}, AUC={rec['auc']}, LogLoss={rec['logloss']:.4f}, mean_pCTR={rec['mean_pctr']:.6f}")

    if not results:
        print("No model evaluated. Check data_root and model_root.", file=sys.stderr)
        sys.exit(1)
    write_reports(model_root, results)
    print("Done.")


if __name__ == "__main__":
    main()
