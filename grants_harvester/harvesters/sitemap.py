
import re, xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Iterable, List
from .base import Harvester
from ..schema import GrantOpportunity

class SitemapHarvester(Harvester):
    def harvest(self) -> Iterable[GrantOpportunity]:
        initial_sitemap_url = self.config["url"]
        locs = self._get_all_page_urls([initial_sitemap_url])

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

    def _get_all_page_urls(self, sitemap_urls: List[str]) -> List[str]:
        """Recursively fetches sitemaps and extracts all page URLs."""
        all_locs: List[str] = []
        queue = sitemap_urls[:]
        processed_sitemaps = set()

        while queue:
            sitemap_url = queue.pop(0)
            if sitemap_url in processed_sitemaps:
                continue
            
            print(f"[INFO] Processing sitemap: {sitemap_url}")
            processed_sitemaps.add(sitemap_url)
            
            try:
                resp = self.fetcher.get(sitemap_url)
                if resp.status_code == 304: continue
                resp.raise_for_status()
                xml = ET.fromstring(resp.content)
                
                # Check if it's a sitemap index file
                if xml.tag.endswith("sitemapindex"):
                    sitemap_locs = [e.text for e in xml.findall(".//{*}sitemap/{*}loc") if e.text]
                    queue.extend(sitemap_locs)
                # Or a regular sitemap file
                elif xml.tag.endswith("urlset"):
                    page_locs = [e.text for e in xml.findall(".//{*}url/{*}loc") if e.text]
                    all_locs.extend(page_locs)
            except Exception as e:
                print(f"[WARN] Failed to process sitemap {sitemap_url}: {e}")
        
        print(f"[INFO] Found {len(all_locs)} page URLs from sitemaps.")
        return all_locs
