"""
Management routes for Bus Campus Connect.
Handles management dashboard, Hash Map request table (sorted ascending),
bus allocations, ID verifications, schedule timelines, and live boarding monitors.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from routes.auth_routes import login_required, role_required
from models.user_model import UserModel
from models.hostel_model import HostelModel
from models.bus_model import BusModel
from models.request_model import RequestModel
from services.request_service import RequestService
from services.bus_service import BusService
from services.boarding_service import BoardingService
from services.notification_service import NotificationService
from datetime import datetime

management_bp = Blueprint('management', __name__, url_prefix='/management')


def get_current_simulated_time():
    """Retrieve simulated datetime if set in session, otherwise current datetime."""
    sim_str = session.get('simulated_datetime')
    if sim_str:
        try:
            return datetime.strptime(sim_str, "%Y-%m-%d %H:%M")
        except Exception:
            return None
    return None


@management_bp.route('/dashboard')
@login_required
@role_required('management')
def dashboard():
    """
    Management Dashboard:
    Computes all statistics from SQLite (no hardcoding),
    loads demand analysis powered by the Python Hash Map,
    and displays active bus timelines.
    """
    sim_time = get_current_simulated_time()
    BoardingService.sync_and_check_missed_boarding(sim_time)

    metrics = RequestModel.get_dashboard_metrics()
    
    # Run Hash Map workflow for high-demand slots preview
    hashmap_view = RequestService.get_management_request_view()
    
    # Bus timeline data
    timeline = BusService.get_schedule_timeline_data(simulated_datetime=sim_time)
    
    active_buses = BusModel.get_all_with_occupancy()
    recent_requests = hashmap_view['sorted_requests'][:6]
    unread_notifications = NotificationService.get_unread_count(session['user_id'])

    return render_template(
        'management/dashboard.html',
        metrics=metrics,
        high_demand_slots=hashmap_view['high_demand_slots'],
        demand_analysis=hashmap_view['demand_analysis'][:5],
        recent_requests=recent_requests,
        timeline=timeline[:4],
        buses=active_buses,
        unread_notifications=unread_notifications,
        simulated_time_str=session.get('simulated_datetime')
    )


@management_bp.route('/requests')
@login_required
@role_required('management')
def requests_view():
    """
    Management Request Table:
    Explicitly powered by the Python Hash Map (dict)!
    Organizes requests by Date+Time key and sorts strictly in ascending order by:
    1. Travel Date
    2. Required Time
    3. Hostel
    4. Register Number
    Displays actual Register Number (never Student A/B/C) and excludes Destination.
    """
    travel_date = request.args.get('date', '').strip()
    travel_type = request.args.get('travel_type', 'all').strip()
    hostel_id = request.args.get('hostel_id', 'all').strip()
    status_filter = request.args.get('status', 'all').strip()

    filters = {
        'travel_date': travel_date if travel_date else None,
        'travel_type': travel_type,
        'hostel_id': hostel_id,
        'request_status': status_filter
    }

    hashmap_data = RequestService.get_management_request_view(filters)
    hostels = HostelModel.get_all_active()
    buses = BusModel.get_all_with_occupancy(travel_date if travel_date else None)

    return render_template(
        'management/requests.html',
        requests=hashmap_data['sorted_requests'],
        demand_analysis=hashmap_data['demand_analysis'],
        high_demand_slots=hashmap_data['high_demand_slots'],
        hostels=hostels,
        buses=buses,
        selected_filters=filters
    )


@management_bp.route('/requests/verify-proof', methods=['POST'])
@login_required
@role_required('management')
def verify_proof():
    """Verify or reject travel proof for Booked Bus / Ticket or Special Permission."""
    request_id = request.form.get('request_id')
    decision = request.form.get('decision')  # 'Verified' or 'Rejected'
    remarks = request.form.get('remarks', '').strip()

    if not request_id or decision not in ['Verified', 'Rejected']:
        flash("Invalid verification parameters.", "danger")
        return redirect(url_for('management.requests_view'))

    req = RequestModel.get_by_id(request_id)
    if not req:
        flash("Request not found.", "danger")
        return redirect(url_for('management.requests_view'))

    new_req_status = 'Verified' if decision == 'Verified' else 'Under Review'
    RequestModel.update_proof_status(request_id, decision, new_req_status)

    msg = f"Your travel document has been {decision.lower()} by management."
    if remarks:
        msg += f" Remarks: {remarks}"
    NotificationService.notify(req['student_id'], f"Proof {decision}", msg, "success" if decision == 'Verified' else "warning")

    flash(f"Proof has been successfully marked as {decision}.", "success")
    return redirect(url_for('management.requests_view'))


@management_bp.route('/requests/verify-status', methods=['POST'])
@login_required
@role_required('management')
def verify_request_status():
    """Directly verify or update the Request Status for a student bus request."""
    request_id = request.form.get('request_id')
    status = request.form.get('status', 'Verified')

    if not request_id:
        flash("Invalid request identifier.", "danger")
        return redirect(request.referrer or url_for('management.requests_view'))

    req = RequestModel.get_by_id(request_id)
    if not req:
        flash("Request not found.", "danger")
        return redirect(request.referrer or url_for('management.requests_view'))

    RequestModel.update_request_status(request_id, status)

    NotificationService.notify(
        req['student_id'],
        f"Bus Request {status}",
        f"Your transit request #{request_id} for {req['travel_date']} to Perundurai Bus Stand has been marked as {status} by campus logistics.",
        "success" if status == 'Verified' else "info"
    )

    flash(f"Request #{request_id} status has been successfully marked as {status}!", "success")
    return redirect(request.referrer or url_for('management.requests_view'))


@management_bp.route('/requests/reject', methods=['POST'])
@login_required
@role_required('management')
def reject_request():
    """Reject an unboarded student request and notify the student with the reason."""
    request_id = request.form.get('request_id', '').strip()
    reason = request.form.get('cancellation_reason', '').strip()
    if not request_id or not reason or len(reason) > 500:
        flash("A request identifier and rejection reason (up to 500 characters) are required.", "danger")
        return redirect(request.referrer or url_for('management.requests_view'))

    req = RequestModel.get_by_id(request_id)
    if not req:
        flash("Request not found.", "danger")
        return redirect(request.referrer or url_for('management.requests_view'))

    if not RequestModel.reject_request(request_id, reason):
        flash("This request can no longer be rejected.", "danger")
        return redirect(request.referrer or url_for('management.requests_view'))

    NotificationService.notify(
        req['student_id'],
        "Bus Request Rejected",
        f"Your bus request #{request_id} for {req['travel_date']} has been rejected by management. Reason: {reason}",
        "warning"
    )
    flash(f"Request #{request_id} was rejected and the student was notified.", "success")
    return redirect(request.referrer or url_for('management.requests_view'))


@management_bp.route('/requests/allocate-bus', methods=['POST'])
@login_required
@role_required('management')
def allocate_bus():
    """
    Allocates a bus to a student request.
    Strictly checks capacity to prevent over-allocation!
    Generates the default 10-minute boarding window.
    """
    request_id = request.form.get('request_id')
    bus_id = request.form.get('bus_id')

    if not request_id or not bus_id:
        flash("Please select both a request and a bus.", "danger")
        return redirect(url_for('management.requests_view'))

    success, message = BusService.allocate_bus_to_request(request_id, bus_id)
    if success:
        flash(message, "success")
    else:
        flash(message, "danger")

    return redirect(url_for('management.requests_view'))


@management_bp.route('/students')
@login_required
@role_required('management')
def students_view():
    """
    Management Student Table:
    Register Number | Name | Hostel | Department | Year | Phone | ID Status
    Supports search, filter, and ID Card verification.
    """
    search = request.args.get('q', '').strip()
    hostel_filter = request.args.get('hostel', 'all').strip()
    status_filter = request.args.get('status', 'all').strip()

    students = UserModel.get_all_students(search, hostel_filter, status_filter)
    hostels = HostelModel.get_all_active()

    return render_template(
        'management/students.html',
        students=students,
        hostels=hostels,
        search=search,
        selected_hostel=hostel_filter,
        selected_status=status_filter
    )


@management_bp.route('/students/verify-id', methods=['POST'])
@login_required
@role_required('management')
def verify_student_id():
    """Approve or reject student college ID card."""
    user_id = request.form.get('user_id')
    decision = request.form.get('decision')  # 'Verified' or 'Rejected'

    if not user_id or decision not in ['Verified', 'Rejected']:
        flash("Invalid student verification request.", "danger")
        return redirect(url_for('management.students_view'))

    UserModel.update_verification_status(user_id, decision)
    
    NotificationService.notify(
        user_id,
        f"College ID Card {decision}",
        f"Your uploaded college ID card has been reviewed and marked as {decision} by management.",
        "success" if decision == 'Verified' else "danger"
    )

    flash(f"Student ID card successfully marked as {decision}.", "success")
    return redirect(request.referrer or url_for('management.students_view'))


@management_bp.route('/schedule')
@login_required
@role_required('management')
def schedule_view():
    """
    Bus Schedule Table & Dynamic Timeline:
    Date | Bus | Start Time | Boarding Ends (10 min window) | Allocated Students | Capacity | Available Seats | Status.
    """
    sim_time = get_current_simulated_time()
    travel_date = request.args.get('date', '').strip()
    
    timeline = BusService.get_schedule_timeline_data(
        travel_date if travel_date else None,
        simulated_datetime=sim_time
    )

    return render_template(
        'management/schedule.html',
        timeline=timeline,
        selected_date=travel_date,
        simulated_time_str=session.get('simulated_datetime')
    )


@management_bp.route('/boarding-monitor')
@login_required
@role_required('management')
def boarding_monitor():
    """
    Boarding Monitor:
    Shows which students have confirmed boarding, who is pending, and who missed the window.
    """
    sim_time = get_current_simulated_time()
    BoardingService.sync_and_check_missed_boarding(sim_time)

    # Fetch all requests that have been allocated a bus
    from database.db import query_db
    records = query_db("""
        SELECT r.id as request_id, r.travel_date, r.required_time, r.request_status,
               u.register_number, u.name as student_name, u.phone,
               h.hostel_name,
               b.bus_number, b.bus_name,
               br.boarded, br.boarding_time
        FROM bus_requests r
        JOIN users u ON r.student_id = u.id
        JOIN hostels h ON r.hostel_id = h.id
        JOIN buses b ON r.bus_id = b.id
        LEFT JOIN boarding_records br ON r.id = br.request_id
        WHERE r.bus_id IS NOT NULL
        ORDER BY r.travel_date DESC, r.required_time ASC, u.register_number ASC
    """)

    from data_structures.hashmap_manager import format_display_time
    for rec in records:
        rec['formatted_time'] = format_display_time(rec['required_time'])
        window = BoardingService.calculate_boarding_window(rec['required_time'], 10)
        rec['boarding_window_text'] = window['display_window']

    return render_template('management/boarding_monitor.html', records=records)


@management_bp.route('/demand-analysis')
@login_required
@role_required('management')
def demand_analysis():
    """
    Dedicated Data Structure Demonstration Page:
    Shows the Python Hash Map (dict) in action, including key generation,
    bucket inspectability, and capacity demand calculations.
    """
    hashmap_data = RequestService.get_management_request_view()
    return render_template(
        'management/demand_analysis.html',
        hashmap_debug=hashmap_data['hashmap_debug'],
        demand_analysis=hashmap_data['demand_analysis'],
        high_demand_slots=hashmap_data['high_demand_slots']
    )


@management_bp.route('/reports')
@login_required
@role_required('management')
def reports_view():
    """Management Reports: statistics, hostel distribution, travel type breakdown."""
    from database.db import query_db
    hostel_stats = query_db("""
        SELECT h.hostel_name, COUNT(r.id) as request_count
        FROM hostels h
        LEFT JOIN bus_requests r ON h.id = r.hostel_id
        GROUP BY h.id
        ORDER BY request_count DESC
    """)

    type_stats = query_db("""
        SELECT travel_type, COUNT(*) as count 
        FROM bus_requests 
        GROUP BY travel_type
    """)

    metrics = RequestModel.get_dashboard_metrics()

    return render_template(
        'management/reports.html',
        hostel_stats=hostel_stats,
        type_stats=type_stats,
        metrics=metrics
    )


@management_bp.route('/notifications')
@login_required
@role_required('management')
def notifications():
    """View management notifications."""
    NotificationService.mark_all_as_read(session['user_id'])
    user_notifications = NotificationService.get_user_notifications(session['user_id'])
    return render_template('management/notifications.html', notifications=user_notifications)


@management_bp.route('/simulate-time', methods=['POST'])
@login_required
@role_required('management')
def simulate_time():
    """
    Testing & Viva Demonstration Tool:
    Sets simulated date/time so evaluators can test:
    - 4:25 PM -> Upcoming
    - 4:32 PM -> Boarding Open
    - 4:39 PM -> Boarding Closing Soon
    - 4:45 PM -> Boarding Closed / Not Boarded
    """
    sim_date = request.form.get('sim_date', '').strip()
    sim_time = request.form.get('sim_time', '').strip()
    action = request.form.get('action')

    if action == 'reset':
        session.pop('simulated_datetime', None)
        flash("Simulated time cleared. System will use real current wall-clock time.", "info")
    else:
        if sim_date and sim_time:
            comb = f"{sim_date} {sim_time}"
            session['simulated_datetime'] = comb
            flash(f"Time simulator active: Application datetime set to {comb}.", "success")
        else:
            flash("Please provide both simulated date and time.", "warning")

    return redirect(request.referrer or url_for('management.dashboard'))
