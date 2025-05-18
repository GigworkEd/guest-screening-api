import csv
import io

def parse_and_normalize_csv(file_contents):
    decoded = file_contents.decode("utf-8")
    reader = csv.DictReader(io.StringIO(decoded))

    results = []
    for row in reader:
        # Case-insensitive access to 'full_name'
        full_name = ''
        for key in row.keys():
            if key.lower().strip() == "full_name":
                full_name = row[key].strip()
                break

        results.append({
            "full_name": full_name,
            "raw": row  # Keep the whole row in case we need more fields later
        })

    return results
