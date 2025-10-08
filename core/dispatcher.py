# core/dispatcher.py
from parsers.sparkasse_parser import SparkasseParser
from parsers.ing_parser import INGParser

def get_parser(bank_name: str):
    bank_name = bank_name.lower()
    if bank_name == "sparkasse":
        return SparkasseParser()
    elif bank_name == "ing":
        return INGParser()
    else:
        raise ValueError(f"Bank '{bank_name}' wird nicht unterstützt")
