import os
import uuid
import hashlib
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, current_app, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, SkinProfile, LifestyleProfile, AllergyProfile, DietProfile, Image, AnalysisResult
from werkzeug.utils import secure_filename
from analysis.pipeline import generate_report
from analysis.ai_analysis import generate_ai_analysis

profile_bp = Blueprint('profile', __name__)


def _image_urls(filenames):
    return [url_for('static', filename=f'uploads/{name}') for name in (filenames or [])]


def _serialize_profile(profile):
    if not profile:
        return None
    serialized = {}
    for column in profile.__table__.columns:
        if column.name in ('id', 'user_id'):
            continue
        serialized[column.name] = getattr(profile, column.name)
    return serialized


def _serialize_result(result, include_images=True):
    data = {
        'id': result.id,
        'username': result.user.username if result.user else None,
        'status': result.status,
        'images_analyzed': result.images_analyzed,
        'images_skipped': result.images_skipped,
        'overall_skin_health_score': result.overall_skin_health_score,
        'metrics': result.metrics,
        'stage_details': result.stage_details,
        'ai_analysis': result.ai_analysis,
        'message': result.message,
        'created_at': result.created_at.isoformat(),
        'intake_summary': {
            'skin_profile': _serialize_profile(result.user.skin_profile) if result.user else None,
            'lifestyle_profile': _serialize_profile(result.user.lifestyle_profile) if result.user else None,
            'allergy_profile': _serialize_profile(result.user.allergy_profile) if result.user else None,
            'diet_profile': _serialize_profile(result.user.diet_profile) if result.user else None,
        }
    }
    if include_images:
        data['images'] = _image_urls(result.image_filenames)
    return data

def _profile_to_dict(profile, fields):
    if not profile:
        return None
    return {f: getattr(profile, f) for f in fields}


@profile_bp.route('/intake', methods=['GET'])
@jwt_required()
def get_intake():
    user_id = int(get_jwt_identity())
    skin = SkinProfile.query.filter_by(user_id=user_id).first()
    lifestyle = LifestyleProfile.query.filter_by(user_id=user_id).first()
    allergy = AllergyProfile.query.filter_by(user_id=user_id).first()
    diet = DietProfile.query.filter_by(user_id=user_id).first()

    return jsonify({
        'skin_profile': _profile_to_dict(skin, [
            'skin_type', 'skin_tone', 'sensitivity_level', 'acne_level',
            'pigmentation_level', 'skin_concerns', 'pore_size',
            'under_eye_issue', 'lip_condition', 'seasonal_skin_changes',
        ]),
        'lifestyle_profile': _profile_to_dict(lifestyle, [
            'sleep_hours', 'stress_level', 'exercise_frequency', 'screen_time',
            'sunscreen_usage', 'face_washing_frequency', 'makeup_usage',
            'pollution_exposure', 'occupation_type',
        ]),
        'allergy_profile': _profile_to_dict(allergy, [
            'has_known_allergy', 'allergy_type',
            'reaction_symptoms', 'reaction_severity', 'visited_dermatologist',
            'taking_medication', 'additional_allergy_info',
        ]),
        'diet_profile': _profile_to_dict(diet, [
            'diet_type', 'water_intake_liters', 'sugar_consumption',
            'fruits_veggies_intake', 'fast_food_freq', 'alcohol_smoking',
            'tea_coffee_intake',
        ]),
    }), 200


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
    # accept list or comma-separated string for multi-select fields
    sc = data.get('skin_concerns', profile.skin_concerns)
    if isinstance(sc, str):
        sc = [s.strip() for s in sc.split(',')] if sc else None
    profile.skin_concerns = sc
    profile.pore_size = data.get('pore_size', profile.pore_size)
    ue = data.get('under_eye_issue', profile.under_eye_issue)
    if isinstance(ue, str):
        ue = [s.strip() for s in ue.split(',')] if ue else None
    profile.under_eye_issue = ue
    lc = data.get('lip_condition', profile.lip_condition)
    if isinstance(lc, str):
        lc = [s.strip() for s in lc.split(',')] if lc else None
    profile.lip_condition = lc
    profile.seasonal_skin_changes = data.get('seasonal_skin_changes', profile.seasonal_skin_changes)
    profile.additional_concern = data.get('additional_concern', profile.additional_concern)
    
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
    mc = data.get('medical_conditions', profile.medical_conditions)
    if isinstance(mc, str):
        mc = [s.strip() for s in mc.split(',')] if mc else None
    profile.medical_conditions = mc
    profile.medical_conditions_other = data.get('medical_conditions_other', profile.medical_conditions_other)
    
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
    at = data.get('allergy_type', profile.allergy_type)
    if isinstance(at, str):
        at = [s.strip() for s in at.split(',')] if at else None
    profile.allergy_type = at
    profile.reaction_symptoms = data.get('reaction_symptoms', profile.reaction_symptoms)
    profile.reaction_severity = data.get('reaction_severity', profile.reaction_severity)
    profile.visited_dermatologist = data.get('visited_dermatologist', profile.visited_dermatologist)
    profile.taking_medication = data.get('taking_medication', profile.taking_medication)
    profile.additional_allergy_info = data.get('additional_allergy_info', profile.additional_allergy_info)
    profile.skin_medication = data.get('skin_medication', profile.skin_medication)
    profile.recent_treatment = data.get('recent_treatment', profile.recent_treatment)
    profile.recent_treatment_other = data.get('recent_treatment_other', profile.recent_treatment_other)
    
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
    profile.supplements = data.get('supplements', profile.supplements)
    profile.supplements_text = data.get('supplements_text', profile.supplements_text)
    dp = data.get('diet_preferences', profile.diet_preferences)
    if isinstance(dp, str):
        dp = [s.strip() for s in dp.split(',')] if dp else None
    profile.diet_preferences = dp
    profile.diet_additional_notes = data.get('diet_additional_notes', profile.diet_additional_notes)
    
    db.session.commit()
    return jsonify({"msg": "Diet profile updated"}), 200

