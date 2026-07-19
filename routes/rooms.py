from flask import Blueprint, request, jsonify
from app import db
from models import ConferenceRoom, Booking
from datetime import datetime, time, timedelta

rooms_bp = Blueprint('rooms', __name__)

# Bookable window for a room: 09:00-18:00 in fixed 30-minute slots.
BUSINESS_START = time(9, 0)
BUSINESS_END = time(18, 0)
SLOT_MINUTES = 30

@rooms_bp.route('/rooms', methods=['GET'])
def get_rooms():
    """List all conference rooms.

    Purpose:
        Return every conference room in the system with its capacity and
        location. Takes no parameters and applies no filtering.

    Returns:
        flask.Response: JSON envelope ``{"data": list[dict], "error": None,
        "status": 200}`` where each item is a ``ConferenceRoom.to_dict()``
        mapping (id, name, capacity, location).

    Examples:
        Example 1 -- list every room::

            GET /rooms

        Example 2 -- pipe the result through a JSON formatter::

            GET /rooms   # then format client-side

    Browser:
        http://localhost:5000/rooms

    cURL:
        curl.exe -s "http://localhost:5000/rooms"
        curl.exe -s "http://localhost:5000/rooms" | python -m json.tool
    """
    rooms = ConferenceRoom.query.all()
    return jsonify({'data': [r.to_dict() for r in rooms], 'error': None, 'status': 200})

@rooms_bp.route('/rooms/<int:room_id>', methods=['GET'])
def get_room(room_id):
    """Retrieve a single conference room by its id.

    Purpose:
        Look up one room and return its details, or a 404 envelope when no room
        with the given id exists.

    Args:
        room_id (int): Primary key of the room, taken from the URL path.

    Returns:
        flask.Response: On success ``{"data": dict, "error": None,
        "status": 200}``; on a missing id ``{"data": None,
        "error": "Room not found", "status": 404}`` with HTTP 404.

    Examples:
        Example 1 -- fetch room 1::

            GET /rooms/1

        Example 2 -- non-existent room returns 404::

            GET /rooms/999999

    Browser:
        http://localhost:5000/rooms/1

    cURL:
        curl.exe -s "http://localhost:5000/rooms/1"
        curl.exe -s -w " [HTTP %{http_code}]\n" "http://localhost:5000/rooms/999999"
    """
    room = ConferenceRoom.query.get(room_id)
    if not room:
        return jsonify({'data': None, 'error': 'Room not found', 'status': 404}), 404
    return jsonify({'data': room.to_dict(), 'error': None, 'status': 200})

@rooms_bp.route('/rooms/<int:room_id>/availability', methods=['GET'])
def get_availability(room_id):
    """List a room's booked (occupied) time slots, optionally filtered by date.

    Purpose:
        Return the ``scheduled`` bookings for a room -- i.e. the slots that are
        already taken. Optionally restrict the result to a single calendar day.
        Cancelled bookings are never included.

    Args:
        room_id (int): Primary key of the room, taken from the URL path.

    Query Parameters:
        date (str, optional): Calendar day in ``YYYY-MM-DD`` form. When omitted,
            bookings across all dates are returned.

    Returns:
        flask.Response: On success ``{"data": list[dict], "error": None,
        "status": 200}`` where each item is a ``Booking.to_dict()`` mapping.
        Returns HTTP 400 ``{"data": None, "error": "Invalid date format. Use
        YYYY-MM-DD.", "status": 400}`` when ``date`` cannot be parsed.

    Examples:
        Example 1 -- all booked slots for room 1::

            GET /rooms/1/availability

        Example 2 -- booked slots for room 1 on a specific day::

            GET /rooms/1/availability?date=2025-07-01

    Browser:
        http://localhost:5000/rooms/1/availability?date=2025-07-01

    cURL:
        curl.exe -s "http://localhost:5000/rooms/1/availability"
        curl.exe -s "http://localhost:5000/rooms/1/availability?date=2025-07-01"
    """
    date_str = request.args.get('date', type=str)
    query = Booking.query.filter(
        Booking.room_id == room_id,
        Booking.status == 'scheduled'
    )
    if date_str:
        try:
            target_date = datetime.fromisoformat(date_str).date()
            query = query.filter(db.func.date(Booking.start_time) == target_date)
        except ValueError:
            return jsonify({'data': None, 'error': 'Invalid date format. Use YYYY-MM-DD.', 'status': 400}), 400
    bookings = query.all()
    return jsonify({'data': [b.to_dict() for b in bookings], 'error': None, 'status': 200})

@rooms_bp.route('/rooms/<int:room_id>/available-slots', methods=['GET'])
def get_available_slots(room_id):
    """List a room's free 30-minute slots within business hours for one day.

    Purpose:
        Return the bookable 30-minute slots between 09:00 and 18:00 on a given
        day that are NOT covered by any ``scheduled`` booking -- the complement
        of :func:`get_availability`. Slot boundaries use strict comparison, so a
        booking ending exactly when a slot starts does not block that slot.

    Args:
        room_id (int): Primary key of the room, taken from the URL path.

    Query Parameters:
        date (str): Required. Calendar day in ``YYYY-MM-DD`` form.

    Returns:
        flask.Response: On success ``{"data": list[dict], "error": None,
        "status": 200}`` where each item is ``{"start_time": iso, "end_time":
        iso}``. Error envelopes: HTTP 404 if the room is missing; HTTP 400 if
        ``date`` is absent or unparseable.

    Examples:
        Example 1 -- free slots for room 1 on a specific day::

            GET /rooms/1/available-slots?date=2025-07-01

        Example 2 -- missing date returns 400::

            GET /rooms/1/available-slots

    Browser:
        http://localhost:5000/rooms/1/available-slots?date=2025-07-01

    cURL:
        curl.exe -s "http://localhost:5000/rooms/1/available-slots?date=2025-07-01"
        curl.exe -s -w " [HTTP %{http_code}]\n" "http://localhost:5000/rooms/1/available-slots"
    """
    room = ConferenceRoom.query.get(room_id)
    if not room:
        return jsonify({'data': None, 'error': 'Room not found', 'status': 404}), 404

    date_str = request.args.get('date', type=str)
    if not date_str:
        return jsonify({'data': None, 'error': 'Missing required query param: date (YYYY-MM-DD)', 'status': 400}), 400
    try:
        target_date = datetime.fromisoformat(date_str).date()
    except ValueError:
        return jsonify({'data': None, 'error': 'Invalid date format. Use YYYY-MM-DD.', 'status': 400}), 400

    # Fetch that day's scheduled bookings once, then test each slot in memory.
    day_start = datetime.combine(target_date, BUSINESS_START)
    day_end = datetime.combine(target_date, BUSINESS_END)
    bookings = Booking.query.filter(
        Booking.room_id == room_id,
        Booking.status == 'scheduled',
        Booking.start_time < day_end,
        Booking.end_time > day_start,
    ).all()

    slots = []
    slot_start = day_start
    delta = timedelta(minutes=SLOT_MINUTES)
    while slot_start + delta <= day_end:
        slot_end = slot_start + delta
        # A slot is free if no booking overlaps it (strict comparison allows back-to-back).
        overlaps = any(b.start_time < slot_end and b.end_time > slot_start for b in bookings)
        if not overlaps:
            slots.append({'start_time': slot_start.isoformat(), 'end_time': slot_end.isoformat()})
        slot_start = slot_end

    return jsonify({'data': slots, 'error': None, 'status': 200})
