from flask import Blueprint, request, jsonify
from datetime import datetime
from . import db
from .models import Sheep  # Lamb model not used here since lambs are stored in Sheep with is_lamb=True
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func

lamb_bp = Blueprint('lambs', __name__)

def resolve_parent_id(tag_id):
    """Case-insensitive parent resolution with debug logging"""
    if not tag_id:
        return None

    tag_id = tag_id.strip()
    all_tags = [t[0] for t in Sheep.query.with_entities(Sheep.tag_id).all()]
    print(f"\n[DEBUG] All tag_ids in DB: {all_tags}")
    print(f"[DEBUG] Resolving parent with tag_id: '{tag_id}'")

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
        'image_url': lamb.image if lamb.image else None,
        'mother_id': lamb.mother.tag_id if lamb.mother else None,
        'father_id': lamb.father.tag_id if lamb.father else None,
        'weight': lamb.weight,
        'weaning_weight': lamb.weaning_weight,
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
        'image_url': lamb.image if lamb.image else None,
        'weight': lamb.weight,
        'weaning_weight': lamb.weaning_weight,
        'breed': lamb.breed
    })

@lamb_bp.route('/lambs', methods=['POST'])
def add_lamb():
    print(f"\n=== NEW LAMB REQUEST ===")
    print(f"Content-Type: {request.content_type}")
    print(f"Data: {request.get_json() if request.is_json else request.form}")

    data = request.get_json() if request.is_json else request.form

    required = ['tag_id', 'gender', 'dob']
    missing = [field for field in required if field not in data or not data.get(field)]
    if missing:
        return jsonify({"error": f"Missing required fields: {missing}"}), 400

    try:
        dob = datetime.strptime(data['dob'], "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    mother_id = resolve_parent_id(data.get("mother_id"))
    father_id = resolve_parent_id(data.get("father_id"))

    try:
        new_lamb = Sheep(
            tag_id=data["tag_id"].strip(),
            dob=dob,
            gender=data["gender"],
            weight=float(data['weight']) if data.get('weight') else None,
            weaning_weight=float(data['weaning_weight']) if data.get('weaning_weight') else None,
            breed=data.get("breed"),
            medical_records=data.get("medical_records", ""),
            image=data.get("image_url"),
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
                "image_url": new_lamb.image,
                "weight": new_lamb.weight,
                "weaning_weight": new_lamb.weaning_weight,
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

    data = request.get_json() if request.is_json else request.form
    print("Incoming lamb update:", data)

    lamb.tag_id = data.get('tag_id', lamb.tag_id)
    lamb.weight = float(data['weight']) if 'weight' in data else lamb.weight
    lamb.weaning_weight = float(data['weaning_weight']) if 'weaning_weight' in data else lamb.weaning_weight
    lamb.medical_records = data.get('medical_records', lamb.medical_records)

    if 'dob' in data:
        try:
            lamb.dob = datetime.strptime(data['dob'], "%Y-%m-%d").date()
        except ValueError:
            print("Invalid date format for DOB")

    if 'mother_id' in data:
        mother_id = resolve_parent_id(data['mother_id'])
        if mother_id is None:
            return jsonify({"error": f"Mother sheep with tag_id '{data['mother_id']}' not found"}), 404
        lamb.mother_id = mother_id

    if 'father_id' in data:
        father_id = resolve_parent_id(data['father_id'])
        if father_id is None:
            return jsonify({"error": f"Father sheep with tag_id '{data['father_id']}' not found"}), 404
        lamb.father_id = father_id

    if 'image_url' in data:
        lamb.image = data['image_url']

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
    parent = Sheep.query.filter(func.lower(Sheep.tag_id) == func.lower(parent_tag_id)).first()
    if not parent:
        return jsonify({"error": "Parent sheep not found"}), 404

    lambs = Sheep.query.filter(
        Sheep.is_lamb == True,
        ((Sheep.mother_id == parent.id) | (Sheep.father_id == parent.id))
    ).all()

    return jsonify([{
        'id': lamb.id,
        'tag_id': lamb.tag_id,
        'dob': lamb.dob.isoformat() if lamb.dob else None,
        'gender': lamb.gender,
        'image_url': lamb.image if lamb.image else None,
        'weight': lamb.weight,
        'weaning_weight': lamb.weaning_weight,
        'breed': lamb.breed,
        'mother_id': lamb.mother.tag_id if lamb.mother else None,
        'father_id': lamb.father.tag_id if lamb.father else None,
    } for lamb in lambs])
