from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from .config import UPLOAD_FOLDER, ALLOWED_EXTENSIONS

app = Flask(__name__)
CORS(app)

# Upload route
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///nduwa_sheepmanager.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Import and register routes
from . import routes
from .lamb_routes import lamb_bp   # ✅ Import lamb blueprint
app.register_blueprint(lamb_bp)    # ✅ Register lamb routes (no prefix)
