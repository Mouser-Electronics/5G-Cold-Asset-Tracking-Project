# Copyright (c) 2019, Digi International, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import time

import network
from machine import I2C
from machine import UART

from hdc1080 import HDC1080

from umqtt.simple import MQTTClient

# Constants
GNGGA_MARK = "$GNGGA"
GNGSA_MARK = "$GNGSA"

SERVER = "mqtt.mediumone.com"
TOPIC = "cold_storage_asset_tracking"
CLIENT_ID = "clientID"  # Should be unique for each device connected.


def sub_cb(topic, msg):
    """
    Callback executed when messages from subscriptions are received. Prints
    the topic and the message.
    :param topic: Topic of the message.
    :param msg: Received message.
    """
    print("- Message received!")
    print("   * %s: %s" % (topic.decode("utf-8"), msg.decode("utf-8")))


def extract_gps(serial_data):
    """
    Extracts the GPS data from the provided text.
    :param serial_data: Text to extract the GPS data from.
    :return: GPS data or and empty string if data could not be found.
    """

    if GNGGA_MARK in serial_data and GNGSA_MARK in serial_data:
        # Find repeating GPS sentence mark "$GNGGA", ignore it
        # and everything before it.
        _, after_gngga = serial_data.split(GNGGA_MARK, 1)
        # Now find mark "$GNGSA" in the result and ignore it
        # and everything after it.
        reading, _ = after_gngga.split(GNGSA_MARK, 1)

        return reading
    else:
        return ""


def extract_latitude(input_string):
    """
    Extracts the latitude from the provided text, value is all in degrees and
    negative if South of Equator.
    :param input_string: Text to extract the latitude from.
    :return: Latitude
    """

    if "N" in input_string:
        find_me = "N"
    elif "S" in input_string:
        find_me = "S"
    else:
        # 9999 is a non-sensical value for Lat or Lon, allowing the user to
        # know that the GPS unit was unable to take an accurate reading.
        return 9999

    index = input_string.index(find_me)
    deg_start = index - 11
    deg_end = index - 9
    deg = input_string[deg_start:deg_end]
    min_start = index - 9
    min_end = index - 1
    deg_decimal = input_string[min_start:min_end]
    latitude = (float(deg)) + ((float(deg_decimal)) / 60)

    if find_me == "S":
        latitude *= -1

    return latitude


def extract_longitude(input_string):
    """
    Extracts the longitude from the provided text, value is all in degrees and
    negative if West of London.
    :param input_string: Text to extract the longitude from.
    :return: Longitude
    """

    if "E" in input_string:
        find_me = "E"
    elif "W" in input_string:
        find_me = "W"
    else:
        # 9999 is a non-sensical value for Lat or Lon, allowing the user to
        # know that the GPS unit was unable to take an accurate reading.
        return 9999

    index = input_string.index(find_me)
    deg_start = index - 12
    deg_end = index - 9
    deg = input_string[deg_start:deg_end]
    min_start = index - 9
    min_end = index - 1
    deg_decimal = input_string[min_start:min_end]
    longitude = (float(deg)) + ((float(deg_decimal)) / 60)

    if find_me == "W":
        longitude *= -1

    return longitude


def read_gps_sample():
    """
    Attempts to read GPS and print the latest GPS values.
    """

    try:
        # Attempt to read GPS data up to 3 times.
        for i in range(3):
            print("- Reading GPS data... ",  end="")
            # Configure the UART to the GPS required parameters.
            u.init(9600, bits=8, parity=None, stop=1)
            time.sleep(1)
            # Ensures that there will only be a print if the UART
            # receives information from the GPS module.
            while not u.any():
                if u.any():
                    break
            # Read data from the GPS.
            gps_data = str(u.read(), 'utf8')
            # Close the UART.
            u.deinit()
            # Get latitude and longitude from the read GPS data.
            lat = extract_latitude(extract_gps(gps_data))
            lon = extract_longitude(extract_gps(gps_data))
            # Print location.
            if lon != 9999 and lat != 9999:
                print("[OK]")
                return lat, lon
            else:
                print("[ERROR]")
                print("   * Bad GPS signal. Retrying...")
                return 9999, 9999

    except Exception as E:
        print("[ERROR]")
        print("   * There was a problem getting GPS data: %s", str(E))


print(" +---------------------------------------+")
print(" | 5G Cold Asset Tracking and Monitoring |")
print(" +---------------------------------------+\n")

# Create a UART instance (this will talk to the GPS module).
u = UART(1, 9600)

# Create a HDC1080 Temp/Humidity Sensor instance
sensor = HDC1080(I2C(1))


# Connect to the cellular network
conn = network.Cellular()

print("- Waiting for the module to be connected to the cellular network... ",
      end="")
while not conn.isconnected():
    time.sleep(5)
print("[OK]")
print("This devices IP address is: ", conn.ifconfig()[0])

# Connect to the MQTT server
client = MQTTClient(CLIENT_ID, SERVER)
client.set_callback(sub_cb)
print("- Connecting to '%s'... " % SERVER, end="")
client.connect()
print("[OK]")
# Subscribe to topic.
print("- Subscribing to topic '%s'... " % TOPIC, end="")
client.subscribe(TOPIC)
print("[OK]")


# Start reading sensor and GPS samples every 30 seconds.
while True:
    latitude_dec, longitude_dec = read_gps_sample()
    temp_celsius = sensor.read_temperature(True)
    humidity_hr = sensor.read_humidity()

    # Print results:
    print("- Temperature: %s C" % round(temp_celsius, 2))
    print("- Humidity: %s %%" % round(humidity_hr, 2))
    print("- Latitude: %s" % latitude_dec)
    print("- Longitude: %s" % longitude_dec)
    print("")

    MESSAGE = """{"event_data":{"temperature":"""
    MESSAGE += temp_celsius
    MESSAGE += ""","humidity":"""
    MESSAGE += humidity_hr
    MESSAGE += ""","lat":"""
    MESSAGE += latitude_dec
    MESSAGE += ""","lon":"""
    MESSAGE += longitude_dec
    MESSAGE += """}}"""

    print("- Publishing message... ", end="")
    client.publish(TOPIC, MESSAGE)
    print("[OK]")

    time.sleep(30)
