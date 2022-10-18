# Hersh Rudrawal
# weather.py
# Contains functions required to update
# the database with weather data
# Also contains the page routes to display
# the data in db
# note: not all inserted field contains correct values,
from flaskr import create_app
import os
import xmltodict
import json
import requests
import datetime


from flask import (
    Blueprint, flash, redirect, render_template, url_for
)

from werkzeug.exceptions import abort
from .extensions import db, scheduler
from .models import OwmCities, OwmCurrentWeather, OwmHourlyWeatherForecast


bp = Blueprint('weather', __name__)

# Add your own Open Weather Api Key here
owm_api_key = os.environ.get("OPENWEATHERMAP_API_KEY")


# fuction to return a list of city ids
def city_ids():
    result = OwmCities.query.with_entities(OwmCities.city_id)
    id = [r for (r,) in result]
    return id


# will get the current weather for a given city
# and updated owm_current_weather with the data
# able to call with free api key
def update_current_weather(city_id):
    error = None
    latitude = None
    longitude = None
    # check is city is being tracked
    city = OwmCities.query.filter_by(city_id=city_id).first()
    if city is None:
        error = 'Update Current Weather Error: city not currently tracked'
    else:
        latitude = city.city_coord_lat
        longitude = city.city_coord_long
        if latitude is None or longitude is None:
            error = 'Update Current Weather Error: coordinates missing for city: ' + city.city_name

    if error is None:
        # get weather data in xml format
        url = "https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={key}&units=metric&mode=xml".format(lat=latitude, lon=longitude, key=owm_api_key)
        r = requests.get(url)
        if r.status_code == 200:
            #convert xml format to dictionary
            data = xmltodict.parse(r.content, attr_prefix="")['current']

            # convert timestamps to datetime
            sunrise = datetime.datetime.strptime(data['city']['sun']['rise'], "%Y-%m-%dT%H:%M:%S")
            sunset = datetime.datetime.strptime(data['city']['sun']['set'], "%Y-%m-%dT%H:%M:%S")
            lastupdate_value = datetime.datetime.strptime(data['lastupdate']['value'], "%Y-%m-%dT%H:%M:%S")

            #check for wind
            if data['wind']['direction'] is None:
                wind_direction_value_deg = None
                wind_direction_code = None
                wind_direction_name = None
            else:
                wind_direction_value_deg = data['wind']['direction']['value']
                wind_direction_code = data['wind']['direction']['code']
                wind_direction_name = data['wind']['direction']['name']

            # insert data into owm_current_weather
            weather = OwmCurrentWeather(city_id=city_id,
                                        city_sun_rise=sunrise,
                                        city_sun_set=sunset,
                                        timezone_offset=data['city']['timezone'],
                                        lastupdate_value=lastupdate_value,
                                        temperature_value=data['temperature']['value'],
                                        temperature_min=data['temperature']['min'],
                                        temperature_max=data['temperature']['max'],
                                        temperature_unit=data['temperature']['unit'],
                                        feels_like_value=data['feels_like']['value'],
                                        feels_like_unit=data['feels_like']['unit'],
                                        humidity_value=data['humidity']['value'],
                                        pressure_value=data['pressure']['value'],
                                        wind_speed_value=data['wind']['speed']['value'],
                                        wind_speed_name=data['wind']['speed']['name'],
                                        wind_direction_value_deg=wind_direction_value_deg,
                                        wind_direction_code=wind_direction_code,
                                        wind_direction_name=wind_direction_name,
                                        cloud_value_pct=data['clouds']['value'],
                                        cloud_name=data['clouds']['name'],
                                        visibility_value_m=data['visibility']['value'],
                                        precipitation_value_mm=0 if 'value' not in data['precipitation'] else data['precipitation']['value'],
                                        precipitation_mode=data['precipitation']['mode'],
                                        weather_number=data['weather']['number'],
                                        weather_value=data['weather']['value'],
                                        weather_icon=data['weather']['icon']
                                        )
            db.session.add(weather)
            db.session.commit()
        else:
            error = 'Update Current Weather Error: Failed to connect to Open Weather API\nstatus code: ' + str(r.status_code)
    return error


