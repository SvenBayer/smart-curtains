#!/usr/bin/python

from flask import request
from flask_api import FlaskAPI
from time import sleep
from multiprocess import Process
import RPi.GPIO as GPIO

DIR_R = 23
STEP_R = 24
ENABL_R = 25
DIR_L = 17
STEP_L = 27
ENABL_L = 22
CW = 1
CCW = 0


STATES  = ["closed", "open"]
SIDES = ["right", "left"]
RANGE = 1780
SPEED = .0005

app = FlaskAPI(__name__)

# Service Layer
def set_curtain_status(value, side):
        status_file = open('status_' + side + '.txt', 'w')
        status_file.write(value)
        status_file.close()
        return value

def get_curtain_status_all():
        status_file_right = open('status_right.txt', 'r')
        value_right = status_file_right.read().splitlines()[0]
        status_file_right.close()

        status_file_left = open('status_left.txt', 'r')
        value_left = status_file_left.read().splitlines()[0]
        status_file_left.close()

        if value_right == "open" and value_left == "open":
                return "open"
        elif value_right == "closed" and value_left == "closed":
                return "closed"
        else:
                return "partlyopen"

def get_curtain_status(side):
        status_file = open('status_' + side + '.txt', 'r')
        value = status_file.read().splitlines()[0]
        status_file.close()
        return value

def opening(side):
        return rotate(CW, side)

def closing(side):
        return rotate(CCW, side)

def rotate(direction, side):
        if side == "right":
                DIR = DIR_R
                STEP = STEP_R
                ENABL = ENABL_R
        elif side == "left":
                DIR = DIR_L
                STEP = STEP_L
                ENABL = ENABL_L
        else:
                return "Wrong side of curtain", 500

        try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(DIR, GPIO.OUT)
                GPIO.setup(STEP, GPIO.OUT)
                GPIO.setup(ENABL, GPIO.OUT)
                GPIO.output(DIR,CW)

                GPIO.output(ENABL,0)
                GPIO.output(DIR,direction)
                for x in range(RANGE):
                        GPIO.output(STEP,GPIO.HIGH)
                        sleep(SPEED)
                        GPIO.output(STEP,GPIO.LOW)
                        sleep(SPEED)
        except:
                print("some error")
                return "Some server error happened", 500
        finally:
                print("Disable motor")
                GPIO.setup(ENABL,GPIO.OUT)
                GPIO.output(ENABL,GPIO.HIGH)

def open_curtain(side):
        curtain_status = set_curtain_status("lock", side)
        opening(side)
        curtain_status = set_curtain_status("open", side)
        return curtain_status

def close_curtain(side):
        curtain_status = set_curtain_status("lock", side)
        closing(side)
        curtain_status = set_curtain_status("closed", side)
        return curtain_status

# Web Layer
@app.route('/curtains', methods=["GET"])
def api_curtains():
        return get_curtain_status_all()

@app.route('/curtain/<side>', methods=["GET"])
def api_curtain(side):
        if side in SIDES:
                return get_curtain_status(side)
        else:
                return {"error": 400, "side": side}

@app.route('/curtains/<status>', methods=["POST"])
def api_curtains_control(status):
        if status in STATES:
                curtain_status_all = get_curtain_status_all()
                if status == "open" and (curtain_status_all == "closed" or curtain_status_all == "partlyopen"):
                        curtain_status_right = get_curtain_status("right")
                        p_right = None
                        if curtain_status_right == "closed":
                                p_right = Process(target=open_curtain, args=('right',))
                                p_right.start()

                        curtain_status_left = get_curtain_status("left")
                        p_left = None
                        if curtain_status_left == "closed":
                                p_left = Process(target=open_curtain, args=('left',))
                                p_left.start()

                        if p_right is not None:
                                p_right.join()
                        if p_left is not None:
                                p_left.join()
                        return get_curtain_status_all()

                elif status == "closed" and (curtain_status_all == "open" or curtain_status_all == "partlyopen"):
                        curtain_status_right = get_curtain_status("right")
                        p_right = None
                        if curtain_status_right == "open":
                                p_right = Process(target=close_curtain, args=('right',))
                                p_right.start()

                        curtain_status_left = get_curtain_status("left")
                        p_left = None
                        if curtain_status_left == "open":
                                p_left = Process(target=close_curtain, args=('left',))
                                p_left.start()

                        if p_right is not None:
                                p_right.join()
                        if p_left is not None:
                                p_left.join()
                        return get_curtain_status_all()

        return {"error": 400, "curtain_status_all": curtain_status_all, "status": status}, 400

@app.route('/curtain/<side>/<status>', methods=["POST"])
def api_curtain_control(side, status):
        if side in SIDES and status in STATES:
                curtain_status = get_curtain_status(side)
                if status == "open" and curtain_status == "closed":
                        return open_curtain(side)
                elif status == "closed" and curtain_status == "open":
                        return close_curtain(side)
        return {"error": 400, "curtain_status": curtain_status, "status": status}, 400

if __name__ == "__main__":
        GPIO.cleanup()
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(ENABL_R, GPIO.OUT)
        GPIO.setup(ENABL_L, GPIO.OUT)
        GPIO.output(ENABL_R, GPIO.HIGH)
        GPIO.output(ENABL_L, GPIO.HIGH)
        app.run(host='0.0.0.0')
