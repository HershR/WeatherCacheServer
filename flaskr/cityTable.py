import os
import json
import requests


from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)

from pprint import pprint
from pyowm.owm import OWM

from werkzeug.exceptions import abort
from flaskr.weather import update_current_weather
from flaskr.db import get_db
from flaskr.weather import update_current_weather

bp = Blueprint('cityTable', __name__)

#owm = OWM(os.environ.get("OPENWEATHER_API_KEY"))
#reg = owm.city_id_registry()

@bp.route('/')
def index():
    #print('index')
    db = get_db()
    cities = db.execute(
        ' SELECT p.city_id , city_name, city_coord_long, city_coord_lat, city_country' 
        ' FROM owm_cities p'
        ' ORDER BY city_name ASC'
    ).fetchall()
    return render_template('cityTable/index.html', cities=cities)


@bp.route('/search/coordinates', methods=('GET', 'POST'))
def search_by_coordinates():
    if request.method == 'POST':
        coordinate = str(request.form['coordinate']).replace(" ","")
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
            print(coord)
            latitude = coord[0]
            longitude = coord[1]
            if not latitude:
                error = 'Latitude is required.'

            if not longitude:
                error = 'Longitude is required.'
        if error is not None:
            flash(error)
        else:

            # cities is a list of tuples
            # cities = reg.ids_for(name, country=country, state=state, matching='exact')

            # use geocoding api to find all cities, only returns a max of 5
            url = "https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={key}".format(lat=latitude, lon=longitude, key=os.environ.get("OPENWEATHER_API_KEY"))
            r = requests.get(url)

            if r.status_code != 200:
                error = 'Request failed'
                print(latitude)
                print(longitude)
            else:
                data = r.json()
                db = get_db()
                db.execute(
                    'INSERT INTO owm_cities (city_id, city_name, city_coord_long, city_coord_lat, city_country)'
                    ' VALUES (?, ?, ?, ?, ?)',
                    (data['id'], data['name'], data['coord']['lon'],data['coord']['lat'], data['sys']['country'])
                )
                db.commit()
                update_current_weather(data['id'])
                return redirect(url_for('cityTable.index'))
        if error is not None:
            flash(error)
    return render_template('cityTable/searchcoordinates.html')

@bp.route('/search', methods=('GET', 'POST'))
def search():
    if request.method == 'POST':
        #print('call def search in post')
        error = None
        name = str(request.form['city_name']).title()
        # state = str(request.form['state']).title()
        # country = str(request.form['country']).upper()
        if not name:
            error = 'Enter City name'

        if error is None:

            # cities is a list of tuples
            # cities = reg.ids_for(name, country=country, state=state, matching='exact')

            # use geocoding api to find all cities, only returns a max of 5
            url = 'http://api.openweathermap.org/geo/1.0/direct?q={name}&limit=5&appid={key}'\
                .format(name=name, key=os.environ.get("OPENWEATHER_API_KEY"))

            r = requests.get(url)

            if r.status_code!=200:
                error = 'Request failed'
            else:
                cities = r.json()
                data = cities
                for d in data:
                    #pprint(d)
                    if('local_names' in d):
                        del d['local_names']
                return render_template('cityTable/add.html', cities=data)
        if error is not None:
            flash(error)
    #print('call def search in get')
    return render_template('cityTable/search.html')


@bp.route('/addcity/<string:city>', methods=('GET', 'POST'))
def add(city=None):
    data = json.loads(city.replace("\'", "\""))
    error = None
    if not data:
        error = 'city data empty'
    name = str(data['name'])
    country = str(data['country'])
    latitude = data['lat']
    longitude = data['lon']
    if not latitude:
        error += ' missing lat'
    if not longitude:
        error += ' missing long'
    if error is None:
        db = get_db()
        db.execute(
            'INSERT INTO owm_cities (city_name, city_coord_long, city_coord_lat, city_country)'
            ' VALUES (?, ?, ?, ?)',
            (name, longitude, latitude, country)
        )
        db.commit()
        return redirect(url_for('cityTable.index'))

    else:
        flash(error)
    return redirect(url_for('cityTable.search'))


@bp.route('/delete/<int:city_id>', methods=('GET', 'POST'))
def delete(city_id=None):
    return

