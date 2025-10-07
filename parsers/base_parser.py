# parsers/base_parser.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseParser(ABC):
    @abstractmethod
    def parse(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Nimmt einen PDF-Pfad, extrahiert Transaktionen und gibt sie
        als Liste von Dictionaries zurück.
        """
        pass
