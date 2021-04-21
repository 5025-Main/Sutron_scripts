"""
Support for the AV9000 sensor
"""
from sl3 import *
import serial
import utime

"""
CurrentTime 49981 Unsigned Long 2 R/W Seconds since 1/1/2000.
we do not set the correct time, but it does not matter as long as
the clock register is written to
"""
set_time = b'\xF7\x10\x26\xFC\x00\x02\x04\x00\x01\x00\x00\x02\x94'

"""
Measurement interval 40133 Unsigned Integer 1 R/W 
1 = 30 seconds
2 = 1 min
3 = 2 min
4 = 5 min
5 = 10 min
6 = 15 min
7 = 30 min
8 = 60 min
"""
# set it up for 1 minute interval
set_interval = b'\xF7\x10\x00\x84\x00\x01\x02\x00\x02\x16\x71'


@TASK
def AV9000_setup():
    """
    Routine should be called once when the AV9000 is powered up
    It sets the AV9000 up
    """

    time_aok = False
    interval_aok = False

    with serial.Serial("RS485", 19200, stopbits=1) as sensor:
        sensor.rs485 = True  # required to actually send data over RS484
        sensor.timeout = 1
        sensor.inter_byte_timeout = .2
        sensor.delay_before_tx = .5  # if you only get intermittent data, increase this value

        # make sure the sensor is powered on OK
        power_control("SW1", False)  # turn off power to sensor
        utime.sleep(2)  # make sure sensor is off
        power_control("SW1", True)  # turn on power to sensor
        utime.sleep(3)  # give sensor a chance to wake up

        # set the clock of the AV9000 so that it measures on its own
        for i in range(3):  # retry
            sensor.write(set_time)
            buff = sensor.read(8)
            sensor.flush()
            if len(buff) >= 8 and buff[0] == 247: # our only verification is that first return byte matches
                time_aok = True
                break
            else:
                utime.sleep(2)

        # set the measurement interval to 1 minute
        for i in range(3):  # retry
            sensor.write(set_interval)
            buff = sensor.read(8)
            sensor.flush()
            if len(buff) >= 8 and buff[0] == 247: # our only verification is that first return byte matches
                interval_aok = True
                break
            else:
                print(buff)
                utime.sleep(2)

    if not time_aok or not interval_aok:
        raise ValueError("Could not setup AV9000")
