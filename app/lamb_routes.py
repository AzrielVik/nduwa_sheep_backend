from flask import Blueprint, request, jsonify, url_for, abort
from werkzeug.utils import secure_filename
from datetime import datetime
import os
from . import db, app
from .models import Lamb, Sheep
from .config import UPLOAD_FOLDER, ALLOWED_EXTENSIONS
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func

lamb_bp = Blueprint('lambs', __name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def resolve_parent_id(tag_id):
    """Case-insensitive parent resolution with debug logging"""
    if not tag_id:
        return None

    tag_id = tag_id.strip()
    
    # Debug: Print all sheep tags
    all_tags = [t[0] for t in Sheep.query.with_entities(Sheep.tag_id).all()]
    print(f"\n[DEBUG] All tag_ids in DB: {all_tags}")
    print(f"[DEBUG] Resolving parent with tag_id: '{tag_id}'")

    # Case-insensitive search
    parent = Sheep.query.filter(func.lower(Sheep.tag_id) == func.lower(tag_id)).first()
    if parent:
        print(f"[DEBUG] Parent found: ID={parent.id}, tag_id={parent.tag_id}")
    else:
        print(f"[DEBUG] Parent with tag_id '{tag_id}' not found")

    return parent.id if parent else None

@lamb_bp.route('/lambs', methods=['GET'])
def get_all_lambs():
    lambs = Sheep.query.filter_by(is_lamb=True).all()
    return jsonify([{
        'id': lamb.id,
        'tag_id': lamb.tag_id,
        'dob': lamb.dob.isoformat() if lamb.dob else None,
        'gender': lamb.gender,
        'image_url': url_for('uploaded_file', filename=lamb.image, _external=True) if lamb.image else None,
        'mother_id': lamb.mother.tag_id if lamb.mother else None,
        'father_id': lamb.father.tag_id if lamb.father else None,
        'weight': lamb.weight,
        'breed': lamb.breed,
        'notes': lamb.medical_records  
    } for lamb in lambs])


@lamb_bp.route('/lambs/<int:lamb_id>', methods=['GET'])
def get_lamb_by_id(lamb_id):
    lamb = Sheep.query.get_or_404(lamb_id)
    if not lamb.is_lamb:
        return jsonify({'error': 'Not a lamb'}), 400
        
    return jsonify({
        'tag_id': lamb.tag_id,
        'dob': lamb.dob.isoformat() if lamb.dob else None,
        'family': {
            'mother': lamb.mother.tag_id if lamb.mother else None,
            'father': lamb.father.tag_id if lamb.father else None,
            'siblings': [sib.tag_id for sib in lamb.mother_children + lamb.father_children if sib.id != lamb.id]
        },
        'medical_records': lamb.medical_records,
        'image_url': url_for('uploaded_file', filename=lamb.image, _external=True) if lamb.image else None
    })

@lamb_bp.route('/lambs', methods=['POST'])
def add_lamb():
    print(f"\n=== NEW LAMB REQUEST ===")
    print(f"Content-Type: {request.content_type}")
    print(f"Data: {request.data.decode() if request.data else request.form}")

    if request.content_type.startswith('application/json'):
        data = request.get_json()
        file = None
    else:
        data = request.form
        file = request.files.get('image')

    required = ['tag_id', 'gender', 'dob']
    missing = [field for field in required if field not in data or not data.get(field)]
    if missing:
        return jsonify({"error": f"Missing required fields: {missing}"}), 400

    try:
        dob = datetime.strptime(data['dob'], "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    mother_id = None
    father_id = None

    if data.get("mother_id"):
        mother_tag = data["mother_id"].strip()
        print(f"\n[DEBUG] Resolving mother: '{mother_tag}'")
        mother = Sheep.query.filter(func.lower(Sheep.tag_id) == func.lower(mother_tag)).first()
        print(f"[DEBUG] Mother lookup result: {mother}")
        if not mother:
            print(f"[DEBUG] Mother tag '{mother_tag}' not found in DB")
            return jsonify({"error": f"Mother sheep with tag_id '{mother_tag}' not found"}), 404
        mother_id = mother.id

    if data.get("father_id"):
        father_tag = data["father_id"].strip()
        print(f"\n[DEBUG] Resolving father: '{father_tag}'")
        father = Sheep.query.filter(func.lower(Sheep.tag_id) == func.lower(father_tag)).first()
        print(f"[DEBUG] Father lookup result: {father}")
        if not father:
            print(f"[DEBUG] Father tag '{father_tag}' not found in DB")
            return jsonify({"error": f"Father sheep with tag_id '{father_tag}' not found"}), 404
        father_id = father.id

    filename = None
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    try:
        new_lamb = Sheep(
            tag_id=data["tag_id"].strip(),
            dob=dob,
            gender=data["gender"],
            weight=float(data['weight']) if data.get('weight') else None,
            breed=data.get("breed"),
            medical_records=data.get("medical_records", ""),
            image=filename,
            mother_id=mother_id,
            father_id=father_id,
            is_lamb=True
        )
        db.session.add(new_lamb)
        db.session.commit()

        return jsonify({
            "message": "Lamb added successfully",
            "data": {
                "id": new_lamb.id,
                "tag_id": new_lamb.tag_id,
                "dob": new_lamb.dob.isoformat(),
                "gender": new_lamb.gender,
                "mother_id": new_lamb.mother.tag_id if new_lamb.mother else None,
                "father_id": new_lamb.father.tag_id if new_lamb.father else None,
                "notes": new_lamb.medical_records,
                "image_url": url_for('uploaded_file', filename=new_lamb.image, _external=True) if new_lamb.image else None,
                "weight": new_lamb.weight,
                "breed": new_lamb.breed,
                "is_lamb": new_lamb.is_lamb
            }
        }), 201

    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Tag ID already exists"}), 400
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@lamb_bp.route('/lambs/<int:lamb_id>', methods=['PUT'])
def update_lamb(lamb_id):
    lamb = Sheep.query.get_or_404(lamb_id)
    if not lamb.is_lamb:
        return jsonify({"error": "Not a lamb"}), 400

    data = request.form if request.form else request.get_json()
    print("Incoming lamb update:", data)

    # Update basic fields
    lamb.tag_id = data.get('tag_id', lamb.tag_id)
    lamb.weight = float(data['weight']) if 'weight' in data else lamb.weight
    lamb.medical_records = data.get('medical_records', lamb.medical_records)

    if 'dob' in data:
        try:
            lamb.dob = datetime.strptime(data['dob'], "%Y-%m-%d").date()
        except ValueError:
            print("Invalid date format for DOB")

    # Update parent references
    if 'mother_id' in data:
        mother_tag = data['mother_id']
        mother_id = resolve_parent_id(mother_tag)
        if mother_id is None:
            return jsonify({"error": f"Mother sheep with tag_id '{mother_tag}' not found"}), 404
        lamb.mother_id = mother_id

    if 'father_id' in data:
        father_tag = data['father_id']
        father_id = resolve_parent_id(father_tag)
        if father_id is None:
            return jsonify({"error": f"Father sheep with tag_id '{father_tag}' not found"}), 404
        lamb.father_id = father_id

    # Optional: handle image update
    if 'image' in request.files:
        image_file = request.files['image']
        if image_file:
            filename = secure_filename(image_file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(filepath)
            lamb.image = filename
            print(f"Image updated: {filename}")

    db.session.commit()
    print(f"Lamb updated: {lamb.tag_id}, mother_id={lamb.mother_id}, father_id={lamb.father_id}")
    return jsonify({"message": "Lamb updated"})

@lamb_bp.route('/lambs/<int:lamb_id>', methods=['DELETE'])
def delete_lamb(lamb_id):
    lamb = Sheep.query.get_or_404(lamb_id)
    if not lamb.is_lamb:
        return jsonify({"error": "Not a lamb"}), 400

    db.session.delete(lamb)
    db.session.commit()
    return jsonify({"message": f"Lamb {lamb.tag_id} deleted"})

@lamb_bp.route('/lambs/by-parent/<string:parent_tag_id>', methods=['GET'])
def get_lambs_by_parent(parent_tag_id):
    # Normalize tag_id case
    parent = Sheep.query.filter(func.lower(Sheep.tag_id) == func.lower(parent_tag_id)).first()
    if not parent:
        return jsonify({"error": "Parent sheep not found"}), 404

    # Get all lambs with this parent as mother or father
    lambs = Sheep.query.filter(
        Sheep.is_lamb == True,
        ((Sheep.mother_id == parent.id) | (Sheep.father_id == parent.id))
    ).all()

    return jsonify([{
        'id': lamb.id,
        'tag_id': lamb.tag_id,
        'dob': lamb.dob.isoformat() if lamb.dob else None,
        'gender': lamb.gender,
        'image_url': url_for('uploaded_file', filename=lamb.image, _external=True) if lamb.image else None,
        'weight': lamb.weight,
        'breed': lamb.breed,
        'mother_id': lamb.mother.tag_id if lamb.mother else None,
        'father_id': lamb.father.tag_id if lamb.father else None,
    } for lamb in lambs])
