import connexion
from connexion import NoContent
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import and_
from base import Base
from record_ability import RecordAbility
from record_item import RecordItem
import yaml
import logging.config
import datetime
import json
from pykafka import KafkaClient
from pykafka.common import OffsetType
from threading import Thread
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

DB_ENGINE = create_engine(f"mysql+pymysql://{app_config['datastore']['user']}:{app_config['datastore']['password']}@{app_config['datastore']['hostname']}:{app_config['datastore']['port']}/{app_config['datastore']['db']}")
Base.metadata.bind = DB_ENGINE
DB_SESSION = sessionmaker(bind=DB_ENGINE)

def get_health():
    return 200

def get_item_usage(start_timestamp, end_timestamp):
    session = DB_SESSION()
    start_timestamp_datetime = datetime.datetime.strptime(start_timestamp, "%Y-%m-%d %H:%M:%S.%f")
    end_timestamp_datetime = datetime.datetime.strptime(end_timestamp, "%Y-%m-%d %H:%M:%S.%f")

    readings = session.query(RecordItem).filter(
        and_(RecordItem.date_created >= start_timestamp_datetime,
             RecordItem.date_created < end_timestamp_datetime))
    
    results_list = []
    
    for reading in readings:
        results_list.append(reading.to_dict())

    session.close()

    logger.info("Query for item usages after %s returns %d results" %
                (start_timestamp, len(results_list)))

    return results_list, 200



def get_ability_usage(start_timestamp, end_timestamp):
    session = DB_SESSION()
    start_timestamp_datetime = datetime.datetime.strptime(start_timestamp, "%Y-%m-%d %H:%M:%S.%f")
    end_timestamp_datetime = datetime.datetime.strptime(end_timestamp, "%Y-%m-%d %H:%M:%S.%f")


    readings = session.query(RecordAbility).filter(
        and_(RecordAbility.date_created >= start_timestamp_datetime,
             RecordAbility.date_created < end_timestamp_datetime))

    results_list = []

    if readings is not None:
        for reading in readings:
            results_list.append(reading.to_dict())

    session.close()

    logger.info("Query for item usages after %s returns %d results" %
                (start_timestamp, len(results_list)))

    return results_list, 200

def kafka_connection():
    current_retries = 0
    max_retries = app_config["kafka"]["max_retries"]

    while current_retries < max_retries:
        logger.info(f"Trying to connect to Kafka client... (ATTEMPT NUMBER{current_retries + 1})")
        kafka_server = app_config['events']['hostname']
        kafka_port = app_config['events']['port']
        try:
            client = KafkaClient(hosts=f"{kafka_server}:{kafka_port}")
            topic = client.topics[str.encode(app_config['events']['topic'])]
            consumer = topic.get_simple_consumer(consumer_group=b'event_group', 
                                                reset_offset_on_start=False, 
                                                auto_offset_reset=OffsetType.LATEST)
            logger.info(f"Successfully connected!")
            return consumer
        except:
            logger.error(f"Connection failed...")
            logger.info(f"Retrying in {app_config['kafka']['sleep_time']} seconds...")
            time.sleep(app_config["kafka"]["sleep_time"])
            current_retries += 1
        
    logger.error(f"Failed to connect to Kafka client after {max_retries} tries...")
    return None

def process_messages():
    consumer = kafka_connection()
    for msg in consumer:
        msg_str = msg.value.decode('utf-8')
        msg = json.loads(msg_str)
        
        payload = msg["payload"]

        session = DB_SESSION()

        if msg["type"] == "ability":
            logger.info("Received request with ability data: %s, type: %s" % (msg["payload"], type(msg["payload"])))
            ability_usage = RecordAbility(
                            payload['steam_id'],
                            payload['match_id'],
                            payload['game_version'],
                            payload['region'],
                            payload['hero_id'],
                            payload['hero_name'],
                            payload['ability_id'],
                            payload['ability_name'],
                            payload['ability_level'],
                            payload['used_in_game'],
                            payload['trace_id'])
            session.add(ability_usage)
            session.commit()
            session.close()
        elif msg["type"] == "item":
            logger.info("Received request with item data: %s, type: %s" % (msg["payload"], type(msg["payload"])))
            session = DB_SESSION()
            item_usage = RecordItem(
                            payload['steam_id'],
                            payload['match_id'],
                            payload['game_version'],
                            payload['region'],
                            payload['item_id'],
                            payload['item_name'],
                            payload['item_type'],
                            payload['item_cost'],
                            payload['obtain_status'],
                            payload['used_in_game'],
                            payload['trace_id'])
            session.add(item_usage)
            session.commit()
            session.close()
        logger.info("Successful commit!")
        consumer.commit_offsets()

app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("openapi.yml", base_path="/storage", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    t1 = Thread(target=process_messages)
    t1.setDaemon(True)
    t1.start()
    logger.info("Connecting to DB. Hostname: %s, Port: %d" % (app_config['datastore']['hostname'], app_config['datastore']['port']))
    app.run(port=8090)
