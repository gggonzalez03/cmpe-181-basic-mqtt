import paho.mqtt.client as mqtt
import jwt
import time
import ssl
import random
import os
import logging
import datetime
import argparse
import json
import psutil

from google.cloud import storage

# Following this guide: https://cloud.google.com/storage/docs/reference/libraries#cloud-console

# Instantiates a client
# Make sure to run export GOOGLE_APPLICATION_CREDENTIALS="./secret/google-secret.json" first
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./secret/google-secret.json"
storage_client = storage.Client()
# storage_client = storage.Client.from_service_account_json('./secret/google-secret.json')

# The name for the new bucket
bucket_name = "mac-data-bucket"
bucket = None

try:
  bucket = storage_client.get_bucket(bucket_name)
  print("Bucket {} retrieved.".format(bucket.name))
except Exception:
  # Creates the new bucket
  bucket = storage_client.create_bucket(bucket_name)
  print("Bucket {} created.".format(bucket.name))

if (bucket is None):
  quit()

# Code from colab: https://github.com/lkk688/IoTCloudConnect/blob/main/Notebook/CMPE-GoogleIoTdata.ipynb
# Just slightly modified
# The initial backoff time after a disconnection occurs, in seconds.
minimum_backoff_time = 1

# The maximum backoff time before giving up, in seconds.
MAXIMUM_BACKOFF_TIME = 32

# Whether to wait with exponential backoff before publishing.
should_backoff = False

def create_jwt(project_id, private_key_file, algorithm):
	"""Creates a JWT (https://jwt.io) to establish an MQTT connection.
	Args:
		project_id: The cloud project ID this device belongs to
		private_key_file: A path to a file containing either an RSA256 or
						ES256 private key.
		algorithm: The encryption algorithm to use. Either 'RS256' or 'ES256'
	Returns:
			A JWT generated from the given project_id and private key, which
			expires in 20 minutes. After 20 minutes, your client will be
			disconnected, and a new JWT will have to be generated.
	Raises:
			ValueError: If the private_key_file does not contain a known key.
	"""

	token = {
			# The time that the token was issued at
			'iat': datetime.datetime.utcnow(),
			# The time the token expires.
			'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=20),
			# The audience field should always be set to the GCP project id.
			'aud': project_id
	}

	# Read the private key file.
	with open(private_key_file, 'r') as f:
			private_key = f.read()

	print('Creating JWT using {} from private key file {}'.format(
			algorithm, private_key_file))

	return jwt.encode(token, private_key, algorithm=algorithm)
# [END iot_mqtt_jwt]

def error_str(rc):
	"""Convert a Paho error to a human readable string."""
	return '{}: {}'.format(rc, mqtt.error_string(rc))


def on_connect(unused_client, unused_userdata, unused_flags, rc):
	"""Callback for when a device connects."""
	print('on_connect', mqtt.connack_string(rc))

	# After a successful connect, reset backoff time and stop backing off.
	global should_backoff
	global minimum_backoff_time
	should_backoff = False
	minimum_backoff_time = 1


def on_disconnect(unused_client, unused_userdata, rc):
	"""Paho callback for when a device disconnects."""
	print('on_disconnect', error_str(rc))

	# Since a disconnect occurred, the next loop iteration will wait with
	# exponential backoff.
	global should_backoff
	should_backoff = True


def on_publish(unused_client, unused_userdata, unused_mid):
	"""Paho callback when a message is sent to the broker."""
	print('on_publish')


def on_message(unused_client, unused_userdata, message):
	"""Callback when the device receives a message on a subscription."""
	payload = str(message.payload.decode('utf-8'))
	print('Received message \'{}\' on topic \'{}\' with Qos {}'.format(
			payload, message.topic, str(message.qos)))

def get_client(project_id, cloud_region, registry_id, device_id, private_key_file, algorithm, ca_certs, mqtt_bridge_hostname, mqtt_bridge_port):

	client_id = 'projects/{}/locations/{}/registries/{}/devices/{}'.format(project_id, cloud_region, registry_id, device_id)
	print('Device client_id is \'{}\''.format(client_id))

	client = mqtt.Client(client_id=client_id)

	# With Google Cloud IoT Core, the username field is ignored, and the
	# password field is used to transmit a JWT to authorize the device.
	client.username_pw_set(
		username='unused',
		password=create_jwt(
				project_id, private_key_file, algorithm))

	# Enable SSL/TLS support.
	client.tls_set(ca_certs=ca_certs, tls_version=ssl.PROTOCOL_TLSv1_2)

	# Register message callbacks. https://eclipse.org/paho/clients/python/docs/
	# describes additional callbacks that Paho supports. In this example, the
	# callbacks just print to standard out.
	client.on_connect = on_connect
	client.on_publish = on_publish
	client.on_disconnect = on_disconnect
	client.on_message = on_message

	# Connect to the Google MQTT bridge.
	client.connect(mqtt_bridge_hostname, mqtt_bridge_port)

	# This is the topic that the device will receive configuration updates on.
	mqtt_config_topic = '/devices/{}/config'.format(device_id)

	# Subscribe to the config topic.
	client.subscribe(mqtt_config_topic, qos=1)

	# The topic that the device will receive commands on.
	mqtt_command_topic = '/devices/{}/commands/#'.format(device_id)

	# Subscribe to the commands topic, QoS 1 enables message acknowledgement.
	print('Subscribing to {}'.format(mqtt_command_topic))
	client.subscribe(mqtt_command_topic, qos=0)

	return client
