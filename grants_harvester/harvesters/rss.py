
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Iterable
from .base import Harvester
from ..schema import GrantOpportunity
from ..util.text import normalize_whitespace
import re

class RssHarvester(Harvester):
    def harvest(self) -> Iterable[GrantOpportunity]:
        url = self.config["url"]
        resp = self.fetcher.get(url)
        if resp.status_code == 304:
            return []
        resp.raise_for_status()
        xml = ET.fromstring(resp.content)
        channel = xml.find("channel")
        items = channel.findall("item") if channel is not None else xml.findall(".//item")
        include_patterns = self.config.get("include_patterns", [])
        exclude_patterns = self.config.get("exclude_patterns", [])
        for it in items:
            title = (it.findtext("title") or "").strip()
            link = (it.findtext("link") or "").strip()
            desc = normalize_whitespace(it.findtext("description") or "")
            if include_patterns and not any(re.search(p, title+desc) for p in include_patterns):
                continue
            if exclude_patterns and any(re.search(p, title+desc) for p in exclude_patterns):
                continue

            opp = GrantOpportunity(
                title=title,
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
                published_at=None,
                fetched_at=datetime.now(timezone.utc).isoformat(),
                raw=None # Do not store raw data
            )
            # classify
            # Classify by title only, as summary is not stored.
            cat = self.classifier(opp.title)
            opp.category = cat
            yield opp
