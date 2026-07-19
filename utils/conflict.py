from models import Booking

def check_overlap(room_id, start_time, end_time, exclude_id=None):
    """Check whether a proposed booking slot clashes with existing bookings.

    Purpose:
        Determine if a proposed time window overlaps any ``scheduled`` booking in
        a given room. Two bookings overlap when one starts before the other ends
        AND ends after the other starts. Strict less-than comparisons are used so
        back-to-back bookings (e.g. 09:00-09:30 then 09:30-10:00) are allowed.

    Args:
        room_id (int): Id of the conference room whose schedule to check.
        start_time (datetime.datetime): Proposed booking start.
        end_time (datetime.datetime): Proposed booking end.
        exclude_id (int, optional): Booking id to ignore, used during
            rescheduling so a booking does not conflict with itself. Defaults to
            None.

    Returns:
        bool: ``True`` if an overlapping scheduled booking exists, ``False`` if
        the slot is free.

    Examples:
        Example 1 -- validate a brand-new booking::

            from datetime import datetime
            if check_overlap(1, datetime(2026, 7, 25, 9), datetime(2026, 7, 25, 10)):
                abort(409)

        Example 2 -- validate a reschedule, ignoring the booking itself::

            clashes = check_overlap(
                booking.room_id, new_start, new_end, exclude_id=booking.id)

    Browser / cURL:
        Not directly callable -- this is an internal helper invoked by the
        booking routes. Its effect is observable via the create/reschedule
        endpoints, which return HTTP 409 when it reports a conflict, e.g.
        curl.exe -X POST http://localhost:5000/bookings -H "Content-Type: application/json" -d "{...overlapping slot...}"
    """
    query = Booking.query.filter(
        Booking.room_id == room_id,
        Booking.status == 'scheduled',
        Booking.start_time < end_time,
        Booking.end_time > start_time,
    )
    if exclude_id:
        query = query.filter(Booking.id != exclude_id)
    return query.first() is not None
