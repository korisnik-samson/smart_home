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

from threading import Thread
from matplotlib import pyplot as plt
from email.mime.image import MIMEImage
from email.mime.text import MIMEText

# Serial communication parameters
PORT = 'COM10'
BAUD_RATE = 9600

# ThingSpeak channel parameters for data exchange
CHANNEL_ID = '2713239'
API_KEY_WRITE = '7IQSGV63A057Q2HT'
API_KEY_READ = 'Y2QP5FLGSO6L5DN8'

# URLs for reading and writing data to ThingSpeak
BASE_URL = 'https://api.thingspeak.com'
WRITE_URL = '{}/update?api_key={}'.format(BASE_URL, API_KEY_WRITE)

READ_CHANNEL_URL = '{}/channels/{}/feeds.json?api_key={}'.format(BASE_URL, CHANNEL_ID, API_KEY_READ)

READ_FIELD_ONE_URL = '{}/channels/{}/fields/{}.json?api_key={}&results={}'.format(BASE_URL, CHANNEL_ID, 1, API_KEY_READ, 10)
READ_FIELD_TWO_URL = '{}/channels/{}/fields/{}.json?api_key={}&results={}'.format(BASE_URL, CHANNEL_ID, 2, API_KEY_READ, 10)
READ_FIELD_THREE_URL = '{}/channels/{}/fields/{}.json?api_key={}&results={}'.format(BASE_URL, CHANNEL_ID, 3, API_KEY_READ, 10)

# get and parse to Json
temp = requests.get(READ_FIELD_TWO_URL)
illum = requests.get(READ_FIELD_ONE_URL)
humid = requests.get(READ_FIELD_THREE_URL)

tempDataJson = temp.json()
illuminationDataJson = illum.json()
humidityDataJson = humid.json()

# Extract temperature
temp_feeds = tempDataJson['feeds']
temperature = []

for temps in temp_feeds:
    temps = float(temps['field2'])
    temperature.append(temps)

# Extract illumination
illum_feeds = illuminationDataJson['feeds']
illumination = []

for illums in illum_feeds:
    illums = float(illums['field1'])
    illumination.append(illums)

# Extract humidity
humid_feeds = humidityDataJson['feeds']
humidity = []

for humids in humid_feeds:
    humids = float(humids['field3'])
    humidity.append(humids)


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

        send_to_things_speak(processed_data)


def send_email_notification(message_body):

    # Create the email message
    msg = MIMEText(message_body)
    msg['Subject'] = 'Smart Home Alert'
    msg['From'] = 'samofforjindu.lfis@gmail.com'  # Replace with your email
    msg['To'] = 'samofforjindu.lfis@gmail.com'  # Replace with recipient email

    # Connect to the email server
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login('samofforjindu.lfis@gmail.com', 'svvduscgcwobbjkp')  # Replace with your email and password

    # Send the email
    server.sendmail('samofforjindu.lfis@gmail.com', 'samofforjindu.lfis@gmail.com',
                    msg.as_string())  # Replace with sender and recipient emails
    server.quit()

# Send data to ThingSpeak
def send_to_things_speak(data):
    # Include motion data in the request
    response = urllib.request.urlopen('{}&field1={}&field2={}&field3={}&field4={}'.format(
        WRITE_URL, data['temp_value'], data['illum_value'], data['humid_value'], data['motion_detected']))


# Read data from the serial port
def read_port_data(serial_com):
    received_data = ''

    while True:
        if serial_com.in_waiting > 0:
            received_data = serial_com.read(size=serial_com.in_waiting).decode('ascii')
            process_data(received_data)


# Global variables for auto mode and secure mode
auto_mode_enabled = False
secure_mode_enabled = False

