from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseModel
import face_recognition
import requests
from io import BytesIO
from fastapi.middleware.cors import CORSMiddleware
import firebase_admin
from firebase_admin import credentials, firestore

# Inisialisasi Firebase
cred = credentials.Certificate("firebase-service-account.json")  # file key Firebase kamu
firebase_admin.initialize_app(cred)
db = firestore.client()

# Supabase URL dan token dari .env atau variabel Railway
SUPABASE_BUCKET_URL = "https://juigrfuhshdlsbphvvqx.supabase.co/storage/v1/object/public/foto-anggota/anggota/"
app = FastAPI()

# Allow CORS (untuk Flutter / Web)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/compare")
async def compare_face(
    image: UploadFile = File(...),
    user_id: str = Form(...)
):
    # Ambil URL foto referensi dari Supabase
    foto_url = f"{SUPABASE_BUCKET_URL}{user_id}.jpg"
    response = requests.get(foto_url)
    if response.status_code != 200:
        return {"status": "error", "message": "Foto referensi tidak ditemukan"}

    known_image = face_recognition.load_image_file(BytesIO(response.content))
    unknown_image = face_recognition.load_image_file(await image.read())

    try:
        known_encoding = face_recognition.face_encodings(known_image)[0]
        unknown_encoding = face_recognition.face_encodings(unknown_image)[0]
    except IndexError:
        return {"status": "error", "message": "Wajah tidak terdeteksi"}

    result = face_recognition.compare_faces([known_encoding], unknown_encoding)[0]
    if result:
        # Simpan ke Firestore
        db.collection("absensi").add({
            "user_id": user_id,
            "status": "valid",
            "timestamp": firestore.SERVER_TIMESTAMP,
        })
        return {"status": "success", "message": "Wajah cocok"}
    else:
        return {"status": "error", "message": "Wajah tidak cocok"}
