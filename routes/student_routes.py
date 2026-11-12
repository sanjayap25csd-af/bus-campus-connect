"""
Student routes for Bus Campus Connect.
Handles student dashboard, bus request submission, viewing requests,
checking current bus boarding window, and one-click boarding confirmation.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from routes.auth_routes import login_required, role_required
from models.user_model import UserModel
from models.request_model import RequestModel
from services.request_service import RequestService
from services.boarding_service import BoardingService
from services.notification_service import NotificationService
from data_structures.hashmap_manager import format_display_time

student_bp = Blueprint('student', __name__, url_prefix='/student')


@student_bp.route('/dashboard')
@login_required
@role_required('student')
def dashboard():
    """Student Dashboard with quick actions, active bus, and status highlights."""
    student = UserModel.get_by_id(session['user_id'])
    
    # Auto sync missed boardings
    BoardingService.sync_and_check_missed_boarding()

    # Get active/current bus allocation
    active_bus = RequestModel.get_student_active_bus(session['user_id'])
    boarding_info = None

    if active_bus:
        active_bus['formatted_time'] = format_display_time(active_bus['required_time'])
        window = BoardingService.calculate_boarding_window(active_bus['required_time'], 10)
        active_bus['boarding_window_text'] = window['display_window']

        # Evaluate automatic boarding status
        boarding_info = BoardingService.evaluate_bus_status(
            active_bus['travel_date'], active_bus['required_time'], 10
        )
        active_bus['status_evaluation'] = boarding_info

    # Fetch recent requests
    my_requests = RequestModel.get_student_requests(session['user_id'])
    for r in my_requests:
        r['formatted_time'] = format_display_time(r['required_time'])

    unread_notifications = NotificationService.get_unread_count(session['user_id'])

    return render_template(
        'student/dashboard.html',
        student=student,
        active_bus=active_bus,
        boarding_info=boarding_info,
        requests=my_requests[:5],
        total_requests_count=len(my_requests),
        unread_notifications=unread_notifications
    )


@student_bp.route('/request-bus', methods=['GET', 'POST'])
@login_required
@role_required('student')
def request_bus():
    """Submit a bus request for College -> Perundurai Bus Stand."""
    student = UserModel.get_by_id(session['user_id'])

    if request.method == 'POST':
        travel_date = request.form.get('travel_date', '').strip()
        required_time = request.form.get('required_time', '').strip()
        travel_type = request.form.get('travel_type', '').strip()
        travel_reason = request.form.get('travel_reason', '').strip()
        proof_file = request.files.get('travel_proof')

        success, message = RequestService.submit_bus_request(
            student_id=student['id'],
            travel_date=travel_date,
            required_time=required_time,
            travel_type=travel_type,
            travel_reason=travel_reason,
            proof_file=proof_file
        )

        if success:
            flash(message, "success")
            return redirect(url_for('student.my_requests'))
        else:
            flash(message, "danger")

    return render_template('student/request_bus.html', student=student)


@student_bp.route('/my-requests')
@login_required
@role_required('student')
def my_requests():
    """List all requests submitted by the logged-in student."""
    requests = RequestModel.get_student_requests(session['user_id'])
    for r in requests:
        r['formatted_time'] = format_display_time(r['required_time'])
    return render_template('student/my_requests.html', requests=requests)


@student_bp.route('/boarding')
@student_bp.route('/current-bus')
@login_required
@role_required('student')
def current_bus():
    """Dedicated Current Bus page showing 10-minute window and boarding button."""
    student = UserModel.get_by_id(session['user_id'])
    active_bus = RequestModel.get_student_active_bus(session['user_id'])
    boarding_info = None

    if active_bus:
        active_bus['formatted_time'] = format_display_time(active_bus['required_time'])
        window = BoardingService.calculate_boarding_window(active_bus['required_time'], 10)
        active_bus['boarding_window_text'] = window['display_window']

        boarding_info = BoardingService.evaluate_bus_status(
            active_bus['travel_date'], active_bus['required_time'], 10
        )
        active_bus['status_evaluation'] = boarding_info

    return render_template(
        'student/current_bus.html',
        student=student,
        active_bus=active_bus,
        boarding_info=boarding_info
    )


@student_bp.route('/confirm-boarding', methods=['POST'])
@login_required
@role_required('student')
def confirm_boarding():
    """
    Action: Student clicks "YES, I HAVE BOARDED".
    Records student_id, register_number, bus_id, request_id, actual boarding time,
    and updates status to BOARDED.
    """
    request_id = request.form.get('request_id')
    if not request_id:
        flash("Invalid request ID for boarding confirmation.", "danger")
        return redirect(url_for('student.dashboard'))

    success, message = BoardingService.confirm_student_boarding(request_id, session['user_id'])
    if success:
        flash(message, "success")
    else:
        flash(message, "danger")

    return redirect(request.referrer or url_for('student.my_requests'))


@student_bp.route('/verify-request', methods=['POST'])
@login_required
@role_required('student')
def verify_request():
    """
    Action: Student verifies/confirms their bus request details.
    Updates request_status to 'Verified'.
    """
    request_id = request.form.get('request_id')
    if not request_id:
        flash("Invalid request ID for verification.", "danger")
        return redirect(url_for('student.dashboard'))

    req = RequestModel.get_by_id(request_id)
    if not req or req['student_id'] != session['user_id']:
        flash("Unauthorized or request not found.", "danger")
        return redirect(url_for('student.my_requests'))

    RequestModel.update_request_status(request_id, 'Verified')
    flash(f"Bus request #{request_id} details have been verified by you.", "success")
    return redirect(request.referrer or url_for('student.my_requests'))


@student_bp.route('/cancel-request/<int:request_id>', methods=['POST'])
@login_required
@role_required('student')
def cancel_request(request_id):
    """Cancel an unboarded request and record the student's reason."""
    reason = request.form.get('cancellation_reason', '').strip()
    if not reason or len(reason) > 500:
        flash("Please enter a cancellation reason (up to 500 characters).", "danger")
        return redirect(request.referrer or url_for('student.my_requests'))

    cancelled = RequestModel.cancel_request(request_id, session['user_id'], reason)
    if not cancelled:
        flash("This request could not be cancelled. It may not belong to you or can no longer be cancelled.", "danger")
        return redirect(request.referrer or url_for('student.my_requests'))

    flash("Your request has been cancelled.", "info")
    return redirect(url_for('student.my_requests'))


@student_bp.route('/notifications')
@login_required
@role_required('student')
def notifications():
    """View notifications for student."""
    NotificationService.mark_all_as_read(session['user_id'])
    user_notifications = NotificationService.get_user_notifications(session['user_id'])
    return render_template('student/notifications.html', notifications=user_notifications)


@student_bp.route('/profile')
@login_required
@role_required('student')
def profile():
    """View student profile."""
    student = UserModel.get_by_id(session['user_id'])
    return render_template('student/profile.html', student=student)
