
from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from .utils import parse_and_normalize_csv
from rapidfuzz import fuzz
import psycopg2
import os

# Create FastAPI app
app = FastAPI()

# Apply CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://guest-screening-dashboard.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load Railway DB URL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:TozLcXkFfNLZKyYIiHIYpDEtbnfgdwxj@ballast.proxy.rlwy.net:40063/railway"
)

@app.get("/")
def health_check():
    return {"message": "API is running"}

@app.options("/add-bad-guest")
async def preflight_add_guest():
    return JSONResponse(content={"status": "preflight ok"})

@app.options("/compare-reservations")
async def preflight_compare_reservations():
    return JSONResponse(content={"status": "preflight ok"})

@app.post("/compare-reservations")
async def compare_reservations(file: UploadFile = File(...)):
    contents = await file.read()
    reservations = parse_and_normalize_csv(contents)

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    matched = []
    seen_guests = set()

    # Fetch all bad guests once
    cursor.execute("SELECT * FROM bad_guests;")
    all_bad_guests = cursor.fetchall()

    for res in reservations:
        input_name = res["full_name"].lower().strip()

        for guest in all_bad_guests:
            db_name = guest[1].lower().strip()
            similarity = fuzz.token_sort_ratio(input_name, db_name)

            if similarity >= 70:
                unique_key = f"{db_name}-{guest[6]}-{guest[13]}"
                if unique_key not in seen_guests:
                    matched.append({
                        "matched_name": guest[1],
                        "incident_type": guest[6],
                        "match_score": similarity,
                        "amount_owed": str(guest[10]),
                        "notes": guest[11],
                        "incident_property": guest[13]
                    })
                    seen_guests.add(unique_key)
                break

    cursor.close()
    conn.close()

    # Sort by match confidence descending
    matched.sort(key=lambda x: x["match_score"], reverse=True)

    return JSONResponse(content={"matches": matched})

@app.post("/add-bad-guest")
async def add_bad_guest(request: Request):
    data = await request.json()
    print("Incoming guest data:", data)

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        query = """
        INSERT INTO bad_guests (full_name, email, incident_type, amount_owed, notes, incident_property_name)
        VALUES (%s, %s, %s, %s, %s, %s);
        """
        values = (
            data.get("full_name"),
            data.get("email"),
            data.get("violation"),
            data.get("amount_owed"),
            data.get("notes"),
            data.get("incident_property")
        )

        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()

        return {"message": "Guest successfully flagged in the database."}

    except Exception as e:
        print("ERROR inserting guest:", e)
        return JSONResponse(status_code=500, content={"error": str(e)})
