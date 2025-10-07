# main.py
import argparse
from core.dispatcher import get_parser
from core.exporter import export_to_excel

def main():
    parser = argparse.ArgumentParser(description="PDF Kontoauszug Parser")
    parser.add_argument("--bank", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    parser_instance = get_parser(args.bank)
    transactions = parser_instance.parse(args.input)
    export_to_excel(transactions, args.output)
    print(f"✅ Exported {len(transactions)} transactions to {args.output}")

if __name__ == "__main__":
    main()
