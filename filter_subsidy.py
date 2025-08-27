# -*- coding: utf-8 -*-
"""
Filter subsidy/grant records from a CSV and emit a filtered CSV (full columns)
and a JA-shaped CSV for BI.
Usage:
  python filter_subsidy.py --in input.csv --out filtered.csv --out-ja filtered_ja.csv
"""
import re
import argparse
import pandas as pd
from pathlib import Path

def read_csv_robust(path: str) -> pd.DataFrame:
    """Tries to read a CSV with multiple common Japanese encodings."""
    for enc in ["utf-8", "utf-8-sig", "cp932", "shift_jis"]:
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            continue
    # Fallback with error ignoring
    return pd.read_csv(path, encoding="utf-8", errors="ignore")

def find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Finds the first matching column name from a list of candidates."""
    return next((c for c in candidates if c in df.columns), None)

def combine_period(s, e) -> str:
    """Combines start and end dates into a string, handling missing values."""
    s_str = str(s).split("T")[0] if pd.notna(s) else ""
    e_str = str(e).split("T")[0] if pd.notna(e) else ""
    if s_str and e_str:
        return f"{s_str} ～ {e_str}"
    return s_str or e_str

def main():
    ap = argparse.ArgumentParser(description="Filters a CSV of grants/subsidies.")
    ap.add_argument("--in", dest="in_path", required=True, help="Path to the input CSV file.")
    ap.add_argument("--out", dest="out_path", required=True, help="Path for the filtered full-column CSV.")
    ap.add_argument("--out-ja", dest="out_ja_path", required=True, help="Path for the BI-friendly JA-shaped CSV.")
    args = ap.parse_args()

    in_path = Path(args.in_path)
    if not in_path.exists():
        print(f"Error: Input file not found at {in_path}")
        return

    df = read_csv_robust(in_path)

    # Define filtering patterns
    subsidy_pat = re.compile(r"(補助金|助成金|助成|支援金|交付金|給付金|補助事業|支援事業|補助制度|助成制度|奨励金)")
    exclude_pat = re.compile(r"(審査結果|結果公表|交付決定|終了|募集終了|中止|完了|取消|停止)")

    # Find relevant columns dynamically
    title_col = find_column(df, ["title", "補助金名", "名称", "件名", "Title"])
    if not title_col:
        print("エラー: 'title'に相当する列（例: 「補助金名」「名称」）が見つかりませんでした。入力CSVファイルを確認してください。")
        return
    summary_col = find_column(df, ["summary", "概要", "説明", "description"])

    # --- Filtering ---
    # Combine title and summary for searching. This is more efficient than iterating row by row.
    text_to_search = df[title_col].astype(str)
    if summary_col:
        # .fillna('') handles cases where the summary column has empty values.
        text_to_search += " " + df[summary_col].fillna('').astype(str)

    # Use vectorized string operations which are significantly faster than df.apply().
    is_subsidy_mask = text_to_search.str.contains(subsidy_pat, regex=True, na=False)
    is_excluded_mask = text_to_search.str.contains(exclude_pat, regex=True, na=False)

    df_sub = df[is_subsidy_mask & ~is_excluded_mask].copy()
    print(f"Found {len(df_sub)} subsidy/grant records.")

    if df_sub.empty:
        print("No records left after filtering. Output files will be empty.")
    
    # --- Create the BI-friendly JA DataFrame ---
    
    # Find columns for the JA dataframe
    url_col = find_column(df_sub, ["url", "詳細URL"])
    issuer_col = find_column(df_sub, ["issuer_name", "対象地域"])
    amount_col = find_column(df_sub, ["amount", "補助金上限額"])
    rate_col = find_column(df_sub, ["subsidy_rate", "補助率"])
    start_col = find_column(df_sub, ["application_start"])
    end_col = find_column(df_sub, ["application_end"])

    # Build the new DataFrame in a pandas-idiomatic way
    df_ja = pd.DataFrame({
        "補助金名": df_sub[title_col],  # title_col is guaranteed to exist due to the check above
        "補助金上限額": df_sub[amount_col] if amount_col and amount_col in df_sub.columns else "",
        "補助率": df_sub[rate_col] if rate_col and rate_col in df_sub.columns else "",
        "対象地域": df_sub[issuer_col] if issuer_col and issuer_col in df_sub.columns else "",
        "従業員数の上限": "",  # Placeholder as in the original script
        "募集期間": df_sub.apply(lambda row: combine_period(row.get(start_col), row.get(end_col)), axis=1),
        "詳細URL": df_sub[url_col] if url_col and url_col in df_sub.columns else ""
    })

    # Save the output files
    out_path = Path(args.out_path)
    out_ja_path = Path(args.out_ja_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    df_sub.to_csv(out_path, index=False, encoding="utf-8-sig")
    df_ja.to_csv(out_ja_path, index=False, encoding="utf-8-sig")

    print(f"Successfully wrote filtered full data to: {out_path}")
    print(f"Successfully wrote BI-friendly data to: {out_ja_path}")

if __name__ == "__main__":
    main()