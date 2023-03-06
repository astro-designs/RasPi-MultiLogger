#!/usr/bin/env python
# Multi-function data logger
# Originally designed to monitor temperature using an LM75 and log data to both a GoogleDocs spreadsheet and Domoticz server
# Further modified to support other temperature sensors and data logging functions
# Support for single-pin based thermistor measurement not yet supported
# Added support for displaying data on a MicroDotPhat
# Added support for one-wire temperature sensor
# Added support for monitoring CPU temperature
# Added support for monitoring CPU under-voltage triggered throttle
# Adding support for GPIO trigger counter but not yet finished or supported
# Added support for a Ping function to monitor network connectivity
# 03/09/20: Adding support to record / monitor electricity energy consumption at a set time
# 17/04/22: Adding support for RPICT3V1 Current & Voltage sensors
#           Moving Domiticz routines to external library

import logging
import time
from datetime import datetime
import LM75
import sys
import requests
from microdotphat import write_string, set_decimal, clear, show
import os
import subprocess
from gpiozero import CPUTemperature
import RPi.GPIO as GPIO
import argparse
import serial

# import sensor interface functions for TBD...

# Import sensor interface functions for RPICT3V1
#import RPICT3V1

# Import Domoticz logging functions
import domoticz

# Import sensor configurations
import sensors

# Import authentication keys
from key import IFTTT_KEY

# Parse any arguments
parser = argparse.ArgumentParser(description='Simple Multi-function Data Logger')

parser.add_argument('-NumReadings', action='store', dest='NumReadings', default=0,
                    help='Number of readings to log')

parser.add_argument('-LogInterval', action='store', dest='LogInterval', default=30,
                    help='Log interval in seconds (e.g. 30)')

parser.add_argument('-NumAverages', action='store', dest='NumAverages', default=1,
                    help='Number of readings to average')

parser.add_argument('-DisplayInterval', action='store', dest='DisplayInterval', default=10,
                    help='Display interval in seconds (e.g. 30)')

parser.add_argument('-DebugLevel', action='store', dest='DebugLevel', default=0,
                    help='Configures debug functions (0 = no debug)')

parser.add_argument('-LogLevel', action='store', dest='LogLevel', default=0,
                    help='Configures log functions (0 = no logging)')

arguments = parser.parse_args()

# Read arguments...
NumReadings = int(arguments.NumReadings)
LogInterval = int(arguments.LogInterval)
NumAverages = int(arguments.NumAverages)
DisplayInterval = int(arguments.DisplayInterval)
DebugLevel = int(arguments.DebugLevel)
LogLevel = int(arguments.LogLevel)

def DebugLog(logString, DebugThreshold = 0, LogThreshold = 0):
    if DebugLevel >= DebugThreshold: print(logString)
    if LogLevel >= LogThreshold: logger.info(logString)

# Setup Log to file function
timestr = 'logs/' + time.strftime("%B-%dth--%I-%M-%S%p") + '.log'
logger = logging.getLogger('myapp')
hdlr = logging.FileHandler(timestr)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr) 
logger.setLevel(logging.INFO)

# Setup serial
ser = serial.Serial('/dev/ttyAMA0', 38400)

# Miscellaneous definitions
DailyReset = False
GET_THROTTLED_CMD = 'vcgencmd get_throttled'
throttle_uv = 0
throttle_uv_level = 0
throttle_readings = 0
throttle_uv_num = 0

#Electricity Import (usage)
Electric_kWhrs_import_total = 0
Electric_kWhrs_import_T1 = 0
prev_Electric_kWhrs_import_total = Electric_kWhrs_import_total
Electric_kWhrs_import_today = 0
Electric_kW_import_now = 0
prev_Electric_kW_import_now = 0
prev_Electric_Time = 0

#Electricity Export
Electric_kWhrs_exported_total = 0
Electric_kWhrs_exported_today = 0

#RPICT3V1
RPICT3V1_data = ""

