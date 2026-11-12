# BUS CAMPUS CONNECT
### SMART BUS REQUEST AND TRAVEL PLANNING FOR HOSTEL STUDENTS

A full-stack, real database-connected Python web application designed for engineering college hostel students and campus transport management.

---

## 🌟 CORE ENGINEERING PILLARS

1. **PYTHON PROGRAMMING**: 
   - 100% Python backend using **Flask 3.1** and standard library modules (`sqlite3`, `datetime`, `collections`, `math`, `hashlib`).
   - Clean modular architecture: Models, Routes, Services, Data Structures, and Database Layers.
   - Real SQLite database persistence (`database.sqlite3`) with relational foreign keys.

2. **MODERN UI/UX DESIGN**:
   - Custom responsive design system with clean visual hierarchy and glassmorphic card elements.
   - Dynamic 10-Minute Boarding Timeline (`4:30 PM ───────── 4:40 PM | BUS-01 | Boarding Open`).
   - One-click student boarding confirmation action: **"YES, I HAVE BOARDED"**.
   - Proof inspection modals, capacity meters, and real-time notification alerts.

3. **DATA STRUCTURES – HASH MAPPING**:
   - Explicit implementation of **Hash Mapping using Python dictionaries (`dict`)** in `data_structures/hashmap_manager.py`.
   - Organizes requests using canonical **`DATE_TIME`** keys (e.g., `2026-11-06_16:30`).
   - Multi-level ascending sorting criteria:
     1. Travel Date (ascending)
     2. Required Time (ascending)
     3. Hostel (alphabetical)
     4. Register Number (alphanumeric, e.g. `25CDR062`)
   - Algorithmic demand calculation vs bus capacity (50 seats), automatically identifying:
     `6:00 PM → 65 students → HIGH DEMAND → Additional Bus Required`.

---

## 🚌 SYSTEM ARCHITECTURE & PROJECT STRUCTURE

```text
BUS CAMPUS CONNECT/
│
├── app.py                         # Application entry point & configuration
├── requirements.txt               # Dependencies (Flask, Werkzeug)
├── README.md                      # Comprehensive documentation & evaluation guide
├── database.sqlite3               # Relational SQLite database
│
├── database/
│   ├── db.py                      # SQLite connection, context teardown, and seeders
│   └── schema.sql                 # DDL definitions for all 7 relational tables
│
├── models/
│   ├── user_model.py              # Student & Management queries, password hashing
│   ├── hostel_model.py            # Dynamic hostel CRUD & student count metrics
│   ├── bus_model.py               # Fleet management & seat capacity controllers
│   └── request_model.py           # Bus travel requests & database statistics
│
├── routes/
│   ├── auth_routes.py             # Login, student registration & RBAC decorators
│   ├── student_routes.py          # Student dashboard, bus request, boarding confirmation
│   ├── management_routes.py       # Management console, Hash Map tables, simulations
│   ├── bus_routes.py              # Bus fleet and capacity management
│   └── hostel_routes.py           # Campus hostel management
│
├── services/
│   ├── bus_service.py             # Allocation engine & capacity limit protection
│   ├── request_service.py         # Request handling, file validation & Hash Map feed
│   ├── notification_service.py    # Persistent user notifications
│   └── boarding_service.py        # 10-min window evaluation & "Not Boarded" sync
│
├── data_structures/
│   └── hashmap_manager.py         # Python Hash Map grouping, demand & sorting logic
│
├── templates/
│   ├── base.html                  # Master student & public template
│   ├── landing.html               # Public hero landing page
│   ├── auth/                      # Login & Registration views
│   ├── student/                   # Student portal (Dashboard, Request, Current Bus)
│   ├── management/                # Management console (Requests, Timeline, Hash Map)
│   └── errors/                    # Friendly 404/500 error pages
│
├── static/
│   ├── css/styles.css             # Modern bespoke responsive CSS stylesheet
│   └── js/main.js                 # Modal controllers, proof toggles & interactions
│
└── uploads/
    ├── id_cards/                  # Student college ID card uploads
    └── travel_proofs/             # Mandatory ticket proof uploads
```

