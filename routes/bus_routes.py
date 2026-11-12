"""
Bus routes for Bus Campus Connect.
Handles bus fleet management: adding new buses, editing capacity,
updating driver contacts, and toggling active/maintenance statuses.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from routes.auth_routes import login_required, role_required
from models.bus_model import BusModel

bus_bp = Blueprint('bus', __name__, url_prefix='/management/buses')


@bus_bp.route('/')
@login_required
@role_required('management')
def list_buses():
    """List all buses with live capacity metrics and occupancy bars."""
    buses = BusModel.get_all_with_occupancy()
    return render_template('management/buses.html', buses=buses)


@bus_bp.route('/add', methods=['POST'])
@login_required
@role_required('management')
def add_bus():
    """Add a new bus to the college transport fleet."""
    bus_number = request.form.get('bus_number', '').strip().upper()
    bus_name = request.form.get('bus_name', '').strip()
    capacity = request.form.get('capacity', '50').strip()
    driver_name = request.form.get('driver_name', '').strip()
    driver_contact = request.form.get('driver_contact', '').strip()
    status = request.form.get('status', 'Active').strip()

    if not all([bus_number, bus_name, capacity, driver_name, driver_contact]):
        flash("All bus fields are required.", "danger")
        return redirect(url_for('bus.list_buses'))

    try:
        cap_val = int(capacity)
        if cap_val <= 0:
            raise ValueError()
    except ValueError:
        flash("Capacity must be a positive integer.", "danger")
        return redirect(url_for('bus.list_buses'))

    existing = BusModel.get_by_number(bus_number)
    if existing:
        flash(f"Bus number {bus_number} already exists.", "danger")
        return redirect(url_for('bus.list_buses'))

    BusModel.add_bus(bus_number, bus_name, cap_val, driver_name, driver_contact, status)
    flash(f"Bus {bus_number} ({bus_name}) successfully added to fleet!", "success")
    return redirect(url_for('bus.list_buses'))


@bus_bp.route('/edit/<int:bus_id>', methods=['POST'])
@login_required
@role_required('management')
def edit_bus(bus_id):
    """Edit bus details and capacity."""
    bus_number = request.form.get('bus_number', '').strip().upper()
    bus_name = request.form.get('bus_name', '').strip()
    capacity = request.form.get('capacity', '50').strip()
    driver_name = request.form.get('driver_name', '').strip()
    driver_contact = request.form.get('driver_contact', '').strip()
    status = request.form.get('status', 'Active').strip()

    try:
        cap_val = int(capacity)
    except ValueError:
        flash("Invalid capacity.", "danger")
        return redirect(url_for('bus.list_buses'))

    BusModel.update_bus(bus_id, bus_number, bus_name, cap_val, driver_name, driver_contact, status)
    flash(f"Bus {bus_number} updated successfully.", "success")
    return redirect(url_for('bus.list_buses'))


@bus_bp.route('/toggle/<int:bus_id>', methods=['POST'])
@login_required
@role_required('management')
def toggle_status(bus_id):
    """Toggle active/inactive status."""
    new_status = BusModel.toggle_status(bus_id)
    flash(f"Bus status updated to {new_status}.", "info")
    return redirect(url_for('bus.list_buses'))

