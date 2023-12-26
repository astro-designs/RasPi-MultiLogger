#!/usr/bin/env python

# Sensor configuration...
# Note - Each array below must be equal in length to len(SensorName)

SensorName = ["Outside Temperature"]
SensorType = ['T1w']
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

SensorLoc = ['28-01191b9257fd']

# Sensor output calculation (gain & offset)
# Output = Ax^2 + Bx + C
Sensor_A = [0.0]
Sensor_B = [1.0]
Sensor_C = [0.0]

# Sensor Error & Warning thresholds
HighWarning = [125]
HighReset = [0]
LowWarning = [-25]
LowReset = [0]

# Domoticz config
DomoticzIDX = ['63'] # Use 'x' to disable logging to Domoticz for each sensor

# Other options

# Number of active sensors
ActiveSensors = len(SensorName)

# Measurement interval in seconds
MeasurementInterval = 30

# Identify which sensor (if any) should be displayed to the local display
DisplaySensor1 = -1 # Set to -1 to disable display

