from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import credentials, firestore
import firebase_admin
import os
from dotenv import load_dotenv
import base64
import json
import requests
from utils import compare_faces_from_urls

load_dotenv()

# Load dan inisialisasi Firebase Admin SDK
firebase_credentials_base64 = os.getenv("FIREBASE_CREDENTIALS_BASE64")
if not firebase_credentials_base64:
    raise RuntimeError("FIREBASE_CREDENTIALS_BASE64 tidak ditemukan di .env")

firebase_credentials_json = base64.b64decode(firebase_credentials_base64).decode("utf-8")
firebase_cred_dict = json.loads(firebase_credentials_json)

cred = credentials.Certificate(firebase_cred_dict)
firebase_admin.initialize_app(cred)
db = firestore.client()

# URL Supabase Storage (harus ending dengan slash '/')
SUPABASE_BUCKET_URL = os.getenv("SUPABASE_BUCKET_URL")
if not SUPABASE_BUCKET_URL:
    raise RuntimeError("SUPABASE_BUCKET_URL tidak ditemukan di .env")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Bisa diubah sesuai kebutuhan
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/compare")
async def compare_face(image: UploadFile = File(...), user_id: str = Form(...)):
    try:
        foto_url = f"{SUPABASE_BUCKET_URL}{user_id}.jpg"
        unknown_image_bytes = await image.read()

        result = compare_faces_from_urls(foto_url, unknown_image_bytes)

        if result is None:
            raise HTTPException(status_code=400, detail="Wajah tidak terdeteksi")

        if result:
            # Simpan absensi ke Firestore
            db.collection("users").add({
                "user_id": user_id,
                "status": "valid",
                "timestamp": firestore.SERVER_TIMESTAMP,
            })
            return {"status": "success", "message": "Wajah cocok"}
        else:
            return {"status": "error", "message": "Wajah tidak cocok"}

    except requests.RequestException:
        raise HTTPException(status_code=503, detail="Gagal mengakses foto referensi")
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
