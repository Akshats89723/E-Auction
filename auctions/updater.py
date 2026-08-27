from apscheduler.schedulers.background import BackgroundScheduler

from .views import finalize_expired_auctions

def start():
    scheduler = BackgroundScheduler()
    # Run the function every 1 minute
    scheduler.add_job(finalize_expired_auctions, 'interval', minutes=1)
    scheduler.start()
