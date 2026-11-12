"""
Main Application Entry Point: Bus Campus Connect
Smart Bus Request and Travel Planning for Hostel Students.
A full-stack, database-connected Python web application using Flask and SQLite.
"""

import os
from datetime import datetime
from flask import Flask, render_template, send_from_directory, session, redirect, url_for, abort, flash, request

from database.db import init_db, seed_data_if_empty, close_db
from routes.auth_routes import auth_bp
from routes.student_routes import student_bp
from routes.management_routes import management_bp
from routes.bus_routes import bus_bp
from routes.hostel_routes import hostel_bp
from services.notification_service import NotificationService
from data_structures.hashmap_manager import format_display_time

# Initialize Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'bus_campus_connect_secret_key_2026_salt')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload limit
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(student_bp)
app.register_blueprint(management_bp)
app.register_blueprint(bus_bp)
app.register_blueprint(hostel_bp)

# Teardown database connection after request
app.teardown_appcontext(close_db)


@app.context_processor
def inject_global_data():
    """Inject unread notifications and user session into all Jinja templates."""
    unread_count = 0
    if 'user_id' in session:
        try:
            unread_count = NotificationService.get_unread_count(session['user_id'])
        except Exception:
            unread_count = 0
    return {
        'current_user_name': session.get('name'),
        'current_user_role': session.get('role'),
        'current_user_reg': session.get('register_number'),
        'unread_notification_count': unread_count,
        'now_year': datetime.now().year,
        'destination_fixed': 'Perundurai Bus Stand'
    }


@app.template_filter('time_12hr')
def time_12hr_filter(time_str):
    """Jinja filter to convert 24hr HH:MM to 12hr AM/PM."""
    return format_display_time(time_str)


# ---------------- PUBLIC ROUTES ---------------- #

@app.route('/')
def landing():
    """
    Landing Page:
    Displays 'BUS CAMPUS CONNECT', subtitle, description,
    and direct access buttons for Student Login and Management Login.
    """
    if 'user_id' in session:
        if session.get('role') == 'management':
            return redirect(url_for('management.dashboard'))
        return redirect(url_for('student.dashboard'))
    return render_template('landing.html')


@app.route('/uploads/<folder>/<filename>')
def uploaded_file(folder, filename):
    """
    Secure file delivery endpoint for college ID cards and travel proof documents.
    Requires active user session.
    """
    if 'user_id' not in session:
        abort(403)

    if folder not in ['id_cards', 'travel_proofs']:
        abort(404)

    target_dir = os.path.join(app.config['UPLOAD_FOLDER'], folder)
    return send_from_directory(target_dir, filename)


# ---------------- ERROR HANDLERS ---------------- #

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template('errors/500.html'), 500


@app.errorhandler(413)
def file_too_large(error):
    flash("The uploaded file exceeds the 16MB maximum limit. Please upload a smaller file.", "danger")
    return redirect(request.referrer or url_for('landing'))


# ---------------- INITIALIZATION ---------------- #

def bootstrap_application():
    """Ensure database tables and initial seed data are primed."""
    os.makedirs(os.path.join(UPLOAD_FOLDER, 'id_cards'), exist_ok=True)
    os.makedirs(os.path.join(UPLOAD_FOLDER, 'travel_proofs'), exist_ok=True)
    init_db()
    seed_data_if_empty()


bootstrap_application()

if __name__ == '__main__':
    # Run development server
    app.run(host='127.0.0.1', port=5000, debug=True)

