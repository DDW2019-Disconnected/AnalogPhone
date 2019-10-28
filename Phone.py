import threading
import time
from multiprocessing import Process, Value
import sqlite3

import RPi.GPIO as GPIO

from osc4py3 import oscbuildparse
from osc4py3.as_eventloop import *
from pythonosc import dispatcher
from pythonosc import osc_server

RESOLUME_CLIENT_NAME = "Arena"
REAPER_CLIENT_NAME = "Framboos"

lock = threading.Lock()
# STORY SETUP
storyActive = Value('b', False)
storyStart = Value('b', False)
currentlyPlaying = Value('i', -1)

# Logging
LOGGING_DB_NAME = "logging"
LOGGING_SQL_FILE_NAME = "logging.sql"
loggingEnabled = False

# RPI SETUP
RED_PI_PIN = 21
BLUE_PI_PIN = 20

# IP of the Resolume & Reaper Server
OSC_REMOTE_SERVER_IP = "192.168.137.1"

RESOLUME_PORT = 2333
OSC_SERVER_PORT = 7001
REAPER_PORT = 4242

# IP of the

# Local IP used to host a server for Resolume to connect to, address used for Resolume
OSC_LOCAL_SERVER_IP = "192.168.137.42"
ADDRESS = "/composition/layers/2/position"


def getNumber():
    currState = 0
    oldState = 0
    pulses = 0

    while GPIO.input(BLUE_PI_PIN) == 0:
        currState = GPIO.input(RED_PI_PIN)
        if oldState != currState and currState == 0:
            oldState = 0
            time.sleep(.08)
            pulses += 1

        if oldState != currState and currState == 1:
            oldState = 1

    return pulses


def choice(choice):
    global storyActive
    if choice == 1:
        storyActive.value = True
        return oscbuildparse.OSCMessage("/composition/columns/1/connect", None, [1])
    elif choice == 2:
        storyActive.value = True
        return oscbuildparse.OSCMessage("/composition/columns/2/connect", None, [1])
    elif choice == 3:
        storyActive.value = True
        return oscbuildparse.OSCMessage("/composition/columns/3/connect", None, [1])
    elif choice == 4:
        storyActive.value = True
        return oscbuildparse.OSCMessage("/composition/columns/4/connect", None, [1])
    elif choice > 4:
        return oscbuildparse.OSCMessage("/composition/columns/11/connect", None, [1])


def sendResolumeMessage(message):
    finished = False
    while not finished:
        osc_send(message, RESOLUME_CLIENT_NAME)
        osc_process()
        finished = True


def storyStarted():
    global storyStart
    storyStart.value = False
    print("Set storystart to false")


def logStoryDialed(currentNumber):
    if not loggingEnabled:
        return

    try:
        # Read Table Schema into a Variable and remove all New Line Chars
        conn = sqlite3.connect(LOGGING_DB_NAME)
        curs = conn.cursor()

        # Create Tables
        query = "INSERT INTO dials (digit) VALUES(" + str(currentNumber) + ")"
        sqlite3.complete_statement(query)
        curs.executescript(query)

        # Close DB
        curs.close()
        conn.close()
    except Exception as e:
        print(e)
        print("Error attempting DB connection")


def logStoryStarted(currentNumber):
    if not loggingEnabled:
        return

    try:
        # Read Table Schema into a Variable and remove all New Line Chars
        conn = sqlite3.connect(LOGGING_DB_NAME)
        curs = conn.cursor()

        # Create Tables
        query = "INSERT INTO plays (digit) VALUES(" + str(currentNumber) + ")"
        sqlite3.complete_statement(query)
        curs.executescript(query)

        # Close DB
        curs.close()
        conn.close()
    except Exception as e:
        print(e)
        print("Error attempting DB connection")


def openClient(currentNumber):
    global storyStart, currentlyPlaying

    if storyStart.value:
        print("Not playing since story started..")
        logStoryDialed(currentNumber)
        return

    lock.acquire()
    try:
        if currentNumber <= 4:
            storyStart.value = True
            print("Set story start to True")
            timer = threading.Timer(3.0, storyStarted)
            timer.start()

        startResolumeVideo(currentNumber)
        startReaperAudio(currentNumber)
        currentlyPlaying.value = currentNumber
        logStoryStarted(currentNumber)
    finally:
        lock.release()
        logStoryDialed(currentNumber)


