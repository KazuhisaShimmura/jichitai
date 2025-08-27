
from datetime import datetime, timezone
from typing import Iterable
from .base import Harvester
from ..schema import GrantOpportunity
from ..util.text import normalize_whitespace, parse_date_range, extract_money, extract_rate

class PdfHarvester(Harvester):
    def harvest(self) -> Iterable[GrantOpportunity]:
        # This is a lightweight placeholder. For real extraction, install pdfminer.six / pdfplumber.
        urls = self.config["urls"]
        for u in urls:
            resp = self.fetcher.get(u)
            if resp.status_code == 304:
                continue
            resp.raise_for_status()
            text = None
            try:
                import io
                from pdfminer.high_level import extract_text
                text = extract_text(io.BytesIO(resp.content))
            except Exception:
                text = None

            summary = normalize_whitespace((text or "")) if text else None
            start, end = parse_date_range(summary or "") # 全文テキストから期間を抽出
            opp = GrantOpportunity(
                title=self.config.get("title_hint") or "(PDF) " + u.split("/")[-1],
                url=u,
                issuer_name=self.config.get("issuer_name"),
                issuer_level=self.config.get("issuer_level"),
                region_code=self.config.get("region_code"),
                category=None,
                summary=(summary[:500] + "…") if summary and len(summary) > 500 else summary, # 要約は切り詰める
                application_start=start,
                application_end=end,
                amount=extract_money(summary or ""),
                subsidy_rate=extract_rate(summary or ""),
                source_type="PDF",
                fetched_at=datetime.now(timezone.utc).isoformat(),
                raw={"parsed": bool(summary)},
            )
            opp.category = self.classifier((opp.title or "") + " " + (opp.summary or ""))
            yield opp
