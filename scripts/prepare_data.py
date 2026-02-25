"""
Data preparation: (1) Split 10% from train as validation; (2) Merge test into unified impression pool.
"""
import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from split_train_to_test import split_train_to_test
from create_impression_pool import create_impression_pool


def main():
    ap = argparse.ArgumentParser(description="Data prep: split train/validation and create impression pool")
    ap.add_argument("data_root", help="Data root (advertiser subdirs)")
    ap.add_argument("--test_ratio", type=float, default=0.1, help="Fraction from train as test (default 0.1)")
    ap.add_argument("--random_seed", type=int, default=42, help="Random seed (default 42)")
    ap.add_argument("--advertiser_ids", nargs="+",
                   default=["1458", "2259", "2261", "2821", "2997", "3358", "3386", "3427", "3476"],
                   help="Advertiser ID list (default: all 9)")
    ap.add_argument("--impression_pool_file", default="impression_pool.yzx.txt", help="Output pool file path")
    args = ap.parse_args()

    print("="*70)
    print("Data preparation")
    print("="*70)
    print()

    print("Step 1: Create unified impression pool (using original test data)")
    print("-"*70)
    pool_file_path = os.path.join(args.data_root, args.impression_pool_file)
    create_impression_pool(
        args.data_root,
        args.advertiser_ids,
        pool_file_path,
        use_original_test=True
    )

    print()
    print("Step 2: Split 10% from train as validation (update train files)")
    print("-"*70)
    split_train_to_test(
        args.data_root,
        args.advertiser_ids,
        args.test_ratio,
        args.random_seed
    )

    print("="*70)
    print("  Data prep done.")
    print("="*70)
    print()
    print("Output:")
    print(f"  1. Impression pool: {pool_file_path}")
    print(f"  2. Per-advertiser validation file updated (10% from train)")
    print(f"  3. Per-advertiser train file updated (90% remaining)")
    print()
    print("Next:")
    print(f"  1. Train CTR: PYTHONPATH=. python scripts/train_ctr.py {args.data_root} models")
    print("  2. Run experiment: python run_gender_fairness_experiment.py")


if __name__ == "__main__":
    main()