# [END iot_mqtt_config]

class Args:
  algorithm = 'RS256'
  ca_certs = './not_so_secret/roots.pem'
  cloud_region = 'us-central1'
  data = 'Hello there'
  device_id = 'cmpe-181-device-1'
  jwt_expires_minutes = 20
  listen_dur = 60
  message_type = 'event'
  mqtt_bridge_hostname = 'mqtt.googleapis.com'
  mqtt_bridge_port = 8883
  num_messages = 20
  private_key_file = './secret/rsa_private.pem'
  project_id = 'spherical-treat-308100'
  registry_id = 'cmpe-181-basic-mqtt'
  service_account_json = './secret/google-secret.json'#os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
  imagefolder_path= './data'


args=Args()

print(args.private_key_file)

def parse_command_line_args():
	"""Parse command line arguments."""
	parser = argparse.ArgumentParser(description=(
		'Example Google Cloud IoT Core MQTT device connection code.'))
	parser.add_argument(
		'--algorithm',
		choices=('RS256', 'ES256'),
		required=True,
		help='Which encryption algorithm to use to generate the JWT.')
	parser.add_argument(
		'--ca_certs',
		default='./roots.pem',
		help='CA root from https://pki.google.com/roots.pem')
	parser.add_argument(
		'--cloud_region', default='us-central1', help='GCP cloud region')
	parser.add_argument(
		'--data',
		default='Hello there',
		help='The telemetry data sent on behalf of a device')
	parser.add_argument(
		'--device_id', required=True, help='Cloud IoT Core device id')
	parser.add_argument(
		'--gateway_id', required=False, help='Gateway identifier.')
	parser.add_argument(
		'--jwt_expires_minutes',
		default=20,
		type=int,
		help='Expiration time, in minutes, for JWT tokens.')
	parser.add_argument(
		'--listen_dur',
		default=60,
		type=int,
		help='Duration (seconds) to listen for configuration messages')
	parser.add_argument(
		'--message_type',
		choices=('event', 'state'),
		default='event',
		help=('Indicates whether the message to be published is a '
					'telemetry event or a device state message.'))
	parser.add_argument(
		'--mqtt_bridge_hostname',
		default='mqtt.googleapis.com',
		help='MQTT bridge hostname.')
	parser.add_argument(
		'--mqtt_bridge_port',
		choices=(8883, 443),
		default=8883,
		type=int,
		help='MQTT bridge port.')
	parser.add_argument(
		'--num_messages',
		type=int,
		default=100,
		help='Number of messages to publish.')
	parser.add_argument(
		'--private_key_file',
		required=True,
		help='Path to private key file.')
	parser.add_argument(
		'--project_id',
		default=os.environ.get('GOOGLE_CLOUD_PROJECT'),
		help='GCP cloud project name')
	parser.add_argument(
		'--registry_id', required=True, help='Cloud IoT Core registry id')
	parser.add_argument(
		'--service_account_json',
		default=os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"),
		help='Path to service account json file.')

	return parser.parse_args()