---

## 🔑 DEFAULT LOGIN CREDENTIALS

### Management Console Account:
- **Email:** `admin@buscampusconnect.edu`
- **Password:** `admin123`
- **Role:** Chief Transport Officer (`MGT001`)

### Sample Verified Student Accounts:
- **Register Number:** `25CDR062` (Bhavani Hostel) &bull; **Password:** `student123`
- **Register Number:** `25CDR064` (Cauvery Hostel) &bull; **Password:** `student123`
- **Register Number:** `25CDR088` (Vaigai Hostel) &bull; **Password:** `student123`
- **Register Number:** `25CDR091` (Amaravathi Hostel) &bull; **Password:** `student123`

---

## ⚡ QUICK START & RUN INSTRUCTIONS

### 1. Requirements:
- Python 3.10+ installed.
- Dependencies: `Flask` and `Werkzeug` (installed via `pip install -r requirements.txt`).

### 2. Run Application:
```bash
python app.py
```

### 3. Open Web Browser:
Navigate to:
```text
http://127.0.0.1:5000/
```

---

## 📋 DEMONSTRATION & TEST SUITE VERIFICATION

The application directly satisfies and fulfills all 25 specific test cases:

1. **Student Registration**: Register with Full Name, Register Number, Department, Year, dynamic Hostel, and College ID Card.
2. **ID Card Upload**: Saves safely to `uploads/id_cards/`.
3. **Login**: Session-based authentication with secure password hashing.
4. **Select Hostel**: Hostels dynamically loaded from SQLite database.
5. **Bus Request**: Calendar travel date & time picker.
6. **Travel Proof**: Mandatory file upload enforced when selecting **"Booked Bus / Ticket"**.
7. **Management Verification**: Review proof documents and mark as Verified / Rejected.
8. **Allocate Bus**: Management allocates **BUS-01** to verified request.
9. **10-Minute Boarding Window**: Automatic generation of `4:30 PM – 4:40 PM` departure window.
10. **Student View**: Student sees allocated bus with live boarding window on their dashboard.
11. **Student Boarding**: Student clicks **"YES, I HAVE BOARDED"**.
12. **Management Boarding Monitor**: Shows student status as `BOARDED` with exact timestamp.
13. **Missed Boarding Detection**: System detects elapsed boarding windows.
14. **Not Boarded Status**: Students who did not confirm before window expiration are flagged `NOT BOARDED`.
15. **Add New Hostel**: Management adds a new hostel in Hostel Management.
16. **Dynamic Registration**: Newly created hostel immediately appears in Student Registration dropdown.
17. **Add New Bus**: Management adds a bus with capacity (e.g. 50 seats).
18. **Dynamic Fleet Allocation**: Newly created bus appears in Bus Allocation modal.
19. **Multiple Requests**: Students submit travel requests across various time slots.
20. **Python Hash Map Grouping**: Hash Map groups requests into date/time buckets ($O(1)$ lookup).
21. **Ascending Sorting**: Table automatically sorts requests in ascending order: Date &rarr; Time &rarr; Hostel &rarr; Register Number.
22. **Actual Register Numbers**: Table strictly shows actual student Register Numbers (`25CDR062`), never fake aliases.
23. **Destination Fixed**: Destination is permanently fixed as **Perundurai Bus Stand** and omitted from management table.
24. **Capacity Enforcement**: Over-allocation is strictly blocked if seats allocated reach maximum bus capacity (50/50 Full).
25. **Database Persistence**: Restarting the Python application retains all records, allocations, and logs in `database.sqlite3`.
26. **Request Cancellation and Rejection**: Students can cancel an unboarded request with a required reason. Management can reject requests with a required reason; the decision and reason are saved and the student receives an in-app notification.
