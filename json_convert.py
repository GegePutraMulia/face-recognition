import json

with open("firebase-service-account.json", "r") as f:
    data = json.load(f)

json_str = json.dumps(data)

# Simpan ke file string JSON (misal supaya bisa dipakai untuk environment variable)
with open("firebase_cred_as_string.txt", "w") as f:
    f.write(json_str)
