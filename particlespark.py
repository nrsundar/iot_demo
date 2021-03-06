import json, StringIO, requests, time, ConfigParser, sys
from sseclient import SSEClient
from datetime import datetime
from kafka import KafkaClient, KafkaProducer


#Config Variables
kafka_broker = "ip-10-0-0-136.ec2.internal:9092"
kafka_topic = "particle"

#Instantiate Kafka Producer
producer = KafkaProducer(bootstrap_servers=kafka_broker,api_version=(0,9))

#get configuration stuff
Config = ConfigParser.ConfigParser()
Config.read('particle_spark.conf')
api_key = Config.get('Particle','ApiKey')
print_events = Config.get('Options','PrintEvents')
batch_size = int(Config.get('Options','BatchSize'))
batch_pause = int(Config.get('Options','BatchPause'))
flume_http_source = Config.get('Options','FlumeHttpSource')
particle_uri = Config.get('Particle','ParticleUri')
uri = particle_uri + '?access_token=' + api_key
count = 0

#not sure if these headers are necessary even, but leaving
headers = {"Accept-Content":"application/json; charset=UTF-8"}
messages = SSEClient(uri)
for msg in messages:
    event = '"'+msg.event+'"'
    data = msg.data
    payload = {}
    if(data):
        json_out = '{"event":' + event + "," + '"data":' + data + '}'
        
        #try loop because some data is wonky and causes exceptions.
        try:
            obj = json.loads(json_out)
            event = str(obj["event"])
            data  = str(obj["data"]["data"].replace(",",""))
            published_at = obj["data"]["published_at"]
            ttl = obj["data"]["ttl"]
            coreid = str(obj["data"]["coreid"])
            parsed_time = datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%S.%fZ")
            print(parsed_time)
            formatted_time = parsed_time.strftime("%Y-%m-%d %H:%M:%S.%f")
            payload["coreid"] = coreid
            payload["published_at"] = formatted_time
            payload["event"] = event
            payload["data"] = data
            payload["ttl"] = int(ttl)
        except:
            continue
     
        message = json.dumps(payload)

        #if event printing is enabled, send to console
        if(print_events == 'enabled'):
            print(message)
        #send to Kafka
        producer.send(kafka_topic,value=message)

        count += 1
        
        #once configured batch is met, wait for configured time
        if count >= batch_size:
            print('Wating for ' + str(batch_pause) + ' seconds')
            time.sleep(batch_pause)
            count = 0