# Check email for commands
def check_email(email, serial_communication):
    email.select('inbox')

    while True:
        # Check for unread emails with the subject 'LIGHT ON', 'LIGHT OFF'
        ret_code, response_light_on = email.search(None, '(SUBJECT "LIGHT ON" UNSEEN)')
        ret_code, response_light_off = email.search(None, '(SUBJECT "LIGHT OFF" UNSEEN)')

        # Check for unread emails with the subject 'CLIMATE ON', 'CLIMATE OFF'
        ret_code, response_climate_on = email.search(None, '(SUBJECT "CLIMATE ON" UNSEEN)')
        ret_code, response_climate_off = email.search(None, '(SUBJECT "CLIMATE OFF" UNSEEN)')

        # Check for unread emails with the subject 'AUTO ON', 'AUTO OFF'
        ret_code, response_auto_on = email.search(None, '(SUBJECT "AUTO ON" UNSEEN)')
        ret_code, response_auto_off = email.search(None, '(SUBJECT "AUTO OFF" UNSEEN)')

        # Check for unread emails with the subject 'SECURE ON', 'SECURE OFF'
        ret_code, response_secure_on = email.search(None, '(SUBJECT "SECURE ON" UNSEEN)')
        ret_code, response_secure_off = email.search(None, '(SUBJECT "SECURE OFF" UNSEEN)')

        # Check for unread emails with the subject 'SEND REPORT'
        ret_code, response_report = email.search(None, '(SUBJECT "SEND REPORT" UNSEEN)')

        # Turn on the light
        if len(response_light_on[0]) > 0:
            text = 'light_on'

            serial_communication.write(text.encode('ascii'))
            email_ids = response_light_on[0].split()

            for id in email_ids:
                email.store(id, '+FLAGS', '\\Seen')

        # Turn off the light
        if len(response_light_off[0]) > 0:
            text = 'light_off'

            serial_communication.write(text.encode('ascii'))
            email_ids = response_light_off[0].split()

            for id in email_ids:
                email.store(id, '+FLAGS', '\\Seen')

        # Send report
        if len(response_report[0]) > 0:
            send_report(email, serial_communication)
            email_ids = response_report[0].split()

            for id in email_ids:
                email.store(id, '+FLAGS', '\\Seen')

        # Turn on the climate control
        if len(response_climate_on[0]) > 0:
            text = 'climate_on'

            serial_communication.write(text.encode('ascii'))
            email_ids = response_climate_on[0].split()

            for id in email_ids:
                email.store(id, '+FLAGS', '\\Seen')

        # Turn off the climate control
        if len(response_climate_off[0]) > 0:
            text = 'climate_off'

            serial_communication.write(text.encode('ascii'))
            email_ids = response_climate_off[0].split()

            for id in email_ids:
                email.store(id, '+FLAGS', '\\Seen')

        # Turn on the auto control
        if len(response_auto_on[0]) > 0:
            auto_mode_enabled = True  # Enable auto mode
            text = 'auto_on'

            serial_communication.write(text.encode('ascii'))
            email_ids = response_auto_on[0].split()

            for id in email_ids:
                email.store(id, '+FLAGS', '\\Seen')

        # Turn off the auto control
        if len(response_auto_off[0]) > 0:
            auto_mode_enabled = False  # Disable auto mode
            text = 'auto_off'

            serial_communication.write(text.encode('ascii'))
            email_ids = response_auto_off[0].split()

            for id in email_ids:
                email.store(id, '+FLAGS', '\\Seen')

        # Turn on the secure control
        if len(response_secure_on[0]) > 0:
            secure_mode_enabled = True  # Enable secure mode
            text = 'secure_on'

            serial_communication.write(text.encode('ascii'))
            email_ids = response_secure_on[0].split()

            for id in email_ids:
                email.store(id, '+FLAGS', '\\Seen')

        # Turn off the secure control
        if len(response_secure_off[0]) > 0:
            secure_mode_enabled = False  # Disable secure mode
            text = 'secure_off'

            serial_communication.write(text.encode('ascii'))
            email_ids = response_secure_off[0].split()

            for id in email_ids:
                email.store(id, '+FLAGS', '\\Seen')

        time.sleep(5)