def mqtt_device_demo(args):
	"""Connects a device, sends data, and receives data."""
	# [START iot_mqtt_run]
	global minimum_backoff_time
	global MAXIMUM_BACKOFF_TIME

	# Publish to the events or state topic based on the flag.
	sub_topic = 'events' if args.message_type == 'event' else 'state'

	mqtt_topic = '/devices/{}/{}'.format(args.device_id, sub_topic)

	jwt_iat = datetime.datetime.utcnow()
	jwt_exp_mins = args.jwt_expires_minutes
	client = get_client(
		args.project_id, args.cloud_region, args.registry_id,
		args.device_id, args.private_key_file, args.algorithm,
		args.ca_certs, args.mqtt_bridge_hostname, args.mqtt_bridge_port)

	# Publish num_messages messages to the MQTT bridge once per second.
	for i in range(1, args.num_messages + 1):
		# Process network events.
		client.loop()

		# Wait if backoff is required.
		if should_backoff:
			# If backoff time is too large, give up.
			if minimum_backoff_time > MAXIMUM_BACKOFF_TIME:
				print('Exceeded maximum backoff time. Giving up.')
				break

			# Otherwise, wait and connect again.
			delay = minimum_backoff_time + random.randint(0, 1000) / 1000.0
			print('Waiting for {} before reconnecting.'.format(delay))
			time.sleep(delay)
			minimum_backoff_time *= 2
			client.connect(args.mqtt_bridge_hostname, args.mqtt_bridge_port)

		payload = '{}/{}-payload-{}'.format(
			args.registry_id, args.device_id, i)
		print('Publishing message {}/{}: \'{}\''.format(
			i, args.num_messages, payload))
		# [START iot_mqtt_jwt_refresh]
		seconds_since_issue = (datetime.datetime.utcnow() - jwt_iat).seconds
		if seconds_since_issue > 60 * jwt_exp_mins:
			print('Refreshing token after {}s'.format(seconds_since_issue))
			jwt_iat = datetime.datetime.utcnow()
			client.loop()
			client.disconnect()
			client = get_client(
				args.project_id, args.cloud_region,
				args.registry_id, args.device_id, args.private_key_file,
				args.algorithm, args.ca_certs, args.mqtt_bridge_hostname,
				args.mqtt_bridge_port)
		# [END iot_mqtt_jwt_refresh]
		# Publish "payload" to the MQTT topic. qos=1 means at least once
		# delivery. Cloud IoT Core also supports qos=0 for at most once
		# delivery.
		client.publish(mqtt_topic, payload, qos=1)

		
		# Send events every second. State should not be updated as often
		time.sleep(1)
		# for i in range(0, 60):
		#     time.sleep(1)
		#     client.loop()
	# [END iot_mqtt_run]


def read_sensor(count):

		# print(psutil.virtual_memory().percent)
		# print(psutil.cpu_percent(interval=0.1, percpu=True))
		# print(len(psutil.pids()))
		# print(psutil.cpu_count())
		# print(psutil.sensors_battery().percent)

		cpu_cores = psutil.cpu_percent(interval=0.1, percpu=True)
		cpu_cores_json = {}
		for index, core in enumerate(cpu_cores, start=0):
			cpu_cores_json['cpu' + str(index)] = core

		ram_usage = psutil.virtual_memory().percent
		cpu_usage = json.dumps(cpu_cores_json)
		number_of_cores = psutil.cpu_count()
		number_of_processes = len(psutil.pids())
		battery_percentage = psutil.sensors_battery().percent

		return (ram_usage, cpu_usage, number_of_cores, number_of_processes, battery_percentage)

def createJSON(reg_id, dev_id, timestamp, ram_usage, cpu_usage, number_of_cores, number_of_processes, battery_percentage):
    data = {
      'registry_id' : reg_id,
      'device_id' : dev_id,
      'time_collected' : timestamp,
      'ram_usage' : ram_usage,
      'cpu_usage' : cpu_usage,
      'number_of_cores' : number_of_cores,
      'number_of_processes' : number_of_processes,
      'battery_percentage' : battery_percentage
    }

    json_str = json.dumps(data)
    return json_str

def simulatesensor_mqtt_device_demo(args):

    """Connects a device, sends data, and receives data."""
    # [START iot_mqtt_run]
    global minimum_backoff_time
    global MAXIMUM_BACKOFF_TIME

    # Publish to the events or state topic based on the flag.
    sub_topic = 'events' if args.message_type == 'event' else 'state'

    mqtt_topic = '/devices/{}/{}'.format(args.device_id, sub_topic)

    jwt_iat = datetime.datetime.utcnow()
    jwt_exp_mins = args.jwt_expires_minutes
    client = get_client(
        args.project_id, args.cloud_region, args.registry_id,
        args.device_id, args.private_key_file, args.algorithm,
        args.ca_certs, args.mqtt_bridge_hostname, args.mqtt_bridge_port)

    # Publish num_messages messages to the MQTT bridge once per second.
    for i in range(1, args.num_messages + 1):
        client.loop()

        currentTime = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        (ram_usage, cpu_usage, number_of_cores, number_of_processes, battery_percentage) = read_sensor(i)

        payloadJSON = createJSON(args.registry_id, args.device_id, currentTime, ram_usage, cpu_usage, number_of_cores, number_of_processes, battery_percentage)

        #payload = '{}/{}-image-{}'.format(args.registry_id, args.device_id, i)
        print('Publishing message {}/: \'{}\''.format(
            i, payloadJSON))

        # Publish "payload" to the MQTT topic. qos=1 means at least once
        # delivery. Cloud IoT Core also supports qos=0 for at most once
        # delivery.
        client.publish(mqtt_topic, payloadJSON, qos=1)

        
        # Send events every second. State should not be updated as often
        time.sleep(1)

# mqtt_device_demo(args)
simulatesensor_mqtt_device_demo(args)