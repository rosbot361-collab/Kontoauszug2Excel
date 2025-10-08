
"""
ING Kontoauszug Parser
Extrahiert Transaktionen aus ING PDF-Kontoauszügen über mehrere Seiten hinweg.
"""

import pdfplumber
import pandas as pd
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class Transaction:
    """Repräsentiert eine einzelne Banktransaktion"""
    datum: str = ""
    valuta: str = ""
    empfaenger: str = ""
    transaktion: str = ""
    betrag_eur: Optional[float] = None
    verwendungszweck: List[str] = field(default_factory=list)
    erlaeuterung: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert die Transaktion in ein Dictionary"""
        return {
            "Datum": self.datum,
            "Valuta": self.valuta,
            "Empfänger": self.empfaenger,
            "Transaktion": self.transaktion,
            "Betrag EUR": self.betrag_eur,
            "Verwendungszweck": " | ".join(self.verwendungszweck),
        }

    def is_valid(self) -> bool:
        """Prüft ob die Transaktion gültig ist"""
        if not self.datum:
            return False
        
        exclude_keywords = ["saldo", "zins", "abschluss"]
        return not any(kw in self.erlaeuterung.lower() for kw in exclude_keywords)

    def reset(self):
        """Setzt alle Felder zurück"""
        self.datum = ""
        self.valuta = ""
        self.empfaenger = ""
        self.transaktion = ""
        self.betrag_eur = None
        self.verwendungszweck = []
        self.erlaeuterung = ""


class INGParser:
    """Parser für ING Kontoauszüge im PDF-Format"""
    
    # PDF-Extraktionseinstellungen
    PDF_SETTINGS = {
        "vertical_strategy": "text",
        "horizontal_strategy": "text",
        "snap_y_tolerance": 8,
        "join_tolerance": 3,
    }
    
    # Bekannte Transaktionsarten
    TRANSACTION_TYPES = [
        "Lastschrift",
        "Ueberweisung",
        "Überweisung",
        "Gutschrift",
        "VISA",
        "Dauerauftrag",
        "Kartenzahlung",
        "Abbuchung",
        "Zahlung",
        "SEPA",
    ]
    
    # Keywords für Header und Footer (zu überspringende Zeilen)
    SKIP_KEYWORDS = [
        # Header-Informationen
        "saldo", "zins", "abschluss", "einlagensicherung",
        "kontoübersicht", "kunden-information", "datum",
        "auszugsnummer", "eingeraumte kontoüberziehung",
        "eingeräumte kontoüberziehung", "ing-diba", "ing ",
        "theodor-heuss", "girokonto nummer", "girokonto",
        "iban", "bic", "buchung / verwendungszweck",
        "betrag (eur)", "valuta", "seite ", "kontoauszug", "blz",
        # Footer-Zusammenfassungen
        "summe belastungen", "summe gutschriften",
        "saldo vorgetragen", "neuer saldo", "alter saldo", "kontostand",
    ]
    
    # Keywords für Tabellenende
    TABLE_END_KEYWORDS = [
        "summe belastungen", "summe gutschriften",
        "saldo vorgetragen", "neuer saldo",
        "alter saldo", "kontostand",
    ]

    def parse(self, pdf_path: str, debug: bool = False) -> List[Dict[str, Any]]:
        """
        Parst einen ING Kontoauszug und extrahiert alle Transaktionen.
        
        Args:
            pdf_path: Pfad zur PDF-Datei
            debug: Aktiviert Debug-Ausgaben
            
        Returns:
            Liste von Transaktions-Dictionaries
        """
        transactions = []
        current_transaction = Transaction()
        
        with pdfplumber.open(pdf_path) as pdf:
            if debug:
                print(f"📄 PDF hat {len(pdf.pages)} Seiten")
            
            for page_number, page in enumerate(pdf.pages, start=1):
                if debug:
                    print(f"\n{'='*60}")
                    print(f"📄 Verarbeite Seite {page_number}/{len(pdf.pages)}")
                    print(f"{'='*60}")
                
                # Transaktion am Seitenende speichern
                self._save_transaction(current_transaction, transactions, debug)
                current_transaction.reset()
                
                # Seite verarbeiten
                self._process_page(page, current_transaction, transactions, debug)
            
            # Letzte Transaktion speichern
            self._save_transaction(current_transaction, transactions, debug)
        
        if debug:
            print(f"\n{'='*60}")
            print(f"✅ Insgesamt {len(transactions)} Transaktionen extrahiert")
            print(f"{'='*60}")
        
        return transactions

    def _process_page(
        self, 
        page, 
        current_transaction: Transaction, 
        transactions: List[Dict[str, Any]], 
        debug: bool
    ):
        """Verarbeitet eine einzelne PDF-Seite"""
        text = page.extract_text(x_tolerance=self.PDF_SETTINGS["join_tolerance"])
        if not text:
            return
        
        lines = self._extract_table_lines(text, debug)
        if not lines:
            return
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Header-Zeilen überspringen
            if self._is_skip_line(line):
                if debug:
                    print(f"  ⏭️  Überspringe: {line[:60]}...")
                i += 1
                continue
            
            # Prüfen ob neue Buchungszeile
            if self._is_booking_line(line):
                # Vorherige Transaktion speichern
                self._save_transaction(current_transaction, transactions, debug)
                current_transaction.reset()
                
                # Neue Transaktion parsen
                self._parse_booking_line(line, current_transaction, page, debug)
                
                # Nächste Zeile auf Valuta prüfen
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if not self._is_skip_line(next_line):
                        valuta_consumed = self._try_parse_valuta(next_line, current_transaction)
                        if valuta_consumed:
                            i += 2
                            continue
            else:
                # Verwendungszweck hinzufügen
                if current_transaction.datum and not self._is_skip_line(line):
                    current_transaction.verwendungszweck.append(line)
                    if debug:
                        print(f"    ➕ Verwendungszweck: {line[:60]}...")
            
            i += 1

    def _extract_table_lines(self, text: str, debug: bool) -> List[str]:
        """Extrahiert nur die Zeilen der Transaktions-Tabelle"""
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        
        in_table = False
        table_lines = []
        
        for line in lines:
            lower_line = line.lower()
            
            # Tabellenanfang erkennen
            if any(start in lower_line for start in [
                "buchung / verwendungszweck",
                "betrag (eur)",
            ]) or lower_line.startswith("valuta"):
                in_table = True
                continue
            
            # Tabellenende erkennen
            if in_table and any(end in lower_line for end in self.TABLE_END_KEYWORDS):
                if debug:
                    print(f"  🛑 Tabellenende: {line[:60]}...")
                break
            
            if in_table:
                table_lines.append(line)
        
        return table_lines

    def _is_booking_line(self, line: str) -> bool:
        """Prüft ob eine Zeile eine neue Buchung ist"""
        parts = line.split()
        return (
            len(parts) >= 3
            and parts[0].count(".") == 2
            and len(parts[0]) >= 8
            and parts[0][2] == "."
        )

    def _is_skip_line(self, line: str) -> bool:
        """Prüft ob eine Zeile übersprungen werden soll"""
        line_lower = line.lower()
        return any(keyword in line_lower for keyword in self.SKIP_KEYWORDS)

    def _parse_booking_line(
        self, 
        line: str, 
        transaction: Transaction, 
        page, 
        debug: bool
    ):
        """Parst eine Buchungszeile und füllt die Transaktion"""
        parts = line.split()
        
        # Datum extrahieren
        transaction.datum = parts[0]
        
        # Betrag extrahieren
        try:
            amount_str = parts[-1].replace(".", "").replace(",", ".")
            transaction.betrag_eur = float(amount_str)
        except (ValueError, IndexError):
            transaction.betrag_eur = None
        
        # Mittleren Teil in Transaktion und Empfänger aufteilen
        middle_text = " ".join(parts[1:-1])
        transaction.erlaeuterung = middle_text
        
        split_data = self._split_transaction_recipient(middle_text)
        transaction.transaktion = split_data["transaktion"]
        transaction.empfaenger = split_data["empfaenger"]
        
        if debug:
            print(f"\n  💰 Neue Transaktion:")
            print(f"     📅 Datum: {transaction.datum}")
            print(f"     🏷️  Typ: {transaction.transaktion}")
            print(f"     👤 Empfänger: {transaction.empfaenger}")
            print(f"     💶 Betrag: {transaction.betrag_eur}")

    def _split_transaction_recipient(self, text: str) -> Dict[str, str]:
        """
        Trennt Transaktionstyp und Empfänger.
        Beispiel: "Lastschrift VISA DOTT SCOOTER" → 
                  Transaktion="Lastschrift VISA", Empfänger="DOTT SCOOTER"
        """
        words = text.split()
        if not words:
            return {"transaktion": "", "empfaenger": ""}
        
        transaktion_words = []
        empfaenger_words = []
        in_transaction_type = False
        
        for word in words:
            clean_word = word.strip(" -").lower()
            
            # Exakte Übereinstimmung mit Transaktionstyp
            if any(kw.lower() == clean_word for kw in self.TRANSACTION_TYPES):
                in_transaction_type = True
                transaktion_words.append(word)
                continue
            
            # Teilübereinstimmung (z.B. "VISA-Zahlung")
            if in_transaction_type and any(
                kw.lower() in clean_word for kw in self.TRANSACTION_TYPES
            ):
                transaktion_words.append(word)
                continue
            
            # Nach Transaktionstyp kommt der Empfänger
            if in_transaction_type:
                empfaenger_words.append(word)
            else:
                empfaenger_words.append(word)
        
        transaktion = " ".join(transaktion_words).strip()
        empfaenger = " ".join(empfaenger_words).strip()
        
        # Fallback: wenn kein Typ erkannt, ist alles der Typ
        if not transaktion and empfaenger:
            transaktion = empfaenger
            empfaenger = ""
        
        return {"transaktion": transaktion, "empfaenger": empfaenger}

    def _try_parse_valuta(self, line: str, transaction: Transaction) -> bool:
        """
        Versucht ein Valuta-Datum aus der Zeile zu extrahieren.
        Returns True wenn Valuta gefunden und konsumiert wurde.
        """
        date_token = self._find_date_token(line)
        if date_token:
            transaction.valuta = date_token
            rest = line.replace(date_token, "").strip()
            if rest:
                transaction.verwendungszweck.append(rest)
            return True
        return False

    def _find_date_token(self, text: str) -> str:
        """Findet ein Datums-Token im Format DD.MM oder DD.MM.YYYY"""
        tokens = text.split()
        for token in tokens:
            clean_token = token.strip("(),;:")
            parts = clean_token.split(".")
            
            # Format: DD.MM
            if (
                len(parts) == 2
                and all(p.isdigit() for p in parts)
                and len(parts[0]) == 2
            ):
                return clean_token
            
            # Format: DD.MM.YYYY
            if (
                len(parts) == 3
                and all(p.isdigit() for p in parts[:2])
            ):
                return clean_token
        
        return ""

    def _save_transaction(
        self, 
        transaction: Transaction, 
        transactions: List[Dict[str, Any]], 
        debug: bool
    ):
        """Speichert eine Transaktion wenn sie gültig ist"""
        if transaction.is_valid():
            transactions.append(transaction.to_dict())
            if debug:
                print(f"  ✅ Transaktion gespeichert")