import os
from flask import Flask
from .extensions import db, migrate, scheduler


def create_app(test_config=None):
    def is_debug_mode():
        """Get app debug status."""
        debug = os.environ.get("FLASK_DEBUG")
        if not debug:
            return os.environ.get("FLASK_ENV") == "development"
        return debug.lower() not in ("0", "false", "no")

    def is_werkzeug_reloader_process():
        """Get werkzeug status."""
        return os.environ.get("WERKZEUG_RUN_MAIN") == "true"

    # create and configure the app
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY='dev',  # todo add key here
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SCHEDULER_API_ENABLED=True,
    )

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    db.init_app(app)
    migrate.init_app(app, db)
    scheduler.init_app(app)

    """
    Flask Scheduler setup from documentation
    https://github.com/viniciuschiele/flask-apscheduler/blob/master/examples/application_factory/__init__.py
    """

    # pylint: disable=C0415, W0611
    with app.app_context():

        # pylint: disable=W0611
        if is_debug_mode() and not is_werkzeug_reloader_process():
            pass
        else:
            from . import tasks  # noqa: F401
            #todo Uncomment to Start Scheduler
            #scheduler.start()

    from . import weather
    app.register_blueprint(weather.bp)

    from . import cities
    app.register_blueprint(cities.bp)
    app.add_url_rule('/', endpoint='index')

    return app
