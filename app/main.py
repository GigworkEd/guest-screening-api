from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from .utils import parse_and_normalize_csv
import psycopg2
import os

# Initialize FastAPI app
app = FastAPI()

# Apply CORS for Vercel frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://guest-screening-dashboard.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# PostgreSQL DB connection (from Railway)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:TozLcXkFfNLZKyYIiHIYpDEtbnfgdwxj@ballast.proxy.rlwy.net:40063/railway"
)

# Health check
@app.get("/")
def health_check():
    return {"message": "API is running"}

# Compare reservations endpoint
@app.post("/compare-reservations")
async def compare_reservations(file: UploadFile = File(...)):
    contents = await file.read()
    reservations = parse_and_normalize_csv(contents)

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

# Handle preflight CORS request for POST /add-bad-guest
@app.options("/add-bad-guest")
async def preflight_add_guest():
    return JSONResponse(content={"status": "preflight ok"})

# Add flagged guest endpoint
@app.post("/add-bad-guest")
async def add_bad_guest(request: Request):
    data = await request.json()
    print("Incoming guest data:", data)

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        query = """
        INSERT INTO bad_guests (full_name, email, incident_type, amount_owed, notes, property_name)

        VALUES (%s, %s, %s, %s, %s, %s);
        """
        values = (
            data.get("full_name"),
            data.get("email"),
            data.get("violation"),  # ← keep this if frontend still uses "violation"
            data.get("amount_owed"),
            data.get("notes"),
            data.get("incident_property") # Stays the same for now becasue of the front end
)

        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()

        return {"message": "Guest successfully flagged in the database."}
    
    except Exception as e:
        print("ERROR inserting guest:", e)
        return JSONResponse(status_code=500, content={"error": str(e)})
