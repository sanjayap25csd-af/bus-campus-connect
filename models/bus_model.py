"""
Bus Model for Bus Campus Connect.
Handles buses, capacity checking, route definitions, and bus scheduling.
"""

from database.db import get_db, query_db, execute_db
from datetime import datetime, timedelta


class BusModel:
    @staticmethod
    def get_all(status_filter=None):
        """Fetch all buses with optional status filter."""
        sql = "SELECT * FROM buses"
        params = []
        if status_filter:
            sql += " WHERE status = ?"
            params.append(status_filter)
        sql += " ORDER BY bus_number ASC"
        return query_db(sql, params)

    @staticmethod
    def get_all_with_occupancy(travel_date=None):
        """
        Fetch buses with dynamic allocated student counts and available seat calculations.
        If travel_date is provided, calculates occupancy for that specific date.
        """
        if travel_date:
            sql = """
                SELECT b.*,
                       COUNT(r.id) as allocated_count
                FROM buses b
                LEFT JOIN bus_requests r ON b.id = r.bus_id AND r.travel_date = ? AND r.request_status IN ('Bus Allocated', 'Boarding Open', 'Boarded')
                GROUP BY b.id
                ORDER BY b.bus_number ASC
            """
            buses = query_db(sql, (travel_date,))
        else:
            sql = """
                SELECT b.*,
                       COUNT(r.id) as allocated_count
                FROM buses b
                LEFT JOIN bus_requests r ON b.id = r.bus_id AND r.request_status IN ('Bus Allocated', 'Boarding Open', 'Boarded')
                GROUP BY b.id
                ORDER BY b.bus_number ASC
            """
            buses = query_db(sql)

        for b in buses:
            alloc = b.get('allocated_count', 0)
            cap = b.get('capacity', 50)
            avail = max(0, cap - alloc)
            b['available_seats'] = avail
            b['is_full'] = (alloc >= cap)
            b['occupancy_text'] = f"{alloc} / {cap} Seats Filled"
            b['occupancy_pct'] = round((alloc / cap) * 100, 1) if cap > 0 else 0

        return buses

    @staticmethod
    def get_by_id(bus_id):
        """Fetch a single bus by ID."""
        sql = "SELECT * FROM buses WHERE id = ?"
        return query_db(sql, (bus_id,), one=True)

    @staticmethod
    def get_by_number(bus_number):
        """Fetch a bus by number (e.g., 'BUS-01')."""
        sql = "SELECT * FROM buses WHERE UPPER(bus_number) = UPPER(?)"
        return query_db(sql, (bus_number.strip(),), one=True)

    @staticmethod
    def add_bus(bus_number, bus_name, capacity, driver_name, driver_contact, status='Active'):
        """Add a new bus to the fleet."""
        sql = """
            INSERT INTO buses (bus_number, bus_name, capacity, driver_name, driver_contact, route, status)
            VALUES (?, ?, ?, ?, ?, 'College → Perundurai Bus Stand', ?)
        """
        return execute_db(sql, (
            bus_number.strip().upper(), bus_name.strip(), int(capacity),
            driver_name.strip(), driver_contact.strip(), status
        ))

    @staticmethod
    def update_bus(bus_id, bus_number, bus_name, capacity, driver_name, driver_contact, status):
        """Update bus attributes."""
        sql = """
            UPDATE buses
            SET bus_number = ?, bus_name = ?, capacity = ?, driver_name = ?, driver_contact = ?, status = ?
            WHERE id = ?
        """
        execute_db(sql, (
            bus_number.strip().upper(), bus_name.strip(), int(capacity),
            driver_name.strip(), driver_contact.strip(), status, bus_id
        ))

    @staticmethod
    def toggle_status(bus_id):
        """Toggle bus status between Active and Inactive."""
        bus = BusModel.get_by_id(bus_id)
        if bus:
            new_status = 'Inactive' if bus['status'] == 'Active' else 'Active'
            execute_db("UPDATE buses SET status = ? WHERE id = ?", (new_status, bus_id))
            return new_status
        return None

    @staticmethod
    def get_active_count():
        """Count total active buses."""
        res = query_db("SELECT COUNT(*) as cnt FROM buses WHERE status = 'Active'", one=True)
        return res['cnt'] if res else 0

    # ---------------- SCHEDULE OPERATIONS ---------------- #

    @staticmethod
    def create_or_update_schedule(bus_id, travel_date, departure_time, window_minutes=10):
        """
        Creates or updates a bus schedule with a strict 10-minute boarding window.
        departure_time: 'HH:MM' (e.g. '16:30')
        boarding_end_time: departure_time + window_minutes (e.g. '16:40')
        """
        dep_dt = datetime.strptime(departure_time.strip(), "%H:%M")
        end_dt = dep_dt + timedelta(minutes=window_minutes)
        boarding_end_time = end_dt.strftime("%H:%M")

        bus = BusModel.get_by_id(bus_id)
        cap = bus['capacity'] if bus else 50

        # Check if schedule exists
        existing = query_db(
            "SELECT id FROM bus_schedules WHERE bus_id = ? AND travel_date = ? AND departure_time = ?",
            (bus_id, travel_date, departure_time),
            one=True
        )
        if existing:
            execute_db(
                "UPDATE bus_schedules SET boarding_end_time = ?, capacity = ? WHERE id = ?",
                (boarding_end_time, cap, existing['id'])
            )
            return existing['id']
        else:
            return execute_db(
                """INSERT INTO bus_schedules (bus_id, travel_date, departure_time, boarding_end_time, capacity, status)
                   VALUES (?, ?, ?, ?, ?, 'Upcoming')""",
                (bus_id, travel_date, departure_time, boarding_end_time, cap)
            )

    @staticmethod
    def get_all_schedules(travel_date=None):
        """
        Fetch all bus schedules with joined bus info, allocated student count,
        and dynamically calculated seat metrics.
        """
        sql = """
            SELECT s.*, b.bus_number, b.bus_name, b.driver_name, b.driver_contact, b.route,
                   (
                       SELECT COUNT(*) 
                       FROM bus_requests r 
                       WHERE r.bus_id = s.bus_id 
                         AND r.travel_date = s.travel_date
                         AND r.required_time = s.departure_time
                         AND r.request_status IN ('Bus Allocated', 'Boarding Open', 'Boarded')
                   ) as allocated_count
            FROM bus_schedules s
            JOIN buses b ON s.bus_id = b.id
        """
        params = []
        if travel_date:
            sql += " WHERE s.travel_date = ?"
            params.append(travel_date)

        sql += " ORDER BY s.travel_date ASC, s.departure_time ASC"
        schedules = query_db(sql, params)

        for s in schedules:
            cap = s.get('capacity', 50)
            alloc = s.get('allocated_count', 0)
            s['available_seats'] = max(0, cap - alloc)
            s['is_full'] = (alloc >= cap)
        return schedules

