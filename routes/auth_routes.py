"""
Authentication routes for Bus Campus Connect.
Handles student registration, student login, management login, logout,
and role-based access control decorators.
"""

from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g
from models.user_model import UserModel
from models.hostel_model import HostelModel
from services.request_service import RequestService
from services.notification_service import NotificationService

auth_bp = Blueprint('auth', __name__)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('auth.login_student'))
        return f(*args, **kwargs)
    return decorated_function


def role_required(required_role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash("Please log in to access this page.", "warning")
                return redirect(url_for('auth.login_student'))
            if session.get('role') != required_role:
                flash(f"Unauthorized. Access restricted to {required_role} accounts.", "danger")
                if session.get('role') == 'management':
                    return redirect(url_for('management.dashboard'))
                else:
                    return redirect(url_for('student.dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@auth_bp.route('/login')
def login():
    """Default login route that redirects to student login."""
    return redirect(url_for('auth.login_student'))


@auth_bp.route('/login/student', methods=['GET', 'POST'])
def login_student():
    """Student Login with Register Number or Email."""
    if 'user_id' in session:
        if session.get('role') == 'student':
            return redirect(url_for('student.dashboard'))
        return redirect(url_for('management.dashboard'))

    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '')

        if not identifier or not password:
            flash("Please enter your Register Number / Email and password.", "danger")
            return render_template('auth/student_login.html')

        # Check by register number first, then by email
        user = UserModel.get_by_register_number(identifier)
        if not user:
            user = UserModel.get_by_email(identifier)

        if not user or user['role'] != 'student':
            flash("Invalid credentials or student account not found.", "danger")
            return render_template('auth/student_login.html')

        if not UserModel.verify_password(password, user['password_hash']):
            flash("Incorrect password. Please try again.", "danger")
            return render_template('auth/student_login.html')

        # Successful login
        session.clear()
        session['user_id'] = user['id']
        session['name'] = user['name']
        session['register_number'] = user['register_number']
        session['role'] = user['role']
        session['email'] = user['email']

        flash(f"Welcome back, {user['name']}!", "success")
        return redirect(url_for('student.dashboard'))

    return render_template('auth/student_login.html')


@auth_bp.route('/login/management', methods=['GET', 'POST'])
def login_management():
    """Secure Management Login."""
    if 'user_id' in session:
        if session.get('role') == 'management':
            return redirect(url_for('management.dashboard'))
        return redirect(url_for('student.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not email or not password:
            flash("Please enter management email and password.", "danger")
            return render_template('auth/management_login.html')

        user = UserModel.get_by_email(email)

        if not user or user['role'] != 'management':
            flash("Invalid management credentials.", "danger")
            return render_template('auth/management_login.html')

        if not UserModel.verify_password(password, user['password_hash']):
            flash("Incorrect password.", "danger")
            return render_template('auth/management_login.html')

        session.clear()
        session['user_id'] = user['id']
        session['name'] = user['name']
        session['register_number'] = user['register_number']
        session['role'] = user['role']
        session['email'] = user['email']

        flash(f"Welcome to Management Dashboard, {user['name']}!", "success")
        return redirect(url_for('management.dashboard'))

    return render_template('auth/management_login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    Student Registration:
    Full Name, Register Number, Email, Password, Phone, Department, Year,
    Hostel (dynamically populated from DB), and College ID Card upload.
    """
    hostels = HostelModel.get_all_active()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        register_number = request.form.get('register_number', '').strip().upper()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        phone = request.form.get('phone', '').strip()
        department = request.form.get('department', '').strip()
        year = request.form.get('year', '')
        hostel_id = request.form.get('hostel_id', '')
        id_card_file = request.files.get('id_card')

        # Validation
        if not all([name, register_number, email, password, phone, department, year, hostel_id]):
            flash("Please fill in all required registration fields.", "danger")
            return render_template('auth/student_register.html', hostels=hostels)

        if not hostel_id:
            flash("Please select your hostel.", "danger")
            return render_template('auth/student_register.html', hostels=hostels)

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template('auth/student_register.html', hostels=hostels)

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template('auth/student_register.html', hostels=hostels)

        if UserModel.get_by_register_number(register_number):
            flash(f"Register number {register_number} is already registered.", "danger")
            return render_template('auth/student_register.html', hostels=hostels)

        if UserModel.get_by_email(email):
            flash(f"Email {email} is already registered.", "danger")
            return render_template('auth/student_register.html', hostels=hostels)

        if not id_card_file or id_card_file.filename == '':
            flash("Please upload your college ID card.", "danger")
            return render_template('auth/student_register.html', hostels=hostels)

        try:
            id_card_path = RequestService.save_upload_file(id_card_file, 'id_cards')
        except ValueError as e:
            flash(str(e), "danger")
            return render_template('auth/student_register.html', hostels=hostels)

        new_user_id = UserModel.create_student(
            name=name,
            register_number=register_number,
            email=email,
            password=password,
            phone=phone,
            department=department,
            year=year,
            hostel_id=hostel_id,
            id_card_path=id_card_path
        )

        NotificationService.notify(
            new_user_id,
            "Registration Successful",
            "Welcome to Bus Campus Connect! Your account is created. Management will review your college ID card.",
            "success"
        )

        flash("Registration successful! You can now log in with your Register Number.", "success")
        return redirect(url_for('auth.login_student'))

    return render_template('auth/student_register.html', hostels=hostels)


@auth_bp.route('/logout')
def logout():
    """Logout current user."""
    role = session.get('role')
    session.clear()
    flash("You have been logged out successfully.", "info")
    if role == 'management':
        return redirect(url_for('auth.login_management'))
    return redirect(url_for('auth.login_student'))

