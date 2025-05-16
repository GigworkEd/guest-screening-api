from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from .utils import parse_and_normalize_csv
import psycopg2
import os

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or restrict to your Vercel URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app = FastAPI()

# Example: load from Railway DATABASE_URL
DATABASE_URL = "postgresql://postgres:TozLcXkFfNLZKyYIiHIYpDEtbnfgdwxj@ballast.proxy.rlwy.net:40063/railway"

@app.get("/")
def health_check():
    return {"message": "API is running"}

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
