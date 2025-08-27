
import json, os
from typing import Dict, Any, List
from datetime import datetime, timezone

from .schema import GrantOpportunity
from .util.fetch import HttpFetcher
from .util.classify import choose_category

from .harvesters.rss import RssHarvester
from .harvesters.ckan import CkanHarvester
from .harvesters.sitemap import SitemapHarvester
from .harvesters.html import HtmlHarvester
from .harvesters.pdf import PdfHarvester

HARVESTER_REGISTRY = {
    "rss": RssHarvester,
    "ckan": CkanHarvester,
    "sitemap": SitemapHarvester,
    "html": HtmlHarvester,
    "pdf": PdfHarvester,
}

def make_classifier(keywords_conf: Dict[str, Dict[str, float]]):
    from .util.classify import choose_category as _choose
    def _clf(text: str) -> str:
        return _choose(text or "", keywords_conf, default="other")
    return _clf

def load_yaml(path: str) -> Dict[str, Any]:
    import yaml  # requires pyyaml (install locally)
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def run_pipeline(config_path: str, keywords_path: str, out_dir: str) -> str:
    config = load_yaml(config_path)
    keywords_conf = load_yaml(keywords_path)

    fetcher = HttpFetcher(min_interval_sec=config.get("min_interval_sec", 1.0))
    classifier = make_classifier(keywords_conf.get("categories", {}))

    results: List[GrantOpportunity] = []
    for src in config.get("sources", []):
        typ = src.get("type")
        Harv = HARVESTER_REGISTRY.get(typ)
        if not Harv:
            print(f"[WARN] unknown harvester type: {typ}")
            continue
        harvester = Harv(fetcher, classifier, src)
        try:
            for opp in harvester.harvest():
                results.append(opp)
        except Exception as e:
            print(f"[ERROR] {typ} failed for {src.get('name','(no name)')}: {e}")

    # Deduplicate by URL + title
    seen = set()
    deduped = []
    for r in results:
        key = (r.url or "", r.title or "")
        if key in seen: 
            continue
        seen.add(key)
        deduped.append(r)

    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_jsonl = os.path.join(out_dir, f"grants_{ts}.jsonl")
    with open(out_jsonl, "w", encoding="utf-8") as f:
        for r in deduped:
            f.write(json.dumps(r.to_dict(), ensure_ascii=False) + "\n")

    # also write CSV (minimal)

    # also write JA CSV matching user's format
    try:
        import csv
        out_csv_ja = os.path.join(out_dir, f"grants_{ts}_ja.csv")
        with open(out_csv_ja, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            # Columns: 補助金名, 補助金上限額, 補助率, 対象地域, 従業員数の上限, 募集期間, 詳細URL, 取得日時
            w.writerow(["補助金名","補助金上限額","補助率","対象地域","従業員数の上限","募集期間","詳細URL", "取得日時"])
            for r in deduped:
                period = None
                if r.application_start or r.application_end:
                    s = r.application_start or ""
                    e = r.application_end or ""
                    if s or e:
                        period = f"{s} ～ {e}".strip(" ～ ")
                w.writerow([
                    r.title or "",
                    r.amount or "",
                    r.subsidy_rate or "",
                    r.issuer_name or "",
                    "",  # 従業員数の上限は未取得のため空欄
                    period or "",
                    r.url or "",
                    r.fetched_at or ""
                ])
    except Exception as e:
        print("[WARN] JA CSV export failed:", e)
    try:
        import csv
        out_csv = os.path.join(out_dir, f"grants_{ts}.csv")
        with open(out_csv, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["title","url","issuer_name","issuer_level","region_code","category",
                        "application_start","application_end","amount","subsidy_rate","published_at","fetched_at"])
            for r in deduped:
                w.writerow([r.title, r.url, r.issuer_name, r.issuer_level, r.region_code, r.category,
                            r.application_start, r.application_end, r.amount, r.subsidy_rate, r.published_at, r.fetched_at])
    except Exception as e:
        print("[WARN] CSV export failed:", e)

    return out_jsonl
