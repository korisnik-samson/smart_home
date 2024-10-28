import urllib.response
import urllib.request

import serial
import time
import requests
import smtplib
import imaplib
import datetime
import numpy as np
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Serial communication parameters
PORT = 'COM10'
BAUD_RATE = 9600

# ThingSpeak channel parameters
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
READ_FIELD_FOUR_URL = '{}/channels/{}/fields/{}.json?api_key={}&results={}'.format(BASE_URL, CHANNEL_ID, 4, API_KEY_READ, 10)

# Email credentials
EMAIL_ADDRESS = "samofforjindu.lfis@gmail.com"
EMAIL_PASSWORD = "svvduscgcwobbjkp"

# Global variables
temperature = []
illumination = []
humidity = []

motion_detected = 0
secure_mode_duration = 0
auto_mode_duration = 0

start_time = time.time()
last_motion_time = 0
auto_mode_enabled = False
secure_mode_enabled = False
climate_control_enabled = False


# Logger function
def log_console(message):
    # print message with timestamp
    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] -- {message}\n")


# Initialize serial communication
serial_communication = serial.Serial(PORT, BAUD_RATE)

# Wait for the serial connection to establish
time.sleep(2)

# Initialize email connection
email = imaplib.IMAP4_SSL('imap.gmail.com')
email.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

# get and parse to Json
temp = requests.get(READ_FIELD_ONE_URL)
illum = requests.get(READ_FIELD_TWO_URL)
humid = requests.get(READ_FIELD_THREE_URL)

tempDataJson = temp.json()
illuminationDataJson = illum.json()
humidityDataJson = humid.json()

# Extract temperature
temp_feeds = tempDataJson['feeds']

for temps in temp_feeds:
    temps = float(temps['field1'])
    temperature.append(temps)

# Extract illumination
illum_feeds = illuminationDataJson['feeds']

for illums in illum_feeds:
    illums = float(illums['field2'])
    illumination.append(illums)

# Extract humidity
humid_feeds = humidityDataJson['feeds']

for humids in humid_feeds:
    humids = float(humids['field3'])
    humidity.append(humids)


# Process the data from the Arduino
def process_data(data):
    global motion_detected, last_motion_time

    processed_data = {}
    data_list = data.split()

    if len(data_list) >= 4:  # Verify enough data points are received
        try:
            processed_data['temp_value'] = float(data_list[0])
            processed_data['illum_value'] = float(data_list[1])
            processed_data['humid_value'] = float(data_list[2])
            processed_data['motion_detected'] = int(data_list[3])

            temperature.append(processed_data['temp_value'])
            illumination.append(processed_data['illum_value'])
            humidity.append(processed_data['humid_value'])

            if processed_data['motion_detected']:
                motion_detected += 1

                if secure_mode_enabled and time.time() - last_motion_time > 10:
                    send_email_notification("Motion detected!")
                    last_motion_time = time.time()

            send_to_things_speak(processed_data)

        except ValueError:
            print("Invalid data received from Arduino:", data)


# Send data to ThingSpeak
def send_to_things_speak(data):
    try:
        # Prepare the data to be sent to ThingSpeak
        payload = {
            'field1': data['temp_value'],
            'field2': data['illum_value'],
            'field3': data['humid_value'],
            'field4': data['motion_detected']
        }

        # Send the data to ThingSpeak
        response = requests.get(WRITE_URL, params=payload)
        print(response.url)

        #response_ = urllib.request.urlopen('{}&field1={}&field2={}&field3={}&field4={}'.format(
        #WRITE_URL, data['temp_value'], data['illum_value'], data['humid_value'], data['motion_detected']))

        if response.status_code == 200:
            log_console(f"Data sent to ThingSpeak")
        else:
            log_console(f"Failed to send data to ThingSpeak. Status code: {response.status_code}")

    except Exception as e:
        log_console(f"Error sending data to ThingSpeak: {e}")


# Send email notification
def send_email_notification(message_body):
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            message = MIMEMultipart()

            message['From'] = EMAIL_ADDRESS
            message['To'] = EMAIL_ADDRESS  # Send the notification to myself
            message['Subject'] = 'Smart Home Notification'

            message.attach(MIMEText(message_body, 'plain'))
            server.sendmail(EMAIL_ADDRESS, EMAIL_ADDRESS, message.as_string())

            print("Email notification sent.")

    except Exception as e:
        print("Error sending email notification:", e)


# Read data from the serial port
def read_serial(serial_com):
    received_data = ''

    if serial_com.in_waiting > 0:
        try:
            received_data = serial_com.read(size=serial_com.in_waiting).decode('ascii', errors='ignore')
            process_data(received_data)

        except Exception as e:
            log_console(f"Error reading data from serial: {e}")


