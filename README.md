First step is to create a project and enable Cloud IoT Core and Cloud Pub/Sub APIs through the following link: 
https://console.cloud.google.com/flows/enableapi?apiid=cloudiot.googleapis.com,pubsub&_ga=2.42615333.-1267971805.1554925613

In the Google Cloud Platform, open menu bar on the top left and look for "IoT Core" and "Pub/Sub". Pin them if you prefer.

1. In IoT Core, create a registry.
2. Create a device
2.1. Create key pair: openssl req -x509 -newkey rsa:2048 -keyout rsa_private.pem -nodes -out rsa_cert.pem -subj "/CN=unused" -days 365
3. Upload Public Key (rsa_cert.pem)
4. Set up authentication
https://cloud.google.com/storage/docs/reference/libraries#cloud-console


With python3

(source pyenv/bin/activate)
(pip install -r requirements.txt)

1. python3 -m pip install --user virtualenv
2. python3 -m venv pyenv
3. source pyenv/bin/activate

4. pip install google-cloud-iot
5. pip install google-api-python-client
6. pip install google-cloud-storage
7. pip install cryptography pyjwt paho-mqtt