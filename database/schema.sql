-- Bus Campus Connect: SQLite Database Schema
-- Smart Bus Request and Travel Planning for Hostel Students

CREATE TABLE IF NOT EXISTS hostels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hostel_name TEXT UNIQUE NOT NULL,
    status TEXT DEFAULT 'Active' CHECK(status IN ('Active', 'Inactive')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    register_number TEXT UNIQUE,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    phone TEXT,
    department TEXT,
    year INTEGER,
    hostel_id INTEGER,
    role TEXT NOT NULL CHECK(role IN ('student', 'management')),
    id_card_path TEXT,
    verification_status TEXT DEFAULT 'Pending' CHECK(verification_status IN ('Pending', 'Verified', 'Rejected')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (hostel_id) REFERENCES hostels (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS buses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bus_number TEXT UNIQUE NOT NULL,
    bus_name TEXT NOT NULL,
    capacity INTEGER NOT NULL DEFAULT 50,
    driver_name TEXT NOT NULL,
    driver_contact TEXT NOT NULL,
    route TEXT NOT NULL DEFAULT 'College → Perundurai Bus Stand',
    status TEXT DEFAULT 'Active' CHECK(status IN ('Active', 'Inactive', 'Maintenance')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bus_requests (
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

CREATE TABLE IF NOT EXISTS bus_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bus_id INTEGER NOT NULL,
    travel_date TEXT NOT NULL,
    departure_time TEXT NOT NULL,
    boarding_end_time TEXT NOT NULL,
    capacity INTEGER NOT NULL DEFAULT 50,
    status TEXT DEFAULT 'Upcoming' CHECK(status IN ('Upcoming', 'Boarding Open', 'Boarding Closing Soon', 'Boarding Closed', 'Departed', 'Completed', 'Cancelled')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bus_id) REFERENCES buses (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS boarding_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    bus_id INTEGER NOT NULL,
    boarded INTEGER DEFAULT 0,
    boarding_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (request_id) REFERENCES bus_requests (id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (bus_id) REFERENCES buses (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    notification_type TEXT DEFAULT 'info',
    is_read INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_users_reg ON users(register_number);
CREATE INDEX IF NOT EXISTS idx_requests_date_time ON bus_requests(travel_date, required_time);
CREATE INDEX IF NOT EXISTS idx_requests_student ON bus_requests(student_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read);
