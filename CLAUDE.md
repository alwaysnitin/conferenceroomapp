# Conference Room Booking System

## Project Overview
A small Flask + SQLite REST API for reserving shared conference rooms. It lets
internal staff browse rooms, see when a room is booked (or free), and create,
reschedule, and cancel meeting bookings — while the server enforces that no two
scheduled meetings in the same room overlap. It is a workshop/training project:
the data is seeded, there is no authentication, and it is meant to be run
locally rather than deployed.

The domain has three entities: **conference rooms** (name, capacity, location),
**employees** (the organizers), and **bookings** (a room reserved by an employee
for a time window). A booking references both a room and an organizer via
foreign keys. Cancellation is a *soft delete* — the booking's `status` flips to
`cancelled` and the row is kept.

### Running it
```bash
# 1. install deps (inside the checked-in venv or your own)
pip install -r requirements.txt

# 2. seed the database (drops & recreates all tables, then inserts sample data)
python db/seed_data.py

# 3. start the server  —  use flask run, NOT `python app.py` (see Useful Context)
#    PowerShell:
$env:FLASK_APP = "app"; flask run
#    bash:
FLASK_APP=app flask run
```
The API listens on `http://localhost:5000`. Seed data provides 5 rooms,
10 employees, and 20 bookings.

### Usage examples
```bash
# List all rooms
curl.exe -s "http://localhost:5000/rooms"

# See a room's booked slots on a given day
curl.exe -s "http://localhost:5000/rooms/1/availability?date=2025-07-01"

# See a room's FREE 30-min slots (09:00–18:00) on a given day
curl.exe -s "http://localhost:5000/rooms/1/available-slots?date=2025-07-01"

# Create a booking (409 if it overlaps an existing scheduled one)
curl.exe -X POST http://localhost:5000/bookings -H "Content-Type: application/json" ^
  -d "{\"room_id\":1,\"organizer_id\":1,\"start_time\":\"2026-07-25T09:00:00\",\"end_time\":\"2026-07-25T10:00:00\"}"

# Reschedule a booking
curl.exe -X PUT http://localhost:5000/bookings/1 -H "Content-Type: application/json" ^
  -d "{\"start_time\":\"2026-07-25T11:00:00\",\"end_time\":\"2026-07-25T12:00:00\"}"

# Cancel a booking (soft delete → status becomes "cancelled")
curl.exe -X DELETE http://localhost:5000/bookings/1
```

## Tech Stack
- Language: Python 3.11
- Framework: Flask 3.0
- ORM: Flask-SQLAlchemy 3.1
- Database: SQLite (db/bookings.db)
- Testing: pytest 8.2 + pytest-cov (see `tests/`)

## Coding Conventions
- **Uniform JSON response envelope.** Every route returns
  `{"data": ..., "error": ..., "status": <int>}`, and the HTTP status code
  matches the `status` field (e.g. a 404 body carries `"status": 404` and is
  returned with `, 404`). Success puts the payload in `data` and `error: None`;
  failures set `data: None` and a human-readable `error` string.
- **Application-factory + blueprint-per-resource.** `db = SQLAlchemy()` is
  created once in `app.py` and initialized inside `create_app()`; models and
  routes import it via `from app import db`. Routes are grouped into blueprints
  named `<resource>_bp` (`bookings_bp`, `rooms_bp`), one file per resource under
  `routes/`.
- **Naming.** Handlers are `verb_noun` in snake_case (`get_rooms`,
  `create_booking`, `reschedule_booking`, `cancel_booking`); URL paths are
  lowercase plural nouns (`/rooms`, `/bookings`) with `<int:...>` path
  converters; DB tables are snake_case plural (`conference_rooms`, `employees`,
  `bookings`).
- **Datetimes cross the boundary as ISO 8601 strings.** Requests are parsed with
  `datetime.fromisoformat`, responses serialize via `.isoformat()` in
  `to_dict()`. Always validate the format and the `end_time > start_time`
  invariant *before* persisting.
- **Business logic lives in `utils/`, not in route handlers.** Overlap detection
  is centralized in `utils/conflict.py::check_overlap` and reused by both create
  and reschedule, rather than being duplicated inline.
- **Soft delete over hard delete.** State transitions use the `status` column
  (`scheduled` → `cancelled`); rows are not removed. Availability and conflict
  queries therefore always filter on `status == 'scheduled'`.

## Do Not Touch
- **The strict-comparison overlap logic in `utils/conflict.py`.** It uses
  `start_time < end_time AND end_time > start_time` (strict `<`/`>`) so that
  back-to-back bookings (e.g. 09:00–09:30 followed by 09:30–10:00) are
  *allowed*. Changing these to `<=`/`>=` would silently reject legitimate
  adjacent bookings, and the `available-slots` route depends on the same rule.
  Any change here must be paired with tests covering the back-to-back case.

## Useful Context
- **Run with `flask run`, not `python app.py`.** Running the module directly
  triggers a circular import: `app.py` executes as `__main__`, then
  `from app import db` in the route/model modules imports `app.py` a *second*
  time as the `app` module, re-running `create_app()` while `routes/bookings.py`
  is only partially initialized → `ImportError: cannot import name
  'bookings_bp'`. Launching via `flask run` (with `FLASK_APP=app`) imports the
  module once and avoids this. The `if __name__ == '__main__': app.run()` block
  at the bottom of `app.py` is effectively broken for this reason.
- **Seed data shape & timing.** `python db/seed_data.py` calls `db.drop_all()`
  first, so it wipes everything before reseeding. It produces 5 rooms,
  10 employees, and 20 bookings all dated in **July 2025** at hourly starts from
  09:00, each 30 minutes long — but several land in the evening (18:00–21:30),
  i.e. *outside* the 09:00–18:00 business window used by
  `/rooms/<id>/available-slots`. When testing that route against seed data,
  expect a mostly-empty booked set; add an in-hours booking to see slots get
  excluded. Business hours and slot length are constants at the top of
  `routes/rooms.py` (`BUSINESS_START`, `BUSINESS_END`, `SLOT_MINUTES`).
