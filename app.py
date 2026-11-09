import os
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Dashboard UMKM - Local Status API",
    docs_url=None,
    redoc_url=None,
)

# Isi dengan alamat Render Static Site, contoh:
# https://dashboard-umkm.onrender.com
raw_origins = os.getenv("ALLOWED_ORIGINS", "")
allowed_origins = [item.strip() for item in raw_origins.split(",") if item.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    """Endpoint minimal untuk mengecek apakah Python di PC sedang aktif."""
    return {
        "status": "online",
        "service": "dashboard-umkm-local-python",
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
