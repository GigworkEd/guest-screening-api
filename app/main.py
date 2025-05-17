from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from .utils import parse_and_normalize_csv
import psycopg2
import os

app = FastAPI()  # ✅ Must come BEFORE CORS middleware

# ✅ CORRECT CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://guest-screening-dashboard.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Load Railway DB URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:TozLcXkFfNLZKyYIiHIYpDEtbnfgdwxj@ballast.proxy.rlwy.net:40063/railway")

# Health check endpoint
@app.get("/")
def health_check():
    return {"message": "API is running"}

# Compare uploaded reservation file against DB
@app.post("/compare-reservations")
async def compare_reservations(file: UploadFile = File(...)):
    contents = await file.read()
    reservations = parse_and_normalize_csv(contents)

    # Connect to PostgreSQL
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    matched = []

    for res in reservations:
        full_name = res["full_name"]
        cursor.execute("SELECT * FROM bad_guests WHERE LOWER(full_name) = LOWER(%s);", (full_name,))
        row = cursor.fetchone()
        if row:
            matched.append({
                "matched_name": full_name,
                "incident_type": row[6],
                "amount_owed": str(row[10]),
                "notes": row[11],
                "incident_property": row[13]
            })

    cursor.close()
    conn.close()

    return JSONResponse(content={"matches": matched})

# Add a new flagged guest record
@app.post("/add-bad-guest")
async def add_bad_guest(request: Request):
    data = await request.json()

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    query = """
    INSERT INTO bad_guests (full_name, email, phone, violation, amount_owed, notes, incident_property)
    VALUES (%s, %s, %s, %s, %s, %s, %s);
    """
    values = (
        data.get("full_name"),
        data.get("email"),
        data.get("phone"),
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
