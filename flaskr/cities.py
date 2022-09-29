import os
import requests

from flaskr.database import db
from flaskr.models import OwmCities

from flask import (
    Blueprint, flash, redirect, render_template, request, url_for
)

bp = Blueprint('cities', __name__)

key = os.environ.get("OPENWEATHERMAP_API_KEY")


@bp.route('/')
def index():
    cities = OwmCities.query.order_by(OwmCities.city_name.asc()).all()
    return render_template('cities/index.html', cities=cities)


# search and add city by its coordinates
@bp.route('/search/coordinates', methods=('GET', 'POST'))
def search_by_coordinates():
    if request.method == 'POST':
        print('postgress call')
        coordinate = str(request.form['coordinate']).replace(" ", "")
        error = None
        coord = []
        latitude = None
        longitude = None
        if not coordinate:
            error = 'Enter Coordinates'
        elif ',' not in coordinate:
            error = 'Check format'
        else:
            coord = coordinate.split(',')
        if len(coord) != 2:
            error = 'Check format'
        else:
            latitude = coord[0]
            longitude = coord[1]
            if not latitude:
                error = 'Latitude is required.'
            if not longitude:
                error = 'Longitude is required.'
        if error is None:
            url = "https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={key}".format(lat=latitude, lon=longitude, key=key)
            r = requests.get(url)

            if r.status_code != 200:
                error = 'Search Error: Request failed Status code: ' + str(r.status_code)
            else:
                data = r.json()
                city = OwmCities.query.filter_by(city_id=data['id']).first()
                if city is not None:
                    error = 'City already being tracked'
                else:
                    city = OwmCities(city_id=data['id'],
                                     city_name=data['name'],
                                     city_coord_long=data['coord']['lon'],
                                     city_coord_lat=data['coord']['lat'],
                                     city_country=data['sys']['country']
                                     )
                    db.session.add(city)
                    db.session.commit()
                    return redirect(url_for('cities.index'))
        if error is not None:
            flash(error)
    return render_template('cities/searchcoordinates.html')
