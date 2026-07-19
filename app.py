from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

db = SQLAlchemy()

def create_app():
    """Build and configure the Flask application (application factory).

    Purpose:
        Instantiate the Flask app, wire up the SQLite database and SQLAlchemy,
        register the bookings and rooms blueprints plus the ``/health`` route,
        and create any missing tables. This is the single entry point used by
        both ``flask run`` and the ``app = create_app()`` module-level call.

    Args:
        None.

    Returns:
        flask.Flask: A fully configured application instance ready to serve
        requests.

    Examples:
        Example 1 -- create an app for the WSGI server::

            app = create_app()

        Example 2 -- create an isolated app inside a test::

            def test_health():
                client = create_app().test_client()
                assert client.get('/health').status_code == 200

    Browser / cURL:
        Not directly callable over HTTP -- this is an internal factory. Run the
        app with ``flask run`` (FLASK_APP=app), then reach its routes such as
        http://localhost:5000/health.
    """
    app = Flask(__name__)
    base_dir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(base_dir, 'db', 'bookings.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'workshop-secret-key'

    db.init_app(app)

    from routes.bookings import bookings_bp
    from routes.rooms import rooms_bp
    app.register_blueprint(bookings_bp)
    app.register_blueprint(rooms_bp)

    @app.route('/health')
    def health():
        """Report service health for liveness/readiness checks.

        Purpose:
            Provide a lightweight endpoint that confirms the service is up. It
            touches no database and always returns the same static payload,
            making it suitable for load-balancer and uptime probes.

        Args:
            None.

        Returns:
            dict: ``{"status": "ok", "service": "conference-room-booking"}``,
            which Flask serializes to JSON with HTTP 200.

        Examples:
            Example 1 -- basic health probe::

                GET /health

            Example 2 -- check just the HTTP status code::

                GET /health   # expect 200

        Browser:
            http://localhost:5000/health

        cURL:
            curl.exe -s "http://localhost:5000/health"
            curl.exe -s -o NUL -w "%{http_code}\n" "http://localhost:5000/health"
        """
        return {'status': 'ok', 'service': 'conference-room-booking'}

    with app.app_context():
        db.create_all()

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
