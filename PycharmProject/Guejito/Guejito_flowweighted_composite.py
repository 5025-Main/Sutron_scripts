from sl3 import *
import utime


""" code below is copied from general_purpose.py """

gp_count = 32  # how many general purpose variable sets there are


def gp_index_valid(gp_index):
    """ returns True if the provided general purpose variable index is valid"""
    if (gp_index >= 1) and (gp_index <= gp_count):
        return True
    else:
        return False


def gp_read_label(gp_index):
    """
    Returns the customer set Label of the general purpose variable.

    :param gp_index: A number between 1 and gp_count
    :type gp_index: int
    :return: the Label of the specified gp
    :rtype: str
    """
    if gp_index_valid(gp_index):
        return setup_read("GP{} label".format(gp_index))
    else:
        raise ValueError("GP index invalid: ", gp_index)


def gp_read_value_by_index(gp_index):
    """
    Returns the customer set Value of the general purpose variable.

    :param gp_index: A number between 1 and gp_count
    :type gp_index: int
    :return: the Value of the specified p
    :rtype: float
    """
    if gp_index_valid(gp_index):
        return float(setup_read("GP{} value".format(gp_index)))
    else:
        raise ValueError("GP index invalid: ", gp_index)


def gp_find_index(label):
    """
    Tells you the index of the general purpose with said label
    Returns zero if no such label is found

    :param label: the customer set label for the gp
    :type label: string
    :return: gp index if a match is found.  zero if no match is found
    :rtype: int
    """
    for gp_index in range(1, gp_count + 1):
        if label.upper() == gp_read_label(gp_index).upper():
            return gp_index

    return 0  # no gp with that label found


def gp_read_value_by_label(label):
    """
    Returns the Value associated with the Label of the general purpose variable.

    :param label: the user set Label of the general purpose variable
    :type label: str
    :return: the Value of the general purpose variable
    :rtype: float
    """
    gp_index = gp_find_index(label)
    if gp_index_valid(gp_index):
        # we found a match.  return associated value
        gp_value = "GP{} value".format(gp_index)
        return float(setup_read(gp_value))
    else:
        raise ValueError("GP Label not found: ", label)
        return -999.9  # return this if no match is found

def gp_write_value_by_label(label, value):
    """
    Writes a new Value to the general purpose variable associated with the label

    :param label: the user set Label of the general purpose variable
    :type label: str
    :param value: the new Value of the general purpose variable
    :type value: float
    """
    gp_index = gp_find_index(label)
    if gp_index_valid(gp_index):
        # we found a match.  return associated value
        gp_value = "GP{} value".format(gp_index)
        setup_write(gp_value, value)
    else:
        raise ValueError("GP Label not found: ", label)

# SampleOn - start/stop sampling
sampling_on = False

# Bottle Number (if pacing is changed bottle number will need to update)
bottle_num = 0

# Running total volume
g_volume_total = 0.0

# Bottle volume - running total of volume in bottle
vol_in_bottle = 0.0

# We count how many aliquots have been collected in each bottle
aliquots_in_bottle = 0

# Volume pacing - keep a global one to check if there are any changes
vol_pacing_cf = gp_read_value_by_label("pacing_volume_cf")  # or with Alarm: setup_read("M{} Alarm 1 Threshold".format(index()))

# Time sampler was triggered last.
time_last_sample = 0.0

# Sample log
sample_log = {'SampleEvent':{'PacingVol':'','Bottle#':'','Aliquot#':'','SampleTime':''}}

def sample_on_true_or_false(inval):
    if inval == 1:
        setup_write("!M1 meas interval", "00:01:00") #PT Level
        #setup_write("!M3 meas interval", "00:01:00") #950 Level
        setup_write("!M4 meas interval", "00:01:00") #Flow calculation
        setup_write("!M7 meas interval", "00:01:00") #Flow pacing - incremental volume
        print("Manually triggered to log at 1 minute interval (FAST)")
        return True

    if inval == 0:
        setup_write("!M1 meas interval", "00:05:00") #PT Level
        #setup_write("!M3 meas interval", "00:05:00") #950 Level
        setup_write("!M4 meas interval", "00:05:00") #Flow calculation
        setup_write("!M7 meas interval", "00:05:00") #Flow pacing - incremental volume
        print("Manually triggered to log at 5 minute interval (SLOW)")
        return False


