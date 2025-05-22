from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import credentials, firestore, auth, initialize_app
from dotenv import load_dotenv
import os, json, base64, requests, tempfile
import face_recognition

load_dotenv()

# Load Firebase credentials from base64
firebase_credentials_base64 = os.getenv("FIREBASE_CREDENTIALS_BASE64")
if not firebase_credentials_base64:
    raise RuntimeError("FIREBASE_CREDENTIALS_BASE64 tidak ditemukan di .env")

cred_json = base64.b64decode(firebase_credentials_base64).decode("utf-8")
cred_dict = json.loads(cred_json)
cred = credentials.Certificate(cred_dict)
initialize_app(cred)
db = firestore.client()

SUPABASE_BUCKET_URL = os.getenv("SUPABASE_BUCKET_URL")
if not SUPABASE_BUCKET_URL:
    raise RuntimeError("SUPABASE_BUCKET_URL tidak ditemukan di .env")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/compare")
async def compare_face(user_id: str, image: UploadFile = File(...)):
    try:
        # Simpan file foto yang diupload ke file sementara
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(await image.read())
            uploaded_path = tmp.name

        uploaded_image = face_recognition.load_image_file(uploaded_path)
        uploaded_encodings = face_recognition.face_encodings(uploaded_image)
        if not uploaded_encodings:
            raise HTTPException(status_code=400, detail="Wajah tidak terdeteksi pada gambar yang diunggah.")
        uploaded_encoding = uploaded_encodings[0]

        # Ambil foto referensi dari Supabase
        reference_url = f"{SUPABASE_BUCKET_URL}{user_id}.jpg"
        response = requests.get(reference_url)
        if response.status_code != 200:
            raise HTTPException(status_code=404, detail="Foto referensi tidak ditemukan di Supabase.")

        with tempfile.NamedTemporaryFile(delete=False) as tmp_ref:
            tmp_ref.write(response.content)
            reference_path = tmp_ref.name

        reference_image = face_recognition.load_image_file(reference_path)
        reference_encodings = face_recognition.face_encodings(reference_image)
        if not reference_encodings:
            raise HTTPException(status_code=400, detail="Wajah tidak terdeteksi pada foto referensi.")
        reference_encoding = reference_encodings[0]

        # Bandingkan wajah
        result = face_recognition.compare_faces([reference_encoding], uploaded_encoding)[0]

        # Simpan hasil ke Firestore
        db.collection("absensi").add({
            "user_id": user_id,
            "match": result,
            "timestamp": firestore.SERVER_TIMESTAMP
        })

        return {"match": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
