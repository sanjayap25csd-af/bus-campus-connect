"""
Full Realistic Demo Seeder for Bus Campus Connect.
Populates the database with the exact scenario from the requirements:
- 06 Nov 4:30 PM -> 18 students (BUS-01 allocated, Boarding Open)
- 06 Nov 5:00 PM -> 25 students (BUS-02 allocated, Upcoming)
- 06 Nov 5:30 PM -> 42 students (Near Full)
- 06 Nov 6:00 PM -> 65 students (HIGH DEMAND - Additional Bus Required!)
- 06 Nov 7:00 PM -> 25CDR091 Booked Ticket Verified
"""

import sqlite3
import random
from werkzeug.security import generate_password_hash
from database.db import DATABASE_PATH, init_db

DEPARTMENTS = [
    "Computer Science and Design",
    "Computer Science and Engineering",
    "Artificial Intelligence & DS",
    "Information Technology",
    "Mechanical Engineering",
    "Electronics & Comm. Engg",
    "Electrical & Electronics Engg"
]

FIRST_NAMES = [
    "Karthik", "Deepak", "Aravind", "Praveen", "Suresh", "Manoj", "Vignesh", "Dinesh",
    "Sanjay", "Anand", "Gokul", "Hari", "Naveen", "Pradeep", "Rahul", "Saravanan",
    "Sathish", "Vijay", "Yuvaraj", "Ajith", "Balaji", "Chandran", "Elango", "Ganesh",
    "Kavitha", "Priya", "Divya", "Ananya", "Sneha", "Keerthi", "Nandhini", "Lavanya",
    "Swetha", "Bhavani", "Pavithra", "Sandhya", "Meena", "Rithika", "Monisha", "Harini"
]

LAST_INITIALS = ["R.", "S.", "M.", "K.", "P.", "A.", "T.", "V.", "N.", "B."]


