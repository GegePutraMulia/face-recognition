import face_recognition
import requests
import numpy as np
from io import BytesIO
from PIL import Image

def load_image_from_url(url):
    response = requests.get(url)
    image = Image.open(BytesIO(response.content))
    return np.array(image)

def compare_faces(known_url, unknown_url):
    known_image = load_image_from_url(known_url)
    unknown_image = load_image_from_url(unknown_url)

    known_encoding = face_recognition.face_encodings(known_image)
    unknown_encoding = face_recognition.face_encodings(unknown_image)

    if not known_encoding or not unknown_encoding:
        return False

    result = face_recognition.compare_faces([known_encoding[0]], unknown_encoding[0])
    return result[0]
