"""
Hostel routes for Bus Campus Connect.
Handles campus hostel management: adding new hostels, viewing student counts,
and toggling active/inactive status.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from routes.auth_routes import login_required, role_required
from models.hostel_model import HostelModel

hostel_bp = Blueprint('hostel', __name__, url_prefix='/management/hostels')


@hostel_bp.route('/')
@login_required
@role_required('management')
def list_hostels():
    """List all hostels with student count."""
    hostels = HostelModel.get_all_with_counts()
    return render_template('management/hostels.html', hostels=hostels)


@hostel_bp.route('/add', methods=['POST'])
@login_required
@role_required('management')
def add_hostel():
    """Add a new hostel to the campus system."""
    hostel_name = request.form.get('hostel_name', '').strip()
    status = request.form.get('status', 'Active').strip()

    if not hostel_name:
        flash("Hostel name cannot be empty.", "danger")
        return redirect(url_for('hostel.list_hostels'))

    try:
        HostelModel.add_hostel(hostel_name, status)
        flash(f"Hostel '{hostel_name}' has been added! It is now available in Student Registration.", "success")
    except Exception:
        flash(f"A hostel with the name '{hostel_name}' already exists.", "danger")

    return redirect(url_for('hostel.list_hostels'))


@hostel_bp.route('/edit/<int:hostel_id>', methods=['POST'])
@login_required
@role_required('management')
def edit_hostel(hostel_id):
    """Edit existing hostel name and status."""
    hostel_name = request.form.get('hostel_name', '').strip()
    status = request.form.get('status', 'Active').strip()

    if not hostel_name:
        flash("Hostel name is required.", "danger")
        return redirect(url_for('hostel.list_hostels'))

    HostelModel.update_hostel(hostel_id, hostel_name, status)
    flash(f"Hostel updated successfully.", "success")
    return redirect(url_for('hostel.list_hostels'))


@hostel_bp.route('/toggle/<int:hostel_id>', methods=['POST'])
@login_required
@role_required('management')
def toggle_status(hostel_id):
    """Toggle hostel active/inactive status."""
    new_status = HostelModel.toggle_status(hostel_id)
    flash(f"Hostel status changed to {new_status}.", "info")
    return redirect(url_for('hostel.list_hostels'))

