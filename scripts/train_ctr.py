import os
import argparse
import json
import math
import numpy as np
from datetime import datetime
from joblib import dump
from scipy.sparse import vstack
from tools.ipinyou_loader import load_yzx_as_csr
from tools.ctr_models import CTRModel

"""
Expected data layout per advertiser_id directory:
  train.yzx.txt
  validation.yzx.txt
  featindex.txt (optional)
Outputs:
  models/{adv_id}/ctr.joblib, bidding.json
  models/ctr_validation_report.json, models/ctr_validation_report.md (for paper)
"""

def train_single(adv_dir: str, out_dir: str, model_type: str = "sgd_log", val_ratio: float = 0.1):
    train_path = os.path.join(adv_dir, "train.yzx.txt")
    test_path = os.path.join(adv_dir, "validation.yzx.txt")
    adv_id = os.path.basename(os.path.normpath(adv_dir))
    save_dir = os.path.join(out_dir, adv_id)
    os.makedirs(save_dir, exist_ok=True)

    # Load training data (already split: 90% in train, 10% in test)
    X_tr, y_tr, z_tr, nfeat = load_yzx_as_csr(train_path)
    
    # Load test data for validation (10% split from original train)
    # Use same n_features as training data to ensure feature dimension consistency
    X_val, y_val, z_val, _ = load_yzx_as_csr(test_path, n_features=nfeat)

    # Train model on training data
    model = CTRModel(model_type=model_type).fit(X_tr, y_tr)
    
    # Evaluate on test set (used as validation set)
    auc, ll = model.evaluate(X_val, y_val)
    model.save(os.path.join(save_dir, "ctr.joblib"))

    # Estimate mean pCTR and simple ORTB2 params (placeholder)
    mean_pctr = float(model.predict_proba(X_tr).mean())
    params = {
        "mean_pctr": mean_pctr,
        "lambda": 1.0,
        "c": 100.0,
        "d": 1.0,
        "validation_auc": round(auc, 6),
        "validation_logloss": round(ll, 6),
        "n_train": len(y_tr),
        "n_test": len(y_val),
    }
    with open(os.path.join(save_dir, "bidding.json"), 'w') as f:
        json.dump(params, f, indent=2)

    print(f"{adv_id}: Train={len(y_tr)}, Val={len(y_val)}, AUC={auc:.4f}, LogLoss={ll:.5f}, mean_pCTR={mean_pctr:.5f}")

    auc_val = None if (math.isnan(auc) if isinstance(auc, float) else False) else round(auc, 6)
    return {
        "adv_id": adv_id,
        "n_train": int(len(y_tr)),
        "n_test": int(len(y_val)),
        "auc": auc_val,
        "logloss": round(ll, 6),
        "mean_pctr": round(mean_pctr, 6),
        "model_type": model_type,
    }


def write_validation_report(out_root: str, results: list, model_type: str):
    """Write ctr_validation_report.json and ctr_validation_report.md for paper."""
    os.makedirs(out_root, exist_ok=True)
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
        "model_type": model_type,
        "validation_data": "validation.yzx.txt (held-out 10%)",
        "per_advertiser": results,
        "summary": summary,
    }
    json_path = os.path.join(out_root, "ctr_validation_report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nValidation report (JSON): {json_path}")

    md_path = os.path.join(out_root, "ctr_validation_report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# CTR Model Validation Report (for Paper)\n\n")
        f.write("Models are trained on `train.yzx.txt` and evaluated on held-out `validation.yzx.txt` (10% split).\n\n")
        f.write("## Per-Advertiser Results\n\n")
        f.write("| Advertiser ID | Train size | Test size | AUC | Log Loss | Mean pCTR |\n")
        f.write("|---------------|------------|-----------|-----|----------|----------|\n")
        for r in results:
            auc_str = f"{r['auc']:.4f}" if r.get("auc") is not None else "—"
            f.write(f"| {r['adv_id']} | {r['n_train']} | {r['n_test']} | {auc_str} | {r['logloss']:.4f} | {r['mean_pctr']:.6f} |\n")
        f.write("\n## Summary\n\n")
        f.write(f"- **Number of advertisers:** {summary['n_advertisers']}\n")
        if summary["mean_auc"] is not None:
            std_str = f" ± {summary['std_auc']:.4f}" if summary.get("std_auc") is not None else ""
            f.write(f"- **Mean AUC (test):** {summary['mean_auc']:.4f}{std_str}\n")
        f.write(f"- **Mean Log Loss (test):** {summary['mean_logloss']:.4f}\n")
        f.write(f"- **Mean pCTR (train):** {summary['mean_pctr']:.6f}\n")
    print(f"Validation report (Markdown, for paper): {md_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data_root", help="root dir containing advertiser subdirs (1458, 2259, ...)")
    ap.add_argument("out_root", help="output models root dir")
    ap.add_argument("--model_type", default="sgd_log", choices=["sgd_log", "logreg"])
    ap.add_argument("--val_ratio", type=float, default=0.1, help="[Deprecated] Data already split: train (90%) and test (10%)")
    args = ap.parse_args()

    results = []
    for adv_id in sorted(os.listdir(args.data_root)):
        adv_dir = os.path.join(args.data_root, adv_id)
        if not os.path.isdir(adv_dir):
            continue
        if not os.path.exists(os.path.join(adv_dir, "train.yzx.txt")):
            continue
        if not os.path.exists(os.path.join(adv_dir, "validation.yzx.txt")):
            print(f"Skip {adv_id}: validation.yzx.txt not found")
            continue
        rec = train_single(adv_dir, args.out_root, model_type=args.model_type, val_ratio=args.val_ratio)
        results.append(rec)

    if results:
        write_validation_report(args.out_root, results, args.model_type)

if __name__ == "__main__":
    main()