## Get pacing
def get_volume_pacing():
    """
    Returns the threshold at which the volume difference triggers the sampler.
    It is stored in the setup as Alarm 1 Threshold.

    :return: volume threshold
    :rtype: float
    """
    ## Get current bottle number and pacing
    global bottle_num
    global aliquots_in_bottle
    global vol_pacing_cf
    global vol_in_bottle

    # Check GP variable or "alarm 1" (which holds the desired pacing) for changes
    # a change in  pacing ALSO signifies a bottle change
    pacing_input = gp_read_value_by_label("pacing_volume_cf")  # or with alarm: setup_read("M{} Alarm 1 Threshold".format(index()))
    gp_bottle_num = int(gp_read_value_by_label("bottle_num")) # update bottle number

    # Compare
    print("checking for pacing change...")
    if vol_pacing_cf != float(pacing_input):
        bottle_num, vol_pacing_cf = bottle_and_pacing_change(gp_bottle_num, pacing_input) #returns new bottle number and pacing from change function
    else:
        print ("No pacing change...Current pacing: "+ "%.0f"%vol_pacing_cf + "cf")
        print("")

        # Check for new bottle but without pacing change (just full bottle)
        # Bottle number is input manually so just use the manual entry

        print("checking for bottle number change...")
        if gp_bottle_num != bottle_num:
            aliquots_in_bottle = 0  # reset aliquot counter to zero
            bottle_num = gp_bottle_num
            print("New Bottle!")
            print("Previous bottle number: " + '%.0f' % bottle_num)
            print("New bottle number: " + '%.0f' % gp_bottle_num)
            print("................Aliquots in bottle: " + "%.0f" % aliquots_in_bottle)
            print("................Volume in bottle: " + "%.0f" % vol_in_bottle + "mL")

        else:
            print("No bottle change...Current Bottle number: " + '%.0f' % bottle_num)
            print("................Aliquots in bottle: " + "%.0f" % aliquots_in_bottle)
            print("................Volume in bottle: " + "%.0f" % vol_in_bottle + "mL")
            # bottle number should always be whatever is in the GP variable

    return float(vol_pacing_cf), bottle_num # return new pacing volume and bottle number to main function

def bottle_and_pacing_change(bottle_num, pacing_input):
    """
    Updates the bottle number (composite) and resets aliquot counts etc
    :return:
    """
    global aliquots_in_bottle
    global vol_in_bottle

    # Update global values
    vol_pacing_cf = float(pacing_input)

    aliquots_in_bottle = 0.
    vol_in_bottle = 0.0

    print("Pacing changed! New Pacing: " + "%.0f"%vol_pacing_cf + "cf")
    print("................New Bottle number: "+ "%.0f" % bottle_num) #input from gp variable
    print("................Aliquots in bottle: " + "%.0f" %aliquots_in_bottle)
    print("................Volume in bottle: " + "%.0f" % vol_in_bottle +"mL")
    print("")


    # write a log entry
    event_label = "BottleChange"+" NewPacing: "+"%.0f"%vol_pacing_cf+"cf  NewBottle: "+ "%.0f" % bottle_num
    reading = Reading(label=event_label, time=utime.time(),
                      etype='E', value=bottle_num,right_digits=0)
    reading.write_log()

    return bottle_num, vol_pacing_cf


def trigger_sampler():
    """
    Call to attempt to trigger the sampler.
    Certain conditions may prevent the triggering.

    :return: True if sampler was triggered.
    """
    global bottle_capacity
    global aliquots_in_bottle
    global time_last_sample

    trigger = True

    # DO NOT SAMPLE conditions
    # if aliquots_in_bottle >= bottle_capacity:
    #     trigger = False  # out of capacity - won't overfill bottle
    # elif is_being_tested():
    #     trigger = False  # script is being tested
    # elif setup_read("Recording").upper() == "OFF":
    #     trigger = False  # if recording is off, do not sample

    # If conditions are met, then trigger the sampler
    if trigger:
        trigger_sampler_master()  # Call routine that controls sampler.
        return True

    else:
        return False  # Sampler was NOT triggered.

