import os

CLOUDINARY_UPLOAD_URL = "https://api.cloudinary.com/v1_1/dr8cmlcqs/image/upload"
CLOUDINARY_UPLOAD_PRESET = "unsigned_sheep"

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
