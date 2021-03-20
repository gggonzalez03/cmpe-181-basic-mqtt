import paho.mqtt.client as mqtt
import jwt
import time
import ssl
import random
import os
import logging
import datetime
import argparse

from google.cloud import storage

# Following this guide: https://cloud.google.com/storage/docs/reference/libraries#cloud-console

# Instantiates a client
storage_client = storage.Client()

# The name for the new bucket
bucket_name = "mac-data-bucket"
bucket = {}

try:
  bucket = storage_client.get_bucket(bucket_name)
  print("Bucket {} retrieved.".format(bucket.name))
except Exception:
  # Creates the new bucket
  bucket = storage_client.create_bucket(bucket_name)
  print("Bucket {} created.".format(bucket.name))
