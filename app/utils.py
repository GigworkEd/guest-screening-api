import csv
from typing import List, Dict
from io import StringIO

def normalize_name(name: str) -> str:
    name = name.strip().title()
    if ',' in name:
        last, first = [n.strip() for n in name.split(',', 1)]
        return f"{first} {last}"
    return name

def parse_and_normalize_csv(file_content: bytes) -> List[Dict]:
    content_str = file_content.decode('utf-8')
    reader = csv.DictReader(StringIO(content_str))
    guests = []

    for row in reader:
        full_name = normalize_name(row.get("Guest Name", ""))
        guests.append({
            "full_name": full_name,
            "raw": row  # Keep full row for future use
        })

    return guests
