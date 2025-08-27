
from typing import Dict
import re

def score_text(text: str, weights: Dict[str, float]) -> float:
    if not text: return 0.0
    s = 0.0
    for kw, w in weights.items():
        if re.search(kw, text, flags=re.IGNORECASE):
            s += w
    return s

def choose_category(text: str, cat_weights: Dict[str, Dict[str, float]], default: str="other") -> str:
    best_cat = default
    best_score = 0.0
    for cat, w in cat_weights.items():
        sc = score_text(text, w)
        if sc > best_score:
            best_score = sc
            best_cat = cat
    return best_cat
