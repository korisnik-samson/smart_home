import urllib.request
import urllib.response
import urllib.error

import time
from email.mime.multipart import MIMEMultipart

import serial
import requests
import smtplib
import imaplib
import datetime
import numpy as np

from http.client import responses
from threading import Thread
from matplotlib import pyplot as plt
from email.mime.image import MIMEImage
from email.mime.text import MIMEText

# ... (rest of your existing code)

# Process the data from the arduino
def process_data(data):
    processed_data = {}
    data_list = data.split()

    if len(data_list) >= 3:
        processed_data['temp_value'] = data_list[0]
        processed_data['illum_value'] = data_list[1]
        processed_data['motion_detected'] = data_list[2]  # Assuming motion data is sent

        send_to_things_speak(processed_data)

        # Check for temperature thresholds and send commands to Arduino
        if float(processed_data['temp_value']) > 23:
            serial_communication.write("cool_on".encode('ascii'))
        elif float(processed_data['temp_value']) < 17:
            serial_communication.write("heat_on".encode('ascii'))
        else:
            serial_communication.write("cool_off".encode('ascii'))
            serial_communication.write("heat_off".encode('ascii'))

        # Check for illumination and auto mode status
        if float(processed_data['illum_value']) < 30 and auto_mode_enabled:
            serial_communication.write("light_on".encode('ascii'))
        else:
            serial_communication.write("light_off".encode('ascii'))

        # Check for motion and secure mode status
        if int(processed_data['motion_detected']) == 1 and secure_mode_enabled:
            send_email_notification("Motion detected!")
            serial_communication.write("light_on".encode('ascii'))
            time.sleep(10)
            if int(processed_data['motion_detected']) == 0:
                serial_communication.write("light_off".encode('ascii'))

# ... (rest of your existing code)

# Send data to ThingSpeak
def send_to_things_speak(data):
    # Include motion data in the request
    response = urllib.request.urlopen('{}&field1={}&field2={}&field3={}&field4={}'.format(
        WRITE_URL, data['temp_value'], data['illum_value'], data['humid_value'], data['motion_detected']))

# ... (rest of your existing code)

# Send report to email
def send_report(email, serial_communication):
    # ... (your existing code to generate graphs)

    # Include motion detection counts and durations for secure and auto modes in the report
    # ...

    print('Email sent successfully')

# ... (rest of your existing code)

# Global variables for auto mode and secure mode
auto_mode_enabled = False
secure_mode_enabled = False

# ... (rest of your existing code)

# Check email for commands
def check_email(email, serial_communication):
    global auto_mode_enabled, secure_mode_enabled  # Access global variables

    email.select('inbox')

    while True:
        # ... (your existing code to check for email commands)

        # Turn on the auto control
        if len(response_auto_on[0]) > 0:
            auto_mode_enabled = True  # Enable auto mode
            # ... (rest of your existing code)

        # Turn off the auto control
        if len(response_auto_off[0]) > 0:
            auto_mode_enabled = False  # Disable auto mode
            # ... (rest of your existing code)

        # Turn on the secure control
        if len(response_secure_on[0]) > 0:
            secure_mode_enabled = True  # Enable secure mode
            # ... (rest of your existing code)

        # Turn off the secure control
        if len(response_secure_off[0]) > 0:
            secure_mode_enabled = False  # Disable secure mode
            # ... (rest of your existing code)

        # ... (rest of your existing code)

# ... (rest of your existing code)