def trigger_sampler_master():
    """Triggers the sampler immediately and logs it."""

    global aliquots_in_bottle
    global vol_in_bottle
    global aliquot_vol_mL
    global time_last_sample

    # increment the number of bottles used
    aliquots_in_bottle += 1
    vol_in_bottle = vol_in_bottle + aliquot_vol_mL

    # update the time of the last trigger
    time_last_sample = utime.time()

    # trigger sampler by pulsing output for 5 seconds
    power_control('SW1', True)
    utime.sleep(0.5)
    power_control('SW1', False)

    # write a log entry
    t = utime.localtime(time_scheduled())
    day, minute = str(t[2]), str(t[4])
    if len(day) == 1:
        day = '0'+day
    if len(minute) == 1:
        minute = '0'+minute
    sample_time= str(t[1])+'/'+day+'/'+str(t[0])+' ' +str(t[3])+':'+minute

    reading = Reading(label="Triggered Sampler", time=time_scheduled(),
                      etype='E', value=aliquots_in_bottle,
                      right_digits=0, quality='G') # 'E' = event, 'M' = measurement, 'D' = debug
    reading.write_log()

    ## Write display log entries
    global sample_log
    global bottle_num
    global vol_pacing_cf

    sample_log[sample_time] = {'PacingVol':'%.0f'%vol_pacing_cf,'Bottle#':str(int(bottle_num)),'Aliquot#':str(int(aliquots_in_bottle)),'SampleTime':sample_time}
    return

## Can be used with digital output
# def trigger_sampler_digital():
#     """ Function triggers DOUT2 for two seconds in order to trigger a sampler"""
#     output_control('OUTPUT2', True)
#     utime.sleep(2.0)
#     output_control('OUTPUT2', False)


