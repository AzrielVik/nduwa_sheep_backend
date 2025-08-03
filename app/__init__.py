import os
from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv
from .config import UPLOAD_FOLDER, ALLOWED_EXTENSIONS

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)

# Upload route
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Database configuration - Now using Neon PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or \
    'sqlite:///nduwa_sheepmanager.db'  # Fallback to SQLite if no DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Import and register routes
from . import routes
from .lamb_routes import lamb_bp   # ✅ Import lamb blueprint
app.register_blueprint(lamb_bp)    # ✅ Register lamb routes (no prefix)

# Optional: Add a health check endpoint
@app.route('/health')
def health_check():
    return {'status': 'healthy', 'database': app.config['SQLALCHEMY_DATABASE_URI']}

# 🔧 Temporary route to run migrations manually
@app.route('/run-migrations')
def run_migrations():
    from flask_migrate import upgrade
    try:
        upgrade()
        return {'status': 'success', 'message': 'Database migrated successfully'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}
