# core/exporter.py
import pandas as pd
from typing import List, Dict

def export_to_excel(transactions: List[Dict], file_path: str):
    if transactions:
        df = pd.DataFrame(transactions)
        df.to_excel(file_path, index=False)
