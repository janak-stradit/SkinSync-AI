from flask import Flask, redirect, render_template, url_for
from flask_cors import CORS
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from config import Config
from models import db
from routes.auth import auth_bp
from routes.profile import profile_bp
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    CORS(app)
    db.init_app(app)
    Migrate(app, db)
    JWTManager(app)

    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(profile_bp, url_prefix='/api/profile')

    # Serve the frontend
    @app.route('/')
    def index():
        return redirect(url_for('login_page'))

    @app.route('/login')
    def login_page():
        return render_template('index.html')

    @app.route('/reports/<int:report_id>')
    def report_detail(report_id):
        return render_template('report_detail.html', report_id=report_id)

    @app.route('/reports/<int:report_id>/treatment')
    def treatment_detail(report_id):
        return render_template('treatment_detail.html', report_id=report_id)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
