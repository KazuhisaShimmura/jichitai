
import re, xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Iterable
from .base import Harvester
from ..schema import GrantOpportunity

class SitemapHarvester(Harvester):
    def harvest(self) -> Iterable[GrantOpportunity]:
        base = self.config["url"].rstrip("/")
        sm_url = base + "/sitemap.xml"
        resp = self.fetcher.get(sm_url)
        if resp.status_code == 304:
            return []
        resp.raise_for_status()
        xml = ET.fromstring(resp.content)
        locs = [e.text for e in xml.findall(".//{*}loc") if e.text]
        inc = self.config.get("include_patterns", [])
        exc = self.config.get("exclude_patterns", [])
        for loc in locs:
            if inc and not any(re.search(p, loc) for p in inc): 
                continue
            if exc and any(re.search(p, loc) for p in exc): 
                continue
            opp = GrantOpportunity(
                title="(ページ候補) " + loc,
                url=loc,
                issuer_name=self.config.get("issuer_name"),
                issuer_level=self.config.get("issuer_level"),
                region_code=self.config.get("region_code"),
                category=None,
                summary=None,
                source_type="SITEMAP",
                fetched_at=datetime.now(timezone.utc).isoformat(),
                raw={},
            )
            opp.category = self.classifier(opp.title)
            yield opp
