import connexion
import logging.config
import yaml
import json
from pykafka import KafkaClient
from flask_cors import CORS, cross_origin
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


def get_item_stats(index):
    kafka_server = app_config['events']['hostname']
    kafka_port = app_config['events']['port']
    client = KafkaClient(hosts=f"{kafka_server}:{kafka_port}")
    topic = client.topics[str.encode(app_config['events']['topic'])]
    
    consumer = topic.get_simple_consumer(reset_offset_on_start=True,
                                         consumer_timeout_ms=1000)
    
    logger.info("Retrieving item statistic at index %d" % index)

    current_index = 0

    try:
        for msg in consumer:
            msg_str = msg.value.decode('utf-8')
            msg = json.loads(msg_str)

            if msg['type'] == 'item':
                if current_index == index:
                    return { "message": msg }, 200
                else:
                    current_index += 1
    except:
        logger.error("No more messages found")
    logger.error("Could not find item statistic at index %d" % index)
    return { "message": "Not found" }, 404

def get_ability_stats(index):
    kafka_server = app_config['events']['hostname']
    kafka_port = app_config['events']['port']
    client = KafkaClient(hosts=f"{kafka_server}:{kafka_port}")
    topic = client.topics[str.encode(app_config['events']['topic'])]
    
    consumer = topic.get_simple_consumer(reset_offset_on_start=True,
                                         consumer_timeout_ms=1000)
    
    logger.info("Retrieving ability statistic at index %d" % index)
    current_index = 0
    try:
        for msg in consumer:
            msg_str = msg.value.decode('utf-8')
            msg = json.loads(msg_str)
            if msg['type'] == 'ability':
                if current_index == index:
                    return {'message': msg}, 200
                else:
                    current_index += 1
    except:
        logger.error("No more messages found")
    logger.error("Could not find ability statistic at index %d" % index)
    return { "message": "Not found" }, 404

app = connexion.FlaskApp(__name__, specification_dir='')

if "TARGET_ENV" not in os.environ or os.environ["TARGET_ENV"] != "test":
    CORS(app.app)
    app.app.config['CORS_HEADERS'] = 'Content-Type'

app.add_api("openapi.yml", base_path="/audit_log", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    app.run(port=8110, use_reloader=False)
