from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)

from werkzeug.exceptions import abort

from flaskr.db import get_db

bp = Blueprint('home', __name__)


@bp.route('/')
def index():
    print('index')
    db = get_db()
    cites = db.execute(
        ' SELECT p.city_id , city_name, city_coord_long, city_coord_lat, city_country' 
        ' FROM owm_cities p'
        ' ORDER BY city_name DESC'
    ).fetchall()
    return render_template('weather/index.html', cities=cites)


@bp.route('/add', methods=('GET', 'POST'))
def add():
    if request.method == 'POST':
        coordinate = str(request.form['coordinate'])
        error = None
        cord = []
        latitude = None
        longitude = None

        if not coordinate:
            error = 'Enter Coordinates'
        elif ',' not in coordinate:
            error = 'Check format'
        else:
            cord = coordinate.split(',')

        if len(cord) != 2:
            error = 'Check format'
        else:
            latitude = cord[0]
            longitude = cord[1]
            if not latitude:
                error = 'Latitude is required.'

            if not longitude:
                error = 'Longitude is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'INSERT INTO owm_cities (000, temp city, latitude, longitude, temp country)'
                ' VALUES (?, ?, ?)',
                (latitude, longitude, g.user['id'])
            )
            db.commit()
            return redirect(url_for('weather.index'))

    return render_template('weather/add.html')