# Solar PV
SolarPV_kWhrs_gen_total = 56.000
prev_SolarPV_kWhrs_gen_total = SolarPV_kWhrs_gen_total
SolarPV_kWhrs_gen_today = 0
SolarPV_kW_gen_now = 0
prev_SolarPV_kW_gen_now = 0
prev_SolarPV_Time = 0

#RPM
RPM_now = 0
prev_RPM_Time = 0
Dist_m_today = 0
prev_Dist_m_today = 0

GPIO.setmode(GPIO.BCM)

# Sensor configuration...
LogTitles = sensors.SensorName
SensorType = sensors.SensorType
SensorLoc = sensors.SensorLoc
Sensor_A = sensors.Sensor_A
Sensor_B = sensors.Sensor_B
Sensor_C = sensors.Sensor_C
TPins = sensors.SensorLoc
HighWarning = sensors.HighWarning
HighReset = sensors.HighReset
LowWarning = sensors.LowWarning
LowReset = sensors.LowReset
DomoticzIDX = sensors.DomoticzIDX
ActiveSensors = sensors.ActiveSensors
DisplaySensor1 = sensors.DisplaySensor1
MeasurementInterval = sensors.MeasurementInterval

# Sensor initialisation...
# Note - supports up to 16 sensors. If more are needed then these arrays need extending
SensorReading = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
LowWarningIssued = [False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False]
HighWarningIssued = [False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False]

print("""RasPi Multi-Function Data Monitor / Logger
By Mark Cantrill @AstroDesignsLtd
Measure and logs data from a variety of sensors and functions
Logs the data to Domoticz server
Optionally displays data on a MicroDot pHAT
Can optionally issues a warning to IFTTT 

Press Ctrl+C to exit.
""")

logString = "Log file: " + timestr
DebugLog(logString,0,0)

logString = "DebugLevel level: " + str(DebugLevel)
DebugLog(logString,1,1)

logString = "LogLevel level: " + str(LogLevel)
DebugLog(logString,1,1)
    
DebugLog ("Starting Logger...", 0, 0)

# Define a function to monitor the throttle status...
def ThrottleMonitor():
	global throttle_readings, throttle_uv_num, throttle_uv, throttle_uv_level
	throttle_output = subprocess.check_output(GET_THROTTLED_CMD, shell=True)
	if DebugLevel > 3: print("throttle_output: ", throttle_output)
	throttle_status_str = throttle_output.decode().split('=')
	if DebugLevel > 3: print("throttle_status_str: ", throttle_status_str)
	throttle_status = int(throttle_status_str[1].strip(), 0)
	if DebugLevel > 3: print("throttle_status: ", throttle_status)
	throttle_readings = throttle_readings + 1
	if throttle_status & 1:
		throttle_uv = 1
		throttle_uv_num = throttle_uv_num + 1
		throttle_uv_level = round(100 * (throttle_uv_num / throttle_readings),0)
	else:
		throttle_uv = 0
		throttle_uv_num = max(0, throttle_uv_num - 1)
		throttle_uv_level = round(100 * (throttle_uv_num / throttle_readings),0)


# Define function to log data...
def LogData(NextLogTime, logTitleString, logString, SensorVal):
	TimeNow = time.time()
	if TimeNow > NextLogTime:
		NextLogTime = NextLogTime + LogInterval
		
        # Log to webhook...
		#DebugLog ("Logging to webhook...", 0, 0)
		#r = requests.post('https://maker.ifttt.com/trigger/RasPi_LogTemp/with/key/'+IFTTT_KEY, params={"value1":logTitleString,"value2":logString,"value3":"none"})
		
		# Log to Domiticz server...
		DebugLog ("Logging to Domoticz...", 0, 0)
		for x in range(0, ActiveSensors):
			if DomoticzIDX[x] != 'x':
				domoticz.LogToDomoticz(DomoticzIDX[x], SensorVal[x])

		# Log to file...
		DebugLog (logString, 999, 0)
	
	return NextLogTime

