import requests
import logging
import logging.config
import yaml
import json
import datetime
import os
import connexion
from connexion import NoContent
from apscheduler.schedulers.background import BackgroundScheduler
from flask_cors import CORS, cross_origin

if "TARGET_ENV" in os.environ and os.environ["TARGET_ENV"] == "test":
    app_conf_file = "/config/app_conf.yml"
    log_conf_file = "/config/log_conf.yml"
else:
    app_conf_file = "app_conf.yml"
    log_conf_file = "log_conf.yml"

with open(app_conf_file, 'r') as f:
    app_config = yaml.safe_load(f.read())

with open(log_conf_file, 'r') as f:
    log_config = yaml.safe_load(f.read())

logging.config.dictConfig(log_config)
logger = logging.getLogger('basicLogger')

DATA_PATH = app_config['datastore']['filename']

if not os.path.exists(DATA_PATH):
    logger.info(f"JSON file not found at {DATA_PATH}. Creating and initializing with default values.")
    health_status = {
        "Receiver": "Down",
        "Storage": "Down",
        "Audit": "Down",
        "Processing": "Down",
        "last_updated": f'{datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")}'
    }
    with open(DATA_PATH, 'w') as f:
        json.dump(health_status, f)
    logger.info("JSON file created and initialized.")


def check_health(url):
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return "Running"
    except requests.RequestException as e:
        logger.error(f"Failed to obtain JSON data.")
    return "Down"

def update_health():

    logger.info("Retrieving health status of services...")  

    current_update = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    
    receiver_url = app_config['eventstore']['url'] + app_config['service']['receiver']
    storage_url = app_config['eventstore']['url'] + app_config['service']['storage']
    processing_url = app_config['eventstore']['url'] + app_config['service']['processing']
    audit_url = app_config['eventstore']['url'] + app_config['service']['audit']
    
    
    health_status = {
        'receiver': check_health(receiver_url),
        'storage': check_health(storage_url),
        'processing': check_health(processing_url),
        'audit': check_health(audit_url),
        'last_updated': current_update
    }
    logger.info(health_status)
    with open(DATA_PATH, 'w') as file:
        json.dump(health_status, file, indent=2)

    logger.info("Successful retrieval of service statuses.")      
    return health_status, 200  


def init_scheduler():
    sched = BackgroundScheduler(daemon=True)
    sched.add_job(update_health, 'interval', seconds=app_config['scheduler']['period_sec'])
    sched.start()

app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("openapi.yml", base_path="/health_check", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    if "TARGET_ENV" not in os.environ or os.environ["TARGET_ENV"] != "test":
        CORS(app.app)
        app.app.config['CORS_HEADERS'] = 'Content-Type'
    init_scheduler()
    app.run(port=8120, use_reloader=False)
