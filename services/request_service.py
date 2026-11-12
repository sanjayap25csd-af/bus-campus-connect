"""
Request Service for Bus Campus Connect.
Handles request submissions, secure file upload validation,
proof verifications, and Hash Map workflow integration.
"""

import os
import uuid
from werkzeug.utils import secure_filename
from models.request_model import RequestModel
from models.user_model import UserModel
from services.notification_service import NotificationService
from data_structures.hashmap_manager import (
    create_request_hashmap,
    calculate_time_slot_demand,
    find_high_demand_slots,
    sort_hashmap_requests,
    get_hashmap_debug_info,
    format_display_time
)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uploads')


def allowed_file(filename):
    """Check if file extension is allowed (jpg, jpeg, png, pdf)."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


class RequestService:
    @staticmethod
    def save_upload_file(file, subfolder='travel_proofs'):
        """Safely saves an uploaded file with a unique filename."""
        if not file or file.filename == '':
            return None
        if not allowed_file(file.filename):
            raise ValueError("Invalid file format. Allowed formats: JPG, JPEG, PNG, PDF.")
        
        ext = file.filename.rsplit('.', 1)[1].lower()
        unique_name = f"{uuid.uuid4().hex[:12]}_{secure_filename(file.filename)}"
        target_dir = os.path.join(UPLOAD_FOLDER, subfolder)
        os.makedirs(target_dir, exist_ok=True)
        file_path = os.path.join(target_dir, unique_name)
        file.save(file_path)
        return unique_name

    @staticmethod
    def submit_bus_request(student_id, travel_date, required_time, travel_type, travel_reason, proof_file=None):
        """
        Validates and saves a student bus request.
        Mandatory proof check if travel_type == 'Booked Bus / Ticket'.
        Destination is always fixed as 'Perundurai Bus Stand'.
        """
        student = UserModel.get_by_id(student_id)
        if not student:
            return False, "Student not found."

        if not student.get('hostel_id'):
            return False, "Please select your hostel in your profile before requesting a bus."

        if not travel_date:
            return False, "Please select a travel date."

        if not required_time:
            return False, "Please select your required departure time."

        if not travel_type:
            return False, "Please select a travel type."

        # Travel proof mandatory check for Booked Bus / Ticket
        proof_filename = None
        if travel_type == 'Booked Bus / Ticket':
            if not proof_file or proof_file.filename == '':
                return False, "Travel proof is mandatory for Booked Bus / Ticket. Please upload your ticket or bus booking document."
            try:
                proof_filename = RequestService.save_upload_file(proof_file, 'travel_proofs')
            except ValueError as e:
                return False, str(e)
        elif proof_file and proof_file.filename != '':
            try:
                proof_filename = RequestService.save_upload_file(proof_file, 'travel_proofs')
            except ValueError as e:
                return False, str(e)

        req_id = RequestModel.create_request(
            student_id=student_id,
            hostel_id=student['hostel_id'],
            travel_date=travel_date,
            required_time=required_time,
            travel_type=travel_type,
            travel_reason=travel_reason,
            proof_path=proof_filename
        )

        # Notify student of submission
        formatted_time = format_display_time(required_time)
        NotificationService.notify(
            student_id,
            "Bus Request Submitted",
            f"Your request for travel on {travel_date} at {formatted_time} to Perundurai Bus Stand has been submitted and is currently being processed.",
            "info"
        )

        return True, "Your bus request has been successfully submitted!"

    @staticmethod
    def get_management_request_view(filters=None):
        """
        Orchestrates the core Hash Map workflow:
        1. Read requests from database using Python.
        2. Generate Date + Time key e.g. '2026-11-06_16:30'.
        3. Insert requests into Python Hash Map (dict).
        4. Group students requesting the same time.
        5. Calculate total demand vs bus capacity (50).
        6. Sort using ascending multi-level key (Date, Time, Hostel, Register Number).
        7. Returns sorted table records and demand analytics.
        """
        raw_requests = RequestModel.get_all_requests_raw(filters)
        active_requests = [
            request for request in raw_requests
            if request['request_status'] not in ['Cancelled', 'Rejected']
        ]
        
        # Build Hash Map
        hash_map = create_request_hashmap(raw_requests)
        
        # Sort Ascending for the Management Request Table
        sorted_requests = sort_hashmap_requests(hash_map)
        
        # Calculate Demand Analytics
        demand_analysis = calculate_time_slot_demand(active_requests, default_bus_capacity=50)
        high_demand_slots = find_high_demand_slots(active_requests, bus_capacity=50)
        hashmap_debug = get_hashmap_debug_info(raw_requests)

        # Format display times for user interface
        for r in sorted_requests:
            r['formatted_time'] = format_display_time(r['required_time'])

        return {
            'sorted_requests': sorted_requests,
            'demand_analysis': demand_analysis,
            'high_demand_slots': high_demand_slots,
            'hashmap_debug': hashmap_debug,
            'raw_count': len(raw_requests)
        }
