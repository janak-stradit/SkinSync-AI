import os
import uuid
from flask import Blueprint, request, jsonify, current_app, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, SkinProfile, LifestyleProfile, AllergyProfile, DietProfile, Image, AnalysisResult
from werkzeug.utils import secure_filename
from analysis.pipeline import generate_report

profile_bp = Blueprint('profile', __name__)


def _image_urls(filenames):
    return [url_for('static', filename=f'uploads/{name}') for name in (filenames or [])]


def _serialize_result(result, include_images=True):
    data = {
        'id': result.id,
        'status': result.status,
        'images_analyzed': result.images_analyzed,
        'images_skipped': result.images_skipped,
        'overall_skin_health_score': result.overall_skin_health_score,
        'metrics': result.metrics,
        'message': result.message,
        'created_at': result.created_at.isoformat(),
    }
    if include_images:
        data['images'] = _image_urls(result.image_filenames)
    return data

@profile_bp.route('/skin', methods=['POST'])
@jwt_required()
def add_skin_profile():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    profile = SkinProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        profile = SkinProfile(user_id=user_id)
        db.session.add(profile)
        
    profile.skin_type = data.get('skin_type', profile.skin_type)
    profile.skin_tone = data.get('skin_tone', profile.skin_tone)
    profile.sensitivity_level = data.get('sensitivity_level', profile.sensitivity_level)
    profile.acne_level = data.get('acne_level', profile.acne_level)
    profile.pigmentation_level = data.get('pigmentation_level', profile.pigmentation_level)
    profile.skin_concerns = data.get('skin_concerns', profile.skin_concerns)
    profile.pore_size = data.get('pore_size', profile.pore_size)
    profile.under_eye_issue = data.get('under_eye_issue', profile.under_eye_issue)
    profile.lip_condition = data.get('lip_condition', profile.lip_condition)
    profile.seasonal_skin_changes = data.get('seasonal_skin_changes', profile.seasonal_skin_changes)
    
    db.session.commit()
    return jsonify({"msg": "Skin profile updated"}), 200

@profile_bp.route('/lifestyle', methods=['POST'])
@jwt_required()
def add_lifestyle_profile():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    profile = LifestyleProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        profile = LifestyleProfile(user_id=user_id)
        db.session.add(profile)
        
    profile.sleep_hours = data.get('sleep_hours', profile.sleep_hours)
    profile.stress_level = data.get('stress_level', profile.stress_level)
    profile.sun_exposure = data.get('sun_exposure', profile.sun_exposure)
    profile.smoking_habit = data.get('smoking_habit', profile.smoking_habit)
    profile.exercise_frequency = data.get('exercise_frequency', profile.exercise_frequency)
    profile.screen_time = data.get('screen_time', profile.screen_time)
    profile.sunscreen_usage = data.get('sunscreen_usage', profile.sunscreen_usage)
    profile.face_washing_frequency = data.get('face_washing_frequency', profile.face_washing_frequency)
    profile.makeup_usage = data.get('makeup_usage', profile.makeup_usage)
    profile.pollution_exposure = data.get('pollution_exposure', profile.pollution_exposure)
    profile.occupation_type = data.get('occupation_type', profile.occupation_type)
    
    db.session.commit()
    return jsonify({"msg": "Lifestyle profile updated"}), 200

@profile_bp.route('/allergy', methods=['POST'])
@jwt_required()
def add_allergy_profile():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    profile = AllergyProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        profile = AllergyProfile(user_id=user_id)
        db.session.add(profile)
        
    profile.has_known_allergy = data.get('has_known_allergy', profile.has_known_allergy)
    profile.allergy_type = data.get('allergy_type', profile.allergy_type)
    profile.reactive_ingredients = data.get('reactive_ingredients', profile.reactive_ingredients)
    profile.reaction_symptoms = data.get('reaction_symptoms', profile.reaction_symptoms)
    profile.reaction_severity = data.get('reaction_severity', profile.reaction_severity)
    profile.visited_dermatologist = data.get('visited_dermatologist', profile.visited_dermatologist)
    profile.taking_medication = data.get('taking_medication', profile.taking_medication)
    profile.additional_allergy_info = data.get('additional_allergy_info', profile.additional_allergy_info)
    
    db.session.commit()
    return jsonify({"msg": "Allergy profile updated"}), 200

@profile_bp.route('/diet', methods=['POST'])
@jwt_required()
def add_diet_profile():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    profile = DietProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        profile = DietProfile(user_id=user_id)
        db.session.add(profile)
        
    profile.diet_type = data.get('diet_type', profile.diet_type)
    profile.water_intake_liters = data.get('water_intake_liters', profile.water_intake_liters)
    profile.sugar_consumption = data.get('sugar_consumption', profile.sugar_consumption)
    profile.fruits_veggies_intake = data.get('fruits_veggies_intake', profile.fruits_veggies_intake)
    profile.fast_food_freq = data.get('fast_food_freq', profile.fast_food_freq)
    profile.alcohol_smoking = data.get('alcohol_smoking', profile.alcohol_smoking)
    profile.tea_coffee_intake = data.get('tea_coffee_intake', profile.tea_coffee_intake)
    
    db.session.commit()
    return jsonify({"msg": "Diet profile updated"}), 200

@profile_bp.route('/upload_images', methods=['POST'])
@jwt_required()
def upload_images():
    user_id = int(get_jwt_identity())
    
    if 'images' not in request.files:
        return jsonify({"msg": "No images provided"}), 400
        
    files = request.files.getlist('images')
    if len(files) < 3:
        return jsonify({"msg": "Minimum 3 images required"}), 400
        
    uploaded_files = []
    saved_paths = []

    for file in files:
        if file.filename == '':
            continue

        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)

        # Save to DB
        img_record = Image(user_id=user_id, file_path=unique_filename)
        db.session.add(img_record)
        uploaded_files.append(unique_filename)
        saved_paths.append(file_path)

    db.session.commit()

    report = generate_report(saved_paths)

    result = AnalysisResult(
        user_id=user_id,
        status=report['status'],
        images_analyzed=report.get('images_analyzed', 0),
        images_skipped=report.get('images_skipped', 0),
        overall_skin_health_score=report.get('overall_skin_health_score'),
        metrics=report.get('metrics'),
        message=report.get('message'),
        image_filenames=uploaded_files,
    )
    db.session.add(result)
    db.session.commit()

    return jsonify({
        "msg": "Images uploaded successfully",
        "files": uploaded_files,
        "report": _serialize_result(result)
    }), 200


@profile_bp.route('/reports', methods=['GET'])
@jwt_required()
def list_reports():
    user_id = int(get_jwt_identity())
    results = AnalysisResult.query.filter_by(user_id=user_id) \
        .order_by(AnalysisResult.created_at.desc()).all()
    return jsonify({
        "reports": [_serialize_result(r, include_images=False) for r in results]
    }), 200


@profile_bp.route('/reports/<int:report_id>', methods=['GET'])
@jwt_required()
def get_report(report_id):
    user_id = int(get_jwt_identity())
    result = AnalysisResult.query.filter_by(id=report_id, user_id=user_id).first()
    if not result:
        return jsonify({"msg": "Report not found"}), 404
    return jsonify(_serialize_result(result)), 200
