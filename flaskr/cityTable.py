import os

import requests
from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)

from pyowm.owm import OWM


from werkzeug.exceptions import abort

from flaskr.db import get_db

bp = Blueprint('cityTable', __name__)

#owm = OWM(os.environ.get("OPENWEATHER_API_KEY"))
#reg = owm.city_id_registry()

@bp.route('/')
def index():
    print('index')
    db = get_db()
    cities = db.execute(
        ' SELECT p.city_id , city_name, city_coord_long, city_coord_lat, city_country' 
        ' FROM owm_cities p'
        ' ORDER BY city_id DESC'
    ).fetchall()
    return render_template('cityTable/index.html', cities=cities)


@bp.route('/search', methods=('GET', 'POST'))
def search():
    if request.method == 'POST':
        error = None
        name = str(request.form['city_name']).title()
        # state = str(request.form['state']).title()
        # country = str(request.form['country']).upper()
        if not name:
            error = 'Enter City name'

        if error is None:

            # cities is a list of tuples
            # cities = reg.ids_for(name, country=country, state=state, matching='exact')
            url = 'http://api.openweathermap.org/geo/1.0/direct?q={name}&limit=5&appid={key}'\
                .format(name=name, key=os.environ.get("OPENWEATHER_API_KEY"))

            r = requests.get(url)

            if r.status_code!=200:
                error = 'Request failed'
            else:
                cities = r.json()
                print((cities[4])['name'])
                data = list()
                for city in cities:
                    c = list()
                    for attribute, value in city.items():
                        if(attribute=='local_names'):
                            continue
                        c.append(city[attribute])
                    data.append(c)
                # for i in len(range(cities)):
                #    data.append(tuple((cities[i]).name, cities[i].lat, cities[i].lon, cities[i].country, cities[i].state))

                # check if in city is in database
                # db = get_db()
                # for i in range(len(cities)):
                #    city = db.execute(
                #        'SELECT * FROM owm_cities WHERE city_id = ?', ((cities[i]).,)
                #    ).fetchone()
                #    if city is not None:
                #        cities.pop(i)
                #        i -= 1
                return render_template('cityTable/addCity.html', cities=data)
        if error is not None:
            flash(error)
    return render_template('cityTable/search.html')


@bp.route('/add', methods=('GET', 'POST'))
def add():
    if request.method == 'POST':
        city_data = request.form['data']
        if not city_data:
            error = 'city_id empty'
        latitude = city_data[-1]
        longitude = city_data[-2]
        error = None

        if error is not None:
            flash(error)
        else:
            db = get_db()


            url = "https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&exclude={part}&appid={API key}".format(latitude, longitude, "hourly,daily", os.environ.get("OPENWEATHER_API_KEY"))
            r = requests.get(url)
            if r.status_code == 200:
                return


            db.execute(
                'INSERT INTO owm_cities (city_id, city_name, city_coord_long, city_coord_lat, city_country)'
                ' VALUES (?, ?, ?, ?, ?)',
                (000, "city a", longitude, latitude, "country a")
            )
            db.commit()
            return redirect(url_for('cityTable.index'))

    return render_template('cityTable/add.html')


@bp.route('/<int:id>/current_weather', methods=('GET', 'POST'))
def current_weather(id):
    db = get_db()
    return render_template('cityTable/current_weather.html')