# Send report to email
def send_report(email, serial_communication):
    message = MIMEMultipart()
    message['Subject'] = 'Arduino Smart Home Report'

    # plot the TEMPERATURE data

    # turn off interactive mode
    plt.ioff()

    x = np.linspace(0, 23, (1 * 10))
    fig = plt.figure()
    plt.title('Daily Temperature')
    plt.xlabel('Hours')
    plt.ylabel('Temperature (C)')

    plt.plot(x, temperature)

    # dir_string = 'C:\\Users\\Samson\\OneDrive - samxhavier\\Desktop\\Internet of Things\\Exercises\LastExercise\\reports\\'
    dir_string = 'C:/Users/Samson/OneDrive - samxhavier/Desktop/private_repos/smart_home/scripts/reports/'

    file_name = 'report-temperature-{}.png'.format(datetime.date.today())

    plt.savefig(dir_string + file_name)
    temp_graph = open(dir_string + file_name, 'rb')

    message_temp_graph = MIMEImage(temp_graph.read())
    temp_graph.close()

    message.attach(message_temp_graph)


    # plot the ILLUMINATION data
    plt.ioff()

    x = np.linspace(0, 23, (1 * 10))
    # fig = plt.figure()
    plt.title('Daily Illumination')
    plt.xlabel('Hours')
    plt.ylabel('Illumination (lux)')

    plt.plot(x, illumination)

    file_name = 'report-illumination-{}.png'.format(datetime.date.today())

    plt.savefig(dir_string + file_name)
    illum_graph = open(dir_string + file_name, 'rb')

    message_illum_graph = MIMEImage(illum_graph.read())
    illum_graph.close()

    message.attach(message_illum_graph)

    # plot the HUMIDITY data
    plt.ioff()

    x = np.linspace(0, 23, (1 * 10))
    # fig = plt.figure()
    plt.title('Daily Humidity')
    plt.xlabel('Hours')
    plt.ylabel('Humidity (%)')

    plt.plot(x, humidity)

    file_name = 'report-humidity-{}.png'.format(datetime.date.today())

    plt.savefig(dir_string + file_name)
    humid_graph = open(dir_string + file_name, 'rb')

    message_humid_graph = MIMEImage(humid_graph.read())
    humid_graph.close()

    message.attach(message_humid_graph)


    # adding text using html
    html_text = '''
        <html>
            <head>
                <style>
                    p {
                        font-size: 20px;
                    }
                </style>
            </head>
            <body>
                <p>Dear User,</p>
                <h1>Daily Report on ${}</h1>
                <p>
                    The minimum daily temperature was: <strong>{:.2f}C</strong> and the maximum was <strong>{:.2f}</strong>C and the 
                    average temperature was: <strong>{:.2f}C</strong>
                </p>
                <p>
                    The minimum daily illumination was: <strong>{:.2f}C</strong> and the maximum illumination was <strong>{:.2f}</strong>C and 
                    the average illumination was: <strong>{:.2f}C</strong>
                </p>
            </body>
        </html>
        '''.format(datetime.date.today(), np.min(temperature), np.max(temperature), np.mean(temperature), np.min(illumination),
                   np.max(illumination), np.np.mean(illumination))

    mime_text = MIMEText(html_text, 'html')
    message.attach(mime_text)

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()

    server.login('samofforjindu.lfis@gmail.com', 'svvduscgcwobbjkp')
    server.sendmail('samofforjindu.lfis@gmail.com', 'samofforjindu.lfis@gmail.com', message.as_string())

    server.quit()

    print('Email sent successfully')


# initialize the serial communication
serial_communication = serial.Serial(PORT, BAUD_RATE)

# email login
email = imaplib.IMAP4_SSL('imap.gmail.com')
email.login('samofforjindu.lfis@gmail.com', 'anvhsswnmpkhezkc')

# check email thread
check_email_thread = Thread(target=check_email, args=(email, serial_communication))
check_email_thread.start()

# Start a thread to receive data from the serial port
receiving_thread = Thread(target=read_port_data, args=(serial_communication,))
receiving_thread.start()
