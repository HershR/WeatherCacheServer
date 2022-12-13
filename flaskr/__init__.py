import os
from flask import Flask
from .extensions import db, migrate, scheduler


def create_app():
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    # config file should be in instance folder
    app.config.from_pyfile('config.py')

    db.init_app(app)
    migrate.init_app(app, db)
    scheduler.init_app(app)

    """
    Flask Scheduler setup from documentation
    https://github.com/viniciuschiele/flask-apscheduler/blob/master/examples/application_factory/__init__.py
    """

    with app.app_context():
        if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
            from . import tasks  # noqa: F401
            #print('start schedualr')
            scheduler.start()

        from . import weather
        app.register_blueprint(weather.bp)

        from . import cities
        app.register_blueprint(cities.bp)
        app.add_url_rule('/', endpoint='index')

        return app
