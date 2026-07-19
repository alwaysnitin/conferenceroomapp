from app import db
from datetime import datetime

class ConferenceRoom(db.Model):
    __tablename__ = 'conference_rooms'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    location = db.Column(db.String(100), nullable=False)
    bookings = db.relationship('Booking', backref='room', lazy=True)

    def to_dict(self):
        """Serialize this conference room to a JSON-friendly dict.

        Purpose:
            Convert the ORM instance into plain primitives so it can be embedded
            in an API response envelope by the route handlers.

        Args:
            None (operates on ``self``).

        Returns:
            dict: ``{"id": int, "name": str, "capacity": int, "location": str}``.

        Examples:
            Example 1 -- serialize a single room::

                ConferenceRoom.query.get(1).to_dict()

            Example 2 -- serialize every room::

                [r.to_dict() for r in ConferenceRoom.query.all()]

        Browser / cURL:
            Not directly callable -- this is an internal helper. Its output is
            exposed through the room routes, e.g.
            http://localhost:5000/rooms/1
            curl.exe -s "http://localhost:5000/rooms/1"
        """
        return {'id': self.id, 'name': self.name, 'capacity': self.capacity, 'location': self.location}

class Employee(db.Model):
    __tablename__ = 'employees'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    department = db.Column(db.String(100), nullable=False)
    bookings = db.relationship('Booking', backref='organizer', lazy=True)

    def to_dict(self):
        """Serialize this employee to a JSON-friendly dict.

        Purpose:
            Convert the ORM instance into plain primitives for inclusion in an
            API response.

        Args:
            None (operates on ``self``).

        Returns:
            dict: ``{"id": int, "name": str, "email": str, "department": str}``.

        Examples:
            Example 1 -- serialize a single employee::

                Employee.query.get(1).to_dict()

            Example 2 -- serialize a filtered set::

                [e.to_dict() for e in Employee.query.filter_by(department='Sales')]

        Browser / cURL:
            Not directly callable -- employees are not currently exposed via a
            dedicated route; this helper is used internally by the ORM layer.
        """
        return {'id': self.id, 'name': self.name, 'email': self.email, 'department': self.department}

class Booking(db.Model):
    __tablename__ = 'bookings'
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('conference_rooms.id'), nullable=False)
    organizer_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    meeting_title = db.Column(db.String(200))
    attendees = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), default='scheduled')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Serialize this booking to a JSON-friendly dict.

        Purpose:
            Convert the ORM instance into plain primitives, rendering the
            ``start_time`` and ``end_time`` datetimes as ISO 8601 strings so the
            payload is JSON-serializable. ``created_at`` is intentionally omitted.

        Args:
            None (operates on ``self``).

        Returns:
            dict: ``{"id": int, "room_id": int, "organizer_id": int,
            "start_time": str, "end_time": str, "meeting_title": str | None,
            "attendees": int | None, "status": str | None}`` where the times are
            ISO 8601 strings.

        Examples:
            Example 1 -- serialize a single booking::

                Booking.query.get(1).to_dict()

            Example 2 -- serialize a room's bookings::

                [b.to_dict() for b in Booking.query.filter_by(room_id=1)]

        Browser / cURL:
            Not directly callable -- this is an internal helper. Its output is
            exposed through the booking routes, e.g.
            http://localhost:5000/bookings/1
            curl.exe -s "http://localhost:5000/bookings/1"
        """
        return {
            'id': self.id,
            'room_id': self.room_id,
            'organizer_id': self.organizer_id,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'meeting_title': self.meeting_title,
            'attendees': self.attendees,
            'status': self.status
        }
