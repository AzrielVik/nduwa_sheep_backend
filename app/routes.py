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

@app.route('/sheep', methods=['POST'])
def add_sheep():
    # Handle both JSON and form-data
    if request.content_type.startswith('application/json'):
        try:
            data = request.get_json(force=True, silent=False)
            if not data:
                return jsonify({"error": "Invalid or empty JSON"}), 400
        except Exception as e:
            return jsonify({"error": f"JSON parsing failed: {str(e)}"}), 400
    else:
        data = request.form

    # Validate required fields
    required_fields = ['tag_id', 'gender', 'dob']
    missing = [field for field in required_fields if field not in data]
    if missing:
        return jsonify({"error": f"Missing required fields: {missing}"}), 400

    # Process date
    try:
        dob = datetime.strptime(data['dob'], "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    # Handle parents
    try:
        mother_id = get_parent_id(data.get("mother_id")) if data.get("mother_id") else None
        father_id = get_parent_id(data.get("father_id")) if data.get("father_id") else None
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

    # Handle image upload
    file = request.files.get('image')
    filename = None
    if file:
        if not allowed_file(file.filename):
            return jsonify({"error": "Invalid image format"}), 400
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

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
        return jsonify({"error": "Tag ID already exists"}), 409
    except Exception as e:
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
    data = request.get_json() if request.is_json else request.form

    # Handle all updatable fields
    if 'dob' in data:
        try:
            sheep.dob = datetime.strptime(data['dob'], "%Y-%m-%d").date()
        except ValueError:
            pass

    sheep.tag_id = data.get('tag_id', sheep.tag_id)
    sheep.gender = data.get('gender', sheep.gender)
    sheep.pregnant = str(data.get('pregnant', sheep.pregnant)).lower() == 'true'
    sheep.medical_records = data.get('medical_records', sheep.medical_records)
    sheep.weight = float(data['weight']) if 'weight' in data else sheep.weight
    sheep.breed = data.get('breed', sheep.breed)
    sheep.is_lamb = str(data.get('is_lamb', sheep.is_lamb)).lower() == 'true'

    # Handle parent relationships
    try:
        if 'mother_id' in data:
            sheep.mother_id = get_parent_id(data['mother_id']) if data['mother_id'] else None
        if 'father_id' in data:
            sheep.father_id = get_parent_id(data['father_id']) if data['father_id'] else None
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

    db.session.commit()
    return jsonify({"message": "Sheep updated"})

@app.route('/sheep/<int:sheep_id>', methods=['DELETE'])
def delete_sheep(sheep_id):
    sheep = Sheep.query.get_or_404(sheep_id)
    db.session.delete(sheep)
    db.session.commit()
    return jsonify({"message": f"Sheep {sheep.tag_id} deleted"})

@app.errorhandler(404)
def resource_not_found(e):
    return jsonify({"error": "Resource not found"}), 404