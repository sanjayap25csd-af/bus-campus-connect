"""
Comprehensive Automated Test Suite for Bus Campus Connect.
Verifies all 25 specific test cases mandated in Section 50 of the requirements.
"""

import os
import io
import sqlite3
from datetime import datetime, timedelta
from app import app
from database.db import get_db, DATABASE_PATH, execute_db
from models.user_model import UserModel
from models.hostel_model import HostelModel
from models.bus_model import BusModel
from models.request_model import RequestModel
from services.bus_service import BusService
from services.boarding_service import BoardingService
from services.request_service import RequestService
from data_structures.hashmap_manager import (
    create_request_hashmap,
    calculate_time_slot_demand,
    find_high_demand_slots,
    sort_hashmap_requests
)


def run_all_tests():
    print("=" * 70)
    print("BUS CAMPUS CONNECT - AUTOMATED VERIFICATION TEST SUITE")
    print("Testing 25 Core Scenarios plus Cancellation and Rejection")
    print("=" * 70)

    with app.app_context():
        client = app.test_client()

        # Clean any prior test user for idempotency
        prior_user = UserModel.get_by_register_number('25CDR099')
        if prior_user:
            execute_db("DELETE FROM users WHERE id = ?", (prior_user['id'],))

        # TEST 1: Register Student
        print("\n[TEST 1] Register Student (25CDR099)...")
        id_card_data = (io.BytesIO(b"Fake ID Card Image"), "id_card.png")
        res = client.post('/register', data={
            'name': 'Sanjay Kumar',
            'register_number': '25CDR099',
            'email': '25cdr099@college.edu',
            'password': 'password123',
            'confirm_password': 'password123',
            'phone': '9876543210',
            'department': 'Computer Science and Design',
            'year': '2',
            'hostel_id': '1',  # Bhavani Hostel
            'id_card': id_card_data
        }, content_type='multipart/form-data', follow_redirects=True)
        assert res.status_code == 200
        student = UserModel.get_by_register_number('25CDR099')
        assert student is not None, "Student registration failed"
        print("  -> Passed: Student registered with ID:", student['id'])

        # TEST 2: Upload ID Card
        print("\n[TEST 2] Verify College ID Card File Persistence...")
        assert student['id_card_path'] is not None
        saved_id_path = os.path.join(app.config['UPLOAD_FOLDER'], 'id_cards', student['id_card_path'])
        assert os.path.exists(saved_id_path), f"ID card file not found at {saved_id_path}"
        print("  -> Passed: ID Card file successfully persisted on disk.")

        # TEST 3: Login
        print("\n[TEST 3] Student Login with Register Number...")
        res = client.post('/login/student', data={
            'identifier': '25CDR099',
            'password': 'password123'
        }, follow_redirects=True)
        assert res.status_code == 200
        assert b"Welcome, Sanjay Kumar" in res.data
        print("  -> Passed: Student login successful, session established.")

        # TEST 4: Select Hostel
        print("\n[TEST 4] Dynamic Hostel Association...")
        assert student['hostel_name'] == 'Bhavani Hostel'
        print("  -> Passed: Student is correctly associated with Bhavani Hostel.")

        # TEST 5: Create Bus Request
        print("\n[TEST 5] Create Bus Request (Normal Travel)...")
        with client.session_transaction() as sess:
            sess['user_id'] = student['id']
            sess['name'] = student['name']
            sess['register_number'] = student['register_number']
            sess['role'] = 'student'

        res = client.post('/student/request-bus', data={
            'travel_date': '2026-11-06',
            'required_time': '16:30',
            'travel_type': 'Normal Travel',
            'travel_reason': 'Weekend journey'
        }, follow_redirects=True)
        assert res.status_code == 200
        reqs = RequestModel.get_student_requests(student['id'])
        assert len(reqs) > 0
        test_req = reqs[0]
        print(f"  -> Passed: Bus request created (ID: {test_req['id']}) for 2026-11-06 at 16:30.")

        # TEST 6: Upload Travel Proof for Booked Bus / Ticket
        print("\n[TEST 6] Create Bus Request with Booked Ticket Proof...")
        ticket_data = (io.BytesIO(b"%PDF-1.4 Fake Ticket Receipt"), "ticket.pdf")
        res = client.post('/student/request-bus', data={
            'travel_date': '2026-11-06',
            'required_time': '19:00',
            'travel_type': 'Booked Bus / Ticket',
            'travel_reason': 'KPN Bus reservation',
            'travel_proof': ticket_data
        }, content_type='multipart/form-data', follow_redirects=True)
        assert res.status_code == 200
        reqs = RequestModel.get_student_requests(student['id'])
        ticket_req = [r for r in reqs if r['travel_type'] == 'Booked Bus / Ticket'][0]
        assert ticket_req['proof_status'] == 'Uploaded'
        assert ticket_req['proof_path'] is not None
        print(f"  -> Passed: Travel proof uploaded for ticket request (ID: {ticket_req['id']}).")

        # TEST 7: Verify Request from Management
        print("\n[TEST 7] Management Proof Verification...")
        with client.session_transaction() as sess:
            admin_user = UserModel.get_by_email('admin@buscampusconnect.edu')
            sess['user_id'] = admin_user['id']
            sess['name'] = admin_user['name']
            sess['register_number'] = admin_user['register_number']
            sess['role'] = 'management'

        res = client.post('/management/requests/verify-proof', data={
            'request_id': ticket_req['id'],
            'decision': 'Verified',
            'remarks': 'Ticket verified for 9:00 PM bus'
        }, follow_redirects=True)
        assert res.status_code == 200
        updated_req = RequestModel.get_by_id(ticket_req['id'])
        assert updated_req['proof_status'] == 'Verified'
        assert updated_req['request_status'] == 'Verified'
        print("  -> Passed: Proof verified by management.")

        # TEST: Student cancellation requires and stores a reason
        print("\n[TEST] Student Cancellation Reason...")
        bus_01 = BusModel.get_by_number('BUS-01')
        cancel_req_id = RequestModel.create_request(
            student['id'], student['hostel_id'], '2026-11-30', '15:30', 'Normal Travel'
        )
        RequestModel.allocate_bus(cancel_req_id, bus_01['id'])
        with client.session_transaction() as sess:
            sess['user_id'] = student['id']
            sess['role'] = 'student'
            sess['name'] = student['name']
        res = client.get('/student/my-requests')
        assert res.status_code == 200 and b'Cancel Bus' in res.data
        res = client.post(f'/student/cancel-request/{cancel_req_id}', data={
            'cancellation_reason': 'Travel plans changed'
        }, follow_redirects=True)
        cancelled_req = RequestModel.get_by_id(cancel_req_id)
        assert res.status_code == 200
        assert cancelled_req['request_status'] == 'Cancelled'
        assert cancelled_req['cancellation_reason'] == 'Travel plans changed'
        assert cancelled_req['bus_id'] is None
        print("  -> Passed: Student cancellation stores the reason and releases the allocation.")

        # TEST: Management rejection requires reason and notifies the student
        print("\n[TEST] Management Rejection Reason...")
        reject_req_id = RequestModel.create_request(
            student['id'], student['hostel_id'], '2026-12-01', '16:00', 'Normal Travel'
        )
        with client.session_transaction() as sess:
            sess['user_id'] = admin_user['id']
            sess['role'] = 'management'
            sess['name'] = admin_user['name']
        res = client.get('/management/requests')
        assert res.status_code == 200 and b'Reason for rejection' in res.data
        res = client.post('/management/requests/reject', data={
            'request_id': reject_req_id,
            'cancellation_reason': 'Request does not meet travel policy'
        }, follow_redirects=True)
        rejected_req = RequestModel.get_by_id(reject_req_id)
        assert res.status_code == 200
        assert rejected_req['request_status'] == 'Rejected'
        assert rejected_req['cancellation_reason'] == 'Request does not meet travel policy'
        notification = get_db().execute(
            "SELECT message FROM notifications WHERE user_id = ? AND title = ? ORDER BY id DESC LIMIT 1",
            (student['id'], 'Bus Request Rejected')
        ).fetchone()
        assert notification and 'Request does not meet travel policy' in notification['message']
        print("  -> Passed: Management rejection stores the reason and notifies the student.")

        # TEST 8: Allocate BUS-01
        print("\n[TEST 8] Allocate BUS-01 to Request...")
        bus_01 = BusModel.get_by_number('BUS-01')
        res = client.post('/management/requests/allocate-bus', data={
            'request_id': test_req['id'],
            'bus_id': bus_01['id']
        }, follow_redirects=True)
        assert res.status_code == 200
        updated_test_req = RequestModel.get_by_id(test_req['id'])
        assert updated_test_req['bus_id'] == bus_01['id']
        assert updated_test_req['request_status'] == 'Bus Allocated'
        print("  -> Passed: BUS-01 successfully allocated to request.")

        # TEST 9: Generate 4:30 PM -> 4:40 PM Boarding Window
        print("\n[TEST 9] Verify 10-Minute Boarding Window...")
        window = BoardingService.calculate_boarding_window(updated_test_req['required_time'], 10)
        assert window['departure_time'] == '16:30'
        assert window['boarding_end_time'] == '16:40'
        assert window['display_window'] == '4:30 PM – 4:40 PM'
        print(f"  -> Passed: Strict 10-Minute boarding window generated: {window['display_window']}")

        # TEST 10: Student Sees BUS-01
        print("\n[TEST 10] Student Portal Active Bus View...")
        with client.session_transaction() as sess:
            sess['user_id'] = student['id']
            sess['role'] = 'student'
            sess['name'] = student['name']

        res = client.get('/student/dashboard')
        assert res.status_code == 200
        assert b"BUS-01" in res.data
        assert b"4:30 PM" in res.data
        print("  -> Passed: Student sees BUS-01 and boarding schedule on dashboard.")

        # TEST 11: Student Clicks "YES, I HAVE BOARDED"
        print("\n[TEST 11] Confirm Boarding via Student Button...")
        res = client.post('/student/confirm-boarding', data={
            'request_id': test_req['id']
        }, follow_redirects=True)
        assert res.status_code == 200
        boarded_req = RequestModel.get_by_id(test_req['id'])
        assert boarded_req['request_status'] == 'Boarded'
        print("  -> Passed: Request status updated to 'Boarded' in database.")

        # TEST 12: Management Sees BOARDED
        print("\n[TEST 12] Management Boarding Monitor Verification...")
        with client.session_transaction() as sess:
            sess['user_id'] = admin_user['id']
            sess['role'] = 'management'
        res = client.get('/management/boarding-monitor')
        assert res.status_code == 200
        assert b"BOARDED" in res.data
        assert student['register_number'].encode() in res.data
        print(f"  -> Passed: Management boarding monitor displays {student['register_number']} as BOARDED.")

        # TEST 13 & 14: Test student who does not board -> NOT BOARDED
        print("\n[TEST 13 & 14] Test Non-Boarded Student Flagging...")
        dummy_req_id = RequestModel.create_request(
            student_id=student['id'],
            hostel_id=student['hostel_id'],
            travel_date='2026-11-06',
            required_time='10:00',
            travel_type='Normal Travel'
        )
        RequestModel.allocate_bus(dummy_req_id, bus_01['id'])
        sim_time = datetime.strptime("2026-11-06 10:15", "%Y-%m-%d %H:%M")
        BoardingService.sync_and_check_missed_boarding(simulated_datetime=sim_time)
        dummy_req = RequestModel.get_by_id(dummy_req_id)
        assert dummy_req['request_status'] == 'Not Boarded', f"Expected 'Not Boarded', got {dummy_req['request_status']}"
        print(f"  -> Passed: Missed boarding window detected. Status correctly marked as: {dummy_req['request_status']}")

        # TEST 15 & 16: Add New Hostel & Check Student Registration
        print("\n[TEST 15 & 16] Add New Hostel & Dynamic Registration Check...")
        new_hostel_name = "Kaveri North Hostel"
        try:
            HostelModel.add_hostel(new_hostel_name)
        except Exception:
            pass  # Already added in previous test run
        active_hostels = HostelModel.get_all_active()
        assert any(h['hostel_name'] == new_hostel_name for h in active_hostels)
        res = client.get('/register')
        assert new_hostel_name.encode() in res.data
        print(f"  -> Passed: '{new_hostel_name}' added and immediately available in registration dropdown.")

        # TEST 17 & 18: Add New Bus & Check Bus Allocation
        print("\n[TEST 17 & 18] Add New Bus & Fleet Availability Check...")
        new_bus_num = "BUS-04"
        try:
            BusModel.add_bus(new_bus_num, "Kongu Express Shuttle", 50, "P. Palanisamy", "+91 98421 99999")
        except Exception:
            pass
        all_buses = BusModel.get_all()
        assert any(b['bus_number'] == new_bus_num for b in all_buses)
        res = client.get('/management/requests')
        assert new_bus_num.encode() in res.data
        print(f"  -> Passed: '{new_bus_num}' created and immediately available in allocation modal.")

        # TEST 19 & 20: Python Hash Map Groups Requests Correctly
        print("\n[TEST 19 & 20] Python Hash Map Grouping & $O(1)$ Lookup...")
        all_raw = RequestModel.get_all_requests_raw()
        hash_map = create_request_hashmap(all_raw)
        assert isinstance(hash_map, dict), "Hash map is not a Python dict"
        assert "2026-11-06_16:30" in hash_map
        slot_students = hash_map["2026-11-06_16:30"]
        assert len(slot_students) >= 1
        print(f"  -> Passed: Hash map successfully keyed by DATE_TIME. Slot '2026-11-06_16:30' holds {len(slot_students)} students.")

        # TEST 21: Ascending Management Table (Date -> Time -> Hostel -> Reg No)
        print("\n[TEST 21] Strict Ascending Sorting by Hash Map...")
        sorted_reqs = sort_hashmap_requests(hash_map)
        for i in range(len(sorted_reqs) - 1):
            a = (sorted_reqs[i]['travel_date'], sorted_reqs[i]['required_time'], sorted_reqs[i]['hostel_name'].lower(), sorted_reqs[i]['register_number'].upper())
            b = (sorted_reqs[i+1]['travel_date'], sorted_reqs[i+1]['required_time'], sorted_reqs[i+1]['hostel_name'].lower(), sorted_reqs[i+1]['register_number'].upper())
            assert a <= b, f"Sort order violation: {a} > {b}"
        print("  -> Passed: Management requests table is strictly sorted ascending across all 4 keys.")

        # TEST 22: Register Numbers Displayed (NEVER Student A/B/C)
        print("\n[TEST 22] Register Numbers Display Check...")
        reg_numbers = [r['register_number'] for r in sorted_reqs]
        assert all(r is not None and len(r) > 0 for r in reg_numbers)
        assert any("25CDR" in r for r in reg_numbers)
        print(f"  -> Passed: Real college register numbers verified: {reg_numbers[:4]}")

        # TEST 23: Destination Omitted from Management Request Table
        print("\n[TEST 23] Management Request Table Destination Column Check...")
        res = client.get('/management/requests')
        assert b"<th>Destination</th>" not in res.data
        print("  -> Passed: Management table does not contain a Destination column (Fixed to Perundurai).")

        # TEST 24: Bus Capacity Prevents Over-Allocation
        print("\n[TEST 24] Bus Capacity Limit Protection (BUS FULL)...")
        small_bus = BusModel.get_by_number("BUS-MINI")
        if not small_bus:
            small_bus_id = BusModel.add_bus("BUS-MINI", "Mini Shuttle", 2, "Driver X", "+91 99999 11111")
        else:
            small_bus_id = small_bus['id']
            
        req1 = RequestModel.create_request(student['id'], student['hostel_id'], '2026-11-20', '15:00', 'Normal Travel')
        req2 = RequestModel.create_request(student['id'], student['hostel_id'], '2026-11-20', '15:00', 'Normal Travel')
        req3 = RequestModel.create_request(student['id'], student['hostel_id'], '2026-11-20', '15:00', 'Normal Travel')

        ok1, msg1 = BusService.allocate_bus_to_request(req1, small_bus_id)
        assert ok1 is True
        ok2, msg2 = BusService.allocate_bus_to_request(req2, small_bus_id)
        assert ok2 is True
        ok3, msg3 = BusService.allocate_bus_to_request(req3, small_bus_id)
        assert ok3 is False, "Over-allocation was allowed when it should have been blocked!"
        assert "BUS FULL" in msg3
        print(f"  -> Passed: Over-allocation blocked. Message: '{msg3}'")

        # TEST 25: Application Restart & Database Persistence
        print("\n[TEST 25] SQLite Database Persistence Verification...")
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM bus_requests")
        count = cursor.fetchone()[0]
        conn.close()
        assert count > 0, "No records persisted in SQLite database"
        print(f"  -> Passed: Database file '{DATABASE_PATH}' persisted with {count} bus requests.")

        print("\n" + "=" * 70)
        print("ALL CORE, CANCELLATION, AND REJECTION SCENARIOS PASSED!")
        print("=" * 70)


if __name__ == '__main__':
    run_all_tests()