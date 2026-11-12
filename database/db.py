"""
Database module for Bus Campus Connect.
Handles SQLite connection, schema initialization, and initial seed data.
"""

import os
import sqlite3
from flask import g
from werkzeug.security import generate_password_hash

DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database.sqlite3')
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schema.sql')


def get_db():
    """Get database connection for the current Flask request context."""
    if 'db' not in g:
        g.db = sqlite3.connect(
            DATABASE_PATH,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db


def close_db(e=None):
    """Close the database connection at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def query_db(query, args=(), one=False):
    """Convenience helper to query database and return dictionary/dictionaries."""
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (dict(rv[0]) if rv else None) if one else [dict(row) for row in rv]


def execute_db(query, args=(), commit=True):
    """Convenience helper to execute an INSERT/UPDATE/DELETE query."""
    db = get_db()
    cur = db.cursor()
    cur.execute(query, args)
    last_id = cur.lastrowid
    cur.close()
    if commit:
        db.commit()
    return last_id


def init_db():
    """Initialize database tables from schema.sql."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF;")
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())

    request_columns = {
        row['name'] for row in conn.execute("PRAGMA table_info(bus_requests)").fetchall()
    }
    if 'cancellation_reason' not in request_columns:
        conn.execute("ALTER TABLE bus_requests ADD COLUMN cancellation_reason TEXT")

    request_table = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'bus_requests'"
    ).fetchone()
    request_status_definition = (
        request_table['sql'].split("request_status", 1)[1].split(")", 1)[0]
        if request_table else ""
    )
    if request_table and "'Rejected'" not in request_status_definition:
        conn.executescript("""
            CREATE TABLE bus_requests_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                hostel_id INTEGER NOT NULL,
                travel_date TEXT NOT NULL,
                required_time TEXT NOT NULL,
                travel_type TEXT NOT NULL CHECK(travel_type IN ('Normal Travel', 'Special Permission', 'Booked Bus / Ticket')),
                travel_reason TEXT,
                proof_path TEXT,
                proof_status TEXT DEFAULT 'Not Uploaded' CHECK(proof_status IN ('Not Uploaded', 'Uploaded', 'Under Review', 'Verified', 'Rejected')),
                request_status TEXT DEFAULT 'Pending' CHECK(request_status IN ('Pending', 'Under Review', 'Verified', 'Bus Allocated', 'Boarding Open', 'Boarded', 'Not Boarded', 'Cancelled', 'Rejected', 'Completed')),
                bus_id INTEGER,
                cancellation_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (hostel_id) REFERENCES hostels (id) ON DELETE RESTRICT,
                FOREIGN KEY (bus_id) REFERENCES buses (id) ON DELETE SET NULL
            );
            INSERT INTO bus_requests_new (
                id, student_id, hostel_id, travel_date, required_time, travel_type,
                travel_reason, proof_path, proof_status, request_status, bus_id,
                cancellation_reason, created_at, updated_at
            )
            SELECT id, student_id, hostel_id, travel_date, required_time, travel_type,
                   travel_reason, proof_path, proof_status, request_status, bus_id,
                   cancellation_reason, created_at, updated_at
            FROM bus_requests;
            DROP TABLE bus_requests;
            ALTER TABLE bus_requests_new RENAME TO bus_requests;
        """)

    conn.executescript("""
        CREATE INDEX IF NOT EXISTS idx_requests_date_time ON bus_requests(travel_date, required_time);
        CREATE INDEX IF NOT EXISTS idx_requests_student ON bus_requests(student_id);
    """)
    conn.commit()
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.close()


def seed_data_if_empty():
    """Seed initial hostels, buses, management account, and sample data if not present."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()

    # 1. Seed Hostels
    cursor.execute("SELECT COUNT(*) as count FROM hostels")
    if cursor.fetchone()['count'] == 0:
        initial_hostels = [
            ('Bhavani Hostel', 'Active'),
            ('Amaravathi Hostel', 'Active'),
            ('Cauvery Hostel', 'Active'),
            ('Vaigai Hostel', 'Active')
        ]
        cursor.executemany("INSERT INTO hostels (hostel_name, status) VALUES (?, ?)", initial_hostels)
        conn.commit()

    # 2. Seed Buses
    cursor.execute("SELECT COUNT(*) as count FROM buses")
    if cursor.fetchone()['count'] == 0:
        initial_buses = [
            ('BUS-01', 'Kongu Express', 50, 'Murugan S.', '+91 98421 01122', 'College → Perundurai Bus Stand', 'Active'),
            ('BUS-02', 'Green Line Shuttle', 50, 'Selvakumar K.', '+91 98421 03344', 'College → Perundurai Bus Stand', 'Active'),
            ('BUS-03', 'Campus Voyager', 50, 'Rajesh P.', '+91 98421 05566', 'College → Perundurai Bus Stand', 'Active')
        ]
        cursor.executemany(
            """INSERT INTO buses (bus_number, bus_name, capacity, driver_name, driver_contact, route, status) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            initial_buses
        )
        conn.commit()

    # 3. Seed Management Account
    cursor.execute("SELECT id FROM users WHERE email = ?", ('admin@buscampusconnect.edu',))
    if not cursor.fetchone():
        admin_pass = generate_password_hash('admin123')
        cursor.execute(
            """INSERT INTO users (name, register_number, email, password_hash, phone, department, year, hostel_id, role, verification_status)
               VALUES (?, ?, ?, ?, ?, ?, ?, NULL, 'management', 'Verified')""",
            ('Chief Transport Officer', 'MGT001', 'admin@buscampusconnect.edu', admin_pass, '+91 98420 00001', 'Campus Administration', 0)
        )
        conn.commit()

    # 4. Seed Sample Verified Students (From Prompt Examples)
    # Register Numbers: 25CDR062, 25CDR064, 25CDR088, 25CDR091
    sample_students = [
        ('Karthik R.', '25CDR062', '25cdr062@college.edu', '9876500001', 'Computer Science and Design', 2, 'Bhavani Hostel'),
        ('Deepak S.', '25CDR064', '25cdr064@college.edu', '9876500002', 'Artificial Intelligence & DS', 2, 'Cauvery Hostel'),
        ('Aravind M.', '25CDR088', '25cdr088@college.edu', '9876500003', 'Mechanical Engineering', 3, 'Vaigai Hostel'),
        ('Praveen Kumar K.', '25CDR091', '25cdr091@college.edu', '9876500004', 'Electronics & Comm. Engg', 2, 'Amaravathi Hostel')
    ]

    hostel_map = {}
    for h in cursor.execute("SELECT id, hostel_name FROM hostels").fetchall():
        hostel_map[h['hostel_name']] = h['id']

    student_pass = generate_password_hash('student123')
    for name, reg, email, phone, dept, yr, h_name in sample_students:
        cursor.execute("SELECT id FROM users WHERE register_number = ?", (reg,))
        if not cursor.fetchone():
            h_id = hostel_map.get(h_name)
            cursor.execute(
                """INSERT INTO users (name, register_number, email, password_hash, phone, department, year, hostel_id, role, id_card_path, verification_status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'student', 'sample_id.jpg', 'Verified')""",
                (name, reg, email, student_pass, phone, dept, yr, h_id)
            )
            s_id = cursor.lastrowid
            # Seed welcome notification
            cursor.execute(
                """INSERT INTO notifications (user_id, title, message, notification_type, is_read)
                   VALUES (?, 'Welcome to Bus Campus Connect', 'Your student account has been verified. You can now request buses for travel to Perundurai Bus Stand.', 'success', 0)""",
                (s_id,)
            )
    conn.commit()
    conn.close()
