from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    gender = db.Column(db.String(30))
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    skin_profile = db.relationship('SkinProfile', backref='user', uselist=False, cascade="all, delete-orphan")
    lifestyle_profile = db.relationship('LifestyleProfile', backref='user', uselist=False, cascade="all, delete-orphan")
    allergy_profile = db.relationship('AllergyProfile', backref='user', uselist=False, cascade="all, delete-orphan")
    diet_profile = db.relationship('DietProfile', backref='user', uselist=False, cascade="all, delete-orphan")
    images = db.relationship('Image', backref='user', cascade="all, delete-orphan")
    analysis_results = db.relationship(
        'AnalysisResult', backref='user', cascade="all, delete-orphan",
        order_by='AnalysisResult.created_at.desc()'
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class SkinProfile(db.Model):
    __tablename__ = 'skin_profiles'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    skin_type = db.Column(db.String(50)) # oily, dry, combination, normal, sensitive
    skin_tone = db.Column(db.String(50))
    sensitivity_level = db.Column(db.String(50))
    acne_level = db.Column(db.String(50))
    pigmentation_level = db.Column(db.String(50))
    skin_concerns = db.Column(db.JSON)
    pore_size = db.Column(db.String(50))
    under_eye_issue = db.Column(db.JSON)
    lip_condition = db.Column(db.JSON)
    additional_concern = db.Column(db.Text)
    seasonal_skin_changes = db.Column(db.String(50))

class LifestyleProfile(db.Model):
    __tablename__ = 'lifestyle_profiles'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    sleep_hours = db.Column(db.Integer)
    stress_level = db.Column(db.String(50)) # low, medium, high
    sun_exposure = db.Column(db.String(50)) # low, medium, high
    smoking_habit = db.Column(db.String(50))
    exercise_frequency = db.Column(db.String(50))
    screen_time = db.Column(db.String(50))
    sunscreen_usage = db.Column(db.String(50))
    face_washing_frequency = db.Column(db.String(50))
    makeup_usage = db.Column(db.String(50))
    pollution_exposure = db.Column(db.String(50))
    occupation_type = db.Column(db.String(50))
    medical_conditions = db.Column(db.JSON)
    medical_conditions_other = db.Column(db.Text)

class AllergyProfile(db.Model):
    __tablename__ = 'allergy_profiles'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    has_known_allergy = db.Column(db.String(50))
    allergy_type = db.Column(db.JSON)
    reactive_ingredients = db.Column(db.String(200))
    reaction_symptoms = db.Column(db.String(100))
    reaction_severity = db.Column(db.String(50))
    visited_dermatologist = db.Column(db.String(50))
    taking_medication = db.Column(db.String(50))
    additional_allergy_info = db.Column(db.Text)
    skin_medication = db.Column(db.String(50))
    recent_treatment = db.Column(db.String(100))
    recent_treatment_other = db.Column(db.Text)

class DietProfile(db.Model):
    __tablename__ = 'diet_profiles'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    diet_type = db.Column(db.String(50)) # veg, non-veg, vegan, etc.
    water_intake_liters = db.Column(db.Float)
    sugar_consumption = db.Column(db.String(100)) # Changed to allow more text
    fruits_veggies_intake = db.Column(db.String(100))
    fast_food_freq = db.Column(db.String(100))
    alcohol_smoking = db.Column(db.String(100))
    tea_coffee_intake = db.Column(db.String(100))
    supplements = db.Column(db.String(10))
    supplements_text = db.Column(db.Text)
    diet_preferences = db.Column(db.JSON)
    diet_additional_notes = db.Column(db.Text)

class Image(db.Model):
    __tablename__ = 'images'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

class AnalysisResult(db.Model):
    __tablename__ = 'analysis_results'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False)  # ok, failed
    images_analyzed = db.Column(db.Integer, default=0)
    images_skipped = db.Column(db.Integer, default=0)
    overall_skin_health_score = db.Column(db.Float)
    metrics = db.Column(db.JSON)
    stage_details = db.Column(db.JSON)
    ai_analysis = db.Column(db.Text)
    message = db.Column(db.Text)
    image_filenames = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
