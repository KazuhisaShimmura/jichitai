
from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict

@dataclass
class GrantOpportunity:
    title: str
    url: str
    issuer_name: Optional[str] = None
    issuer_level: Optional[str] = None  # 'prefecture' | 'municipality' | 'national' | 'agency'
    region_code: Optional[str] = None   # JIS X 0401/0402 etc.
    category: Optional[str] = None      # 'medical' | 'care' | 'dx' | 'other'
    summary: Optional[str] = None
    application_start: Optional[str] = None  # ISO date
    application_end: Optional[str] = None    # ISO date
    amount: Optional[str] = None             # human-readable (e.g., '最大1,000万円')
    subsidy_rate: Optional[str] = None       # e.g., '2/3', '1/2', '～3/4', '50%'
    audience: Optional[str] = None           # 対象（病院／介護事業者／自治体 等）
    contact: Optional[str] = None
    attachment_urls: List[str] = field(default_factory=list)
    source_type: Optional[str] = None        # 'RSS' | 'CKAN' | 'SITEMAP' | 'HTML' | 'PDF'
    published_at: Optional[str] = None       # ISO datetime if available
    fetched_at: Optional[str] = None
    raw: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)
