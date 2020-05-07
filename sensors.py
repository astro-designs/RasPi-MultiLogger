#!/usr/bin/env python

# Sensors.py defines the range and configurations of the sensors available to MultiLogger
# Designed for the Raspberry Pi (Zero, 2, 3B, 3B+, 4)

# Sensors supported for SensorType:
# 'TPin' = Analogue Thermistor. Set SensorLoc to the BCM pin number
# 'LM75' = LM75 I2C Temperature Sensor. Set SensorLoc to the I2C address
# 'T1w' = One-Wire Temperature Sensor. Set SensorLoc to the one-wire address 
# 'CPU_Temp' = CPU temperature. SensorLoc not used, leave as 'x'
# 'Throttle_Status' = CPU Throttle status (Current throttle status). SensorLoc not used, leave as 'x'
# 'Throttle_Level' = CPU Throttle level (% time throttled). SensorLoc not used, leave as 'x'
# 'Ping' = network ping function. Set SensorLoc to the address to ping
# 'LDRPin' = Analogue Light Dependant Resistor. Set SensorLoc to the BCM pin number

# The following list is not yet supported (work in progress...)
# 'ADC'
# 'GPI_FCount'
# 'SecondsRunning'

# Sensor configuration...
SensorName = 			["Temperature Probe", 	"CPU Temperature", 		"CPU Throttle", 		"CPU Throttle %"]
SensorType = 			['T1w',					'CPU_Temp',				'Throttle_Status',		'Throttle_Level'] # See list above for supported sensor types
SensorLoc = 			['10-000801503137',		'x',					'x',					'x']
SensorCal_Squ =         [0,						0,						0,						0]
SensorCal_Mult =        [1,						1,						1,						1]
SensorCal_Add =         [0,						0,						0,						0]
HighWarning = 			[125,					125,					125,					125]
HighReset = 			[0,						0,						0,						0]
LowWarning = 			[-25,					-25,					-25,					-25]
LowReset = 				[0,						0,						0,						0]
DomoticzIDX = 			['x', 					'x', 					'x', 					'x'] # Use 'x' to disable logging to Domoticz for each sensor
InitialMeasurements = 	[0,						0,						0,						0]

ActiveSensors = len(SensorName)

MeasurementInterval = 5

# Identify which sensor (if any) should be displayed to the local display
DisplaySensor1 = -1 # Set to -1 to disable display