# Check email for commands
def check_email(email, serial_communication):
    global auto_mode_enabled, secure_mode_enabled, secure_mode_duration, auto_mode_duration, climate_control_enabled
    email.select('inbox')

    while True:
        # Search for emails with specific subjects
        _, response_light_on = email.search(None, '(SUBJECT "LIGHT ON" UNSEEN)')
        _, response_light_off = email.search(None, '(SUBJECT "LIGHT OFF UNSEEN")')

        _, response_climate_on = email.search(None, '(SUBJECT "CLIMATE ON" UNSEEN)')
        _, response_climate_off = email.search(None, '(SUBJECT "CLIMATE OFF" UNSEEN)')

        _, response_auto_on = email.search(None, '(SUBJECT "AUTO ON" UNSEEN)')
        _, response_auto_off = email.search(None, '(SUBJECT "AUTO OFF" UNSEEN)')

        _, response_secure_on = email.search(None, '(SUBJECT "SECURE ON" UNSEEN)')
        _, response_secure_off = email.search(None, '(SUBJECT "SECURE OFF" UNSEEN)')

        _, response_cooling_on = email.search(None, '(SUBJECT "COOLING ON" UNSEEN)')
        _, response_cooling_off = email.search(None, '(SUBJECT "COOLING OFF" UNSEEN)')

        _, response_heating_on = email.search(None, '(SUBJECT "HEATING ON" UNSEEN)')
        _, response_heating_off = email.search(None, '(SUBJECT "HEATING OFF" UNSEEN)')

        _, response_report = email.search(None, '(SUBJECT "SEND REPORT" UNSEEN)')

        # Turn on the light
        if len(response_light_on[0]) > 0:
            serial_communication.write("light_on".encode('ascii'))
            auto_mode_enabled = False  # Disable auto mode when manual control is used
            log_console("Light on")

            for msg_id in response_light_on[0].split():
                email.store(msg_id, '+FLAGS', '\\Seen')

        # Turn off the light
        if len(response_light_off[0]) > 0:
            serial_communication.write("light_off".encode('ascii'))
            auto_mode_enabled = False  # Disable auto mode when manual control is used
            log_console("Light off")

            for msg_id in response_light_off[0].split():
                email.store(msg_id, '+FLAGS', '\\Seen')

        # Turn on the climate control
        if len(response_climate_on[0]) > 0:
            serial_communication.write("climate_on".encode('ascii'))
            log_console("Climate control on")

            for msg_id in response_climate_on[0].split():
                email.store(msg_id, '+FLAGS', '\\Seen')

        # Turn off the climate control
        if len(response_climate_off[0]) > 0:
            serial_communication.write("climate_off".encode('ascii'))
            log_console("Climate control off")

            for msg_id in response_climate_off[0].split():
                email.store(msg_id, '+FLAGS', '\\Seen')

        # Turn on the auto control
        if len(response_auto_on[0]) > 0:
            auto_mode_enabled = True  # Enable auto mode
            auto_mode_duration += time.time() - start_time  # Accumulate auto mode duration
            serial_communication.write("auto_on".encode('ascii'))

            log_console("Auto mode on")

            for msg_id in response_auto_on[0].split():
                email.store(msg_id, '+FLAGS', '\\Seen')

        # Turn off the auto control
        if len(response_auto_off[0]) > 0:
            auto_mode_enabled = False  # Disable auto mode
            serial_communication.write("auto_off".encode('ascii'))

            log_console("Auto mode off")

            for msg_id in response_auto_off[0].split():
                email.store(msg_id, '+FLAGS', '\\Seen')

        # Turn on the secure control
        if len(response_secure_on[0]) > 0:
            secure_mode_enabled = True  # Enable secure mode
            secure_mode_duration += time.time() - start_time  # Accumulate secure mode duration
            serial_communication.write("secure_on".encode('ascii'))

            log_console("Secure mode on")

            for msg_id in response_secure_on[0].split():
                email.store(msg_id, '+FLAGS', '\\Seen')

        # Turn off the secure control
        if len(response_secure_off[0]) > 0:
            secure_mode_enabled = False  # Disable secure mode
            serial_communication.write("secure_off".encode('ascii'))

            log_console("Secure mode off")

            for msg_id in response_secure_off[0].split():
                email.store(msg_id, '+FLAGS', '\\Seen')

        # Turn on the cooling control
        if len(response_cooling_on[0]) > 0:

            serial_communication.write("cooling_on".encode('ascii'))
            log_console("Cooling on")

            for msg_id in response_cooling_on[0].split():
                email.store(msg_id, '+FLAGS', '\\Seen')

        # Turn off the cooling control
        if len(response_cooling_off[0]) > 0:

            serial_communication.write("cooling_off".encode('ascii'))
            log_console("Cooling off")

            for msg_id in response_cooling_off[0].split():
                email.store(msg_id, '+FLAGS', '\\Seen')

        # Turn on the heating control
        if len(response_heating_on[0]) > 0:

            serial_communication.write("heating_on".encode('ascii'))
            log_console("Heating on")

            for msg_id in response_heating_on[0].split():
                email.store(msg_id, '+FLAGS', '\\Seen')

        # Turn off the heating control
        if len(response_heating_off[0]) > 0:

            serial_communication.write("heating_off".encode('ascii'))
            log_console("Heating off")

            for msg_id in response_heating_off[0].split():
                email.store(msg_id, '+FLAGS', '\\Seen')


        # Send report
        if len(response_report[0]) > 0:

            # could adjust the condition to check if the data is available or time duration is greater than 24 hours
            if len(temperature) > 0 and len(illumination) > 0 and len(humidity) > 0:
                send_report(email, serial_communication)

            for msg_id in response_report[0].split():
                email.store(msg_id, '+FLAGS', '\\Seen')

        time.sleep(10)


