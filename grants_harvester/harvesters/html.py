
import re
from urllib.parse import urljoin
from datetime import datetime, timezone
from typing import Iterable
from email.utils import parsedate_to_datetime
from bs4 import BeautifulSoup
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
            soup = BeautifulSoup(html, 'html.parser')
            page_title = self._extract_title(soup) or base_url
            text = self._extract_text(soup)

            # 1) Emit page itself if it matches
            if self._matches(text + " " + page_title, incl, excl):
                start, end = parse_date_range(text)

                published_at = None
                if resp.headers.get("Last-Modified"):
                    try:
                        published_at = parsedate_to_datetime(resp.headers.get("Last-Modified")).isoformat()
                    except Exception:
                        pass

                opp = GrantOpportunity(
                    title=page_title.strip(),
                    url=base_url,
                    issuer_name=self.config.get("issuer_name"),
                    issuer_level=self.config.get("issuer_level"),
                    region_code=self.config.get("region_code"),
                    category=None,
                    summary=(text[:500] + "…") if len(text) > 500 else text,
                    application_start=start,
                    application_end=end,
                    amount=extract_money(text),
                    subsidy_rate=extract_rate(text),
                    source_type="HTML",
                    published_at=published_at,
                    fetched_at=datetime.now(timezone.utc).isoformat(),
                    raw={"html_len": len(html)},
                )
                opp.category = self.classifier(opp.title + " " + (opp.summary or ""))
                yield opp

            # 2) Extract <a> links whose text matches include_patterns
            for (href, anchor_text) in self._extract_links(soup):
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

    def _extract_title(self, soup: BeautifulSoup):
        if soup.title and soup.title.string:
            return normalize_whitespace(soup.title.string)
        h1 = soup.find('h1')
        if h1:
            return normalize_whitespace(h1.get_text())
        return None

    def _extract_text(self, soup: BeautifulSoup):
        for script_or_style in soup(["script", "style"]):
            script_or_style.decompose()
        return normalize_whitespace(soup.get_text())

    def _extract_links(self, soup: BeautifulSoup):
        cleaned = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            text = normalize_whitespace(a.get_text())
            if href:
                cleaned.append((href, text))
        return cleaned
