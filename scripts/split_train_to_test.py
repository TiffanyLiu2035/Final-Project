"""Split 10% from each advertiser's train data into validation (test) file."""
import os
import argparse
import random
from tools.ipinyou_loader import iter_yzx


def split_train_to_test(data_root: str, advertiser_ids: list, test_ratio: float = 0.1, random_seed: int = 42):
    """Split 10% from each advertiser's train into validation file. Args: data_root, advertiser_ids, test_ratio (default 0.1), random_seed."""
    print("="*70)
    print("Splitting train into validation (test)")
    print("="*70)
    print()
    print(f"Test ratio: {test_ratio*100:.1f}%")
    print(f"Random seed: {random_seed}")
    print()
    random.seed(random_seed)
    for adv_id in advertiser_ids:
        train_file = os.path.join(data_root, adv_id, "train.yzx.txt")
        test_file = os.path.join(data_root, adv_id, "validation.yzx.txt")
        if not os.path.exists(train_file):
            print(f"  Warning: {train_file} not found, skip")
            continue
        print(f"Processing {adv_id}...")
        train_data = []
        for y, z, feats in iter_yzx(train_file):
            train_data.append((y, z, feats))
        total_count = len(train_data)
        test_count = int(total_count * test_ratio)
        train_count = total_count - test_count
        print(f"  Total: {total_count:,}, train: {train_count:,}, test: {test_count:,}")
        random.shuffle(train_data)
        test_data = train_data[:test_count]
        new_train_data = train_data[test_count:]
        if os.path.exists(test_file):
            backup_file = test_file + ".backup"
            print(f"  Backup test to: {backup_file}")
            os.rename(test_file, backup_file)
        train_backup_file = train_file + ".backup"
        print(f"  Backup train to: {train_backup_file}")
        import shutil
        shutil.copy2(train_file, train_backup_file)
        print(f"  Writing new validation: {test_file}")
        with open(test_file, 'w') as f:
            for y, z, feats in test_data:
                feat_str = " ".join([f"{idx}:{val}" for idx, val in feats])
                f.write(f"{y}\t{z}\t{feat_str}\n")
        print(f"  Updating train: {train_file}")
        with open(train_file, 'w') as f:
            for y, z, feats in new_train_data:
                feat_str = " ".join([f"{idx}:{val}" for idx, val in feats])
                f.write(f"{y}\t{z}\t{feat_str}\n")
        print(f"  Done: {adv_id}")
        print()
    print("="*70)
    print("All advertisers done.")
    print("="*70)
    print("Note: original test/train backed up as .backup; new validation = 10% from train; train updated to 90%.")
    print()


def main():
    ap = argparse.ArgumentParser(description="Split train into validation (test) per advertiser.")
    ap.add_argument("data_root", help="Data root (advertiser subdirs)")
    ap.add_argument("--test_ratio", type=float, default=0.1, help="Fraction to use as test (default 0.1)")
    ap.add_argument("--random_seed", type=int, default=42, help="Random seed (default 42)")
    ap.add_argument("--advertiser_ids", nargs="+",
                   default=["1458", "2259", "2261", "2821", "2997", "3358", "3386", "3427", "3476"],
                   help="Advertiser ID list (default: all 9)")
    args = ap.parse_args()
    
    split_train_to_test(args.data_root, args.advertiser_ids, args.test_ratio, args.random_seed)


if __name__ == "__main__":
    main()

