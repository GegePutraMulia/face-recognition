import face_recognition
import requests
from io import BytesIO

def load_image_from_url(url: str):
    response = requests.get(url)
    response.raise_for_status()
    return face_recognition.load_image_file(BytesIO(response.content))

def load_image_from_bytes(image_bytes: bytes):
    return face_recognition.load_image_file(BytesIO(image_bytes))

def compare_faces_from_urls(reference_url: str, unknown_image_bytes: bytes, tolerance=0.6):
    # Load reference image from URL (Supabase Storage)
    try:
        ref_image = load_image_from_url(reference_url)
    except Exception as e:
        print(f"Error loading reference image: {e}")
        return None

    unknown_image = load_image_from_bytes(unknown_image_bytes)

    # Encode faces
    ref_encodings = face_recognition.face_encodings(ref_image)
    unknown_encodings = face_recognition.face_encodings(unknown_image)

    if not ref_encodings or not unknown_encodings:
        return None  # Wajah tidak terdeteksi

    # Bandingkan encoding pertama (asumsi 1 wajah di tiap gambar)
    results = face_recognition.compare_faces([ref_encodings[0]], unknown_encodings[0], tolerance=tolerance)
    return results[0]
