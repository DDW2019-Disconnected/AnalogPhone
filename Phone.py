import threading
import time
from multiprocessing import Process, Value

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
storyStart = False

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
ADDRESS = "/composition/layers/1/position"

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
    print(choice)
    if choice > 4:
            storyActive.value = False
            return oscbuildparse.OSCMessage("/composition/columns/8/connect", None, [1])
    elif choice == 1:
            storyActive.value = True
            return oscbuildparse.OSCMessage("/composition/columns/1/connect", None, [1])
    elif choice == 2:
            storyActive.value = True
            return oscbuildparse.OSCMessage("/composition/columns/2/connect", None, [1])
    elif choice == 3:
            storyActive.value = True
            return oscbuildparse.OSCMessage("/composition/columns/3/connect", None, [1])
    elif choice== 4:
            storyActive.value = True
            return oscbuildparse.OSCMessage("/composition/columns/4/connect", None, [1])

def sendResolumeMessage(message):
    finished = False
    while not finished:
            osc_send(message, RESOLUME_CLIENT_NAME)
            osc_process()
            finished = True
            
def storyStarted():
    global storyStart
    storyStart = False

def openClient(currentNumber):
    global storyStart
    
    if storyStart == True:
        return
    
    lock.acquire()
    try:
        storyStart = True
        timer = threading.Timer(5.0, storyStarted)
        timer.start()

        startResolumeVideo(currentNumber)
        startReaperAudio(currentNumber)
    finally:
        lock.release()


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


def stopReaperAudio():
    stopMessage = oscbuildparse.OSCMessage("/stop/", None, [1])
    finished = False
    while not finished:
            osc_send(stopMessage, REAPER_CLIENT_NAME)
            osc_process()
            finished = True


def startReaperAudio(currentNumber):
    osc_startup()
    osc_udp_client(OSC_REMOTE_SERVER_IP, REAPER_PORT, REAPER_CLIENT_NAME)

    if currentNumber > 4:
        stopReaperAudio()
    else:
        setReaperMarker(currentNumber)
        playReaperAudio()
        osc_terminate()


def dataHandler(address, message):
    if storyActive.value == True:
        if message > 0.98:
            print(message) #debug
            openClient(10)

def startServer(isActive):
    storyActive = isActive
    dispatch = dispatcher.Dispatcher()
    dispatch.map(ADDRESS, dataHandler)
    server = osc_server.ThreadingOSCUDPServer((OSC_LOCAL_SERVER_IP, OSC_SERVER_PORT), dispatch)
    server.serve_forever()
    
def init():
    # set gpio
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(RED_PI_PIN, GPIO.IN)
    GPIO.setup(BLUE_PI_PIN, GPIO.IN)
    
    # start server
    serverRunner = Process(target = startServer, args=(storyActive,))
    serverRunner.start()

init()

while True:
    try:
        if GPIO.input(BLUE_PI_PIN) == 0:
            currentNumber = getNumber()
            if currentNumber != 0:
                if storyActive.value == False:
                    openClient(currentNumber)
                    print(currentNumber)
        
    except KeyboardInterrupt: # ctrl + c
        GPIO.cleanup()