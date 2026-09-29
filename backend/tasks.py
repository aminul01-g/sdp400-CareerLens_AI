from extensions import scheduler, db
from models import Event
import os, json, datetime
def daily_summary():
    # example scheduled job: count events in last day
    from datetime import datetime, timedelta
    since = datetime.utcnow() - timedelta(days=1)
    count = Event.query.filter(Event.created_at >= since).count()
    print('[scheduler] events in last 24h =', count)

def start_scheduler(app=None):
    try:
        scheduler.remove_all_jobs()
        scheduler.add_job(func=daily_summary, trigger='interval', hours=24, id='daily_summary')
        scheduler.start()
    except Exception as e:
        print('scheduler start error', e)