# will get the next day's forecast for a city
# in 3h intervals
# able to call with free api key
def update_forcast_3h(city_id, days=1):
    # ensure days is within range
    if days < 1:
        days = 1
    if days > 5:
        days = 5
    timestamps = days * 8  # number of timestamps to receive from api call, 8 timestamps per day
    error = None
    latitude = longitude = None

    # check is city is being tracked
    city = OwmCities.query.filter_by(city_id=city_id).first()
    if city is None:
        error = 'Update Weather Hourly Error: city not currently tracked'
    else:
        latitude = city.city_coord_lat
        longitude = city.city_coord_long
        if latitude is None or longitude is None:
            error = 'Update Weather Hourly Error: coordinates missing for city: ' + city.city_name
    if error is None:
        url = 'http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&units=metric&cnt={count}&appid={key}&mode=xml'.format(lat=latitude, lon=longitude, count=timestamps, key=owm_api_key)
        r = requests.get(url)
        if r.status_code == 200:
            # convert to dictionary
            data = xmltodict.parse(r.content, attr_prefix="")['weatherdata']
            for i in range(0, timestamps):
                exist = OwmHourlyWeatherForecast.query.filter_by(city_id=city_id, forecast_timestamp=data['forecast']['time'][i]['from']).first()

                if exist is not None:
                    continue

                # convert timestamps to datetime
                sunrise = datetime.datetime.strptime(data['sun']['rise'], "%Y-%m-%dT%H:%M:%S")
                sunset = datetime.datetime.strptime(data['sun']['set'], "%Y-%m-%dT%H:%M:%S")
                forecast_timestamp = datetime.datetime.strptime(data['forecast']['time'][i]['from'], "%Y-%m-%dT%H:%M:%S")
                lastupdate_value = None
                if data['meta']['lastupdate'] is not None:
                    lastupdate_value = datetime.datetime.strptime(data['meta']['lastupdate'], "%Y-%m-%dT%H:%M:%S")

                #check if there is no wind
                if data['forecast']['time'][i]['windDirection'] is None:
                    wind_direction_value_deg = None
                    wind_direction_code = None
                    wind_direction_name = None
                else:
                    wind_direction_value_deg = data['forecast']['time'][i]['windDirection']['deg']
                    wind_direction_code = data['forecast']['time'][i]['windDirection']['code']
                    wind_direction_name = data['forecast']['time'][i]['windDirection']['name']

                weather = OwmHourlyWeatherForecast( forecast_timestamp=forecast_timestamp,
                                                    city_id=city_id,
                                                    city_sun_rise=sunrise,
                                                    city_sun_set=sunset,
                                                    timezone_offset=data['location']['timezone'],
                                                    lastupdate_value=lastupdate_value,
                                                    temperature_value=data['forecast']['time'][i]['temperature']['value'],
                                                    temperature_min=data['forecast']['time'][i]['temperature']['min'],
                                                    temperature_max=data['forecast']['time'][i]['temperature']['max'],
                                                    temperature_unit=data['forecast']['time'][i]['temperature']['unit'],
                                                    feels_like_value=data['forecast']['time'][i]['feels_like']['value'],
                                                    feels_like_unit=data['forecast']['time'][i]['feels_like']['unit'],
                                                    humidity_value=data['forecast']['time'][i]['humidity']['value'],
                                                    pressure_value=data['forecast']['time'][i]['pressure']['value'],
                                                    wind_speed_value=data['forecast']['time'][i]['windSpeed']['mps'],
                                                    wind_speed_name=data['forecast']['time'][i]['windSpeed']['name'],
                                                    wind_direction_value_deg=wind_direction_value_deg,
                                                    wind_direction_code=wind_direction_code,
                                                    wind_direction_name=wind_direction_name,
                                                    cloud_value_pct=data['forecast']['time'][i]['clouds']['all'],
                                                    cloud_name=data['forecast']['time'][i]['clouds']['value'],
                                                    visibility_value_m=data['forecast']['time'][i]['visibility']['value'],
                                                    precipitation_value_mm=0 if 'value' not in data['forecast']['time'][i]['precipitation'] else data['forecast']['time'][i]['precipitation']['value'],
                                                    precipitation_mode='no' if 'type' not in data['forecast']['time'][i]['precipitation'] else data['forecast']['time'][i]['precipitation']['type'],
                                                    weather_number=data['forecast']['time'][i]['symbol']['number'],
                                                    weather_value=data['forecast']['time'][i]['symbol']['name'],
                                                    weather_icon=data['forecast']['time'][i]['symbol']['var']
                                                    )
                db.session.add(weather)
            db.session.commit()
        else:
            error = 'Update Weather Hourly Error: Failed to connect to Open Weather API\nstatus code: ' + str(r.status_code)
    return error