@MEASUREMENT
def rating_table(stage_in):
    """
    Given stage reading, this script will find the closest stage/discharge pair in
    rating table that is less than the input stage reading, and then perform a linear
    interpolation on the discharge values on either side of the stage reading to
    determine the discharge value at the current stage. For example, a stage value
    of 4" would output 32.0 CFS discharge because 4 is between (3, 22) and (5, 42).

    User will need to define the values for the rating table based on their application.
    The example below assumes an input stage value in inches and outputs discharge in cubic feet
    per second (CFS).

    To configure this script, attach this function to a Stage measurement
    or second meta referring to stage and make sure your stage units match your rating
    table stage values.
    """
    # stage, flow pairs
    STAGETBL = ((0.0, 0.0),
                (1.53, 0.25),
                (1.91, 0.5),
                (2.22, 0.75),
                (2.5, 1.0),
                (2.73, 1.25),
                (2.92, 1.5),
                (3.1, 1.75),
                (3.26, 2.0),
                (3.58, 2.5),
                (3.87, 3.0),
                (4.14, 3.5),
                (4.35, 4.0),
                (4.57, 4.5),
                (4.81, 5.0),
                (5.01, 5.5),
                (5.2, 6.0),
                (5.39, 6.5),
                (5.55, 7.0),
                (5.73, 7.5),
                (5.9, 8.0),
                (6.05, 8.5),
                (6.2, 9.0),
                (6.35, 9.5),
                (6.49, 10.0),
                (6.63, 10.5),
                (6.76, 11.0),
                (6.9, 11.5),
                (7.07, 12.0),
                (7.2, 12.5),
                (7.32, 13.0),
                (7.42, 13.5),
                (7.54, 14.0),
                (7.65, 14.5),
                (7.81, 15.0),
                (7.91, 15.5),
                (8.02, 16.0),
                (8.12, 16.5),
                (8.23, 17.0),
                (8.33, 17.5),
                (8.43, 18.0),
                (8.53, 18.5),
                (8.62, 19.0),
                (8.72, 19.5),
                (8.81, 20.0),
                (8.91, 20.5),
                (9.01, 21.0),
                (9.1, 21.5),
                (9.19, 22.0),
                (9.28, 22.5),
                (9.37, 23.0),
                (9.46, 23.5),
                (9.56, 24.0),
                (9.63, 24.5),
                (9.71, 25.0),
                (9.79, 25.5),
                (9.87, 26.0),
                (9.96, 26.5),
                (10.04, 27.0),
                (10.11, 27.5),
                (10.19, 28.0),
                (10.26, 28.5),
                (10.34, 29.0),
                (10.41, 29.5),
                (10.48, 30.0),
                (10.63, 31.0),
                (10.77, 32.0),
                (10.91, 33.0),
                (11.05, 34.0),
                (11.15, 35.0),
                (11.29, 36.0),
                (11.42, 37.0),
                (11.54, 38.0),
                (11.67, 39.0),
                (11.79, 40.0),
                (11.91, 41.0),
                (12.03, 42.0),
                (12.15, 43.0),
                (12.27, 44.0),
                (12.39, 45.0),
                (12.5, 46.0),
                (12.65, 47.0),
                (12.76, 48.0),
                (12.87, 49.0),
                (12.98, 50.0),
                (13.09, 51.0),
                (13.2, 52.0),
                (13.31, 53.0),
                (13.42, 54.0),
                (13.52, 55.0),
                (13.63, 56.0),
                (13.73, 57.0),
                (13.84, 58.0),
                (13.94, 59.0),
                (14.04, 60.0),
                (14.14, 61.0),
                (14.23, 62.0),
                (14.33, 63.0),
                (14.43, 64.0),
                (14.52, 65.0),
                (14.62, 66.0),
                (14.71, 67.0),
                (14.81, 68.0),
                (14.9, 69.0),
                (14.99, 70.0),
                (15.08, 71.0),
                (15.18, 72.0),
                (15.27, 73.0),
                (15.36, 74.0),
                (15.45, 75.0),
                (15.54, 76.0),
                (15.63, 77.0),
                (15.71, 78.0),
                (15.8, 79.0),
                (15.89, 80.0),
                (15.98, 81.0),
                (16.06, 82.0),
                (16.15, 83.0),
                (16.24, 84.0),
                (16.32, 85.0),
                (16.41, 86.0),
                (16.49, 87.0),
                (16.57, 88.0),
                (16.66, 89.0),
                (16.74, 90.0),
                (16.82, 91.0),
                (16.91, 92.0),
                (16.99, 93.0),
                (17.07, 94.0),
                (17.15, 95.0),
                (17.23, 96.0),
                (17.31, 97.0),
                (17.39, 98.0),
                (17.47, 99.0),
                (17.55, 100.0),
                (17.63, 101.0),
                (17.71, 102.0),
                (17.78, 103.0),
                (17.86, 104.0),
                (17.94, 105.0),
                (18.02, 106.0),
                (18.09, 107.0),
                (18.17, 108.0),
                (18.25, 109.0),
                (18.32, 110.0),
                (18.4, 111.0),
                (18.47, 112.0),
                (18.55, 113.0),
                (18.62, 114.0),
                (18.7, 115.0),
                (18.77, 116.0),
                (18.84, 117.0),
                (18.91, 118.0),
                (18.98, 119.0),
                (19.06, 120.0),
                (19.13, 121.0),
                (19.2, 122.0),
                (19.27, 123.0),
                (19.34, 124.0),
                (19.41, 125.0),
                (19.48, 126.0),
                (19.55, 127.0),
                (19.62, 128.0),
                (19.69, 129.0),
                (19.76, 130.0),
                (19.83, 131.0),
                (19.89, 132.0),
                (19.96, 133.0),
                (20.03, 134.0),
                (20.1, 135.0),
                (20.17, 136.0),
                (20.23, 137.0),
                (20.3, 138.0),
                (20.37, 139.0),
                (20.44, 140.0),
                (20.51, 141.0),
                (20.58, 142.0),
                (20.64, 143.0),
                (20.71, 144.0),
                (20.77, 145.0),
                (20.84, 146.0),
                (20.9, 147.0),
                (20.97, 148.0),
                (21.04, 149.0),
                (21.1, 150.0),
                (21.42, 155.0),
                (21.74, 160.0),
                (22.05, 165.0),
                (22.36, 170.0),
                (22.66, 175.0),
                (22.96, 180.0),
                (23.25, 185.0),
                (23.55, 190.0),
                (23.83, 195.0),
                (24.12, 200.0),
                (24.4, 205.0),
                (24.68, 210.0),
                (24.95, 215.0),
                (25.22, 220.0),
                (25.49, 225.0),
                (25.75, 230.0),
                (26.02, 235.0),
                (26.28, 240.0),
                (26.53, 245.0),
                (26.79, 250.0),
                (27.04, 255.0),
                (27.29, 260.0),
                (27.54, 265.0),
                (27.77, 270.0),
                (28.02, 275.0),
                (28.26, 280.0),
                (28.49, 285.0),
                (28.73, 290.0),
                (28.96, 295.0),
                (29.19, 300.0),
                (29.42, 305.0),
                (29.65, 310.0),
                (29.88, 315.0),
                (30.06, 319.0),
                (30.1, 320.0),
                (30.31, 325.0),
                (30.54, 330.0),
                (30.76, 335.0),
                (30.98, 340.0),
                (31.2, 345.0),
                (31.41, 350.0),
                (31.63, 355.0),
                (31.84, 360.0),
                (32.05, 365.0),
                (32.26, 370.0),
                (32.47, 375.0),
                (32.67, 380.0),
                (32.88, 385.0),
                (33.08, 390.0),
                (33.28, 395.0),
                (33.49, 400.0),
                (33.87, 410.0),
                (34.27, 420.0),
                (34.66, 430.0),
                (35.04, 440.0),
                (35.42, 450.0),
                (35.8, 460.0),
                (36.17, 470.0),
                (36.54, 480.0),
                (36.91, 490.0),
                (37.27, 500.0),
                (37.63, 510.0),
                (37.98, 520.0),
                (38.33, 530.0),
                (38.68, 540.0),
                (39.03, 550.0),
                (39.37, 560.0),
                (39.71, 570.0),
                (40.05, 580.0),
                (40.39, 590.0),
                (40.72, 600.0),
                (41.37, 620.0),
                (42.02, 640.0),
                (42.66, 660.0),
                (43.28, 680.0),
                (43.9, 700.0),
                (44.5, 720.0),
                (45.1, 740.0),
                (45.7, 760.0),
                (46.28, 780.0),
                (46.86, 800.0),
                (47.43, 820.0),
                (48.0, 840.0),
                (48.55, 860.0),
                (49.1, 880.0),
                (51.08, 900.0),
                (51.57, 920.0),
                (52.05, 940.0),
                (52.51, 960.0),
                (53.0, 980.0),
                (53.5, 1000.0),
                (53.98, 1020.0),
                (54.46, 1040.0),
                (54.92, 1060.0),
                (55.37, 1080.0),
                (55.82, 1100.0),
                (56.25, 1120.0),
                (56.67, 1140.0),
                (57.09, 1160.0),
                (57.29, 1170.0),
                (57.5, 1180.0),
                (57.89, 1200.0),
                (61.4, 1400.0),
                (64.2, 1600.0),
                (66.35, 1800.0),
                (80.7, 2000.0),
                (81.89, 2170.0),
                (86.27, 2400.0),
                (91.37, 2600.0),
                (95.04, 2800.0),
                (98.6, 3000.0),
                (101.92, 3200.0),
                (108.54, 3600.0),
                (108.84, 3800.0),
                (109.41, 3870.0),
                (110.56, 4000.0),
                (114.94, 4500.0),
                (118.54, 5000.0),
                (121.94, 5490.0),
                (125.63, 6000.0),
                (128.56, 6500.0),
                (131.51, 7000.0),
                (133.21, 7350.0),
                (136.79, 8000.0),
                (139.07, 8500.0),
                (141.62, 9000.0),
                (144.22, 9580.0),
                (146.07, 10000.0),
                (150.58, 11000.0),
                (154.54, 12000.0),
                (156.93, 12600.0))
    # Test for out of bounds stage values
    if stage_in < STAGETBL[0][0]:  # below
        flow_cfs = STAGETBL[0][0]
    elif stage_in > STAGETBL[-1][0]:  # above
        flow_cfs = -99.99
    else:
        # use for loop to walk through flow (discharge) table
        for flow_match in range(len(STAGETBL)):
            if stage_in < STAGETBL[flow_match][0]:
                break
        flow_match -= 1  # first pair
        # compute linear interpolation
        a_flow1 = STAGETBL[flow_match][1]
        b_diff_stage = stage_in - STAGETBL[flow_match][0]
        c_stage2 = STAGETBL[flow_match + 1][0]
        d_stage1 = STAGETBL[flow_match][0]
        e_flow2 = STAGETBL[flow_match + 1][1]
        flow_cfs = a_flow1 + (b_diff_stage / (c_stage2 - d_stage1)) * (e_flow2 - a_flow1)
    print ("")
    print("Stage: {}".format("%.2f" % stage_in) + ' in')
    print("Flow: {}".format("%.3f"%flow_cfs) +' cfs')
    print("")
    return flow_cfs

