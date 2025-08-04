from flask import request, jsonify
from datetime import datetime
from . import app, db
from .models import Sheep
from sqlalchemy.exc import IntegrityError

# ────────────────────────────────────────────────────────────
def get_parent_id(tag_id):
    if not tag_id:
        return None
    parent = Sheep.query.filter_by(tag_id=tag_id).first()
    if not parent:
        raise ValueError(f"Parent sheep with tag_id '{tag_id}' not found")
    return parent.id

# ────────────────────────────────────────────────────────────
@app.route('/sheep', methods=['POST'], strict_slashes=False)
def add_sheep():
    print("📝 Received POST /sheep request")
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415

    data = request.get_json()
    print("📥 Incoming data:", data)

    required_fields = ['tag_id', 'gender', 'dob']
    missing = [field for field in required_fields if not data.get(field)]
    if missing:
        return jsonify({"error": f"Missing required fields: {missing}"}), 400

    try:
        dob = datetime.strptime(data['dob'], "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    try:
        mother_id = get_parent_id(data.get("mother_id")) if data.get("mother_id") else None
        father_id = get_parent_id(data.get("father_id")) if data.get("father_id") else None
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

    image_url = data.get('image_url')  # Expect frontend to send this

    try:
        new_sheep = Sheep(
            tag_id=data["tag_id"],
            dob=dob,
            gender=data["gender"],
            pregnant=str(data.get("pregnant", "false")).lower() == "true",
            medical_records=data.get("medical_records", ""),
            image=image_url,
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
                "image_url": new_sheep.image
            }
        }), 201

    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Tag ID already exists"}), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Server error: {str(e)}"}), 500

# ────────────────────────────────────────────────────────────
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
        'image': sheep.image,
        'weight': sheep.weight,
        'breed': sheep.breed,
        'mother_id': sheep.mother.tag_id if sheep.mother else None,
        'father_id': sheep.father.tag_id if sheep.father else None,
        'is_lamb': sheep.is_lamb
    } for sheep in sheep_list])

# ────────────────────────────────────────────────────────────
@app.route('/sheep/<int:sheep_id>', methods=['GET'])
def get_sheep_by_id(sheep_id):
    sheep = Sheep.query.get_or_404(sheep_id)
    return jsonify({
        "tag_id": sheep.tag_id,
        "dob": sheep.dob.isoformat() if sheep.dob else None,
        "gender": sheep.gender,
        "image": sheep.image,
        "pregnant": sheep.pregnant,
        "weight": sheep.weight,
        "breed": sheep.breed,
        "medical_records": sheep.medical_records,
        "is_lamb": sheep.is_lamb,
        "mother_id": sheep.mother.tag_id if sheep.mother else None,
        "father_id": sheep.father.tag_id if sheep.father else None,
        "family": {
            "children": [lamb.tag_id for lamb in sheep.mother_children + sheep.father_children]
        }
    })

# ────────────────────────────────────────────────────────────
@app.route('/sheep/by_tag/<string:tag_id>', methods=['GET'])
def get_sheep_by_tag_id(tag_id):
    sheep = Sheep.query.filter_by(tag_id=tag_id).first()
    if not sheep:
        return jsonify({'error': 'Sheep not found'}), 404
    return jsonify({
        "id": sheep.id,
        "tag_id": sheep.tag_id,
        "dob": sheep.dob.isoformat() if sheep.dob else None,
        "gender": sheep.gender,
        "image": sheep.image,
        "pregnant": sheep.pregnant,
        "weight": sheep.weight,
        "breed": sheep.breed,
        "medical_records": sheep.medical_records,
        "is_lamb": sheep.is_lamb,
        "mother_id": sheep.mother.tag_id if sheep.mother else None,
        "father_id": sheep.father.tag_id if sheep.father else None,
    })

# ────────────────────────────────────────────────────────────
@app.route('/sheep/<int:sheep_id>', methods=['PUT'])
def update_sheep(sheep_id):
    sheep = Sheep.query.get_or_404(sheep_id)

    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415

    data = request.get_json()
    print("🔄 Updating Sheep ID:", sheep_id)
    print("📝 Incoming JSON data:", data)

    try:
        sheep.tag_id = data['tag_id']
        sheep.gender = data['gender']
        sheep.dob = datetime.strptime(data['dob'], "%Y-%m-%d").date()
        sheep.pregnant = (data.get('pregnant', 'false').lower() == 'true') if sheep.gender.lower() == 'female' else None
        sheep.weight = float(data['weight']) if data.get('weight') else None
        sheep.breed = data.get('breed')
        sheep.medical_records = data.get('medical_records')
        sheep.mother_id = get_parent_id(data['mother_id']) if data.get('mother_id') else None
        sheep.father_id = get_parent_id(data['father_id']) if data.get('father_id') else None
        sheep.is_lamb = data.get('is_lamb', 'false').lower() == 'true'

        image_url = data.get('image_url')
        if image_url is not None:
            sheep.image = image_url

        db.session.commit()
        return jsonify({'message': 'Sheep updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ────────────────────────────────────────────────────────────
@app.route('/sheep/<int:sheep_id>', methods=['DELETE'])
def delete_sheep(sheep_id):
    sheep = Sheep.query.get_or_404(sheep_id)
    db.session.delete(sheep)
    db.session.commit()
    return jsonify({"message": f"Sheep {sheep.tag_id} deleted"})

# ────────────────────────────────────────────────────────────
@app.errorhandler(404)
def resource_not_found(e):
    return jsonify({"error": "Resource not found"}), 404
