"""
Create unified Impression Pool from raw test.log.txt data.
Merge all advertisers' test.log.txt, keep raw format for gender extraction.
Format: same as test.log.txt, append advertiser ID per line if not present.
"""
import os
import argparse
from experiments.config import ExperimentConfig


def create_impression_pool_original(
    data_root: str,
    advertiser_ids: list,
    output_file: str
):
    """Merge all advertisers' test.log.txt into one impression pool. Args: data_root, advertiser_ids, output_file."""
    print("="*70)
    print("Creating unified Impression Pool (raw test.log.txt format)")
    print("="*70)
    print()
    total_count = 0
    with open(output_file, 'w') as out_f:
        first_file = os.path.join(data_root, advertiser_ids[0], "test.log.txt")
        if os.path.exists(first_file):
            with open(first_file, 'r') as f:
                header = f.readline()
                if 'advertiser' in header.lower():
                    out_f.write(header)
                else:
                    out_f.write(header.strip() + '\tadvertiser\n')
        for adv_id in advertiser_ids:
            test_log_file = os.path.join(data_root, adv_id, "test.log.txt")
            if not os.path.exists(test_log_file):
                print(f"  Warning: {test_log_file} not found, skip")
                continue
            count = 0
            print(f"Processing {adv_id}...")
            with open(test_log_file, 'r') as f:
                header_line = f.readline()
                has_advertiser_col = 'advertiser' in header_line.lower()
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    if not has_advertiser_col:
                        parts = line.split('\t')
                        if len(parts) < 27 or (len(parts) >= 26 and parts[25] != adv_id):
                            line = line + f'\t{adv_id}'
                    out_f.write(line + '\n')
                    count += 1
                    total_count += 1
            print(f"  {adv_id}: {count:,} impressions")
    print()
    print(f"  Done: {output_file}, total {total_count:,} impressions")
    print("  Format: raw test.log.txt, all columns (usertag, advertiser).")
    print("  Col 1: click (0/1), Col 14: payprice, Col 26: advertiser, Col 27: usertag (gender 10110=male, 10111=female)")
    print()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Create unified Impression Pool (raw test.log.txt format)")
    ap.add_argument("data_root", nargs='?', default=ExperimentConfig.DATA_ROOT,
                   help="Data root (default: ExperimentConfig.DATA_ROOT)")
    ap.add_argument("--output", default="impression_pool_original.log.txt",
                   help="Output pool file path (default: impression_pool_original.log.txt)")
    ap.add_argument("--advertiser_ids", nargs="+",
                   default=ExperimentConfig.ADVERTISER_IDS,
                   help="Advertiser ID list (default: ExperimentConfig.ADVERTISER_IDS)")
    args = ap.parse_args()
    
    create_impression_pool_original(
        args.data_root,
        args.advertiser_ids,
        args.output
    )

