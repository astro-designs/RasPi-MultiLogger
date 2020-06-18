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

import logging
import time
from datetime import datetime
import LM75
import sys
import urllib
import urllib2
import requests
from microdotphat import write_string, set_decimal, clear, show
import os
import subprocess
from gpiozero import CPUTemperature
import RPi.GPIO as GPIO

# Import sensor configurations
import sensors

# Note - enable 1-wire interface using raspi-config
# Note - Once enabled, run (once):

# IFTTT Key definition
# Save your IFTTT key to key.py
# or just define IFTTT_KEY somewhere inside this file
# example key.py:
# IFTTT_KEY = "randomstringofcharacters..."
from key import IFTTT_KEY

import argparse

parser = argparse.ArgumentParser(description='Simple Domoticz data logger')

parser.add_argument('-ip', action='store', dest='IP_Address', default='192.168.1.31',
                    help='IP Address of Domoticz server (e.g. 192.168.1.31)')

parser.add_argument('-port', action='store', dest='port', default='8085',
                    help='Domoticz listening port (e.g. 8085')

parser.add_argument('-NumReadings', action='store', dest='NumReadings', default=0,
                    help='Number of readings to log')

parser.add_argument('-LogInterval', action='store', dest='LogInterval', default=30,
                    help='Log interval in seconds (e.g. 30)')

parser.add_argument('-NumAverages', action='store', dest='NumAverages', default=1,
                    help='Number of readings to average')

parser.add_argument('-DisplayInterval', action='store', dest='DisplayInterval', default=10,
                    help='Display interval in seconds (e.g. 30)')

arguments = parser.parse_args()

# Read arguments...
IP_Address = arguments.IP_Address
port = arguments.port
NumReadings = int(arguments.NumReadings)
LogInterval = int(arguments.LogInterval)
NumAverages = int(arguments.NumAverages)
DisplayInterval = int(arguments.DisplayInterval)

# Setup Log to file function
timestr = 'logs/' + time.strftime("%B-%dth--%I-%M-%S%p") + '.log'
logger = logging.getLogger('myapp')
hdlr = logging.FileHandler(timestr)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr) 
logger.setLevel(logging.INFO)

# Miscellaneous definitions
DailyReset = False
GET_THROTTLED_CMD = 'vcgencmd get_throttled'
throttle_uv = 0
throttle_uv_level = 0
throttle_readings = 0
throttle_uv_num = 0

#Electricity Import (usage)
Electric_kWhrs_imported_total = 0
prev_Electric_kWhrs_imported_total = Electric_kWhrs_imported_total
Electric_kWhrs_imported_today = 0
Electric_kWhrs_import_now = 0
prev_Electric_Time = 0

#Electricity Export
Electric_kWhrs_exported_total = 0
Electric_kWhrs_exported_today = 0

# Solar PV
SolarPV_kWhrs_gen_total = 56.000
prev_SolarPV_kWhrs_gen_total = SolarPV_kWhrs_gen_total
SolarPV_kWhrs_gen_today = 36.461
SolarPV_kWhrs_gen_now = 0
prev_SolarPV_Time = 0

GPIO.setmode(GPIO.BCM)

# Sensor configuration...
LogTitles = sensors.SensorName
SensorType = sensors.SensorType
SensorLoc = sensors.SensorLoc
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
Measure and logs temperature from external DS18B20 1-wire temperature sensor or LM75
Logs the data to Domoticz server
Optionally displays data on a MicroDot pHAT
Can optionally issues a warning to IFTTT 

