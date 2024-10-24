import urllib.request
import urllib.response
import urllib.error

import time
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

# Serial communication parameters
PORT = 'COM10'
BAUD_RATE = 9600

# ThingSpeak channel parameters for data exchange
CHANNEL_ID = '2713239'
API_KEY_WRITE = 'QUZCI4Y20LCRANH5'
API_KEY_READ = 'P6NLPNBSZYM9JARU'