# Define function to display temperature on MicroDot Phat...
def DisplayData(NextDisplayTime, SensorVal, unitstr):
	TimeNow = time.time()
	if TimeNow > NextDisplayTime:
		NextDisplayTime = NextDisplayTime + DisplayInterval
		DebugLog ("Displaying Temperature on MicroDot Phat...", 0, 0)
		write_string( "%.1f" % SensorVal + unitstr, kerning=False)
		show()

	return NextDisplayTime

def read_temp_CPU():
	measurement = CPUTemperature()
	measurement = round(measurement, 1)
	return measurement

# Define function to read one-wire temperature sensors...
def read_temp_T1w(SensorID):
    # Read one-wire device
    device_file = base_dir + SensorLoc[SensorID] + '/w1_slave'
    f = open(device_file, 'r')
    lines = f.readlines()

    # Extract temperature data
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = f.readlines()
    f.close()

    # Format temperature data
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        measurement = float(temp_string) / 1000.0
        measurement = round(measurement,1)
        return measurement

def read_temp_LM75(SensorID):
	clear()
	temp_raw = sensor.getTemp()
	if temp_raw > 128:
		measurement = temp_raw - 256
	else:
		measurement = temp_raw
	
	measurement = round(measurement, 1)
	return measurement

def read_temp_TPin(SensorID):
	measurement = 22.2
	return measurement

def read_Trig(SensorID):
	measurement = 100
	return measurement

def read_throttle(Mode = 0):
	if Mode == 0: # Check status of under-voltage detection
		measurement = throttle_uv

	elif Mode == 1: # Check level of throttle
		measurement = throttle_uv_level

	else: # Any unsupported mode...
		measurement = -999

	return measurement