@MEASUREMENT
def compute_volume_total(flow_cfs):
    """
    This function needs to be associated with the total volume measurement.
    It will compute the total volume based on the current flow rate and past volume.
    The script will trigger the sampler if appropriate.

    :param flow: current flow rate
    :return: the current volume reading

    """
    global sampling_on
    global vol_pacing_cf
    global g_volume_total
    global aliquots_in_bottle
    global bottle_capacity
    global bottle_num
    global aliquot_vol_mL

    gp_sampling_on = gp_read_value_by_label("sampling_on")
    sampling_on = sample_on_true_or_false(gp_sampling_on)


    # Aliquot volume
    aliquot_vol_mL = gp_read_value_by_label("aliquot_vol_mL")

    # The container can hold a maximum number of aliquots
    bottle_size_L = gp_read_value_by_label("bottle_size_L")
    # aliquots; 19L / 250mL = 76
    bottle_capacity = bottle_size_L / (aliquot_vol_mL/1000)

    if sampling_on == False:
        print ('Sampling is OFF')
        print('Flow:' + "%.2f" % flow_cfs + 'cfs')
        print ("Current bottle number: "+"%.0f"%bottle_num)
        print ("Current pacing: "+"%.0f"%vol_pacing_cf)
        print("Aliquots in bottle: " + "%.0f"%aliquots_in_bottle)
        print("Bottle capacity: " + "%.0f"%bottle_capacity)


    elif sampling_on == True:
        print ('sampling is ON')
        # Measurement is at 1 minute, flow in cfs * 60 sec = cfm
        # flow = measure("Flow_cfs", READING_LAST).value  # what is the current flow rate?
        incremental_vol = flow_cfs * 60. # cfs x 60 sec = cf per minute
        # Add to running total volume
        g_volume_total = g_volume_total + incremental_vol # cf per minute, at minute intervals just total up

        print('Flow:' + "%.2f" % flow_cfs + 'cfs', '  IncrVol:' + "%.2f" % incremental_vol + 'cf',
              '  TotalVol:' + "%.2f" % g_volume_total + 'cf')

        # Pacing - check pacing, if it's different this function will update everything
        pacing_vol, bottle_num = get_volume_pacing()


        # update total volume and store it in a local variable
        # in case we need to clear g_volume_total
        #if is_scheduled():  # do not tally volume unless this is a scheduled measurement
            #g_volume_total += incremental_vol  # update total volume

        local_total = g_volume_total  # copy to a local variable

        # if the running total volume is higher than pacing volume, trigger sampler
        if local_total >= pacing_vol:
            if trigger_sampler():
                # sampler was triggered
                # Write a log entry indicating why sampler was triggered.
                reading = Reading(label="VolumeTrig", time=time_scheduled(),
                                  etype='E', value=local_total, quality='G')
                reading.write_log()

                # get remaining volume and keep in running total
                g_volume_total = g_volume_total - pacing_vol
        #print ('Flow:'+"%.2f"%flow_cfs+'cfs', 'IncrVol:'+"%.2f"%incremental_vol+'cf', 'TotalVol:'+"%.2f"%g_volume_total+'cf')
        # add diagnostic info to the script status
        print ("Current bottle number: "+"%.0f"%bottle_num)
        print ("Current pacing: "+"%.0f"%pacing_vol)
        print("Aliquots in bottle: " + "%.0f"%aliquots_in_bottle)
        print("Bottle capacity: " + "%.0f"%bottle_capacity)

    if time_last_sample:
        print("Last trigger: {}".format(ascii_time(time_last_sample)))
    else:
        print("Not triggered since bootup")

    # Display log of samples taken
    global sample_log
    print ('Sample Log: ')
    for k in sorted(sample_log):
        print(sample_log[k])

    return g_volume_total  # return the total volume (before clearing it)

