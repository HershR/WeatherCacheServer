from .weather import city_ids, update_current_weather, update_forcast_3h
from .extensions import scheduler

def add_existing_weather_tasks():
    for id in city_ids():
        scheduler.add_job(
            func=update_current_weather,
            trigger="cron",
            minute=0,
            args=[id],
            id="update current weather: {}".format(id),
            name="update current weather: {}".format(id),
            replace_existing=True
        )
        scheduler.add_job(
            func=update_forcast_3h,
            trigger="cron",
            hour=0,
            args=[id],
            id="update current forecast: {}".format(id),
            name="update current forecast: {}".format(id),
            replace_existing=True
        )
        print('Update weather task added(existing): ' + str(id))


def add_weather_task(city_id):
    with scheduler.app.app_context():
        scheduler.add_job(
            func=update_current_weather,
            trigger="cron",
            minute=0,
            args=[city_id],
            id="update current weather: {}".format(city_id),
            name="update current weather: {}".format(city_id),
            replace_existing=True
        )
        scheduler.add_job(
            func=update_forcast_3h,
            trigger="cron",
            hour=0,
            args=[city_id],
            id="update current forecast: {}".format(city_id),
            name="update current forecast: {}".format(city_id),
            replace_existing=True
        )
        print('Update weather task added(new): ' + str(city_id))

