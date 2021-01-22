"""MQTT Client for Python"""

__version__ = '0.0.2'

import asyncio
import inspect
import json
import os
import time
import random
import re
import urllib

import paho.mqtt.client as mqtt
from wheezy.routing import PathRouter

from .mqtt_messages import MqttMessages

_underscorer1 = re.compile(r'(.)([A-Z][a-z]+)')
_underscorer2 = re.compile('([a-z0-9])([A-Z])')
def camelToSnake(s):
    # https://gist.github.com/jaytaylor/3660565
    subbed = _underscorer1.sub(r'\1_\2', s)
    return _underscorer2.sub(r'\1_\2', subbed).lower()

class MqttClient(MqttMessages):
    """
       Example MqttClient for Application Frameworks (such as Microdrop)
       Used with the following broker:
       https://github.com/sci-bots/microdrop-3.0/blob/master/MoscaServer.js
    """

    def __init__(self, host="localhost", port=1883, base="microdrop"):
        super().__init__()
        self.router = PathRouter()
        self.host = host
        self.port = port
        self.base = base
        self.subscriptions = []
        self.client_id = self.ClientID()
        self.client = self.Client()
        self.connected = False

    @property
    def filepath(self):
        try:
            return os.path.dirname(inspect.getfile(self.__class__))
        except:
            return 'unknown'

    @property
    def name(self):
        safe_chars = '~@#$&()*!+=:;,.?/\''
        return urllib.parse.quote(camelToSnake(self.__class__.__name__), safe=safe_chars)

    @property
    def version(self):
        return '0.0'

    def send_message(self, topic, msg={}, retain=False, qos=0, dup=False):
        message = json.dumps(msg)
        self.client.publish(topic, message, retain=retain, qos=qos)

    def on_connect(self, client, userdata, flags, rc):
        self.connected = True
        self.listen()
        self.trigger('start', 'null')

    def on_disconnect(self, client, userdata, rc):
        self.connected = False

    def listen(self):
        print(f'No listen method implemented for {self.name}')

    def on_message(self, client, userdata, msg):
        method, args = self.router.match(msg.topic)

        try:
            payload = json.loads(msg.payload)
        except ValueError:
            print("Message contains invalid json")
            print(f'topic: {msg.topic}')
            payload = None

        if method:
            method(payload, args)

    def wrap_data(self, key, val):
        msg = {}
        if isinstance(val, dict) and val != None:
            msg = val
        else:
            msg[key] = val
        msg['__head__'] = self.DefaultHeader()
        return msg

    def Client(self, keepalive=60):
        client = mqtt.Client(self.client_id)
        client.on_connect = self.on_connect
        client.on_message = self.on_message
        client.on_disconnect = self.on_disconnect
        client.connect(host=self.host, port=self.port)
        client.loop_start()
        return client

    def ClientID(self):
        timestamp = str(time.time()).replace(".","")
        randnum = random.randint(1,1000)
        return f'{self.name}>>{self.filepath}>>{timestamp}.{randnum}'

    def DefaultHeader(self):
        header = {}
        header['plugin_name'] = self.name
        header['plugin_version'] = self.version
        return header
