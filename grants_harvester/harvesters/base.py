
from abc import ABC, abstractmethod
from typing import Iterable, Dict, Any
from ..schema import GrantOpportunity

class Harvester(ABC):
    def __init__(self, fetcher, classifier, config: Dict[str, Any]):
        self.fetcher = fetcher
        self.classifier = classifier
        self.config = config

    @abstractmethod
    def harvest(self) -> Iterable[GrantOpportunity]:
        ...
