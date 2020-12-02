#!/usr/bin/env python

# Sensor configuration...
# Note - Each array below must be equal in length to len(SensorName)

SensorName = ["Kitchen Temperature", "CPU Throttle", "CPU Throttle %", "Ping 192.168.1.249", "Ping 192.168.1.250", "Ping 192.168.1.251", "Ping 192.168.1.252", "Ping 192.168.1.253", "Ping 192.168.1.254", "Ping 192.168.1.124", "Ping 192.168.1.138", "Ping 192.168.1.58", "Ping 192.168.1.185"]
SensorType = ['T1w','Throttle_Status','Throttle_Level','Ping','Ping','Ping','Ping', 'Ping','Ping','Ping','Ping','Ping','Ping']
# 'Throttle_Status' = CPU Throttle status (Current throttle status)
# 'Throttle_Level' = CPU Throttle level (% time throttled)
# 'CPU_Temp' = CPU temperature
# 'T1w' = One-Wire Temperature Sensor 
# 'LM75' = LM75 I2C Temperature Sensor
# 'TPin' = Analogue Thermistor
# 'Ping' = network ping success (%)
# 'LDRPin' = Analogue Light Dependant Resistor
# 'Electric_Whrs_import_today' = Electricity usage meter (daily)
# 'Electric_kW' = Electricity usage meter (Watts now)
# 'SolarPV_Whrs_gen_today' = Solar PV generation meter (daily)
# 'SolarPV_W' = Solar PV generation meter (Watts now)
#SensorLoc = ['28-01191b9257fd','x','x','x']
SensorLoc = ['10-000801503137','x','x','192.168.1.249','192.168.1.250','192.168.1.251','192.168.1.252','192.168.1.253','192.168.1.254','192.168.1.124','192.168.1.138','192.168.1.58','192.168.1.185']
HighWarning = [125,125,125,125,125,125,125,125,125,125,125,125,125]
HighReset = [0,0,0,0,0,0,0,0,0,0,0,0,0]
LowWarning = [-25,-25,-25,-25,-25,-25,-25,-25,-25,-25,-25,-25,-25]
LowReset = [0,0,0,0,0,0,0,0,0,0,0,0,0]
DomoticzIDX = ['8','40','43','48','41','49','38','39','37','44','45','46','47'] # Use 'x' to disable logging to Domoticz for each sensor

# Other options

# Number of active sensors
ActiveSensors = len(SensorName)

# Measurement interval in seconds
MeasurementInterval = 30

# Identify which sensor (if any) should be displayed to the local display
DisplaySensor1 = -1 # Set to -1 to disable display

