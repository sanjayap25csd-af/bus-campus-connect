"""
Hostel Model for Bus Campus Connect.
Handles database queries and management for campus hostels.
"""

from database.db import get_db, query_db, execute_db


class HostelModel:
    @staticmethod
    def get_all_active():
        """Fetch all active hostels for student registration and dropdowns."""
        sql = "SELECT * FROM hostels WHERE status = 'Active' ORDER BY hostel_name ASC"
        return query_db(sql)

    @staticmethod
    def get_all_with_counts():
        """Fetch all hostels along with registered student counts for management."""
        sql = """
            SELECT h.id, h.hostel_name, h.status, h.created_at,
                   COUNT(u.id) as student_count
            FROM hostels h
            LEFT JOIN users u ON h.id = u.hostel_id AND u.role = 'student'
            GROUP BY h.id
            ORDER BY h.hostel_name ASC
        """
        return query_db(sql)

    @staticmethod
    def get_by_id(hostel_id):
        """Fetch single hostel by ID."""
        sql = "SELECT * FROM hostels WHERE id = ?"
        return query_db(sql, (hostel_id,), one=True)

    @staticmethod
    def add_hostel(hostel_name, status='Active'):
        """Add a new hostel to the database."""
        sql = "INSERT INTO hostels (hostel_name, status) VALUES (?, ?)"
        return execute_db(sql, (hostel_name.strip(), status))

    @staticmethod
    def update_hostel(hostel_id, hostel_name, status):
        """Update existing hostel name and active status."""
        sql = "UPDATE hostels SET hostel_name = ?, status = ? WHERE id = ?"
        execute_db(sql, (hostel_name.strip(), status, hostel_id))

    @staticmethod
    def toggle_status(hostel_id):
        """Toggle hostel between Active and Inactive."""
        hostel = HostelModel.get_by_id(hostel_id)
        if hostel:
            new_status = 'Inactive' if hostel['status'] == 'Active' else 'Active'
            execute_db("UPDATE hostels SET status = ? WHERE id = ?", (new_status, hostel_id))
            return new_status
        return None

    @staticmethod
    def get_hostel_count():
        """Get total count of active hostels."""
        res = query_db("SELECT COUNT(*) as cnt FROM hostels WHERE status = 'Active'", one=True)
        return res['cnt'] if res else 0

