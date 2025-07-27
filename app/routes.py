from flask import request, jsonify, url_for
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from .config import UPLOAD_FOLDER, ALLOWED_EXTENSIONS
from . import app, db
from .models import Sheep
from sqlalchemy.exc import IntegrityError

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_parent_id(tag_id):
    """Helper function to resolve parent tag_id to database ID"""
    if not tag_id:
        return None
    parent = Sheep.query.filter_by(tag_id=tag_id).first()
    if not parent:
        raise ValueError(f"Parent sheep with tag_id '{tag_id}' not found")
    return parent.id

@app.route('/sheep', methods=['POST'], strict_slashes=False)
def add_sheep():
    print("📝 Received POST /sheep request")
    print("Content-Type:", request.content_type)
    if request.content_type.startswith('application/json'):
        try:
            data = request.get_json(force=True, silent=False)
            if not data:
                print("❌ Empty or invalid JSON body")
                return jsonify({"error": "Invalid or empty JSON"}), 400
        except Exception as e:
            print("❌ JSON parsing failed:", str(e))
            return jsonify({"error": f"JSON parsing failed: {str(e)}"}), 400
    else:
        data = request.form
    print("📥 Incoming data:", data)
    print("📂 Incoming files:", request.files)

    # Validate required fields
    required_fields = ['tag_id', 'gender', 'dob']
    missing = [field for field in required_fields if field not in data or not data[field]]
    if missing:
        print(f"❌ Missing required fields: {missing}")
        return jsonify({"error": f"Missing required fields: {missing}"}), 400

    # Process date
    try:
        dob = datetime.strptime(data['dob'], "%Y-%m-%d").date()
    except ValueError:
        print("❌ Invalid date format for dob:", data['dob'])
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    # Handle parents
    try:
        mother_id = get_parent_id(data.get("mother_id")) if data.get("mother_id") else None
        father_id = get_parent_id(data.get("father_id")) if data.get("father_id") else None
    except ValueError as e:
        print("❌ Parent sheep not found error:", str(e))
        return jsonify({"error": str(e)}), 404

    # Handle image upload
    file = request.files.get('image')
    filename = None
    if file:
        if not allowed_file(file.filename):
            print(f"❌ Invalid image format: {file.filename}")
            return jsonify({"error": "Invalid image format"}), 400
        filename = secure_filename(file.filename)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)
        print(f"✅ Saved image file to {save_path}")

    # Create sheep record
    try:
        new_sheep = Sheep(
            tag_id=data["tag_id"],
            dob=dob,
            gender=data["gender"],
            pregnant=str(data.get("pregnant", "false")).lower() == "true",
            medical_records=data.get("medical_records", ""),
            image=filename,
            weight=float(data['weight']) if data.get('weight') else None,
            breed=data.get("breed"),
            mother_id=mother_id,
            father_id=father_id,
            is_lamb=str(data.get("is_lamb", "false")).lower() == "true"
        )

        db.session.add(new_sheep)
        db.session.commit()
        print(f"✅ Added new sheep with tag_id: {new_sheep.tag_id}")

        return jsonify({
            "message": "Sheep added successfully",
            "data": {
                "tag_id": new_sheep.tag_id,
                "dob": new_sheep.dob.isoformat(),
                "image_url": url_for('uploaded_file', filename=filename, _external=True) if filename else None
            }
        }), 201

    except IntegrityError:
        db.session.rollback()
        print(f"❌ IntegrityError: Tag ID {data['tag_id']} already exists")
        return jsonify({"error": "Tag ID already exists"}), 409
    except Exception as e:
        db.session.rollback()
        print("❌ Server error:", str(e))
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@app.route('/sheep', methods=['GET'])
def get_sheep():
    sheep_list = Sheep.query.all()
    return jsonify([{
        'id': sheep.id,
        'tag_id': sheep.tag_id,
        'dob': sheep.dob.isoformat() if sheep.dob else None,
        'gender': sheep.gender,
        'pregnant': sheep.pregnant,
        'medical_records': sheep.medical_records,
        'image': url_for('uploaded_file', filename=sheep.image, _external=True) if sheep.image else None,
        'weight': sheep.weight,
        'breed': sheep.breed,
        'mother_id': sheep.mother.tag_id if sheep.mother else None,
        'father_id': sheep.father.tag_id if sheep.father else None,
        'is_lamb': sheep.is_lamb
    } for sheep in sheep_list])

@app.route('/sheep/<int:sheep_id>', methods=['GET'])
def get_sheep_by_id(sheep_id):
    sheep = Sheep.query.get_or_404(sheep_id)
    return jsonify({
        "tag_id": sheep.tag_id,
        "dob": sheep.dob.isoformat() if sheep.dob else None,
        "gender": sheep.gender,
        "family": {
            "mother": sheep.mother.tag_id if sheep.mother else None,
            "father": sheep.father.tag_id if sheep.father else None,
            "children": [lamb.tag_id for lamb in sheep.mother_children + sheep.father_children]
        }
    })

@app.route('/sheep/<int:sheep_id>', methods=['PUT'])
def update_sheep(sheep_id):
    sheep = Sheep.query.get_or_404(sheep_id)

    print("🔍 Incoming update for Sheep ID:", sheep_id)
    print("Form:", request.form)
    print("Files:", request.files)

    tag_id = request.form.get('tag_id')
    gender = request.form.get('gender')
    dob_str = request.form.get('dob')
    pregnant = request.form.get('pregnant')
    weight = request.form.get('weight')
    breed = request.form.get('breed')
    medical_records = request.form.get('medical_records')
    mother_id = request.form.get('mother_id')
    father_id = request.form.get('father_id')
    is_lamb = request.form.get('is_lamb')
    file = request.files.get('image')

    # Check required fields
    if not tag_id or not gender or not dob_str:
        return jsonify({'error': 'Missing required fields'}), 400

    # Convert dob string to Python date object
    try:
        dob = datetime.fromisoformat(dob_str).date()
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400

    # Update sheep fields
    sheep.tag_id = tag_id
    sheep.gender = gender
    sheep.dob = dob
    sheep.pregnant = (pregnant.lower() == 'true') if gender.lower() == 'female' and pregnant is not None else None
    sheep.weight = weight
    sheep.breed = breed
    sheep.medical_records = medical_records
    sheep.mother_id = mother_id
    sheep.father_id = father_id
    sheep.is_lamb = is_lamb.lower() == 'true' if is_lamb else False

    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        sheep.image = filename

    try:
        db.session.commit()
        return jsonify({'message': 'Sheep updated successfully'})
    except Exception as e:
        db.session.rollback()
        print("❌ DB Error:", e)
        return jsonify({'error': str(e)}), 500



@app.route('/sheep/<int:sheep_id>', methods=['DELETE'])
def delete_sheep(sheep_id):
    sheep = Sheep.query.get_or_404(sheep_id)
    db.session.delete(sheep)
    db.session.commit()
    return jsonify({"message": f"Sheep {sheep.tag_id} deleted"})

@app.errorhandler(404)
def resource_not_found(e):
    return jsonify({"error": "Resource not found"}), 404