@profile_bp.route('/upload_images', methods=['POST'])
@jwt_required()
def upload_images():
    user_id = int(get_jwt_identity())
    request_id = uuid.uuid4().hex
    
    if 'images' not in request.files:
        return jsonify({"msg": "No images provided"}), 400
        
    files = request.files.getlist('images')
    if len(files) < 3:
        return jsonify({"msg": "Minimum 3 images required"}), 400

    # During testing we allow repeated images so the analysis pipeline can be
    # exercised without needing three new face captures each time.
    for file in files:
        raw_bytes = file.stream.read()
        digest = hashlib.sha256(raw_bytes).hexdigest()
        file.stream.seek(0)
        current_app.logger.info(
            '[%s] upload-check user=%s filename=%s size=%s hash=%s at=%s',
            request_id,
            user_id,
            file.filename,
            len(raw_bytes),
            digest,
            datetime.now(timezone.utc).isoformat(),
        )
        
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
        current_app.logger.info(
            '[%s] saved image user=%s stored_name=%s path=%s',
            request_id,
            user_id,
            unique_filename,
            file_path,
        )

    try:
        db.session.commit()
        intake_context = {
            'skin_profile': _serialize_profile(SkinProfile.query.filter_by(user_id=user_id).first()),
            'lifestyle_profile': _serialize_profile(LifestyleProfile.query.filter_by(user_id=user_id).first()),
            'allergy_profile': _serialize_profile(AllergyProfile.query.filter_by(user_id=user_id).first()),
            'diet_profile': _serialize_profile(DietProfile.query.filter_by(user_id=user_id).first()),
        }
        report = generate_report(saved_paths, intake_context=intake_context, request_id=request_id)
        result = AnalysisResult(
            user_id=user_id,
            status=report['status'],
            images_analyzed=report.get('images_analyzed', 0),
            images_skipped=report.get('images_skipped', 0),
            overall_skin_health_score=report.get('overall_skin_health_score'),
            metrics=report.get('metrics'),
            stage_details=report.get('stage_details'),
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
    except Exception as e:
        current_app.logger.exception('Error during image analysis or DB save')
        try:
            db.session.rollback()
        except Exception:
            pass
        try:
            fallback_report = {
                'status': 'failed',
                'images_analyzed': 0,
                'images_skipped': len(saved_paths),
                'overall_skin_health_score': None,
                'metrics': None,
                'stage_details': None,
                'message': 'Image analysis failed. Please upload new images or click new images and submit again.',
            }
            fallback_result = AnalysisResult(
                user_id=user_id,
                status=fallback_report['status'],
                images_analyzed=fallback_report['images_analyzed'],
                images_skipped=fallback_report['images_skipped'],
                overall_skin_health_score=fallback_report['overall_skin_health_score'],
                metrics=fallback_report['metrics'],
                stage_details=fallback_report['stage_details'],
                message=fallback_report['message'],
                image_filenames=uploaded_files,
            )
            db.session.add(fallback_result)
            db.session.commit()
            return jsonify({
                "msg": "Image analysis failed. Please upload new images or click new images and submit again.",
                "error": str(e),
                "request_id": request_id,
                "status": "failed",
            }), 200
        except Exception:
            current_app.logger.exception('Failed to persist fallback analysis result')
            try:
                db.session.rollback()
            except Exception:
                pass
            return jsonify({
                "msg": "Internal server error",
                "error": str(e),
                "request_id": request_id
            }), 500


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


@profile_bp.route('/reports/<int:report_id>/ai-analysis', methods=['POST'])
@jwt_required()
def get_ai_analysis(report_id):
    user_id = int(get_jwt_identity())
    result = AnalysisResult.query.filter_by(id=report_id, user_id=user_id).first()
    if not result:
        return jsonify({"msg": "Report not found"}), 404
    if result.status != 'ok':
        return jsonify({"msg": "This report has no analysis to summarize"}), 400

    if not current_app.config.get('OPENROUTER_API_KEY'):
        return jsonify({"msg": "AI analysis is not configured on this server"}), 503

    try:
        ai_analysis = generate_ai_analysis(_serialize_result(result, include_images=False))
    except Exception as e:
        return jsonify({"msg": f"AI analysis failed: {e}"}), 502

    result.ai_analysis = ai_analysis
    db.session.commit()

    return jsonify({"ai_analysis": ai_analysis}), 200