def startResolumeVideo(currentNumber):
    osc_startup()
    osc_udp_client(OSC_REMOTE_SERVER_IP, RESOLUME_PORT, RESOLUME_CLIENT_NAME)
    sendResolumeMessage(choice(int(currentNumber)))
    osc_terminate()


def setReaperMarker(currentNumber):
    markerMessage = oscbuildparse.OSCMessage("/marker/" + str(currentNumber), None, [1])
    finished = False
    while not finished:
        osc_send(markerMessage, REAPER_CLIENT_NAME)
        osc_process()
        finished = True

def playReaperAudio():
    playMessage = oscbuildparse.OSCMessage("/action/40317", None, [1])
    finished = False
    while not finished:
        finished = True
        osc_send(playMessage, REAPER_CLIENT_NAME)
        osc_process()


def playReaperPauseMusic():
    pauseMessage = oscbuildparse.OSCMessage("/marker/11", None, [1])
    finished = False
    while not finished:
        osc_send(pauseMessage, REAPER_CLIENT_NAME)
        osc_process()
        finished = True


def startReaperAudio(currentNumber):
    osc_startup()
    osc_udp_client(OSC_REMOTE_SERVER_IP, REAPER_PORT, REAPER_CLIENT_NAME)

    if currentNumber > 4:
        playReaperPauseMusic()
        playReaperAudio()
    else:
        setReaperMarker(currentNumber)
        playReaperAudio()
    osc_terminate()


def dataHandler(address, message):
    # if storyActive.value and message >= 0.99 and storyStart.value:
    #     print("Story is active, message is over 0.98, but preventing start due StoryStart")
    # if not storyActive.value and message >= 0.99 and not storyStart.value:
    #     print("story is not active, message is over 0.98, but not preventing from storyStart")
    # if not storyActive.value and message >= 0.99 and storyStart.value:
    #     print("Story is not active, storystart is preventing start, AND message is over 0.98, wtf??")
    if currentlyPlaying.value < 5 and not storyStart.value and message >= 0.99:
        print("Ending")
        print(message)  # debug
        stopStory()


def stopStory():
    global currentlyPlaying
    currentlyPlaying.value = 11
    openClient(11)
    storyActive.value = False


def startServer(isActive, storyStatus, playingNumber):
    global storyActive, storyStart, currentlyPlaying
    storyActive = isActive
    storyStart = storyStatus
    currentlyPlaying = playingNumber
    dispatch = dispatcher.Dispatcher()
    dispatch.map(ADDRESS, dataHandler)
    server = osc_server.BlockingOSCUDPServer((OSC_LOCAL_SERVER_IP, OSC_SERVER_PORT), dispatch)
    print("Starting server, serving forever")
    server.serve_forever()


def init():
    # set gpio
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(RED_PI_PIN, GPIO.IN)
    GPIO.setup(BLUE_PI_PIN, GPIO.IN)

    # start server
    serverRunner = Process(target=startServer, args=(storyActive,storyStart, currentlyPlaying))
    serverRunner.start()

    initializeDatabase()


def initializeDatabase():
    try:
        schema = ""
        with open(LOGGING_SQL_FILE_NAME, 'r') as SchemaFile:
            schema = SchemaFile.read().replace('\n', '')

        # Connect or Create DB File
        conn = sqlite3.connect(LOGGING_DB_NAME)
        curs = conn.cursor()

        # Create Tables
        sqlite3.complete_statement(schema)
        curs.executescript(schema)

        # Close DB
        curs.close()
        conn.close()
        global loggingEnabled
        loggingEnabled = True
        print("Logging Started")
    except Exception as e:
        print(e)
        print("Could not initialize logging. Proceeding without logs.")


init()

while True:
    try:
        if GPIO.input(BLUE_PI_PIN) == 0:
            currentNumber = getNumber()
            if currentNumber != 0:
                openClient(currentNumber)
                print(currentNumber)
        else:
            time.sleep(.16)

    except KeyboardInterrupt:  # ctrl + c
        GPIO.cleanup()
