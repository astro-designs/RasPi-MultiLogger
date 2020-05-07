#!/usr/bin/env python

# Sensor configuration...
SensorName = ["Kitchen Temperature", "Ping 192.168.1.254", "Ping 192.168.1.252", "Ping 192.168.1.253", "Ping 192.168.1.250", "192.168.1.179", "CPU Throttle", "CPU Throttle %", "192.168.1.174"]
SensorType = ['T1w','Ping','Ping','Ping','Ping', 'Ping','Throttle_Status','Throttle_Level','Ping']
# 'Throttle_Status' = CPU Throttle status (Current throttle status)
# 'Throttle_Level' = CPU Throttle level (% time throttled)
# 'CPU_Temp' = CPU temperature
# 'T1w' = One-Wire Temperature Sensor 
# 'LM75' = LM75 I2C Temperature Sensor
# 'TPin' = Analogue Thermistor
# 'Ping' = network ping success (%)
# 'LDRPin' = Analogue Light Dependant Resistor
#SensorLoc = ['28-01191b9257fd','x','x','x']
SensorLoc = ['10-000801503137','192.168.1.254','192.168.1.252','192.168.1.253','192.168.1.250','192.168.1.179','x','x','192.168.1.174']
HighWarning = [125,125,125,125,125,125,125,125,125]
HighReset = [0,0,0,0,0,0,0,0,0]
LowWarning = [-25,-25,-25,-25,-25,-25,-25,-25,-25]
LowReset = [0,0,0,0,0,0,0,0,0]
DomoticzIDX = ['8','37','38','39','41','42','x','40','43','x'] # Use 'x' to disable logging to Domoticz for each sensor

ActiveSensors = len(SensorName)

MeasurementInterval = 5

# Identify which sensor (if any) should be displayed to the local display
DisplaySensor1 = -1 # Set to -1 to disable display