def read_ping(SensorID):
	global SensorReading
	address = SensorLoc[SensorID]
	res = subprocess.Popen(['ping', '-c1', address], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

	out, err = res.communicate()

	if "ttl=" in out:
		SensorReading[SensorID] = min(SensorReading[SensorID] + 1,100)
	else:
		SensorReading[SensorID] = max(SensorReading[SensorID] - 1,0)

	measurement = SensorReading[SensorID]
	#measurement = round(measurement, 0)
	
	return measurement

# Interrupt callback routine for increasing Electric import count
def Electric_import_pulse(channel):
	global Electric_kWhrs_import_T1, Electric_kWhrs_import_total, prev_Electric_kWhrs_import_total, Electric_kWhrs_import_today, Electric_kW_import_now, prev_Electric_kW_import_now, prev_Electric_Time
	
	Electric_kWhrs_import_total = round(Electric_kWhrs_import_total + 0.001,3)
	Electric_kWhrs_import_today = round(Electric_kWhrs_import_today + 0.001,3)
	Electric_Time = time.time()

	# Track daily total untip 6AM to measure 
	if time.localtime(Electric_Time).tm_hour < 6:
		Electric_kWhrs_import_T1 = Electric_kWhrs_import_today
	
	# Reset daily total
	if time.localtime(Electric_Time).tm_hour < time.localtime(prev_Electric_Time).tm_hour:
		Electric_kWhrs_import_today = 0
		Electric_kWhrs_import_T1 = 0

	if prev_Electric_Time > 0:
		Electric_kW_import_now = (Electric_kWhrs_import_total - prev_Electric_kWhrs_import_total) / ((Electric_Time - prev_Electric_Time) / 3600)
	
	prev_Electric_kWhrs_import_total = Electric_kWhrs_import_total
	prev_Electric_Time = Electric_Time

	DebugLog ("Electric import/export pulse detected", 1, 1)

# Interrupt callback routine for increasing SolarPV count
def SolarPV_gen_pulse(channel):
	global SolarPV_kWhrs_gen_total, prev_SolarPV_kWhrs_gen_total, SolarPV_kWhrs_gen_today, SolarPV_kW_gen_now, prev_SolarPV_Time
	
	SolarPV_kWhrs_gen_total = round(SolarPV_kWhrs_gen_total + 0.001,3)
	SolarPV_kWhrs_gen_today = round(SolarPV_kWhrs_gen_today + 0.001,3)
	SolarPV_Time = time.time()
	
	# Reset daily total
	if time.localtime(SolarPV_Time).tm_hour < time.localtime(prev_SolarPV_Time).tm_hour:
		SolarPV_kWhrs_gen_today = 0

	if prev_SolarPV_Time > 0:
		SolarPV_kW_gen_now = (SolarPV_kWhrs_gen_total - prev_SolarPV_kWhrs_gen_total) / ((SolarPV_Time - prev_SolarPV_Time) / 3600)
	
	prev_SolarPV_kWhrs_gen_total = SolarPV_kWhrs_gen_total
	prev_SolarPV_Time = SolarPV_Time
	
	DebugLog ("SolarPV gen pulse detected", 1, 1)
		
def read_Electric_kWhrs_import_today(SensorID):
	global Electric_kWhrs_import_today
	
	if DailyReset:
		Electric_kWhrs_import_today = 0

	measurement = Electric_kWhrs_import_today
	measurement = round(measurement, 3)

	logString = "Read kWhrs imported today: " + str(measurement)
	DebugLog (logString, 1, 1)
	
	return measurement

def read_Electric_Whrs_import_today(SensorID):
	global Electric_kWhrs_import_today
	
	if DailyReset:
		Electric_kWhrs_import_today = 0

	measurement = Electric_kWhrs_import_today * 1000
	measurement = round(measurement, 0)

	logString = "Read Whrs imported today: " + str(measurement)
	DebugLog (logString, 1, 1)
	
	return measurement

def read_Electric_Whrs_import_T1(SensorID):
	global Electric_kWhrs_import_T1
	
	if DailyReset:
		Electric_kWhrs_import_T1 = 0

	measurement = Electric_kWhrs_import_T1 * 1000
	measurement = round(measurement, 0)

	logString = "Read Whrs imported today: " + str(measurement)
	DebugLog (logString, 1, 1)
	
	return measurement

def read_Electric_kW_import_now(SensorID):
	global Electric_kW_import_now, prev_Electric_kW_import_now
	
	if Electric_kW_import_now == prev_Electric_kW_import_now:
		Electric_kW_import_now = 0
		prev_Electric_kW_import_now = 0

	measurement = Electric_kW_import_now
	prev_Electric_kW_import_now = Electric_kW_import_now
	
	logString = "Electric_kW_import_now: " + str(measurement)
	DebugLog (logString, 1, 1)
	
	return measurement
	
def read_SolarPV_kWhrs_gen_today(SensorID):
	global SolarPV_kWhrs_gen_today
	
	if DailyReset:
		SolarPV_kWhrs_gen_today = 0

	measurement = SolarPV_kWhrs_gen_today
	measurement = round(measurement, 3)

	logString = "SolarPV_kWhrs_gen_today: " + str(measurement)
	DebugLog (logString, 1, 1)
	
	return measurement
	
def read_SolarPV_Whrs_gen_today(SensorID):
	global SolarPV_kWhrs_gen_today
	
	if DailyReset:
		SolarPV_kWhrs_gen_today = 0

	measurement = SolarPV_kWhrs_gen_today * 1000
	measurement = round(measurement, 0)

	logString = "SolarPV_Whrs_gen_today: " + str(measurement)
	DebugLog (logString, 1, 1)
	
	return measurement
	
def read_SolarPV_kW_gen_now(SensorID):
	global SolarPV_kW_gen_now, prev_SolarPV_kW_gen_now
	
	if SolarPV_kW_gen_now == prev_SolarPV_kW_gen_now:
		SolarPV_kW_gen_now = 0
		prev_SolarPV_kW_gen_now = 0

	measurement = SolarPV_kW_gen_now
	prev_SolarPV_kW_gen_now = SolarPV_kW_gen_now
	measurement = round(measurement, 3)
	
	logString = "SolarPV_kW_gen_now: " + str(measurement)
	DebugLog (logString, 1, 1)
	
	return measurement

def read_RPICT3V1_MainsElectricityVoltage(SensorID):
    
    global RPICT3V1_data
    
    # Buffer is capturing constantly so mush be flushed before reading the next line
    # in order to ensure we capture the latest data
    ser.flushInput()
    
    # Read line from serial (assumes RPICT3V1 is running and 
    RPICT3V1_data = ""
    NodeID = 0
    timeout = 10
    while (len(RPICT3V1_data) < 16 or NodeID != '11') and timeout > 0: 
        RPICT3V1_data = ser.readline()
        logString = "RPICT3V1 RX Data: " + str(RPICT3V1_data)
        DebugLog (logString, 2, 2)

        # Remove the trailing carriage return line feed...
        RPICT3V1_data = RPICT3V1_data[:-2]

        # Decode data...
        RPICT3V1_data = RPICT3V1_data.decode().split(' ')

        # Extract NodeID for to validate dataset...
        NodeID = RPICT3V1_data[0]
        
        timeout = timeout - 1

    print("RPICT3V1_data length: ", len(RPICT3V1_data))
    
    # Check that a read error or timeout hasn't occured
    if (len(RPICT3V1_data) == 16 and NodeID == '11') and timeout > 0:
        measurement = float(RPICT3V1_data[int(SensorLoc[SensorID])])
    else:
        measurement = 0.0
        
    measurement = round(measurement, 0)
    
    logString = "Mains Electricity Voltage (V): " + str(measurement)
    DebugLog (logString, 1, 1)

    return measurement

def read_RPICT3V1_SCT013_100A_1(SensorID):
    
    global RPICT3V1_data
    
    measurement = float(RPICT3V1_data[int(SensorLoc[SensorID])])
    measurement = round(measurement, 3)
    
    logString = "Mains Electricity Current (A): " + str(measurement)
    DebugLog (logString, 1, 1)
    
    return measurement
	
def read_RPICT3V1_ActiveImport(SensorID):    
    
    global RPICT3V1_data

    measurement = float(RPICT3V1_data[int(SensorLoc[SensorID])])
    
    # Check if current flow indicates export, then clamp to zero
    if measurement < 0:
        measurement = 0
    measurement = round(measurement, 3)
    
    logString = "Mains Electricity Import (W): " + str(measurement)
    DebugLog (logString, 1, 1)
    
    return measurement
	
def read_RPICT3V1_ActiveExport(SensorID):
    
    global RPICT3V1_data

    measurement = float(RPICT3V1_data[int(SensorLoc[SensorID])])

    # Check if current flow indicates import, then clamp to zero
    if measurement > 0:
        measurement = 0
    # otherwise invert measurement
    else:
        measurement = 0 - measurement
    measurement = round(measurement, 3)
    
    logString = "Mains Electricity Export (W): " + str(measurement)
    DebugLog (logString, 1, 1)
    
    return measurement
	
def read_RPICT3V1_PowerFactor(SensorID):
    
    global RPICT3V1_data

    measurement = float(RPICT3V1_data[int(SensorLoc[SensorID])])
    measurement = round(measurement, 3)
    
    logString = "Mains Electricity PowerFactor: " + str(measurement)
    DebugLog (logString, 1, 1)
    
    return measurement

def read_RPM_now(SensorID):
	global RPM_now, Dist_m_today, prev_Dist_m_today
	
	if Dist_m_today == prev_Dist_m_today:
		RPM_now = 0

	measurement = RPM_now
	prev_Dist_m_today = Dist_m_today
	measurement = round(measurement, 3)
	
	logString = "RPM_now: " + str(measurement)
	DebugLog (logString, 1, 1)
	print(logString)
    
	return measurement

def read_Dist_m(SensorID):
	global RPM_now, Dist_m_today, prev_Dist_m_today
	
	measurement = Dist_m_today
	measurement = round(measurement, 3)
	
	logString = "Dist_m: " + str(measurement)
	DebugLog (logString, 1, 1)
	print(logString)
	
	return measurement

# Interrupt callback routine for RPM & Dist_m
def RPM_pulse(channel):
	global Dist_m_today, RPM_now, prev_RPM_Time
	
	Dist_m_today = Dist_m_today + 1
	RPM_Time = time.time()
	
	# Reset daily total
	if time.localtime(RPM_Time).tm_hour < time.localtime(prev_RPM_Time).tm_hour:
		Dist_m_today = 0

	if prev_RPM_Time > 0:
		RPM_now = 60 / (RPM_Time - prev_RPM_Time) 
	
	prev_RPM_Time = RPM_Time
	
	DebugLog ("RPM gen pulse detected", 1, 1)
		
def read_sensor(SensorID):
	measurement = -999

	if SensorType[SensorID] == 'CPU_Temp':
		cpu = read_temp_CPU()
		measurement = cpu.temperature

	if SensorType[SensorID] == 'T1w':
		measurement = read_temp_T1w(SensorID)

	if SensorType[SensorID] == 'LM75':
		measurement = read_temp_LM75(SensorID)

	if SensorType[SensorID] == 'TPin':
		measurement = read_temp_TPin(SensorID)

	if SensorType[SensorID] == 'Throttle_Level':
		measurement = read_throttle(1)

	if SensorType[SensorID] == 'Throttle_Status':
		measurement = read_throttle(0)

	if SensorType[SensorID] == 'Ping':
		measurement = read_ping(SensorID)
	
	if SensorType[SensorID] == 'Electric_kWhrs_import_today':
		measurement = read_Electric_kWhrs_import_today(SensorID)

	if SensorType[SensorID] == 'Electric_kWhrs_import_total':
		measurement = read_Electric_kWhrs_import_total(SensorID)
		
	if SensorType[SensorID] == 'Electric_Whrs_import_today':
		measurement = read_Electric_Whrs_import_today(SensorID)
		
	if SensorType[SensorID] == 'Electric_Whrs_import_T1':
		measurement = read_Electric_Whrs_import_T1(SensorID)
		
	if SensorType[SensorID] == 'Electric_kW':
		measurement = read_Electric_kW_import_now(SensorID)		
		
	if SensorType[SensorID] == 'SolarPV_kWhrs_gen_today':
		measurement = read_SolarPV_kWhrs_gen_today(SensorID)

	if SensorType[SensorID] == 'SolarPV_kWhrs_gen_total':
		measurement = read_SolarPV_kWhrs_gen_total(SensorID)

	if SensorType[SensorID] == 'SolarPV_Whrs_gen_today':
		measurement = read_SolarPV_Whrs_gen_today(SensorID)
		
	if SensorType[SensorID] == 'SolarPV_W':
		measurement = read_SolarPV_kW_gen_now(SensorID)
		
	if SensorType[SensorID] == 'RPM':
		measurement = read_RPM_now(SensorID)
		
	if SensorType[SensorID] == 'Dist_m':
		measurement = read_Dist_m(SensorID)
		
	# RPICT3V1_MainsElectricityVoltage must be read before any other RPICT3V1 sensors as it is the only function that reads the data set from the device
	if SensorType[SensorID] == 'RPICT3V1_MainsElectricityVoltage':
		measurement = read_RPICT3V1_MainsElectricityVoltage(SensorID)

	if SensorType[SensorID] == 'RPICT3V1_SCT013_100A_1':
		measurement = read_RPICT3V1_SCT013_100A_1(SensorID)

	if SensorType[SensorID] == 'RPICT3V1_ActiveImport':
		measurement = read_RPICT3V1_ActiveImport(SensorID)

	if SensorType[SensorID] == 'RPICT3V1_ActiveExport':
		measurement = read_RPICT3V1_ActiveExport(SensorID)

	if SensorType[SensorID] == 'RPICT3V1_PowerFactor':
		measurement = read_RPICT3V1_PowerFactor(SensorID)

	#Apply gain / offset calculation
	measurement = float(Sensor_A[SensorID]) * (measurement)**2 + float(Sensor_B[SensorID]) * measurement + float(Sensor_C[SensorID])

	return measurement


# 1-wire config...
if 'T1w' in SensorType:
	if DebugLevel > 0: print("Using 1-Wire Temperature Sensor(s)")
	os.system('modprobe w1-gpio')
	os.system('modprobe w1-therm')
	base_dir = '/sys/bus/w1/devices/'

# LM75 config...
if 'LM75' in SensorType:
	if DebugLevel > 0: print("Using LM75 Temperature Sensor(s)")
	sensor = LM75.LM75()

# TrigN config...
if 'TrigN' in SensorType:
	if DebugLevel > 0: print("Using Negative-Edge trigger on pin")

# SolarPV config...
# Assumes the I/O pin is connected directly to the output of the photo detector stuck to the front of the electricity meter
# and that the output is pulled up to around 3.3V within the sensor monitoring module.
# Recommend a resistor (say, 1kR) is connected in-line with the connection to the GPIO pin to protect the Pi
if 'Electric_Whrs_import_today' in SensorType:
	for x in range(0, ActiveSensors):
		if SensorType[x] == 'Electric_Whrs_import_today':
			if DebugLevel > 0: print("Using Electricity strobe monitor on pin ",SensorLoc[x])
			GPIO.setup(int(SensorLoc[x],10), GPIO.IN, pull_up_down=GPIO.PUD_UP) # Add pull-up here only when testing without the photo-sensor attached
			GPIO.add_event_detect(int(SensorLoc[x],10), GPIO.FALLING, callback=Electric_import_pulse, bouncetime=500)

if 'SolarPV_Whrs_gen_today' in SensorType:
	for x in range(0, ActiveSensors):
		if SensorType[x] == 'SolarPV_Whrs_gen_today':
			if DebugLevel > 0: print("Using SolarPV strobe monitor on pin ",SensorLoc[x])
			GPIO.setup(int(SensorLoc[x],10), GPIO.IN) #, pull_up_down=GPIO.PUD_UP) # Add pull-up here only when testing without the photo-sensor attached
			GPIO.add_event_detect(int(SensorLoc[x],10), GPIO.FALLING, callback=SolarPV_gen_pulse, bouncetime=500)

if 'RPM' in SensorType:
	for x in range(0, ActiveSensors):
		if SensorType[x] == 'RPM':
			if DebugLevel > 0: print("Using active low edge on pin ",SensorLoc[x])
			GPIO.setup(int(SensorLoc[x],10), GPIO.IN) #, pull_up_down=GPIO.PUD_UP) # Add pull-up here only when testing without the photo-sensor attached
			GPIO.add_event_detect(int(SensorLoc[x],10), GPIO.FALLING, callback=RPM_pulse, bouncetime=500)

# Update LogTitlesString with description of all sensors...
logTitleString = ""
for x in range(0, ActiveSensors):
	logTitleString = logTitleString + LogTitles[x] + ";"

DebugLog (logTitleString, 0, 0)

############################################################
# Main program loop
try:
	
	print("Number of Readings: ", NumReadings)
	print("Number of Averages: ", NumAverages)
	print("Measurement Interval: ", MeasurementInterval)
	print("Log Interval: ", LogInterval)
	print("Display Interval: ", DisplayInterval)
	print("Multi-format data logger running...")

	# Set first LogTime
	NextLogTime = time.time() + LogInterval
	
	# Set first DisplayTime
	NextDisplayTime = time.time() + DisplayInterval
	
	# Set first MeasurementTime
	NextMeasurementTime = time.time()
	
	# First reading...
	Reading = 0
	prev_TimeNow = time.time()
	
	while Reading < NumReadings or NumReadings < 1:
		TimeNow = time.time()
		
		# Pause between measurements
		while TimeNow < NextMeasurementTime:
			# Check CPU throttle status while waiting...
			if DebugLevel > 2: print ("Reading throttle...")
			ThrottleMonitor()
			time.sleep(0.2)
			TimeNow = time.time()

		NextMeasurementTime = NextMeasurementTime + MeasurementInterval

		# Reset average measurements
		# Note: Averaging is only supported for some types of sensors
		for x in range(0, ActiveSensors):
			if SensorType[x] == 'T1w' or SensorType[x] == 'LM75' or SensorType[x] == 'CPU_Temp' or SensorType[x] == 'TPin':
				SensorReading[x] = 0.0

		# Measurement loop
		# Note: Averaging is only supported for some types of sensors
		for i in range (0, NumAverages):
			for x in range(0, ActiveSensors):
				if SensorType[x] == 'T1w' or SensorType[x] == 'LM75' or SensorType[x] == 'CPU_Temp' or SensorType[x] == 'TPin':
					SensorReading[x] = SensorReading[x] + read_sensor(x)
				else:
					SensorReading[x] = read_sensor(x)
				

		# Calculate average
		# Note: Averaging is only supported for some types of sensors
		for x in range(0, ActiveSensors):
			if SensorType[x] == 'T1w' or SensorType[x] == 'LM75' or SensorType[x] == 'CPU_Temp' or SensorType[x] == 'TPin':
				SensorReading[x] = SensorReading[x] / NumAverages

		# Check for warnings...
		for x in range(0, ActiveSensors):
			# Check for low warning
			if SensorReading[x] < LowWarning[x]:
				if LowWarningIssued[x] == False:
					if DebugLevel > -1: logger.info('Low warning!')
					# Issue Warning via IFTTT...
					#r = requests.post('https://maker.ifttt.com/trigger/Water_low_temp/with/key/' + IFTTT_KEY, params={"value1":"none","value2":"none","value3":"none"})
					LowWarningIssued[x] = True
			if SensorReading[x] > LowReset[x]:
				LowWarningIssued[x] = False
			# Check for high warning
			if SensorReading[x] > HighWarning[x]:
				if HighWarningIssued[x] == False:
					if DebugLevel > -1: logger.info('High warning!')
					# Issue Warning via IFTTT...
					#r = requests.post('https://maker.ifttt.com/trigger/Water_low_temp/with/key/' + IFTTT_KEY, params={"value1":"none","value2":"none","value3":"none"})
					HighWarningIssued[x] = True
			if SensorReading[x] < HighReset[x]:
				HighWarningIssued[x] = False

		# update logString with current temperature(s)
		logTime = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(TimeNow))
		logString = logTime + ";" + str(Reading) + ";"
		for x in range(0, ActiveSensors):
			logString = logString + str(SensorReading[x]) + ";"

		# Print the result
		if DebugLevel > 0: print(logString)
		
		# Write to log...
		if LogInterval > 0:
			NextLogTime = LogData(NextLogTime, logTitleString, logString, SensorReading)
		
		# Write to display...
		if DisplayInterval > 0 and DisplaySensor1 >= 0:
			NextDisplayTime = DisplayData(NextDisplayTime, SensorReading[DisplaySensor1], "c ")
		
		# NumReadings countdown...
		if Reading < NumReadings:
			Reading = Reading + 1
			
		prev_TimeNow = TimeNow
	
	if LogLevel > 0: logger.info('Logging completed.')
	
# If you press CTRL+C, cleanup and stop
except KeyboardInterrupt:
	if LogLevel > 0: logger.info('Keyboard Interrupt (ctrl-c) detected - exiting program loop')
	print("Keyboard Interrupt (ctrl-c) detected - exiting program loop")

finally:
	if LogLevel > 0: logger.info('Closing data logger')
	print("Closing data logger")

	
	
	
	
	
	
