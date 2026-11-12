"""
User Model for Bus Campus Connect.
Handles database queries and operations for students and management accounts.
"""

from database.db import get_db, query_db, execute_db
from werkzeug.security import generate_password_hash, check_password_hash


class UserModel:
    @staticmethod
    def get_by_id(user_id):
        """Fetch a single user with hostel details by ID."""
        sql = """
            SELECT u.*, h.hostel_name 
            FROM users u
            LEFT JOIN hostels h ON u.hostel_id = h.id
            WHERE u.id = ?
        """
        return query_db(sql, (user_id,), one=True)

    @staticmethod
    def get_by_email(email):
        """Fetch user by email."""
        sql = """
            SELECT u.*, h.hostel_name 
            FROM users u
            LEFT JOIN hostels h ON u.hostel_id = h.id
            WHERE LOWER(u.email) = LOWER(?)
        """
        return query_db(sql, (email.strip(),), one=True)

    @staticmethod
    def get_by_register_number(reg_no):
        """Fetch user by register number (e.g., '25CDR062')."""
        sql = """
            SELECT u.*, h.hostel_name 
            FROM users u
            LEFT JOIN hostels h ON u.hostel_id = h.id
            WHERE UPPER(u.register_number) = UPPER(?)
        """
        return query_db(sql, (reg_no.strip(),), one=True)

    @staticmethod
    def create_student(name, register_number, email, password, phone, department, year, hostel_id, id_card_path):
        """Register a new student with hashed password."""
        password_hash = generate_password_hash(password)
        sql = """
            INSERT INTO users (
                name, register_number, email, password_hash, phone, 
                department, year, hostel_id, role, id_card_path, verification_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'student', ?, 'Pending')
        """
        return execute_db(
            sql,
            (name.strip(), register_number.strip().upper(), email.strip().lower(),
             password_hash, phone.strip(), department.strip(), int(year),
             int(hostel_id), id_card_path)
        )

    @staticmethod
    def update_verification_status(user_id, status):
        """Update student college ID verification status (Pending, Verified, Rejected)."""
        sql = "UPDATE users SET verification_status = ? WHERE id = ?"
        execute_db(sql, (status, user_id))
        if status == 'Verified':
            execute_db("UPDATE bus_requests SET proof_status = 'Verified' WHERE student_id = ? AND proof_status != 'Verified'", (user_id,))
        elif status == 'Rejected':
            execute_db("UPDATE bus_requests SET proof_status = 'Rejected' WHERE student_id = ? AND (proof_path IS NULL OR travel_type = 'Normal Travel')", (user_id,))

    @staticmethod
    def get_all_students(search=None, hostel_filter=None, status_filter=None):
        """Fetch all students with optional search and filters for Management Student Table."""
        sql = """
            SELECT u.id, u.name, u.register_number, u.email, u.phone,
                   u.department, u.year, u.hostel_id, u.id_card_path,
                   u.verification_status, u.created_at, h.hostel_name
            FROM users u
            LEFT JOIN hostels h ON u.hostel_id = h.id
            WHERE u.role = 'student'
        """
        params = []

        if search:
            search_term = f"%{search.strip()}%"
            sql += " AND (u.name LIKE ? OR u.register_number LIKE ? OR u.email LIKE ?)"
            params.extend([search_term, search_term, search_term])

        if hostel_filter and hostel_filter != 'all':
            sql += " AND h.id = ?"
            params.append(hostel_filter)

        if status_filter and status_filter != 'all':
            sql += " AND u.verification_status = ?"
            params.append(status_filter)

        sql += " ORDER BY u.register_number ASC"
        return query_db(sql, params)

    @staticmethod
    def verify_password(plain_password, password_hash):
        """Verify user password against hash."""
        return check_password_hash(password_hash, plain_password)

    @staticmethod
    def get_student_count():
        """Get total number of registered students."""
        res = query_db("SELECT COUNT(*) as cnt FROM users WHERE role = 'student'", one=True)
        return res['cnt'] if res else 0

