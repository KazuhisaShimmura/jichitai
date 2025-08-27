
import xml.etree.ElementTree as ET
import re
from datetime import datetime, timezone
from typing import Iterable
from email.utils import parsedate_to_datetime
from .base import Harvester
from ..schema import GrantOpportunity
from ..util.text import normalize_whitespace

class RssHarvester(Harvester):
    def harvest(self) -> Iterable[GrantOpportunity]:
        url = self.config["url"]
        resp = self.fetcher.get(url)
        if resp.status_code == 304:
            return []
        resp.raise_for_status()
        xml = ET.fromstring(resp.content)
        channel = xml.find("channel")
        # RSS 2.0, 1.0, Atomなど様々な形式に対応するため、名前空間を無視してitem/entryを探す
        items = xml.findall(".//{*}item")
        if not items:
            items = xml.findall(".//{*}entry") # Atomフィードの場合

        include_patterns = self.config.get("include_patterns", [])
        exclude_patterns = self.config.get("exclude_patterns", [])
        for it in items:
            # 名前空間を考慮せずに要素を取得するため、ワイルドカードを使用
            title_node = it.find("{*}title")
            title = (title_node.text or "").strip() if title_node is not None else ""

            link_node = it.find("{*}link")
            link = ""
            if link_node is not None:
                # Atomフィードではlinkは空要素でhref属性にURLがある
                link = (link_node.get("href") or link_node.text or "").strip()

            # descriptionはキーワードフィルタリングにのみ使用し、保存はしない
            # Atomではsummaryの場合もある
            desc_node = it.find("{*}description") or it.find("{*}summary")
            desc = normalize_whitespace(desc_node.text or "") if desc_node is not None else ""

            # キーワードフィルタリング (タイトルとdescriptionの両方を対象)
            text_to_check = title + " " + desc
            if include_patterns and not any(re.search(p, text_to_check) for p in include_patterns):
                continue
            if exclude_patterns and any(re.search(p, text_to_check) for p in exclude_patterns):
                continue

            # 日付取得の互換性を向上 (RSS 2.0: pubDate, RSS 1.0: dc:date, Atom: published/updated)
            pub_date_node = it.find("{*}pubDate") or it.find("{http://purl.org/dc/elements/1.1/}date") or it.find("{*}published") or it.find("{*}updated")
            published_at_str = pub_date_node.text if pub_date_node is not None else None
            published_at_dt = None
            if published_at_str:
                try:
                    published_at_dt = parsedate_to_datetime(published_at_str)
                except Exception:
                    published_at_dt = None

            opp = GrantOpportunity(
                title=title or link, # タイトルが空の場合、リンクをタイトルとして使用
                url=link or url,
                issuer_name=self.config.get("issuer_name"),
                issuer_level=self.config.get("issuer_level"),
                region_code=self.config.get("region_code"),
                category=None,  # filled by classifier later
                summary=None,  # Do not store description from RSS
                application_start=None, # Do not parse from RSS description
                application_end=None, # Do not parse from RSS description
                amount=None, # Do not parse from RSS description
                subsidy_rate=None, # Do not parse from RSS description
                source_type="RSS",
                published_at=published_at_dt.isoformat() if published_at_dt else None,
                fetched_at=datetime.now(timezone.utc).isoformat(),
                raw=None # Do not store raw data
            )
            # Classify using both title and description for better accuracy
            cat = self.classifier(text_to_check)
            opp.category = cat
            yield opp
