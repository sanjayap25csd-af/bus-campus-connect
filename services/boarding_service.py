"""
Boarding Service for Bus Campus Connect.
Handles the strict 10-Minute Boarding Window calculation, automatic bus status progression,
student boarding confirmation ("YES, I HAVE BOARDED"), and 'Not Boarded' detection.
"""

from datetime import datetime, timedelta
from database.db import query_db, execute_db
from services.notification_service import NotificationService
from data_structures.hashmap_manager import format_display_time


class BoardingService:
    DEFAULT_WINDOW_MINUTES = 10
    CLOSING_SOON_THRESHOLD_MINUTES = 2

    @staticmethod
    def calculate_boarding_window(departure_time_str, window_minutes=10):
        """
        Calculates the start and end times for the 10-minute boarding window.
        Returns:
            departure_time ('16:30')
            boarding_end_time ('16:40')
            display_window ('4:30 PM – 4:40 PM')
        """
        try:
            dep_dt = datetime.strptime(departure_time_str.strip(), "%H:%M")
            end_dt = dep_dt + timedelta(minutes=window_minutes)
            
            dep_formatted = format_display_time(dep_dt.strftime("%H:%M"))
            end_formatted = format_display_time(end_dt.strftime("%H:%M"))
            
            return {
                'departure_time': dep_dt.strftime("%H:%M"),
                'boarding_end_time': end_dt.strftime("%H:%M"),
                'display_window': f"{dep_formatted} – {end_formatted}"
            }
        except Exception:
            return {
                'departure_time': departure_time_str,
                'boarding_end_time': departure_time_str,
                'display_window': f"{departure_time_str} (Window: 10 mins)"
            }

    @staticmethod
    def evaluate_bus_status(travel_date_str, departure_time_str, window_minutes=10, simulated_datetime=None):
        """
        Calculates automatic status based on current/simulated time:
        - 'Upcoming' (Before departure)
        - 'Boarding Open' (Within boarding window)
        - 'Boarding Closing Soon' (Within last 2 minutes of boarding window)
        - 'Boarding Closed' / 'Departed' (After boarding window expires)
        """
        now = simulated_datetime if simulated_datetime else datetime.now()

        try:
            dep_datetime = datetime.strptime(f"{travel_date_str} {departure_time_str}", "%Y-%m-%d %H:%M")
            end_datetime = dep_datetime + timedelta(minutes=window_minutes)
            closing_soon_datetime = end_datetime - timedelta(minutes=BoardingService.CLOSING_SOON_THRESHOLD_MINUTES)

            if now < dep_datetime:
                # Minutes until boarding opens
                diff = int((dep_datetime - now).total_seconds() / 60)
                return {
                    'status': 'Upcoming',
                    'badge_class': 'badge-info',
                    'message': f'Boarding starts in {diff} mins' if diff < 60 else 'Scheduled',
                    'can_board': False
                }
            elif dep_datetime <= now < closing_soon_datetime:
                return {
                    'status': 'Boarding Open',
                    'badge_class': 'badge-success',
                    'message': 'Boarding is now open. Please proceed to the bus bay.',
                    'can_board': True
                }
            elif closing_soon_datetime <= now <= end_datetime:
                return {
                    'status': 'Boarding Closing Soon',
                    'badge_class': 'badge-warning',
                    'message': 'Attention! Boarding closes in less than 2 minutes!',
                    'can_board': True
                }
            else:
                return {
                    'status': 'Boarding Closed',
                    'badge_class': 'badge-secondary',
                    'message': 'Boarding is closed. Bus has departed for Perundurai Bus Stand.',
                    'can_board': False
                }
        except Exception:
            return {
                'status': 'Upcoming',
                'badge_class': 'badge-info',
                'message': 'Scheduled',
                'can_board': True
            }

    @staticmethod
    def confirm_student_boarding(request_id, student_id):
        """
        Core Action: Student clicks "YES, I HAVE BOARDED".
        Records:
        1. student_id
        2. register_number
        3. bus_id
        4. request_id
        5. actual boarding_time
        6. Updates request_status to 'Boarded'
        7. Saves boarding record to database.
        """
        request = query_db("""
            SELECT r.*, u.register_number, b.bus_number 
            FROM bus_requests r
            JOIN users u ON r.student_id = u.id
            JOIN buses b ON r.bus_id = b.id
            WHERE r.id = ? AND r.student_id = ?
        """, (request_id, student_id), one=True)

        if not request:
            return False, "Bus request not found or not assigned to your account."

        if not request['bus_id']:
            return False, "No bus has been allocated for this travel request yet."

        if request['request_status'] == 'Boarded':
            return True, "Boarding was already confirmed previously."

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 1. Insert or update boarding_records table
        existing_record = query_db("SELECT id FROM boarding_records WHERE request_id = ?", (request_id,), one=True)
        if existing_record:
            execute_db("""
                UPDATE boarding_records 
                SET boarded = 1, boarding_time = ?
                WHERE id = ?
            """, (now_str, existing_record['id']))
        else:
            execute_db("""
                INSERT INTO boarding_records (request_id, student_id, bus_id, boarded, boarding_time)
                VALUES (?, ?, ?, 1, ?)
            """, (request_id, student_id, request['bus_id'], now_str))

        # 2. Update bus_requests table
        execute_db("""
            UPDATE bus_requests
            SET request_status = 'Boarded', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (request_id,))

        # 3. Send confirmation notification to student
        bus_no = request['bus_number']
        NotificationService.notify(
            student_id,
            "Boarding Confirmed",
            f"You have successfully confirmed boarding on {bus_no} for Perundurai Bus Stand at {now_str}.",
            "success"
        )

        return True, f"Boarding confirmed on {bus_no}! Have a safe journey to Perundurai Bus Stand."

    @staticmethod
    def sync_and_check_missed_boarding(simulated_datetime=None):
        """
        Scans active requests whose travel_date and boarding_end_time have elapsed.
        If a student was allocated a bus but never confirmed boarding,
        updates status to 'Not Boarded'.
        """
        now = simulated_datetime if simulated_datetime else datetime.now()
        current_date_str = now.strftime("%Y-%m-%d")

        # Get all allocated/open requests for today or previous dates
        requests = query_db("""
            SELECT r.id, r.student_id, r.travel_date, r.required_time, r.bus_id,
                   u.name as student_name, u.register_number, b.bus_number
            FROM bus_requests r
            JOIN users u ON r.student_id = u.id
            LEFT JOIN buses b ON r.bus_id = b.id
            WHERE r.request_status IN ('Bus Allocated', 'Boarding Open')
              AND r.bus_id IS NOT NULL
        """)

        updated_count = 0
        for req in requests:
            try:
                # Window ends 10 mins after departure
                dep_dt = datetime.strptime(f"{req['travel_date']} {req['required_time']}", "%Y-%m-%d %H:%M")
                window_end = dep_dt + timedelta(minutes=BoardingService.DEFAULT_WINDOW_MINUTES)

                if now > window_end:
                    # Mark as Not Boarded
                    execute_db("""
                        UPDATE bus_requests 
                        SET request_status = 'Not Boarded', updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (req['id'],))

                    # Insert boarding record as not boarded if not present
                    rec = query_db("SELECT id FROM boarding_records WHERE request_id = ?", (req['id'],), one=True)
                    if not rec:
                        execute_db("""
                            INSERT INTO boarding_records (request_id, student_id, bus_id, boarded, boarding_time)
                            VALUES (?, ?, ?, 0, NULL)
                        """, (req['id'], req['student_id'], req['bus_id']))

                    NotificationService.notify(
                        req['student_id'],
                        "Boarding Closed - Not Boarded",
                        f"The boarding window for your bus ({req['bus_number'] or 'Allocated Bus'}) closed. Your status has been marked as Not Boarded.",
                        "warning"
                    )
                    updated_count += 1
            except Exception:
                continue

        return updated_count

