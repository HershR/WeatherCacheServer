import os

from flask import Flask
from flaskr.database import db, migrate


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY='dev',  # todo add key here
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False
    )

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    db.init_app(app)
    migrate.init_app(app, db)

    from . import weather
    app.register_blueprint(weather.bp)

    from . import cities
    app.register_blueprint(cities.bp)
    app.add_url_rule('/', endpoint='index')

    return app