# Send report
def send_report(email, serial_communication):
    global motion_detected, secure_mode_duration, auto_mode_duration, temperature, illumination, humidity
    message = MIMEMultipart()
    message['Subject'] = 'Arduino Smart Home Report'

    # Generate report content
    report_content = f"""
    <html>
        <head>
            <style>
            </style>
        </head>
        
        <body>
            <h1>Daily Smart Home Report</h1>
            <p>Generated at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
            <h3>Temperature Statistics</h3>
            <p>Minimum: {np.min(temperature):.2f}°C</p>
            <p>Maximum: {np.max(temperature):.2f}°C</p>
            <p>Average: {np.mean(temperature):.2f}°C</p>
        
            <h3>Illumination Statistics</h3>
            <p>Minimum: {np.min(illumination):.2f} %</p>
            <p>Maximum: {np.max(illumination):.2f} %</p>
            <p>Average: {np.mean(illumination):.2f} %</p>
        
            <h3>Humidity Statistics</h3>
            <p>Minimum: {np.min(humidity):.2f} %</p>
            <p>Maximum: {np.max(humidity):.2f} %</p>
            <p>Average: {np.mean(humidity):.2f} %</p>
        
            <h3>Motion</h3>
            <p>Total Detections: {motion_detected}</p>
        
            <h3>Mode Durations</h3>
            <p>Secure Mode: {secure_mode_duration:.2f} seconds</p>
            <p>Auto Mode: {auto_mode_duration:.2f} seconds</p>
        </body>
    </html>
    """

    # Plot the TEMPERATURE data
    plt.ioff()

    x = np.linspace(0, 23, len(temperature))
    fig, ax = plt.subplots()

    ax.plot(x, temperature)
    ax.set_title('Daily Temperature')
    ax.set_xlabel('Hours')
    ax.set_ylabel('Temperature (°C)')

    # Format the x-axis to show hours
    hours = mdates.HourLocator(interval=1)  # Every hour
    ax.xaxis.set_major_locator(hours)
    formatter = mdates.DateFormatter('%H:%M')

    ax.xaxis.set_major_formatter(formatter)
    fig.autofmt_xdate()  # Rotates and aligns the dates
    fig.savefig('temperature.png')
    plt.close(fig)

    dir_string = 'C:/Users/Samson/OneDrive - samxhavier/Desktop/private_repos/smart_home/scripts/reports/'

    with open('temperature.png', 'rb') as f:
        img_data = f.read()

    image = MIMEImage(img_data, name='temperature.png')
    message.attach(image)

    # Plot the ILLUMINATION data
    plt.ioff()

    x = np.linspace(0, 23, len(illumination))
    fig, ax = plt.subplots()

    ax.plot(x, illumination)
    ax.set_title('Daily Illumination')
    ax.set_xlabel('Hours')
    ax.set_ylabel('Illumination (%)')

    # Format the x-axis to show hours
    hours = mdates.HourLocator(interval=1)  # Every hour
    ax.xaxis.set_major_locator(hours)
    formatter = mdates.DateFormatter('%H:%M')
    ax.xaxis.set_major_formatter(formatter)

    fig.autofmt_xdate()  # Rotates and aligns the dates
    fig.savefig('illumination.png')
    plt.close(fig)

    with open('illumination.png', 'rb') as f:
        img_data = f.read()

    image = MIMEImage(img_data, name='illumination.png')
    message.attach(image)

    # Plot the HUMIDITY data
    plt.ioff()

    x = np.linspace(0, 23, len(humidity))
    fig, ax = plt.subplots()

    ax.plot(x, humidity)
    ax.set_title('Daily Humidity')
    ax.set_xlabel('Hours')
    ax.set_ylabel('Humidity (%)')

    # Format the x-axis to show hours
    hours = mdates.HourLocator(interval=1)  # Every hour
    ax.xaxis.set_major_locator(hours)
    formatter = mdates.DateFormatter('%H:%M')
    ax.xaxis.set_major_formatter(formatter)

    fig.autofmt_xdate()  # Rotates and aligns the dates
    fig.savefig('humidity.png')
    plt.close(fig)

    with open('humidity.png', 'rb') as f:
        img_data = f.read()

    image = MIMEImage(img_data, name='humidity.png')
    message.attach(image)

    # Attach the report content to the email
    message.attach(MIMEText(report_content, 'html')) # serves as mime text

    # Send the email
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, EMAIL_ADDRESS, message.as_string())

        print("Daily report sent.")


# Start the threads
email_thread = threading.Thread(target=check_email, args=(email, serial_communication))
email_thread.start()

serial_thread = threading.Thread(target=read_serial, args=(serial_communication,))
serial_thread.start()

while True:
    time.sleep(1) # Keep the main thread alive