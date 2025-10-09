# core/dispatcher.py
from parsers.sparkasse_parser import SparkasseParser
from parsers.ing_parser import INGParser
from parsers.db_parser import DBParser

def get_parser(bank_name: str):
    bank_name = bank_name.lower()
    if bank_name == "sparkasse":
        return SparkasseParser()
    elif bank_name == "ing":
        return INGParser()
    elif bank_name in ["db", "deutschebank", "deutsche bank", "deutsche_bank"]:
        return DBParser()
    else:
        raise ValueError(f"Bank '{bank_name}' wird nicht unterstützt")