@MEASUREMENT
def current_pacing(input):
    global vol_pacing_cf
    print ('Current flow pacing: '+str(vol_pacing_cf))
    return vol_pacing_cf

@MEASUREMENT
def number_of_aliquots(input):
    global aliquots_in_bottle
    print ('Number of aliquots in bottle: '+str(aliquots_in_bottle))
    return aliquots_in_bottle
@TASK
def alarm_in_fast():
    # Up the sampling interval when in alarm
    """script task should be setup when system goes into alarms to increase meas and tx rate"""
    setup_write("!M1 meas interval", "00:01:00")
    setup_write("!M4 meas interval", "00:01:00")
    setup_write("!M7 meas interval", "00:01:00")

    print("Setup changed to log at 1 minute interval (FAST)")

    # Start sampling when level triggered
    gp_write_value_by_label("sampling_on",1) # 1=True

    ## Reset all params for start of event
    global g_volume_total
    global bottle_num
    global aliquots_in_bottle
    global vol_in_bottle

    g_volume_total = 0.0
    bottle_num = 1
    aliquots_in_bottle = 0
    vol_in_bottle = 0
    return

@TASK
def alarm_out_slow():
    # Don't forget to set back when out of alarm
    """script task should be setup when system goes out of alarms to slow meas and tx rate"""
    setup_write("!M1 meas interval", "00:05:00")
    setup_write("!M4 meas interval", "00:05:00")
    setup_write("!M7 meas interval", "00:05:00")
    print ("Setup changed to log at 5 minute interval (SLOW)")

    # Stop sampling when level triggered
    gp_write_value_by_label("sampling_on",0) # 0=False
    return

@TASK
def turn_on_sampling():
    print("Manually started sampling!")

    # Start sampling when level triggered
    gp_write_value_by_label("sampling_on", 1)  # 1=True

    ## Reset all params for start of event
    global g_volume_total
    global bottle_num
    global aliquots_in_bottle
    global vol_in_bottle

    g_volume_total = 0.0
    bottle_num = 1
    aliquots_in_bottle = 0
    vol_in_bottle = 0
    return

@TASK
def turn_off_sampling():
    print ("Manually stop sampling")
    # Stop sampling when level triggered
    gp_write_value_by_label("sampling_on", 0)  # 0=False

@TASK
def reset_sampling_params():
    print("Manually reset sampling parameters!")

    # Start sampling when level triggered
    gp_write_value_by_label("sampling_on", 0)  # 0=False

    ## Reset all params for start of event
    global g_volume_total
    global bottle_num
    global aliquots_in_bottle
    global vol_in_bottle

    g_volume_total = 0.0
    bottle_num = 1
    aliquots_in_bottle = 0
    vol_in_bottle = 0
    return