#Routes


# updates the current weather to owm_current_weather for given city
@bp.route('/weather/<int:city_id>/current', methods=('GET', 'POST'))
def current_weather(city_id):
    #error = update_current_weather_all()
    city = db.session.query(OwmCities)\
        .filter_by(city_id=city_id)\
        .first()
    data = db.session.query(OwmCurrentWeather)\
        .order_by(OwmCurrentWeather.timestamp.asc())\
        .filter_by(city_id=city_id)\
        .all()

    if data is None:
        error = "Unable to retrieve current weather data for city: " + str(city_id)
    else:
        return render_template('weather/currentweather.html', city=city, data=data)
    flash(error)
    return redirect(url_for('cities.index'))


# updates the current forcast to owm_hourly_weather_forecast for given city
@bp.route('/weather/<int:city_id>/forecast', methods=('GET', 'POST'))
def current_forecast(city_id):
    city = db.session.query(OwmCities) \
        .filter_by(city_id=city_id) \
        .first()
    data = db.session.query(OwmHourlyWeatherForecast)\
        .order_by(OwmHourlyWeatherForecast.forecast_timestamp.asc())\
        .filter_by(city_id=city_id)\
        .all()
    if data is None:
        error = "Unable to retrieve current forecast data for city: " + str(city_id)
    else:
        return render_template('weather/currentforecast.html', city=city, data=data)
    flash(error)
    return redirect(url_for('cities.index'))


#todo find reliable way to convert sqlalchemy results to json

def row2dict(row):
    d = {}
    for column in row.__table__.columns:
        if isinstance(column, datetime.date):
            d[column.name] = column.isoformat()
        else:
            d[column.name] = str(getattr(row, column.name))
    return d


# returns all data in owm_current_weather for a given city as a json
@bp.route('/weather/<int:city_id>/current/dump', methods=('GET', 'POST'))
def current_weather_dump(city_id):

    #{city info, weather entries, weather data}
    weather = {"city": {}, "count": 0, "data": []}
    city = OwmCities.query.filter_by(city_id=city_id).first()
    weather["city"] = row2dict(city)

    data = OwmCurrentWeather.query\
        .filter_by(city_id=city_id) \
        .order_by(OwmCurrentWeather.timestamp.asc())

    weather["count"] = data.count()
    for d in data.all():
        entry = row2dict(d)
        entry.pop('id')
        entry.pop('city_id')
        weather['data'].append(entry)
    return json.dumps(weather)


# returns all data in owm_hourly_weather_forecast for a given city as a json
@bp.route('/weather/<int:city_id>/forecast/dump', methods=('GET', 'POST'))
def forecast_dump(city_id):
    # {city info, weather entries, weather data}
    weather = {"city": {}, "count": 0, "data": []}
    city = OwmCities.query.filter_by(city_id=city_id).first()
    weather["city"] = row2dict(city)

    data = OwmHourlyWeatherForecast.query \
        .filter_by(city_id=city_id) \
        .order_by(OwmHourlyWeatherForecast.forecast_timestamp.asc())

    weather["count"] = data.count()

    for d in data.all():
        entry = row2dict(d)
        entry.pop('id')
        entry.pop('city_id')
        weather['data'].append(entry)
    return json.dumps(weather)
