"""
Robust Data Loader for Foresight AI.
Python Standard Library only.
Provides safe ingestion, header detection, type inference, date normalization,
and anomaly/null/duplicate identification.
"""

import csv
import re
from datetime import datetime
from pathlib import Path


class DataLoader:
    """Safe CSV loader and profile detector."""

    DATE_FORMATS = (
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%Y-%m-%d %H:%M:%S",
    )

    @classmethod
    def infer_type(cls, value):
        """Infers scalar type from string value."""
        if value is None:
            return "null"
        val = str(value).strip()
        if val == "" or val.lower() in ("none", "null", "nan", "na", "n/a"):
            return "null"
        if val.lower() in ("true", "false"):
            return "boolean"
        # Integer check
        if re.match(r"^-?\d+$", val):
            return "integer"
        # Float check
        if re.match(r"^-?\d+\.\d+$", val):
            return "float"
        # Date check
        for fmt in cls.DATE_FORMATS:
            try:
                datetime.strptime(val, fmt)
                return "date"
            except ValueError:
                pass
        return "string"

    @classmethod
    def standardize_date(cls, value):
        """Converts string date into ISO YYYY-MM-DD string."""
        if not value:
            return None
        val = str(value).strip()
        for fmt in cls.DATE_FORMATS:
            try:
                dt = datetime.strptime(val, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                pass
        return val

    @classmethod
    def load_csv(cls, filepath):
        """Reads CSV file safely with encoding fallback and dialect sniffing."""
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Source file not found: {filepath}")

        # Encodings to try
        encodings = ["utf-8", "utf-8-sig", "latin-1"]
        content = None
        used_enc = None

        for enc in encodings:
            try:
                with open(filepath, "r", encoding=enc) as f:
                    content = f.read()
                used_enc = enc
                break
            except (UnicodeDecodeError, LookupError):
                continue

        if content is None:
            raise IOError(f"Could not decode {filepath} with any supported encoding.")

        lines = [line for line in content.splitlines() if line.strip()]
        if not lines:
            return {
                "filename": filepath.name,
                "filepath": str(filepath),
                "headers": [],
                "rows": [],
                "row_count": 0,
                "encoding": used_enc,
            }

        # Sniff delimiter
        sample = "\n".join(lines[:20])
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
            delimiter = dialect.delimiter
        except Exception:
            delimiter = ","

        reader = csv.DictReader(lines, delimiter=delimiter)
        headers = [h.strip() for h in (reader.fieldnames or [])]
        rows = list(reader)

        return {
            "filename": filepath.name,
            "filepath": str(filepath),
            "headers": headers,
            "rows": rows,
            "row_count": len(rows),
            "encoding": used_enc,
            "delimiter": delimiter,
        }