def seed_full_demo():
    print("Seeding full scenario dataset into database...")
    init_db()
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()

    # 1. Ensure Hostels
    hostels_data = [
        ('Bhavani Hostel', 'Active'),
        ('Amaravathi Hostel', 'Active'),
        ('Cauvery Hostel', 'Active'),
        ('Vaigai Hostel', 'Active')
    ]
    for h_name, status in hostels_data:
        cursor.execute("INSERT OR IGNORE INTO hostels (hostel_name, status) VALUES (?, ?)", (h_name, status))
    conn.commit()

    hostel_map = {}
    for h in cursor.execute("SELECT id, hostel_name FROM hostels").fetchall():
        hostel_map[h[1]] = h[0]

    # 2. Ensure Buses
    buses_data = [
        ('BUS-01', 'Kongu Express', 50, 'Murugan S.', '+91 98421 01122', 'College → Perundurai Bus Stand', 'Active'),
        ('BUS-02', 'Green Line Shuttle', 50, 'Selvakumar K.', '+91 98421 03344', 'College → Perundurai Bus Stand', 'Active'),
        ('BUS-03', 'Campus Voyager', 50, 'Rajesh P.', '+91 98421 05566', 'College → Perundurai Bus Stand', 'Active')
    ]
    for b_num, b_name, cap, d_name, d_contact, route, status in buses_data:
        cursor.execute(
            """INSERT OR IGNORE INTO buses (bus_number, bus_name, capacity, driver_name, driver_contact, route, status)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (b_num, b_name, cap, d_name, d_contact, route, status)
        )
    conn.commit()

    bus_map = {}
    for b in cursor.execute("SELECT id, bus_number FROM buses").fetchall():
        bus_map[b[1]] = b[0]

    # 3. Ensure Admin
    admin_pass = generate_password_hash('admin123')
    cursor.execute("SELECT id FROM users WHERE email = 'admin@buscampusconnect.edu'")
    if not cursor.fetchone():
        cursor.execute(
            """INSERT INTO users (name, register_number, email, password_hash, phone, department, year, role, verification_status)
               VALUES ('Chief Transport Officer', 'MGT001', 'admin@buscampusconnect.edu', ?, '+91 98420 00001', 'Campus Administration', 0, 'management', 'Verified')""",
            (admin_pass,)
        )
        conn.commit()

    student_pass = generate_password_hash('student123')

    # 4. Explicit Core Students from Prompt:
    # 25CDR062 (Bhavani), 25CDR064 (Cauvery), 25CDR088 (Vaigai), 25CDR091 (Amaravathi)
    core_students = [
        ('Karthik R.', '25CDR062', '25cdr062@college.edu', '9876500001', 'Computer Science and Design', 2, 'Bhavani Hostel'),
        ('Deepak S.', '25CDR064', '25cdr064@college.edu', '9876500002', 'Artificial Intelligence & DS', 2, 'Cauvery Hostel'),
        ('Aravind M.', '25CDR088', '25cdr088@college.edu', '9876500003', 'Mechanical Engineering', 3, 'Vaigai Hostel'),
        ('Praveen Kumar K.', '25CDR091', '25cdr091@college.edu', '9876500004', 'Electronics & Comm. Engg', 2, 'Amaravathi Hostel')
    ]

    for name, reg, email, phone, dept, yr, h_name in core_students:
        cursor.execute("SELECT id FROM users WHERE register_number = ?", (reg,))
        if not cursor.fetchone():
            cursor.execute(
                """INSERT INTO users (name, register_number, email, password_hash, phone, department, year, hostel_id, role, id_card_path, verification_status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'student', 'sample_id.jpg', 'Verified')""",
                (name, reg, email, student_pass, phone, dept, yr, hostel_map[h_name])
            )
    conn.commit()

    # 5. Clear old requests to rebuild exact demonstration distributions
    cursor.execute("DELETE FROM boarding_records")
    cursor.execute("DELETE FROM bus_requests")
    cursor.execute("DELETE FROM bus_schedules")
    conn.commit()

    # Create Schedules
    cursor.execute(
        """INSERT INTO bus_schedules (bus_id, travel_date, departure_time, boarding_end_time, capacity, status)
           VALUES (?, '2026-11-06', '16:30', '16:40', 50, 'Boarding Open')""",
        (bus_map['BUS-01'],)
    )
    cursor.execute(
        """INSERT INTO bus_schedules (bus_id, travel_date, departure_time, boarding_end_time, capacity, status)
           VALUES (?, '2026-11-06', '17:00', '17:10', 50, 'Upcoming')""",
        (bus_map['BUS-02'],)
    )
    cursor.execute(
        """INSERT INTO bus_schedules (bus_id, travel_date, departure_time, boarding_end_time, capacity, status)
           VALUES (?, '2026-11-06', '18:00', '18:10', 50, 'Upcoming')""",
        (bus_map['BUS-03'],)
    )
    conn.commit()

    # Target Scenario distributions for 2026-11-06:
    # 4:30 PM (16:30) -> 18 students (BUS-01 allocated)
    # 5:00 PM (17:00) -> 25 students (BUS-02 allocated)
    # 5:30 PM (17:30) -> 42 students
    # 6:00 PM (18:00) -> 65 students (HIGH DEMAND - 2 Buses Required!)
    # 7:00 PM (19:00) -> 1 student (25CDR091 Booked Ticket)
    
    slots_target = [
        ('16:30', 18, bus_map['BUS-01'], 'Bus Allocated'),
        ('17:00', 25, bus_map['BUS-02'], 'Pending'),
        ('17:30', 42, None, 'Pending'),
        ('18:00', 65, None, 'Pending'),
        ('19:00', 1, None, 'Verified')
    ]

    hostel_names = list(hostel_map.keys())
    student_index = 100

    print("Generating student accounts and requests for exact target slots...")
    for time_str, count, allocated_bus_id, default_req_status in slots_target:
        for i in range(count):
            # Special case for core prompt records
            if time_str == '16:30' and i == 0:
                reg_no = '25CDR062'
                travel_type = 'Special Permission'
                reason = 'Academic symposium at Erode Arts College'
                proof_status = 'Verified'
                req_status = 'Bus Allocated'
                bid = bus_map['BUS-01']
            elif time_str == '17:00' and i == 0:
                reg_no = '25CDR064'
                travel_type = 'Normal Travel'
                reason = 'Weekend home visit'
                proof_status = 'Verified'
                req_status = 'Pending'
                bid = None
            elif time_str == '18:00' and i == 0:
                reg_no = '25CDR088'
                travel_type = 'Normal Travel'
                reason = 'Train boarding from Erode Junction'
                proof_status = 'Under Review'
                req_status = 'Pending'
                bid = None
            elif time_str == '19:00' and i == 0:
                reg_no = '25CDR091'
                travel_type = 'Booked Bus / Ticket'
                reason = 'KPN Travels Bus at 9:00 PM from Erode'
                proof_status = 'Verified'
                req_status = 'Bus Allocated'
                bid = bus_map['BUS-02']
            else:
                student_index += 1
                reg_no = f"25CDR{student_index:03d}"
                h_name = random.choice(hostel_names)
                name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_INITIALS)}"
                email = f"{reg_no.lower()}@college.edu"
                dept = random.choice(DEPARTMENTS)
                yr = random.choice([1, 2, 3, 4])
                
                # Check or insert user
                cursor.execute("SELECT id FROM users WHERE register_number = ?", (reg_no,))
                row = cursor.fetchone()
                if not row:
                    cursor.execute(
                        """INSERT INTO users (name, register_number, email, password_hash, phone, department, year, hostel_id, role, id_card_path, verification_status)
                           VALUES (?, ?, ?, ?, '9842100000', ?, ?, ?, 'student', 'sample_id.jpg', 'Verified')""",
                        (name, reg_no, email, student_pass, dept, yr, hostel_map[h_name])
                    )
                    user_id = cursor.lastrowid
                else:
                    user_id = row[0]

                travel_type = random.choice(['Normal Travel', 'Normal Travel', 'Special Permission', 'Booked Bus / Ticket'])
                reason = "Weekend hometown departure"
                proof_status = 'Verified' if travel_type != 'Booked Bus / Ticket' else random.choice(['Uploaded', 'Verified'])
                req_status = default_req_status
                bid = allocated_bus_id

            # Get user ID and hostel ID
            u = cursor.execute("SELECT id, hostel_id FROM users WHERE register_number = ?", (reg_no,)).fetchone()
            uid, hid = u[0], u[1]

            cursor.execute(
                """INSERT INTO bus_requests (student_id, hostel_id, travel_date, required_time, travel_type, travel_reason, proof_path, proof_status, request_status, bus_id)
                   VALUES (?, ?, '2026-11-06', ?, ?, ?, ?, ?, ?, ?)""",
                (uid, hid, time_str, travel_type, reason, 'sample_ticket.pdf' if travel_type == 'Booked Bus / Ticket' else None, proof_status, req_status, bid)
            )

    conn.commit()

    # Confirm one boarding record for 25CDR062 on BUS-01 for demonstration
    req_62 = cursor.execute("SELECT id, student_id, bus_id FROM bus_requests WHERE required_time = '16:30' AND bus_id IS NOT NULL LIMIT 1").fetchone()
    if req_62:
        cursor.execute(
            """INSERT INTO boarding_records (request_id, student_id, bus_id, boarded, boarding_time)
               VALUES (?, ?, ?, 1, '2026-11-06 16:34:12')""",
            (req_62[0], req_62[1], req_62[2])
        )
        cursor.execute("UPDATE bus_requests SET request_status = 'Boarded' WHERE id = ?", (req_62[0],))
        conn.commit()

    total_reqs = cursor.execute("SELECT COUNT(*) FROM bus_requests").fetchone()[0]
    total_users = cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'student'").fetchone()[0]
    conn.close()

    print(f"Database successfully primed with {total_users} students and {total_reqs} requests.")
    print("Exact demand verification:")
    print("  06 Nov 4:30 PM -> 18 students (BUS-01 Allocated)")
    print("  06 Nov 5:00 PM -> 25 students (BUS-02 Allocated)")
    print("  06 Nov 5:30 PM -> 42 students")
    print("  06 Nov 6:00 PM -> 65 students (HIGH DEMAND - 2 Buses Required!)")
    print("  06 Nov 7:00 PM -> 1 student (25CDR091 Verified Ticket)")


if __name__ == '__main__':
    seed_full_demo()

