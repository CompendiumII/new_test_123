import connexion
from connexion import NoContent
import requests
import yaml
import logging
import logging.config
import uuid
import datetime
import json
from pykafka import KafkaClient
import time
import os

if "TARGET_ENV" in os.environ and os.environ["TARGET_ENV"] == "test":
    print("In Test Environment")
    app_conf_file = "/config/app_conf.yml"
    log_conf_file = "/config/log_conf.yml"
    
else:
    print("In Dev Environment")
    app_conf_file = "app_conf.yml"
    log_conf_file = "log_conf.yml"

with open(app_conf_file, 'r') as f:
    app_config = yaml.safe_load(f.read())

# External Logging Configuration
with open(log_conf_file, 'r') as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

logger = logging.getLogger('basicLogger')

logger.info("App Conf File: %s" % app_conf_file)
logger.info("Log Conf File: %s" % log_conf_file)

headers = {"Content-Type": 'application/json; charset=utf-8'}

def kafka_connection():
    current_retries = 0
    max_retries = app_config["kafka"]["max_retries"]

    while current_retries < max_retries:
        logger.info(f"Trying to connect to Kafka client... (ATTEMPT #{current_retries + 1})")
        kafka_server = app_config['events']['hostname']
        kafka_port = app_config['events']['port']
        try:
            client = KafkaClient(hosts=f"{kafka_server}:{kafka_port}")
            topic = client.topics[str.encode(app_config['events']['topic'])]
            producer = topic.get_sync_producer()
            logger.info(f"Successfully connected!")
            return producer
        except:
            logger.error(f"Connection failed...")
            logger.info(f"Retrying in {app_config['kafka']['sleep_time']} seconds...")
            time.sleep(app_config["kafka"]["sleep_time"])
            current_retries += 1
        
    logger.error(f"Failed to connect to Kafka client after {max_retries} tries...")
    return None

producer = kafka_connection()

def record_ability_usage(body):
    body["trace_id"] = str(uuid.uuid4())
    logger.info(f"Event received 'RECORD_ABILITY_USAGE' with trace id {body['trace_id']}")
    msg = { "type": "ability",
            "datetime" :
                datetime.datetime.now().strftime(
                    "%Y-%m-%dT%H:%M:%S"),
            "payload": body }
    msg_str = json.dumps(msg)
    producer.produce(msg_str.encode('utf-8'))
    logger.info(f"Returned event 'RECORD_ABILITY_USAGE' response(Id: {body['trace_id']})")
    return NoContent, 201

def record_item_usage(body):
    body["trace_id"] = str(uuid.uuid4())
    logger.info(f"Event received 'RECORD_ITEM_USAGE' with trace id {body['trace_id']}")
    msg = { "type": "item",
            "datetime" :
                datetime.datetime.now().strftime(
                    "%Y-%m-%dT%H:%M:%S"),
            "payload": body }
    msg_str = json.dumps(msg)
    producer.produce(msg_str.encode('utf-8'))
    logger.info(f"Returned event 'RECORD_ITEM_USAGE' response(Id: {body['trace_id']})")
    return NoContent, 201
 

app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("openapi.yml", base_path="/receiver", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    app.run(port=8080)
