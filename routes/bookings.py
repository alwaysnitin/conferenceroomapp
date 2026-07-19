from flask import Blueprint, request, jsonify
from app import db
from models import Booking, ConferenceRoom, Employee
from utils.conflict import check_overlap
from datetime import datetime

bookings_bp = Blueprint('bookings', __name__)

@bookings_bp.route('/bookings', methods=['GET'])
def get_bookings():
    """List bookings, optionally filtered by room and/or organizer.

    Purpose:
        Return every booking in the system, narrowing the result set with the
        optional ``room_id`` and ``organizer_id`` query-string parameters. When
        both are supplied they are combined with AND.

    Query Parameters:
        room_id (int, optional): Restrict results to this conference room's id.
        organizer_id (int, optional): Restrict results to this employee's id.

    Returns:
        flask.Response: JSON envelope ``{"data": list[dict], "error": None,
        "status": 200}`` where each item is a ``Booking.to_dict()`` mapping.

    Examples:
        Example 1 -- all bookings for room 1::

            GET /bookings?room_id=1

        Example 2 -- bookings organized by employee 3::

            GET /bookings?organizer_id=3

    Browser:
        http://localhost:5000/bookings?room_id=1

    cURL:
        curl.exe -s "http://localhost:5000/bookings?room_id=1"
        curl.exe -s "http://localhost:5000/bookings?organizer_id=3"
    """
    room_id = request.args.get('room_id', type=int)
    organizer_id = request.args.get('organizer_id', type=int)
    query = Booking.query
    if room_id:
        query = query.filter_by(room_id=room_id)
    if organizer_id:
        query = query.filter_by(organizer_id=organizer_id)
    bookings = query.all()
    return jsonify({'data': [b.to_dict() for b in bookings], 'error': None, 'status': 200})

@bookings_bp.route('/bookings/<int:booking_id>', methods=['GET'])
def get_booking(booking_id):
    """Retrieve a single booking by its id.

    Purpose:
        Look up one booking and return it, or a 404 envelope if no booking with
        that id exists.

    Args:
        booking_id (int): Primary key of the booking, taken from the URL path.

    Returns:
        flask.Response: On success ``{"data": dict, "error": None,
        "status": 200}``; on a missing id ``{"data": None,
        "error": "Booking not found", "status": 404}`` with HTTP 404.

    Examples:
        Example 1 -- fetch booking 1::

            GET /bookings/1

        Example 2 -- non-existent booking returns 404::

            GET /bookings/999999

    Browser:
        http://localhost:5000/bookings/1

    cURL:
        curl.exe -s "http://localhost:5000/bookings/1"
        curl.exe -s -w " [HTTP %{http_code}]\n" "http://localhost:5000/bookings/999999"
    """
    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({'data': None, 'error': 'Booking not found', 'status': 404}), 404
    return jsonify({'data': booking.to_dict(), 'error': None, 'status': 200})

@bookings_bp.route('/bookings', methods=['POST'])
def create_booking():
    """Create a new booking after validating input and checking for conflicts.

    Purpose:
        Validate the JSON body, reject bad datetimes or time-slot conflicts, and
        persist a new ``scheduled`` booking for the given room and organizer.

    JSON Body:
        room_id (int): Required. Id of the room to book.
        organizer_id (int): Required. Id of the organizing employee.
        start_time (str): Required. ISO 8601 datetime, e.g. ``2026-07-25T09:00:00``.
        end_time (str): Required. ISO 8601 datetime; must be after ``start_time``.
        meeting_title (str, optional): Defaults to ``""``.
        attendees (int, optional): Defaults to ``1``.

    Returns:
        flask.Response: On success ``{"data": dict, "error": None,
        "status": 201}`` with HTTP 201. Error envelopes: HTTP 400 for missing
        body/fields, bad datetime format, or ``end_time <= start_time``; HTTP
        409 when the slot overlaps an existing scheduled booking.

    Examples:
        Example 1 -- book room 1 for a one-hour meeting::

            POST /bookings
            {"room_id": 1, "organizer_id": 1,
             "start_time": "2026-07-25T09:00:00", "end_time": "2026-07-25T10:00:00"}

        Example 2 -- with optional title and attendee count::

            POST /bookings
            {"room_id": 2, "organizer_id": 3,
             "start_time": "2026-07-25T14:00:00", "end_time": "2026-07-25T15:30:00",
             "meeting_title": "Design Review", "attendees": 8}

    Browser:
        Not possible -- POST cannot be issued from the address bar. Use cURL,
        Postman, or fetch() from JavaScript.

    cURL:
        curl.exe -X POST http://localhost:5000/bookings -H "Content-Type: application/json" -d "{\\"room_id\\":1,\\"organizer_id\\":1,\\"start_time\\":\\"2026-07-25T09:00:00\\",\\"end_time\\":\\"2026-07-25T10:00:00\\"}"
        curl.exe -X POST http://localhost:5000/bookings -H "Content-Type: application/json" -d "{\\"room_id\\":2,\\"organizer_id\\":3,\\"start_time\\":\\"2026-07-25T14:00:00\\",\\"end_time\\":\\"2026-07-25T15:30:00\\",\\"meeting_title\\":\\"Design Review\\",\\"attendees\\":8}"
    """
    data = request.get_json()
    if not data:
        return jsonify({'data': None, 'error': 'No data provided', 'status': 400}), 400
    required = ['room_id', 'organizer_id', 'start_time', 'end_time']
    for field in required:
        if field not in data:
            return jsonify({'data': None, 'error': f'Missing field: {field}', 'status': 400}), 400
    try:
        start = datetime.fromisoformat(data['start_time'])
        end = datetime.fromisoformat(data['end_time'])
    except ValueError:
        return jsonify({'data': None, 'error': 'Invalid datetime format. Use ISO 8601.', 'status': 400}), 400
    if end <= start:
        return jsonify({'data': None, 'error': 'end_time must be after start_time', 'status': 400}), 400
    if check_overlap(data['room_id'], start, end):
        return jsonify({'data': None, 'error': 'Time slot conflicts with existing booking', 'status': 409}), 409
    booking = Booking(
        room_id=data['room_id'],
        organizer_id=data['organizer_id'],
        start_time=start,
        end_time=end,
        meeting_title=data.get('meeting_title', ''),
        attendees=data.get('attendees', 1),
        status='scheduled'
    )
    db.session.add(booking)
    db.session.commit()
    return jsonify({'data': booking.to_dict(), 'error': None, 'status': 201}), 201