Press Ctrl+C to exit.
""")

logger.info('Starting Logger...')

# Define function to log data to Domoticz server...
def LogToDomoticz(idx, SensorVal):
	url = 'http://' + IP_Address + ':' + port + '/json.htm?type=command&param=udevice&nvalue=0&idx='+idx+'&svalue='+str(SensorVal)
	try:
		request = urllib2.Request(url)
		response = urllib2.urlopen(request)
		print('Logged ' + str(SensorVal) + ' to Domoticz ID ' + idx)
	except urllib2.HTTPError, e:
		logger.info(e.code)
		print e.code;
	except urllib2.URLError, e:
		logger.info(e.args)
		print e.args;


# Define a function to monitor the throttle status...
def ThrottleMonitor():
	global throttle_readings, throttle_uv_num, throttle_uv, throttle_uv_level
	throttle_output = subprocess.check_output(GET_THROTTLED_CMD, shell=True)
	throttle_status = int(throttle_output.split('=')[1], 0)
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
def LogTemp(NextLogTime, logTitleString, logString, SensorVal):
	TimeNow = time.time()
	if TimeNow > NextLogTime:
		NextLogTime = NextLogTime + LogInterval
		# Log to webhook...
		#print("Logging Temperature to webhook...")
		#r = requests.post('https://maker.ifttt.com/trigger/RasPi_LogTemp/with/key/'+IFTTT_KEY, params={"value1":logTitleString,"value2":logString,"value3":"none"})
		
		print("Logging to Domoticz...")
		for x in range(0, ActiveSensors):
			if DomoticzIDX[x] != 'x':
				LogToDomoticz(DomoticzIDX[x], SensorVal[x])

	return NextLogTime

# Define function to display temperature on MicroDot Phat...
def DisplayTemp(NextDisplayTime, SensorVal, unitstr):
	TimeNow = time.time()
	if TimeNow > NextDisplayTime:
		NextDisplayTime = NextDisplayTime + DisplayInterval
		#print("Displaying Temperature on MicroDot Phat...")
		write_string( "%.1f" % SensorVal + unitstr, kerning=False)
		show()

	return NextDisplayTime

def read_temp_CPU():
	measurement = CPUTemperature()
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

	#print(address + ": Prev Success = " + str(SensorReading[SensorID]) + " %")

	if "ttl=" in out:
		SensorReading[SensorID] = min(SensorReading[SensorID] + 1,100)
		#print (address + ": Ping ok ")
	else:
		SensorReading[SensorID] = max(SensorReading[SensorID] - 1,0)
		#print (address + ": Ping failed ")

	#print(address + ": Success = " + str(SensorReading[SensorID]) + " %")
	
	measurement = SensorReading[SensorID]
	
	return measurement

# Interrupt callback routine for increasing Electric import count
def Electric_import_pulse(channel):
	global Electric_kWhrs_imported_total, prev_Electric_kWhrs_imported_total, Electric_kWhrs_imported_today, Electric_kWhrs_gen_now, prev_Electric_Time
	
	Electric_kWhrs_imported_total = round(Electric_kWhrs_imported_total + 0.001,3)
	Electric_kWhrs_imported_today = round(Electric_kWhrs_imported_today + 0.001,3)
	Electric_Time = time.time()
		
	# Reset daily total
	if time.localtime(Electric_Time).tm_hour < time.localtime(prev_Electric_Time).tm_hour:
		Electric_kWhrs_imported_today = 0

	if prev_Electric_Time > 0:
		Electric_kWhrs_import_now = (Electric_kWhrs_imported_total - prev_Electric_kWhrs_imported_total) / ((Electric_Time - prev_Electric_Time) / 3600)
	
	prev_Electric_kWhrs_imported_total = Electric_kWhrs_imported_total
	prev_Electric_Time = Electric_Time

	#print("Electric_kWhrs_imported_today: ", Electric_kWhrs_imported_today)
	#print("Electric_kWhrs_imported_today: ", Electric_kWhrs_imported_today)

# Interrupt callback routine for increasing SolarPV count
def SolarPV_gen_pulse(channel):
	global SolarPV_kWhrs_gen_total, prev_SolarPV_kWhrs_gen_total, SolarPV_kWhrs_gen_today, SolarPV_kWhrs_gen_now, prev_SolarPV_Time
	
	SolarPV_kWhrs_gen_total = round(SolarPV_kWhrs_gen_total + 0.001,3)
	SolarPV_kWhrs_gen_today = round(SolarPV_kWhrs_gen_today + 0.001,3)
	SolarPV_Time = time.time()
	
	# Reset daily total
	if time.localtime(SolarPV_Time).tm_hour < time.localtime(prev_SolarPV_Time).tm_hour:
		SolarPV_kWhrs_gen_today = 0

	if prev_SolarPV_Time > 0:
		SolarPV_kWhrs_gen_now = (SolarPV_kWhrs_gen_total - prev_SolarPV_kWhrs_gen_total) / ((SolarPV_Time - prev_SolarPV_Time) / 3600)
	
	prev_SolarPV_kWhrs_gen_total = SolarPV_kWhrs_gen_total
	prev_SolarPV_Time = SolarPV_Time
	
	#print("SolarPV_kWhrs_gen_total: ", SolarPV_kWhrs_gen_total)
	#print("SolarPV_kWhrs_gen_today: ", SolarPV_kWhrs_gen_today)
	#print("SolarPV_kWhrs_gen_now: ", SolarPV_kWhrs_gen_now)
		
def read_Electric_kWhrs_imported_today(SensorID):
	global Electric_kWhrs_imported_today
	
	if DailyReset:
		Electric_kWhrs_imported_today = 0

	measurement = Electric_kWhrs_imported_today
	#print("Read kWhrs imported today: ", measurement)
	
	return measurement

def read_Electric_Whrs_imported_today(SensorID):
	global Electric_kWhrs_imported_today
	
	if DailyReset:
		Electric_kWhrs_imported_today = 0

	measurement = Electric_kWhrs_imported_today * 1000
	#print("Read Whrs imported today: ", measurement)
	
	return measurement

def read_SolarPV_kWhrs_gen_today(SensorID):
	global SolarPV_kWhrs_gen_today
	
	if DailyReset:
		SolarPV_kWhrs_gen_today = 0

	measurement = SolarPV_kWhrs_gen_today
	#print("kWhrs in: ", measurement)
	
	return measurement
	
def read_SolarPV_Whrs_gen_today(SensorID):
	global SolarPV_kWhrs_gen_today
	
	if DailyReset:
		SolarPV_kWhrs_gen_today = 0

	measurement = SolarPV_kWhrs_gen_today * 1000
	#print("Whrs in: ", measurement)
	
	return measurement
	
def read_SolarPV_kW_gen_now(SensorID):
	global SolarPV_kWhrs_gen_now
	
	measurement = SolarPV_kWhrs_gen_now
	
	#print("kSolarPV_kW_gen_now: ", measurement)
	
	return measurement
	
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

	if SensorType[SensorID] == 'SolarPV_kWhrs_gen_today':
		measurement = read_SolarPV_kWhrs_gen_today(SensorID)

	if SensorType[SensorID] == 'SolarPV_kWhrs_gen_total':
		measurement = read_SolarPV_kWhrs_gen_total(SensorID)

	if SensorType[SensorID] == 'SolarPV_Whrs_gen_today':
		measurement = read_SolarPV_Whrs_gen_today(SensorID)
		
	if SensorType[SensorID] == 'SolarPV_W':
		measurement = read_SolarPV_kW_gen_now(SensorID)
		

	return measurement


# 1-wire config...
if 'T1w' in SensorType:
	print("Using 1-Wire Temperature Sensor(s)")
	os.system('modprobe w1-gpio')
	os.system('modprobe w1-therm')
	base_dir = '/sys/bus/w1/devices/'

# LM75 config...
if 'LM75' in SensorType:
	print("Using LM75 Temperature Sensor(s)")
	sensor = LM75.LM75()

# TrigN config...
if 'TrigN' in SensorType:
	print("Using Negative-Edge trigger on pin")

# Electricity config...
# Assumes the I/O pin is connected directly to the output of the photo detector stuck to the front of the electricity meter
# and that the output is pulled up to around 3.3V within the sensor monitoring module.
# Recommend a resistor (say, 1kR) is connected in-line with the connection to the GPIO pin to protect the Pi
if 'SolarPV_Whrs_gen_today' in SensorType:
	for x in range(0, ActiveSensors):
		if SensorType[x] == 'SolarPV_Whrs_gen_today':
			GPIO.setup(int(SensorLoc[x],10), GPIO.IN) #, pull_up_down=GPIO.PUD_UP) # Add pull-up here only when testing without the photo-sensor attached
			GPIO.add_event_detect(int(SensorLoc[x],10), GPIO.FALLING, callback=SolarPV_gen_pulse, bouncetime=500)

# Update LogTitlesString with description of all sensors...
logTitleString = ""
for x in range(0, ActiveSensors):
	logTitleString = logTitleString + LogTitles[x] + ";"
print (logTitleString)

############################################################
# Main program loop
try:
	
	print("Number of Readings: ", NumReadings)
	print("Number of Averages: ", NumAverages)
	print("Measurement Interval: ", MeasurementInterval)
	print("Log Interval: ", LogInterval)
	print("Display Interval: ", DisplayInterval)
	print("Temperature data logger running...")

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
			#print ("Reading throttle...")
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
					logger.info('Low temperature warning')
					# Issue Warning via IFTTT...
					#r = requests.post('https://maker.ifttt.com/trigger/Water_low_temp/with/key/' + IFTTT_KEY, params={"value1":"none","value2":"none","value3":"none"})
					LowWarningIssued[x] = True
			if SensorReading[x] > LowReset[x]:
				LowWarningIssued[x] = False
			# Check for high warning
			if SensorReading[x] > HighWarning[x]:
				if HighWarningIssued[x] == False:
					logger.info('High temperature warning')
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
		print(logString)
		
		# Write to log...
		if LogInterval > 0:
			NextLogTime = LogTemp(NextLogTime, logTitleString, logString, SensorReading)
		
		# Write to display...
		if DisplayInterval > 0 and DisplaySensor1 >= 0:
			NextDisplayTime = DisplayTemp(NextDisplayTime, SensorReading[DisplaySensor1], "c ")
		
		# NumReadings countdown...
		if Reading < NumReadings:
			Reading = Reading + 1
			
		prev_TimeNow = TimeNow
	
	logger.info('Logging completed.')
	
# If you press CTRL+C, cleanup and stop
except KeyboardInterrupt:
	logger.info('Keyboard Interrupt (ctrl-c) detected - exiting program loop')
	print("Keyboard Interrupt (ctrl-c) detected - exiting program loop")

finally:
	logger.info('Closing data logger')
	print("Closing data logger")

	
	
	
	
	
	
