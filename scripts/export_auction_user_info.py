"""Export per-round impression (user/auction) info from saved round_history JSON to CSV."""
import os
import sys
import csv
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.save_round_history import load_round_history


def _gender_from_usertag(usertag_str):
    if not usertag_str or not isinstance(usertag_str, str):
        return ""
    tags = usertag_str.strip().split(",")
    if "10110" in tags:
        return "male"
    if "10111" in tags:
        return "female"
    return "unknown"


def export_rounds_to_csv(round_history, output_path: str):
    """Export each round's impression (user/auction) from round_history to CSV. Row = one round; cols = round, winner, payment, gender_derived + impression columns (by namecol)."""
    if not round_history:
        print("round_history is empty, cannot export")
        return

    namecol = None
    for rec in round_history:
        imp = rec.get("impression")
        if imp and imp.get("namecol") and imp.get("raw_line"):
            namecol = imp["namecol"]
            break
    if not namecol:
        namecol = {"round": 0, "winner": 1, "payment": 2}

    sorted_cols = sorted(namecol.items(), key=lambda x: x[1])
    col_names = [c[0] for c in sorted_cols]
    header = ["round", "winner", "payment", "gender_derived"] + col_names

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for rec in round_history:
            round_num = rec.get("round", "")
            winner = rec.get("winner") or ""
            payment = rec.get("payment")
            payment_str = "" if payment is None else str(payment)
            imp = rec.get("impression") or {}
            raw_line = imp.get("raw_line") or []
            nc = imp.get("namecol") or {}
            # Derive gender from usertag column
            usertag_col = nc.get("usertag")
            usertag_val = ""
            if usertag_col is not None and usertag_col < len(raw_line):
                usertag_val = raw_line[usertag_col] if isinstance(raw_line[usertag_col], str) else str(raw_line[usertag_col])
            gender_derived = _gender_from_usertag(usertag_val)
            row_vals = [round_num, winner, payment_str, gender_derived]
            for col_name, idx in sorted_cols:
                val = raw_line[idx] if idx < len(raw_line) else ""
                row_vals.append(val)
            writer.writerow(row_vals)

    print(f"  Exported {len(round_history)} rounds to: {output_path}")


def main():
    ap = argparse.ArgumentParser(description="Export per-round impression (user) info from round_history JSON to CSV")
    ap.add_argument("--history", default=None, help="round_history JSON path (default: logs/gender_fairness_baseline_*.json)")
    ap.add_argument("--output", default="logs/auction_rounds_user_info.csv", help="Output CSV path")
    args = ap.parse_args()
    history_file = args.history or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "logs",
        "gender_fairness_baseline_20260204_163828.json",
    )
    if not os.path.isfile(history_file):
        print(f"File not found: {history_file}")
        print("Use --history to point to your round_history JSON")
        sys.exit(1)
    round_history, metadata = load_round_history(history_file)
    export_rounds_to_csv(round_history, args.output)


if __name__ == "__main__":
    main()
