from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import credentials, firestore, initialize_app
from dotenv import load_dotenv
import os, requests, logging
import face_recognition
from PIL import Image
import numpy as np
import io

# Inisialisasi logger
logger = logging.getLogger("uvicorn.error")

# Load environment variables
load_dotenv()

# Inisialisasi Firebase
cred_path = os.getenv("FIREBASE_CREDENTIALS")
if not cred_path or not os.path.exists(cred_path):
    raise RuntimeError("File kredensial Firebase tidak ditemukan")
cred = credentials.Certificate(cred_path)
initialize_app(cred)

# Firestore client
db = firestore.client()

# FastAPI instance
app = FastAPI()

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Fungsi bantu: Konversi bytes gambar ke face_encoding
def image_bytes_to_encoding(image_bytes: bytes):
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        image = image.resize((300, 300))  # Resize untuk percepatan
        np_image = np.array(image)
        encodings = face_recognition.face_encodings(np_image, model="hog")  # model ringan
        if not encodings:
            return None
        return encodings[0]
    except Exception as e:
        logger.error("Gagal proses image_bytes: %s", str(e), exc_info=True)
        return None

@app.post("/compare")
async def compare_face(user_id: str, image: UploadFile = File(...)):
    try:
        if not user_id:
            raise HTTPException(status_code=400, detail="Parameter user_id diperlukan.")
        
        uploaded_bytes = await image.read()
        uploaded_encoding = image_bytes_to_encoding(uploaded_bytes)
        if uploaded_encoding is None:
            raise HTTPException(status_code=400, detail="Wajah tidak terdeteksi pada gambar yang diunggah.")
        
        # Bentuk URL foto referensi sesuai user_id
        foto_url_target = f"https://juigrfuhshdlsbphvvqx.supabase.co/storage/v1/object/public/foto-anggota/anggota/{user_id}.jpg"
        
        # Query user berdasarkan URL foto_anggota
        query = db.collection("users").where("foto_anggota", "==", foto_url_target).limit(1).get()
        if not query:
            raise HTTPException(status_code=404, detail="User tidak ditemukan di Firestore.")
        
        user_doc = query[0]
        user_data = user_doc.to_dict()
        
        reference_url = user_data.get("foto_anggota")
        if not reference_url:
            raise HTTPException(status_code=404, detail="URL foto referensi tidak ditemukan.")
        
        response = requests.get(reference_url, timeout=5)
        if response.status_code != 200:
            raise HTTPException(status_code=404, detail="Foto referensi tidak dapat diakses.")
        
        reference_encoding = image_bytes_to_encoding(response.content)
        if reference_encoding is None:
            raise HTTPException(status_code=400, detail="Wajah tidak terdeteksi pada foto referensi.")
        
        distance = face_recognition.face_distance([reference_encoding], uploaded_encoding)[0]
        match = distance < 0.5
        status = "hadir" if match else "gagal"
        
        # Update last_absen di dokumen user yang ditemukan
        db.collection("users").document(user_doc.id).update({
            "last_absen": {
                "match": bool(match),                  # convert numpy.bool_ ke bool native
                "distance": float(distance),           # convert numpy.float64 ke float native
                "status": status,
                "timestamp": firestore.SERVER_TIMESTAMP
            }
        })
        
        return {
            "match": bool(match),
            "distance": float(distance),
            "status": status
        }
    
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error("Terjadi error saat proses compare_face: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Terjadi kesalahan internal server.")
