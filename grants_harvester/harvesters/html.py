
import re
from urllib.parse import urljoin
from datetime import datetime, timezone
from typing import Iterable
from .base import Harvester
from ..schema import GrantOpportunity
from ..util.text import normalize_whitespace, parse_date_range, extract_money, extract_rate

class HtmlHarvester(Harvester):
    def harvest(self) -> Iterable[GrantOpportunity]:
        urls = self.config["urls"]
        incl = self.config.get("include_patterns", [])
        excl = self.config.get("exclude_patterns", [])
        for base_url in urls:
            resp = self.fetcher.get(base_url)
            if resp.status_code == 304:
                continue
            resp.raise_for_status()
            html = resp.text
            page_title = self._extract_title(html) or base_url
            text = normalize_whitespace(self._extract_text(html))

            # 1) Emit page itself if it matches
            if self._matches(text + " " + page_title, incl, excl):
                opp = GrantOpportunity(
                    title=page_title.strip(),
                    url=base_url,
                    issuer_name=self.config.get("issuer_name"),
                    issuer_level=self.config.get("issuer_level"),
                    region_code=self.config.get("region_code"),
                    category=None,
                    summary=(text[:500] + "…") if len(text) > 500 else text,
                    application_start=None,
                    application_end=None,
                    amount=extract_money(text),
                    subsidy_rate=extract_rate(text),
                    source_type="HTML",
                    published_at=None,
                    fetched_at=datetime.now(timezone.utc).isoformat(),
                    raw={"html_len": len(html)},
                )
                opp.category = self.classifier(opp.title + " " + (opp.summary or ""))
                yield opp

            # 2) Extract <a> links whose text matches include_patterns
            for (href, anchor_text) in self._extract_links(html):
                if not href:
                    continue
                full = urljoin(base_url, href)
                if not self._matches(anchor_text, incl, excl):
                    continue
                opp = GrantOpportunity(
                    title=normalize_whitespace(anchor_text) or full,
                    url=full,
                    issuer_name=self.config.get("issuer_name"),
                    issuer_level=self.config.get("issuer_level"),
                    region_code=self.config.get("region_code"),
                    category=None,
                    summary=None,
                    application_start=None,
                    application_end=None,
                    amount=None,
                    subsidy_rate=None,
                    source_type="HTML",
                    fetched_at=datetime.now(timezone.utc).isoformat(),
                    raw={"from": base_url},
                )
                opp.category = self.classifier(opp.title)
                yield opp

    def _matches(self, text: str, incl, excl):
        if incl:
            ok = any(re.search(p, text) for p in incl)
            if not ok: return False
        if excl and any(re.search(p, text) for p in excl):
            return False
        return True

    def _extract_title(self, html: str):
        m = re.search(r"<title>(.*?)</title>", html, flags=re.IGNORECASE|re.DOTALL)
        if m:
            return re.sub(r"\s+", " ", m.group(1)).strip()
        h1 = re.search(r"<h1[^>]*>(.*?)</h1>", html, flags=re.IGNORECASE|re.DOTALL)
        return re.sub(r"\s+", " ", h1.group(1)).strip() if h1 else None

    def _extract_text(self, html: str):
        text = re.sub(r"(?is)<script.*?>.*?</script>", "", html)
        text = re.sub(r"(?is)<style.*?>.*?</style>", "", text)
        text = re.sub(r"(?is)<[^>]+>", " ", text)
        return text

    def _extract_links(self, html: str):
        # Very simple anchor extractor
        anchors = re.findall(r'<a\s+[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, flags=re.IGNORECASE|re.DOTALL)
        cleaned = []
        for href, inner in anchors:
            # Remove tags inside anchor
            t = re.sub(r"(?is)<[^>]+>", " ", inner)
            t = re.sub(r"\s+", " ", t).strip()
            cleaned.append((href, t))
        return cleaned
