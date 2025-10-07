# core/dispatcher.py
from parsers.sparkasse_parser import SparkasseParser
# später: from parsers.commerzbank_parser import CommerzbankParser

def get_parser(bank_name: str):
    bank_name = bank_name.lower()
    if bank_name == "sparkasse":
        return SparkasseParser()
    # elif bank_name == "commerzbank":
    #     return CommerzbankParser()
    else:
        raise ValueError(f"Bank '{bank_name}' wird nicht unterstützt")
