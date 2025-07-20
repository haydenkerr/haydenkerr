from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
import qrcode
from typing import Dict
from pathlib import Path
import secrets
import sqlite3
from datetime import datetime
import os
from mangum import Mangum

# Allow custom locations so the app can run on AWS Lambda
QR_DIR = Path(os.environ.get("QR_DIR", "qr_codes"))
QR_DIR.mkdir(exist_ok=True)
DB_PATH = Path(os.environ.get("DB_PATH", str(QR_DIR / "qr_codes.db")))

app = FastAPI(title="QR Code Webhook Server")

# Simple in-memory user store
fake_users_db = {
    "user@example.com": {
        "username": "user@example.com",
        "full_name": "Example User",
        "hashed_password": "secret",  # Not secure, demo only
    }
}

# Token storage for demo purposes
fake_tokens_db: Dict[str, str] = {}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class WebhookPayload(BaseModel):
    params: Dict[str, str]
    base_url: str = "https://example.com"


@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user_dict = fake_users_db.get(form_data.username)
    if not user_dict or form_data.password != user_dict["hashed_password"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # create a simple random token
    token = secrets.token_urlsafe(16)
    fake_tokens_db[token] = form_data.username
    return {"access_token": token, "token_type": "bearer"}


def get_current_user(token: str = Depends(oauth2_scheme)):
    username = fake_tokens_db.get(token)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return username


# Directory to store generated QR codes
app.mount("/static", StaticFiles(directory=str(QR_DIR)), name="static")


def init_db():
    """Initialize the SQLite database and tables."""
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS qr_codes (
                slug TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                file_path TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS qr_scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL,
                ip TEXT NOT NULL,
                scanned_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


@app.on_event("startup")
def startup_event():
    init_db()


@app.post("/webhook")
def receive_webhook(
    payload: WebhookPayload,
    request: Request,
    user: str = Depends(get_current_user),
):
    """Receive webhook data and generate a tracked QR code."""
    from urllib.parse import urlencode

    # Construct final destination URL
    url = payload.base_url
    if payload.params:
        url += "?" + urlencode(payload.params)

    # Unique slug used for redirect handler
    slug = secrets.token_urlsafe(8)

    # URL that will be encoded in the QR code
    redirect_url = str(request.base_url) + f"r/{slug}"

    # Generate QR code that points to the redirect handler
    img = qrcode.make(redirect_url)

    filename = f"{slug}.png"
    filepath = QR_DIR / filename
    img.save(filepath)

    # Persist QR code info in the database
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO qr_codes(slug, url, file_path, created_at) VALUES (?, ?, ?, ?)",
            (slug, url, str(filepath), datetime.utcnow().isoformat()),
        )
        conn.commit()

    # Link to static file for download
    link = f"/static/{filename}"

    return JSONResponse({"qr_code_url": link, "redirect_url": redirect_url})


@app.get("/r/{slug}")
def follow_qr(slug: str, request: Request):
    """Handle a QR code scan, log it and redirect to the final URL."""
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT url FROM qr_codes WHERE slug=?", (slug,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Unknown QR code")
        final_url = row[0]

        ip = request.client.host if request.client else ""
        cur.execute(
            "INSERT INTO qr_scans(slug, ip, scanned_at) VALUES (?, ?, ?)",
            (slug, ip, datetime.utcnow().isoformat()),
        )
        conn.commit()

    return RedirectResponse(final_url)


@app.get("/qr/{filename}")
def get_qr_code(filename: str, user: str = Depends(get_current_user)):
    filepath = QR_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(filepath)


# AWS Lambda handler
handler = Mangum(app)
