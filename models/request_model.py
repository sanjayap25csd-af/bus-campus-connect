"""
Bus Request Model for Bus Campus Connect.
Handles database queries for student bus requests, proof uploads,
management verification, bus allocation, and request status lifecycle.
"""

from database.db import get_db, query_db, execute_db
from datetime import datetime


class RequestModel:
    @staticmethod
    def create_request(student_id, hostel_id, travel_date, required_time, travel_type, travel_reason=None, travel_details=None, proof_path=None):
        """Submit a new bus travel request."""
        student_user = query_db("SELECT verification_status FROM users WHERE id = ?", (student_id,), one=True)
        is_verified_id = student_user and student_user.get('verification_status') == 'Verified'

        if proof_path:
            proof_status = 'Uploaded'
        elif travel_type == 'Booked Bus / Ticket':
            proof_status = 'Under Review'
        elif is_verified_id:
            proof_status = 'Verified'
        else:
            proof_status = 'Not Uploaded'

        initial_status = 'Under Review' if travel_type in ['Booked Bus / Ticket', 'Special Permission'] else 'Pending'

        sql = """
            INSERT INTO bus_requests (
                student_id, hostel_id, travel_date, required_time,
                travel_type, travel_reason, proof_path, proof_status,
                request_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        return execute_db(sql, (
            student_id, hostel_id, travel_date.strip(), required_time.strip(),
            travel_type.strip(), travel_reason, proof_path, proof_status, initial_status
        ))

    @staticmethod
    def get_by_id(request_id):
        """Fetch a single request with all relational details."""
        sql = """
            SELECT r.*, 
                   u.name as student_name, u.register_number, u.phone as student_phone, u.department, u.year,
                   u.id_card_path, u.verification_status as id_card_status,
                   h.hostel_name,
                   b.bus_number, b.bus_name, b.driver_name, b.driver_contact, b.route, b.capacity as bus_capacity
            FROM bus_requests r
            JOIN users u ON r.student_id = u.id
            JOIN hostels h ON r.hostel_id = h.id
            LEFT JOIN buses b ON r.bus_id = b.id
            WHERE r.id = ?
        """
        return query_db(sql, (request_id,), one=True)

    @staticmethod
    def get_student_requests(student_id):
        """Fetch all requests made by a specific student, ordered by travel date desc."""
        sql = """
            SELECT r.*, 
                   u.id_card_path, u.verification_status as id_card_status,
                   h.hostel_name,
                   b.bus_number, b.bus_name, b.driver_name, b.driver_contact, b.route
            FROM bus_requests r
            JOIN users u ON r.student_id = u.id
            JOIN hostels h ON r.hostel_id = h.id
            LEFT JOIN buses b ON r.bus_id = b.id
            WHERE r.student_id = ?
            ORDER BY r.travel_date DESC, r.required_time DESC
        """
        return query_db(sql, (student_id,))

    @staticmethod
    def get_student_active_bus(student_id):
        """
        Fetch the current or upcoming bus allocated to the student.
        Used for the 'YOUR CURRENT BUS' section in student dashboard.
        """
        sql = """
            SELECT r.*,
                   u.register_number, u.name as student_name,
                   h.hostel_name,
                   b.bus_number, b.bus_name, b.driver_name, b.driver_contact, b.route,
                   br.boarded as boarding_confirmed, br.boarding_time
            FROM bus_requests r
            JOIN users u ON r.student_id = u.id
            JOIN hostels h ON r.hostel_id = h.id
            JOIN buses b ON r.bus_id = b.id
            LEFT JOIN boarding_records br ON r.id = br.request_id
            WHERE r.student_id = ? 
              AND r.request_status IN ('Bus Allocated', 'Boarding Open', 'Boarded')
            ORDER BY r.travel_date DESC, r.required_time DESC
            LIMIT 1
        """
        return query_db(sql, (student_id,), one=True)

    @staticmethod
    def get_all_requests_raw(filters=None):
        """
        Fetch all requests with relational joins for Hash Map processing in Python.
        Always retrieves the actual student register_number and hostel_name.
        """
        sql = """
            SELECT r.id, r.student_id, r.hostel_id, r.travel_date, r.required_time,
                   r.travel_type, r.travel_reason, r.proof_path, r.proof_status,
                   r.request_status, r.bus_id, r.cancellation_reason, r.created_at, r.updated_at,
                   u.register_number, u.name as student_name, u.phone as student_phone,
                   u.department, u.year, u.id_card_path, u.verification_status as id_card_status,
                   h.hostel_name,
                   b.bus_number, b.bus_name, b.capacity as bus_capacity
            FROM bus_requests r
            JOIN users u ON r.student_id = u.id
            JOIN hostels h ON r.hostel_id = h.id
            LEFT JOIN buses b ON r.bus_id = b.id
            WHERE 1=1
        """
        params = []
        if filters:
            if filters.get('travel_date'):
                sql += " AND r.travel_date = ?"
                params.append(filters['travel_date'])
            if filters.get('travel_type') and filters['travel_type'] != 'all':
                sql += " AND r.travel_type = ?"
                params.append(filters['travel_type'])
            if filters.get('hostel_id') and filters['hostel_id'] != 'all':
                sql += " AND r.hostel_id = ?"
                params.append(filters['hostel_id'])
            if filters.get('request_status') and filters['request_status'] != 'all':
                sql += " AND r.request_status = ?"
                params.append(filters['request_status'])

        return query_db(sql, params)

    @staticmethod
    def update_proof_status(request_id, proof_status, new_request_status=None):
        """Update proof verification status and optionally update request status."""
        if new_request_status:
            sql = "UPDATE bus_requests SET proof_status = ?, request_status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
            execute_db(sql, (proof_status, new_request_status, request_id))
        else:
            sql = "UPDATE bus_requests SET proof_status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
            execute_db(sql, (proof_status, request_id))

    @staticmethod
    def update_request_status(request_id, request_status):
        """Update request status lifecycle."""
        sql = "UPDATE bus_requests SET request_status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        execute_db(sql, (request_status, request_id))

    @staticmethod
    def allocate_bus(request_id, bus_id):
        """Allocate a specific bus to a request and set status to 'Bus Allocated'."""
        sql = """
            UPDATE bus_requests
            SET bus_id = ?, request_status = 'Bus Allocated', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        execute_db(sql, (bus_id, request_id))

    @staticmethod
    def cancel_request(request_id, student_id, reason):
        """Cancel a request owned by a student before they board."""
        sql = """
            UPDATE bus_requests
            SET request_status = 'Cancelled', cancellation_reason = ?, bus_id = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND student_id = ?
              AND request_status IN ('Pending', 'Under Review', 'Verified', 'Bus Allocated', 'Boarding Open')
        """
        cursor = get_db().execute(sql, (reason, request_id, student_id))
        get_db().commit()
        return cursor.rowcount > 0

    @staticmethod
    def reject_request(request_id, reason):
        """Reject a request from management before it has been boarded."""
        sql = """
            UPDATE bus_requests
            SET request_status = 'Rejected', cancellation_reason = ?, bus_id = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
              AND request_status IN ('Pending', 'Under Review', 'Verified', 'Bus Allocated')
        """
        cursor = get_db().execute(sql, (reason, request_id))
        get_db().commit()
        return cursor.rowcount > 0

    @staticmethod
    def get_dashboard_metrics():
        """
        Compute management dashboard statistics directly from the database.
        No hardcoded values.
        """
        metrics = {}
        metrics['total_students'] = query_db("SELECT COUNT(*) as c FROM users WHERE role = 'student'", one=True)['c']
        metrics['total_hostels'] = query_db("SELECT COUNT(*) as c FROM hostels WHERE status = 'Active'", one=True)['c']
        metrics['total_buses'] = query_db("SELECT COUNT(*) as c FROM buses WHERE status = 'Active'", one=True)['c']
        metrics['total_requests'] = query_db("SELECT COUNT(*) as c FROM bus_requests", one=True)['c']
        metrics['pending_requests'] = query_db("SELECT COUNT(*) as c FROM bus_requests WHERE request_status IN ('Pending', 'Under Review')", one=True)['c']
        metrics['verified_requests'] = query_db("SELECT COUNT(*) as c FROM bus_requests WHERE request_status = 'Verified' OR proof_status = 'Verified'", one=True)['c']
        metrics['allocated_requests'] = query_db("SELECT COUNT(*) as c FROM bus_requests WHERE bus_id IS NOT NULL", one=True)['c']
        metrics['students_boarded'] = query_db("SELECT COUNT(*) as c FROM bus_requests WHERE request_status = 'Boarded'", one=True)['c']
        metrics['students_not_boarded'] = query_db("SELECT COUNT(*) as c FROM bus_requests WHERE request_status = 'Not Boarded'", one=True)['c']
        return metrics