@bookings_bp.route('/bookings/<int:booking_id>', methods=['PUT'])
def reschedule_booking(booking_id):
    """Reschedule an existing booking to a new time window.

    Purpose:
        Update the ``start_time`` and ``end_time`` of an existing booking after
        validating the new window and confirming it does not clash with other
        scheduled bookings in the same room (the booking itself is excluded from
        the conflict check).

    Args:
        booking_id (int): Primary key of the booking, taken from the URL path.

    JSON Body:
        start_time (str): Required. New ISO 8601 start datetime.
        end_time (str): Required. New ISO 8601 end datetime; must be after start.

    Returns:
        flask.Response: On success ``{"data": dict, "error": None,
        "status": 200}``. Error envelopes: HTTP 404 if the booking is missing;
        HTTP 400 for missing body, bad datetime format, or
        ``end_time <= start_time``; HTTP 409 if the new slot conflicts.

    Examples:
        Example 1 -- move booking 1 to a later hour::

            PUT /bookings/1
            {"start_time": "2026-07-25T11:00:00", "end_time": "2026-07-25T12:00:00"}

        Example 2 -- shorten booking 2 to 30 minutes::

            PUT /bookings/2
            {"start_time": "2026-07-25T09:00:00", "end_time": "2026-07-25T09:30:00"}

    Browser:
        Not possible -- PUT cannot be issued from the address bar. Use cURL or
        Postman.

    cURL:
        curl.exe -X PUT http://localhost:5000/bookings/1 -H "Content-Type: application/json" -d "{\\"start_time\\":\\"2026-07-25T11:00:00\\",\\"end_time\\":\\"2026-07-25T12:00:00\\"}"
        curl.exe -X PUT http://localhost:5000/bookings/2 -H "Content-Type: application/json" -d "{\\"start_time\\":\\"2026-07-25T09:00:00\\",\\"end_time\\":\\"2026-07-25T09:30:00\\"}"
    """
    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({'data': None, 'error': 'Booking not found', 'status': 404}), 404
    data = request.get_json()
    if not data:
        return jsonify({'data': None, 'error': 'No data provided', 'status': 400}), 400
    try:
        start = datetime.fromisoformat(data['start_time'])
        end = datetime.fromisoformat(data['end_time'])
    except ValueError:
        return jsonify({'data': None, 'error': 'Invalid datetime format. Use ISO 8601.', 'status': 400}), 400
    if end <= start:
        return jsonify({'data': None, 'error': 'end_time must be after start_time', 'status': 400}), 400
    if check_overlap(booking.room_id, start, end, exclude_id=booking_id):
        return jsonify({'data': None, 'error': 'New time slot conflicts with existing booking', 'status': 409}), 409
    booking.start_time = start
    booking.end_time = end
    db.session.commit()
    return jsonify({'data': booking.to_dict(), 'error': None, 'status': 200})

@bookings_bp.route('/bookings/<int:booking_id>', methods=['DELETE'])
def cancel_booking(booking_id):
    """Cancel a booking (soft delete).

    Purpose:
        Mark a booking as ``cancelled`` rather than removing the row. The record
        remains in the database and continues to appear in ``GET /bookings``, but
        is excluded from availability and conflict checks.

    Args:
        booking_id (int): Primary key of the booking, taken from the URL path.

    Returns:
        flask.Response: On success ``{"data": dict, "error": None,
        "status": 200}`` with the booking now showing ``"status": "cancelled"``.
        Returns HTTP 404 ``{"data": None, "error": "Booking not found",
        "status": 404}`` if the id does not exist.

    Examples:
        Example 1 -- cancel booking 1::

            DELETE /bookings/1

        Example 2 -- cancelling a missing booking returns 404::

            DELETE /bookings/999999

    Browser:
        Not possible -- DELETE cannot be issued from the address bar. Use cURL or
        Postman.

    cURL:
        curl.exe -X DELETE http://localhost:5000/bookings/1
        curl.exe -X DELETE -w " [HTTP %{http_code}]\n" http://localhost:5000/bookings/999999
    """
    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({'data': None, 'error': 'Booking not found', 'status': 404}), 404
    booking.status = 'cancelled'
    db.session.commit()
    return jsonify({'data': booking.to_dict(), 'error': None, 'status': 200})
