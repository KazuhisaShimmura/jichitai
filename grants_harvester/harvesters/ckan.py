
from datetime import datetime, timezone
from typing import Iterable
from urllib.parse import urlencode
from .base import Harvester
from ..schema import GrantOpportunity
from ..util.text import normalize_whitespace

class CkanHarvester(Harvester):
    def harvest(self) -> Iterable[GrantOpportunity]:
        base = self.config["base_url"].rstrip("/")
        params = {
            "q": self.config.get("query", "補助金 OR 助成金 OR 公募 OR 募集"),
            "rows": self.config.get("rows", 100),
            "sort": "metadata_modified desc",
        }
        url = f"{base}/api/3/action/package_search?{urlencode(params)}"
        resp = self.fetcher.get(url)
        if resp.status_code == 304:
            return []
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success"):
            return []
        for pkg in data["result"]["results"]:
            title = pkg.get("title") or pkg.get("name") or ""
            notes = normalize_whitespace(pkg.get("notes") or "")
            opp = GrantOpportunity(
                title=title.strip(),
                url=pkg.get("url") or pkg.get("ckan_url") or base,
                issuer_name=self.config.get("issuer_name"),
                issuer_level=self.config.get("issuer_level"),
                region_code=self.config.get("region_code"),
                category=None,
                summary=notes or None,
                application_start=None,
                application_end=None,
                amount=None,
                subsidy_rate=None,
                source_type="CKAN",
                published_at=pkg.get("metadata_created"),
                fetched_at=datetime.now(timezone.utc).isoformat(),
                raw={"ckan": pkg},
            )
            opp.category = self.classifier(opp.title + " " + (opp.summary or ""))
            yield opp
