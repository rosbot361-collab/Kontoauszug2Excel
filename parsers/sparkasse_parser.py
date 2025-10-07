# parsers/sparkasse_parser.py
import pdfplumber
from typing import List, Dict, Any
from .base_parser import BaseParser

OPTIMAL_SETTINGS = {
    "vertical_strategy": "lines", 
    "horizontal_strategy": "text", 
    "snap_y_tolerance": 8,
    "join_tolerance": 3,
}

class SparkasseParser(BaseParser):
    def parse(self, pdf_path: str) -> List[Dict[str, Any]]:
        result = []
        current_transaction = {"Datum": "", "Erläuterung": "", "Betrag": None, "Bemerkung_List": []}

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    table = page.extract_table(table_settings=OPTIMAL_SETTINGS)
                    if not table or len(table) < 2:
                        continue
                    for row in table[1:]:
                        if not row or len(row) < 3:
                            continue
                        dates = str(row[0]).split("\n") if row[0] else []
                        descs = str(row[1]).split("\n") if row[1] else []
                        amounts = str(row[2]).split("\n") if row[2] else []

                        max_len = max(len(dates), len(descs), len(amounts))
                        dates += [""] * (max_len - len(dates))
                        descs += [""] * (max_len - len(descs))
                        amounts += [""] * (max_len - len(amounts))

                        for d, desc, amt in zip(dates, descs, amounts):
                            d = d.strip()
                            desc = desc.strip()
                            amt_clean = None
                            if amt and amt.strip():
                                try:
                                    amt_clean = float(amt.replace(".", "").replace(",", "."))
                                except ValueError:
                                    pass

                            # Start new transaction
                            if d and amt_clean is not None:
                                if current_transaction["Datum"]:
                                    result.append({
                                        "Datum": current_transaction["Datum"],
                                        "Erläuterung": current_transaction["Erläuterung"],
                                        "Betrag EUR": current_transaction["Betrag"],
                                        "Bemerkung": " | ".join(current_transaction["Bemerkung_List"])
                                    })
                                current_transaction = {"Datum": d, "Erläuterung": desc, "Betrag": amt_clean, "Bemerkung_List": []}

                            # Continuation line
                            elif not d and amt_clean is None and desc:
                                if current_transaction["Datum"]:
                                    current_transaction["Bemerkung_List"].append(desc)

                # Final append
                if current_transaction["Datum"]:
                    result.append({
                        "Datum": current_transaction["Datum"],
                        "Erläuterung": current_transaction["Erläuterung"],
                        "Betrag EUR": current_transaction["Betrag"],
                        "Bemerkung": " | ".join(current_transaction["Bemerkung_List"])
                    })

            return result
        except Exception as e:
            print(f"Error processing {pdf_path}: {e}")
            return []
