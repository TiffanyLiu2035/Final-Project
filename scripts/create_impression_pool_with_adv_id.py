"""Create unified impression pool with advertiser ID appended per line: y \\t z \\t feat_str \\t adv_id."""
import os
import argparse
from tools.ipinyou_loader import iter_yzx


def create_impression_pool_with_adv_id(
    data_root: str, advertiser_ids: list, output_file: str, use_original_test: bool = True
):
    """Merge all advertisers' test into one pool file with adv_id per line. Args: data_root, advertiser_ids, output_file, use_original_test."""
    print("="*70)
    print("Creating unified impression pool (with advertiser ID)")
    print("="*70)
    print()
    if use_original_test:
        print("  Note: using original test (.backup) for pool")
        print()
    total_count = 0
    with open(output_file, 'w') as out_f:
        for adv_id in advertiser_ids:
            if use_original_test:
                test_file = os.path.join(data_root, adv_id, "validation.yzx.txt.backup")
                if not os.path.exists(test_file):
                    test_file = os.path.join(data_root, adv_id, "validation.yzx.txt")
                    if not os.path.exists(test_file):
                        print(f"  Warning: {adv_id} test not found, skip")
                        continue
                    print(f"  Warning: {adv_id} no .backup, using current test")
            else:
                test_file = os.path.join(data_root, adv_id, "validation.yzx.txt")
            if not os.path.exists(test_file):
                print(f"  Warning: {test_file} not found, skip")
                continue
            count = 0
            print(f"Processing {adv_id}...")
            for y, z, feats in iter_yzx(test_file):
                feat_str = " ".join([f"{idx}:{val}" for idx, val in feats])
                out_f.write(f"{y}\t{z}\t{feat_str}\t{adv_id}\n")
                count += 1
                total_count += 1
            print(f"  {adv_id}: {count:,} impressions")
    print()
    print(f"  Done: {output_file}, total {total_count:,} impressions, format: y \\t z \\t features \\t adv_id")
    print()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Create unified impression pool (with advertiser ID)")
    ap.add_argument("data_root", help="Data root (advertiser subdirs)")
    ap.add_argument("--output", default="impression_pool.yzx.txt", help="Output pool file path")
    ap.add_argument("--advertiser_ids", nargs="+",
                   default=["1458", "2259", "2261", "2821", "2997", "3358", "3386", "3427", "3476"],
                   help="Advertiser ID list (default: all 9)")
    ap.add_argument("--use_original_test", action="store_true", default=True,
                   help="Use original test (.backup) for pool (default: True)")
    args = ap.parse_args()
    
    create_impression_pool_with_adv_id(
        args.data_root, 
        args.advertiser_ids, 
        args.output, 
        args.use_original_test
    )

