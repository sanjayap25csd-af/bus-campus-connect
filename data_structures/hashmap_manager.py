"""
Data Structure Implementation: Hash Mapping for Bus Campus Connect.
Explicitly utilizes Python dictionaries (dict) as Hash Maps to organize, group,
and efficiently retrieve hostel student bus requests by (Date + Time).

Complexity Analysis:
- Hash Map Insertion: Average O(1), Worst O(N)
- Hash Map Lookup: Average O(1), Worst O(N)
- Grouping: O(N) linear pass over N requests
- Sorting: O(K log K) where K is the number of keys or elements sorted by multi-level criteria
"""

import math
from datetime import datetime
from collections import defaultdict


def create_request_hashmap(requests):
    """
    Constructs a Python Hash Map (dict) where the key is formatted as:
    `DATE_TIME` (e.g., '2026-11-06_16:30')
    and the value is a list of student request records requesting that slot.

    :param requests: List of request dictionaries from the database
    :return: dict mapping "YYYY-MM-DD_HH:MM" -> list of request dicts
    """
    request_map = {}
    for req in requests:
        date_str = str(req.get('travel_date', '')).strip()
        time_str = str(req.get('required_time', '')).strip()
        
        # Canonicalize time to HH:MM format if needed
        canonical_key = f"{date_str}_{time_str}"
        
        if canonical_key not in request_map:
            request_map[canonical_key] = []
        
        request_map[canonical_key].append(req)
        
    return request_map


def group_requests_by_time(requests):
    """
    Groups requests using a Hash Map and returns the grouped dictionary.
    """
    return create_request_hashmap(requests)


def get_slot_requests(request_map, date_str, time_str):
    """
    O(1) Hash Map fast lookup for all student requests at a specific date & time.
    """
    key = f"{date_str.strip()}_{time_str.strip()}"
    return request_map.get(key, [])


def calculate_time_slot_demand(requests, default_bus_capacity=50):
    """
    Calculates demand metrics for each date/time slot using the Hash Map.
    
    :param requests: List of request dicts
    :param default_bus_capacity: Default capacity of standard college bus (50)
    :return: list of demand analysis dicts sorted chronologically
    """
    hash_map = create_request_hashmap(requests)
    demand_summary = []

    for slot_key, slot_requests in hash_map.items():
        parts = slot_key.split('_')
        travel_date = parts[0] if len(parts) > 0 else ''
        required_time = parts[1] if len(parts) > 1 else ''

        student_count = len(slot_requests)
        hostels_count = defaultdict(int)
        travel_types_count = defaultdict(int)
        allocated_count = 0
        allocated_buses = set()

        for req in slot_requests:
            h_name = req.get('hostel_name', 'Unknown Hostel')
            hostels_count[h_name] += 1

            t_type = req.get('travel_type', 'Normal Travel')
            travel_types_count[t_type] += 1

            if req.get('bus_id'):
                allocated_count += 1
                if req.get('bus_number'):
                    allocated_buses.add(req.get('bus_number'))

        # Calculate required buses based on capacity
        required_buses = max(1, math.ceil(student_count / default_bus_capacity))
        is_high_demand = student_count > default_bus_capacity
        occupancy_pct = round((student_count / default_bus_capacity) * 100, 1)

        demand_summary.append({
            'slot_key': slot_key,
            'travel_date': travel_date,
            'required_time': required_time,
            'formatted_time': format_display_time(required_time),
            'student_count': student_count,
            'bus_capacity': default_bus_capacity,
            'occupancy_pct': occupancy_pct,
            'required_buses': required_buses,
            'is_high_demand': is_high_demand,
            'hostels_distribution': dict(hostels_count),
            'travel_types_distribution': dict(travel_types_count),
            'allocated_count': allocated_count,
            'allocated_buses': list(allocated_buses),
            'status_label': 'HIGH DEMAND - Extra Bus Required' if is_high_demand else ('Near Full' if occupancy_pct >= 80 else 'Normal Demand'),
            'status_class': 'badge-danger' if is_high_demand else ('badge-warning' if occupancy_pct >= 80 else 'badge-success')
        })

    # Sort demand summary chronologically by (travel_date, required_time)
    demand_summary.sort(key=lambda x: (x['travel_date'], x['required_time']))
    return demand_summary


def find_high_demand_slots(requests, bus_capacity=50):
    """
    Filters and returns time slots where student demand strictly exceeds single bus capacity.
    Example: 6:00 PM -> 65 students (Capacity 50) -> Additional Bus Required
    """
    all_demand = calculate_time_slot_demand(requests, bus_capacity)
    return [slot for slot in all_demand if slot['is_high_demand']]


def sort_hashmap_requests(request_map):
    """
    Flattens and sorts all requests organized by the Hash Map strictly in ascending order by:
    1. Travel Date (ascending)
    2. Required Time (ascending)
    3. Hostel (alphabetical)
    4. Register Number (alphabetical/numeric)

    :param request_map: dict mapping "YYYY-MM-DD_HH:MM" -> list of requests
    :return: list of request dicts sorted by the 4 strict criteria
    """
    all_flattened_requests = []
    for slot_requests in request_map.values():
        all_flattened_requests.extend(slot_requests)

    def sort_key(req):
        travel_date = str(req.get('travel_date', '') or '')
        required_time = str(req.get('required_time', '') or '')
        hostel = str(req.get('hostel_name', '') or '')
        reg_no = str(req.get('register_number', '') or '')
        return (travel_date, required_time, hostel.lower(), reg_no.upper())

    all_flattened_requests.sort(key=sort_key)
    return all_flattened_requests


def format_display_time(time_str):
    """
    Converts 24-hour HH:MM format (e.g., '16:30', '19:00') into 12-hour display ('4:30 PM', '7:00 PM').
    """
    if not time_str:
        return ''
    try:
        dt = datetime.strptime(time_str.strip(), "%H:%M")
        # Format without leading zero on Windows (%#I) or fallback (%I)
        formatted = dt.strftime("%I:%M %p")
        if formatted.startswith('0'):
            formatted = formatted[1:]
        return formatted
    except ValueError:
        return time_str


def get_hashmap_debug_info(requests):
    """
    Provides data structure inspection metrics for demonstrating the Hash Map
    to academic evaluators, showing memory buckets, keys, internal Python hash values,
    and bucket sizes.
    """
    hash_map = create_request_hashmap(requests)
    debug_buckets = []
    
    for key, items in hash_map.items():
        debug_buckets.append({
            'key': key,
            'python_hash': hash(key),
            'item_count': len(items),
            'student_register_numbers': [item.get('register_number') for item in items],
            'first_item_hostel': items[0].get('hostel_name') if items else 'N/A'
        })

    return {
        'total_buckets': len(hash_map),
        'total_elements': len(requests),
        'load_factor': round(len(requests) / max(1, len(hash_map)), 2),
        'buckets': debug_buckets
    }

