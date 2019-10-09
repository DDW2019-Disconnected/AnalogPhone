import RPi.GPIO as GPIO
import time

from osc4py3.as_eventloop import *
from osc4py3 import oscbuildparse

from pythonosc import dispatcher
from pythonosc import osc_server

from pprint import pprint

import threading

from multiprocessing import Process, Value

lock = threading.Lock()
# STORY SETUP
storyActive = Value('b', False)
storyStart = False

# RPI SETUP
redPin = 21
bluePin = 20

# IP CLIENT
ipClient = "192.168.43.40"

# IP SERVER & RESOLUME ADDRESS
ipServer = "192.168.43.181"
address = "/composition/layers/1/position"

def getNumber():
    currState = 0
    oldState = 0
    pulses = 0
    
    while GPIO.input(bluePin) == 0:
        currState = GPIO.input(redPin)
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

def sendMessage(message): 
    finished = False
    while not finished:
            osc_send(message, "Arena")
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
        
        osc_startup()
        osc_udp_client(ipClient, 2333, "Arena")
        sendMessage(choice(int(currentNumber)))
        osc_terminate()
    finally:
        lock.release()

def dataHandler(address, message):
    if storyActive.value == True:
        if message > 0.98:
            print(message) #debug
            openClient(10)

def startServer(isActive):
    storyActive = isActive
    dispatch = dispatcher.Dispatcher()
    dispatch.map(address, dataHandler)
    server = osc_server.ThreadingOSCUDPServer((ipServer, 7001), dispatch)
    server.serve_forever()
    
def init():
    # set gpio
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(redPin, GPIO.IN)
    GPIO.setup(bluePin, GPIO.IN)
    
    # start server
    serverRunner = Process(target = startServer, args=(storyActive,))
    serverRunner.start()

init()

while True:
    try:
        if GPIO.input(bluePin) == 0:
            currentNumber = getNumber()
            if currentNumber != 0:
                if storyActive.value == False:
                    openClient(currentNumber)
                    print(currentNumber)
        
    except KeyboardInterrupt: # ctrl + c
        GPIO.cleanup()