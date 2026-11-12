"""
Bus Service for Bus Campus Connect.
Coordinates bus allocations, capacity enforcement (preventing over-allocation),
and automated 10-minute boarding window schedules.
"""

from database.db import query_db, execute_db
from models.bus_model import BusModel
from models.request_model import RequestModel
from services.boarding_service import BoardingService
from services.notification_service import NotificationService
from data_structures.hashmap_manager import format_display_time


class BusService:
    @staticmethod
    def allocate_bus_to_request(request_id, bus_id):
        """
        Allocates a bus to a student travel request with strict capacity check.
        Ensures bus cannot be over-allocated!
        Creates/updates the corresponding 10-minute schedule.
        """
        request = RequestModel.get_by_id(request_id)
        if not request:
            return False, "Request not found."

        bus = BusModel.get_by_id(bus_id)
        if not bus:
            return False, "Selected bus does not exist."

        if bus['status'] != 'Active':
            return False, f"{bus['bus_number']} is currently marked as {bus['status']} and cannot take allocations."

        # Check existing allocations for this bus on this travel date & time
        travel_date = request['travel_date']
        required_time = request['required_time']
        bus_capacity = bus['capacity']

        existing_allocations = query_db("""
            SELECT COUNT(*) as count 
            FROM bus_requests 
            WHERE bus_id = ? AND travel_date = ? AND required_time = ?
              AND request_status IN ('Bus Allocated', 'Boarding Open', 'Boarded')
              AND id != ?
        """, (bus_id, travel_date, required_time, request_id), one=True)

        current_count = existing_allocations['count'] if existing_allocations else 0

        if current_count >= bus_capacity:
            return False, f"BUS FULL: {bus['bus_number']} has reached its full capacity ({bus_capacity} seats) for {travel_date} at {format_display_time(required_time)}."

        # Update Request
        RequestModel.allocate_bus(request_id, bus_id)

        # Create or update 10-minute schedule
        BusModel.create_or_update_schedule(bus_id, travel_date, required_time, window_minutes=10)

        # Format window
        window = BoardingService.calculate_boarding_window(required_time, 10)

        # Notify student
        student_id = request['student_id']
        NotificationService.notify(
            student_id,
            "Bus Allocated!",
            f"You have been allocated {bus['bus_number']} ({bus['bus_name']}) for your travel on {travel_date}. Boarding window is {window['display_window']}. Route: College → Perundurai Bus Stand.",
            "success"
        )

        return True, f"Successfully allocated {bus['bus_number']} ({current_count + 1}/{bus_capacity} seats filled). Boarding window set to {window['display_window']}."

    @staticmethod
    def get_schedule_timeline_data(travel_date=None, simulated_datetime=None):
        """
        Builds the visual timeline data structure for the management & student views.
        Shows: Start Time, End Time (10 mins), Bus Number, Allocated count, Capacity, Status.
        """
        schedules = BusModel.get_all_schedules(travel_date)
        timeline = []

        for s in schedules:
            status_info = BoardingService.evaluate_bus_status(
                s['travel_date'], s['departure_time'], 10, simulated_datetime
            )
            
            dep_fmt = format_display_time(s['departure_time'])
            end_fmt = format_display_time(s['boarding_end_time'])
            
            cap = s['capacity']
            alloc = s['allocated_count']
            avail = max(0, cap - alloc)

            timeline.append({
                'id': s['id'],
                'travel_date': s['travel_date'],
                'departure_time': s['departure_time'],
                'boarding_end_time': s['boarding_end_time'],
                'start_formatted': dep_fmt,
                'end_formatted': end_fmt,
                'time_span': f"{dep_fmt} ───────── {end_fmt}",
                'bus_id': s['bus_id'],
                'bus_number': s['bus_number'],
                'bus_name': s['bus_name'],
                'driver_name': s['driver_name'],
                'driver_contact': s['driver_contact'],
                'route': s['route'],
                'capacity': cap,
                'allocated_count': alloc,
                'available_seats': avail,
                'is_full': alloc >= cap,
                'occupancy_pct': round((alloc / cap) * 100, 1) if cap > 0 else 0,
                'dynamic_status': status_info['status'],
                'status_class': status_info['badge_class'],
                'can_board': status_info['can_board']
            })

        return timeline

