"""
Deutsche Bank Kontoauszug Parser
Extrahiert Transaktionen aus Deutsche Bank PDF-Kontoauszügen.
"""

import pdfplumber
import re
from typing import List, Dict, Any, Optional, Tuple
from .base_parser import BaseParser
from datetime import datetime



def parse_deutsche_bank_pdf(pdf_path: str, debug: bool = False) -> List[Dict[str, Any]]:
    """
    Parst einen Deutsche Bank Kontoauszug und extrahiert ALLE Transaktionen.

    Args:
        pdf_path: Pfad zur PDF-Datei
        debug: Aktiviert Debug-Ausgaben

    Returns:
        Liste von Transaktions-Dictionaries
    """
    transactions = []

    with pdfplumber.open(pdf_path) as pdf:
        if debug:
            print(f"\n=== PDF hat {len(pdf.pages)} Seiten ===\n")

        for page_number, page in enumerate(pdf.pages, start=1):
            if debug:
                print(f"\n{'='*60}")
                print(f"Verarbeite Seite {page_number}/{len(pdf.pages)}")
                print(f"{'='*60}\n")

            text = page.extract_text()
            if not text:
                if debug:
                    print("  ✗ Kein Text auf dieser Seite")
                continue

            lines = text.split('\n')

            # Find transaction area (starts after "Buchung Valuta Vorgang")
            transaction_area_start = -1
            for i, line in enumerate(lines):
                if 'Buchung' in line and 'Valuta' in line and 'Vorgang' in line:
                    transaction_area_start = i + 1
                    if debug:
                        print(f"  ✓ Header gefunden in Zeile {i}, starte Scan ab Zeile {transaction_area_start}")
                    break

            if transaction_area_start == -1:
                if debug:
                    print("  ✗ Kein Transaction-Header gefunden")
                continue

            # Parse all transactions
            i = transaction_area_start
            page_transaction_count = 0
            while i < len(lines):
                line = lines[i].strip()

                # Stop at page footer
                if is_page_footer(line):
                    if debug:
                        print(f"  ! Reached page footer at line {i}")
                    break

                # Check if this is a transaction start (line with date and amount)
                if is_transaction_start(line):
                    if debug:
                        print(f"  → Line {i}: Found transaction start: {line[:60]}")
                    transaction, lines_consumed = parse_full_transaction(lines, i, debug)
                    if transaction:
                        transactions.append(transaction)
                        page_transaction_count += 1
                        if debug:
                            print(f"✓ {transaction['Buchungstag']} | "
                                  f"{transaction['Vorgang'][:50]:50s} | "
                                  f"{transaction['Betrag EUR']:>10.2f} €")
                    i += lines_consumed
                else:
                    i += 1

            if debug:
                print(f"  ✓ {page_transaction_count} Transaktionen auf dieser Seite")

    if debug:
        print(f"\n{'='*60}")
        print(f"✓ {len(transactions)} Transaktionen extrahiert")
        print(f"{'='*60}\n")

    return transactions


def is_transaction_start(line: str) -> bool:
    """Prüft ob eine Zeile eine Transaktion startet (Datum + Betrag)."""
    if not line:
        return False

    # Must start with date (DD.MM.)
    if not re.match(r'^\d{2}\.\d{2}\.', line):
        return False

    # Must contain an amount at the end (+/-X,XX)
    if not re.search(r'[+-]\s*\d{1,3}(?:\.\d{3})*,\d{2}$', line):
        return False

    return True


def is_page_footer(line: str) -> bool:
    """Prüft ob eine Zeile zum Seiten-Footer gehört."""
    footer_keywords = [
        'auszug', 'seite', 'iban de76',
        'neuer saldo', 'alter saldo', 'wichtige hinweise',
        'bitte erheben', 'filialnummer', 'kontonummer',
        'bic (swift)'
    ]
    line_lower = line.lower()

    if 'seite' in line_lower and ('von' in line_lower or 'iban' in line_lower):
        return True

    if line_lower.startswith('iban de'):
        return True

    if any(keyword in line_lower for keyword in footer_keywords):
        return True

    return False


def parse_full_transaction(lines: List[str], start_idx: int, debug: bool = False) -> Tuple[Optional[Dict[str, Any]], int]:
    """
    Parst eine vollständige Transaktion ab der Startzeile.

    Returns:
        (transaction_dict, number_of_lines_consumed)
    """
    try:
        first_line = lines[start_idx].strip()

        # Extract dates (DD.MM.)
        dates = re.findall(r'\d{2}\.\d{2}\.', first_line)
        if len(dates) < 1:
            return None, 1

        buchungstag = dates[0]
        valuta = dates[1] if len(dates) > 1 else buchungstag

        # Extract amount from end
        betrag_match = re.search(r'([+-])\s*(\d{1,3}(?:\.\d{3})*,\d{2})$', first_line)
        if not betrag_match:
            return None, 1

        sign = betrag_match.group(1)
        amount_str = betrag_match.group(2).replace('.', '').replace(',', '.')
        betrag = float(amount_str) * (1 if sign == '+' else -1)

        # Extract description (between date(s) and amount)
        desc_start = first_line.find(dates[-1]) + len(dates[-1])
        desc_end = betrag_match.start()
        beschreibung = first_line[desc_start:desc_end].strip()

        # Remove date prefix (if present)
        if re.match(r'^\d{2}\.\d{2}', beschreibung):
            beschreibung = beschreibung[6:].strip()

        beschreibung = clean_text(beschreibung)

        # --- Dynamic year detection (handles statements spanning multiple years) ---

        # Fallback: current calendar year
        year = datetime.now().year

        # Try to find an explicit year in the next line (e.g. "2024", "2025")
        next_idx = start_idx + 1
        if next_idx < len(lines):
            next_line = lines[next_idx].strip()
            year_match = re.search(r'(20\d{2})', next_line)
            if year_match:
                year = int(year_match.group(1))

        # Extract month and day from first date in 'dates' list (e.g. "28.12.")
        month_match = re.match(r'(\d{2})\.(\d{2})\.', dates[0])
        if month_match:
            day, month = int(month_match.group(1)), int(month_match.group(2))

            # Use function-scoped persistent variables
            # (or you can store them in class attributes if using OOP)
            if not hasattr(parse_full_transaction, "last_month"):
                parse_full_transaction.last_month = month
                parse_full_transaction.last_year = year

            # Detect year rollover (e.g. Dec → Jan)
            if month < parse_full_transaction.last_month:
                parse_full_transaction.last_year += 1  # increment year
            else:
                # keep same year
                parse_full_transaction.last_year = parse_full_transaction.last_year

            parse_full_transaction.last_month = month
            year = parse_full_transaction.last_year

        # Append year to the dates
        buchungstag = buchungstag + str(year)
        valuta = valuta + str(year)


        # --- Simplified logic: collect all following lines into one single Vorgang ---
        vorgang_lines = [beschreibung]
        i = start_idx + 1
        lines_consumed = 1

        while i < len(lines):
            line = lines[i].strip()
            lines_consumed += 1

            # Stop if we hit next transaction or footer
            if is_transaction_start(line) or is_page_footer(line):
                lines_consumed -= 1
                break

            # Skip empty or technical lines
            if not line or is_technical_line(line):
                i += 1
                continue

            # Skip year line (format: "2025 2025" or variations like "2025 2025 2025")
            if re.match(r'^(20\d{2}\s*)+$', line):
                i += 1
                continue

            # Remove year prefixes from lines (e.g., "2025 2025 PayPal" -> "PayPal")
            line = re.sub(r'^(?:20\d{2}\s+)+', '', line)

            if line:  # Only add if something remains after removing years
                vorgang_lines.append(line)
            i += 1

        # Combine everything into one field
        vorgang = clean_text(' '.join(vorgang_lines))

        return {
            "Buchungstag": buchungstag,
            "Valuta": valuta,
            "Vorgang": vorgang[:750],
            "Betrag EUR": betrag,
        }, lines_consumed

    except Exception as e:
        if debug:
            print(f"✗ Fehler beim Parsen: {e}")
        return None, 1


def is_technical_line(line: str) -> bool:
    """Prüft ob eine Zeile technische Informationen enthält (soll nicht in Verwendungszweck)."""
    technical_keywords = [
        'Gläubiger-ID', 'Mand-ID', 'RCUR', 'OTHR', 'SALA', 'RINP',
        'Wiederholungslastschrift', 'Dauerauftrag', 'BIC ', 'IBAN',
        'Folgenr.', 'Verfalld.', 'Kartennr.'
    ]
    return any(keyword in line for keyword in technical_keywords)


def clean_text(text: str) -> str:
    """Bereinigt Text durch Hinzufügen von Leerzeichen."""
    if not text:
        return ""

    # Add space before capitals
    text = re.sub(r'([a-zäöü])([A-ZÄÖÜ])', r'\1 \2', text)

    # Fix common stuck words
    replacements = {
        'vonvon': 'von von',
        'einzugvon': 'einzug von',
        'überweisungvon': 'überweisung von',
        'überweisungan': 'überweisung an',
        'Einkaufbei': 'Einkauf bei',
        'Ratefuer': 'Rate für',
        'fuerMonat': 'für Monat',
        'sagtDanke': 'sagt Danke',
        'mangelsDeckung': 'mangels Deckung',
        'oderwegen': 'oder wegen',
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    # Normalize whitespace
    text = ' '.join(text.split())

    return text


class DBParser(BaseParser):
    """Parser für Deutsche Bank Kontoauszüge im PDF-Format"""

    def parse(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Parst einen Deutsche Bank Kontoauszug und extrahiert alle Transaktionen.

        Args:
            pdf_path: Pfad zur PDF-Datei

        Returns:
            Liste von Transaktions-Dictionaries
        """
        return parse_deutsche_bank_pdf(pdf_path, debug=False)
