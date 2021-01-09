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
                (4.31, 0.25),
                (5.0, 0.5),
                (5.6, 0.75),
                (6.17, 1.0),
                (6.64, 1.25),
                (7.12, 1.5),
                (7.56, 1.75),
                (8.03, 2.0),
                (8.42, 2.25),
                (8.84, 2.5),
                (9.2, 2.75),
                (9.57, 3.0),
                (9.93, 3.25),
                (10.73, 4.25),
                (10.97, 4.5),
                (11.21, 4.75),
                (11.44, 5.0),
                (11.67, 5.25),
                (11.9, 5.5),
                (12.12, 5.75),
                (12.34, 6.0),
                (12.55, 6.25),
                (12.76, 6.5),
                (12.97, 6.75),
                (13.18, 7.0),
                (13.39, 7.25),
                (13.59, 7.5),
                (13.79, 7.75),
                (13.99, 8.0),
                (14.18, 8.25),
                (14.38, 8.5),
                (14.65, 8.75),
                (14.76, 9.0),
                (14.95, 9.25),
                (15.14, 9.5),
                (15.32, 9.75),
                (15.51, 10.0),
                (15.69, 10.25),
                (15.87, 10.5),
                (16.05, 10.75),
                (16.23, 11.0),
                (16.4, 11.25),
                (16.58, 11.5),
                (16.75, 11.75),
                (16.92, 12.0),
                (17.1, 12.25),
                (17.27, 12.5),
                (17.44, 12.75),
                (17.6, 13.0),
                (14.48, 13.25),
                (14.6, 13.5),
                (17.93, 13.75),
                (18.09, 14.0),
                (18.24, 14.25),
                (18.4, 14.5),
                (18.55, 14.75),
                (18.7, 15.0),
                (18.85, 15.25),
                (19.0, 15.5),
                (19.15, 15.75),
                (19.3, 16.0),
                (19.45, 16.25),
                (19.6, 16.5),
                (19.74, 16.75),
                (19.89, 17.0),
                (20.04, 17.25),
                (20.18, 17.5),
                (20.32, 17.75),
                (20.47, 18.0),
                (20.61, 18.25),
                (20.75, 18.5),
                (20.89, 18.75),
                (21.03, 19.0),
                (21.17, 19.25),
                (21.31, 19.5),
                (21.44, 19.75),
                (21.58, 20.0),
                (21.84, 20.5),
                (22.03, 21.0),
                (22.31, 21.5),
                (22.54, 22.0),
                (22.76, 22.5),
                (22.97, 23.0),
                (23.18, 23.5),
                (23.38, 24.0),
                (23.47, 24.5),
                (23.66, 25.0),
                (23.84, 25.5),
                (24.01, 26.0),
                (24.19, 26.5),
                (24.35, 27.0),
                (24.54, 27.5),
                (24.58, 28.0),
                (24.8, 28.5),
                (25.01, 29.0),
                (25.22, 29.5),
                (25.28, 30.0),
                (25.5, 30.5),
                (25.55, 31.0),
                (25.67, 31.5),
                (25.81, 32.0),
                (25.98, 32.5),
                (26.18, 33.0),
                (26.34, 33.5),
                (26.5, 34.0),
                (26.61, 34.5),
                (26.77, 35.0),
                (26.9, 35.5),
                (27.02, 36.0),
                (27.15, 36.5),
                (27.27, 37.0),
                (27.39, 37.5),
                (27.52, 38.0),
                (27.65, 38.5),
                (27.77, 39.0),
                (27.89, 39.5),
                (28.02, 40.0),
                (28.14, 40.5),
                (28.27, 41.0),
                (28.39, 41.5),
                (28.51, 42.0),
                (28.76, 42.5),
                (28.84, 43.0),
                (28.93, 43.5),
                (29.01, 44.0),
                (29.1, 44.5),
                (29.18, 45.0),
                (29.26, 45.5),
                (29.34, 46.0),
                (29.42, 46.5),
                (29.66, 47.0),
                (29.77, 47.5),
                (29.88, 48.0),
                (29.88, 48.5),
                (30.0, 49.0),
                (30.09, 49.5),
                (30.19, 50.0),
                (30.49, 51.0),
                (30.7, 52.0),
                (30.9, 53.0),
                (31.1, 54.0),
                (31.3, 55.0),
                (31.5, 56.0),
                (31.69, 57.0),
                (31.88, 58.0),
                (32.07, 59.0),
                (32.12, 60.0),
                (32.3, 61.0),
                (32.48, 62.0),
                (32.65, 63.0),
                (32.83, 64.0),
                (33.0, 65.0),
                (33.17, 66.0),
                (33.32, 67.0),
                (33.75, 68.0),
                (33.83, 69.0),
                (33.94, 70.0),
                (34.0, 71.0),
                (34.11, 72.0),
                (34.24, 73.0),
                (34.39, 74.0),
                (34.55, 75.0),
                (34.69, 76.0),
                (34.84, 77.0),
                (34.99, 78.0),
                (35.14, 79.0),
                (35.29, 80.0),
                (35.43, 81.0),
                (35.58, 82.0),
                (35.72, 83.0),
                (35.86, 84.0),
                (36.01, 85.0),
                (36.21, 86.0),
                (36.29, 87.0),
                (36.49, 88.0),
                (36.64, 89.0),
                (36.79, 90.0),
                (36.93, 91.0),
                (37.07, 92.0),
                (37.21, 93.0),
                (37.34, 94.0),
                (37.48, 95.0),
                (37.61, 96.0),
                (37.75, 97.0),
                (37.88, 98.0),
                (38.01, 99.0),
                (38.14, 100.0),
                (38.28, 101.0),
                (38.41, 102.0),
                (38.54, 103.0),
                (38.67, 104.0),
                (38.79, 105.0),
                (38.92, 106.0),
                (38.99, 107.0),
                (39.2, 108.0),
                (39.32, 109.0),
                (39.45, 110.0),
                (39.58, 111.0),
                (39.7, 112.0),
                (39.83, 113.0),
                (39.96, 114.0),
                (40.11, 115.0),
                (40.2, 116.0),
                (40.31, 117.0),
                (40.42, 118.0),
                (40.54, 119.0),
                (40.66, 120.0),
                (40.78, 121.0),
                (41.08, 123.0),
                (41.24, 124.0),
                (41.25, 125.0),
                (41.37, 126.0),
                (41.49, 127.0),
                (41.61, 128.0),
                (41.72, 129.0),
                (41.93, 130.0),
                (42.07, 131.0),
                (42.2, 132.0),
                (42.34, 133.0),
                (42.49, 134.0),
                (42.62, 135.0),
                (42.71, 136.0),
                (42.89, 137.0),
                (43.02, 138.0),
                (43.15, 139.0),
                (43.23, 140.0),
                (43.34, 141.0),
                (43.47, 142.0),
                (43.6, 143.0),
                (43.77, 144.0),
                (43.9, 145.0),
                (44.03, 146.0),
                (44.16, 147.0),
                (44.29, 148.0),
                (44.41, 149.0),
                (44.56, 150.0),
                (44.69, 151.0),
                (44.82, 152.0),
                (44.94, 153.0),
                (45.05, 154.0),
                (45.15, 155.0),
                (45.25, 156.0),
                (45.36, 157.0),
                (45.47, 158.0),
                (45.58, 159.0),
                (45.69, 160.0),
                (45.81, 161.0),
                (45.92, 162.0),
                (46.03, 163.0),
                (46.1, 164.0),
                (46.22, 165.0),
                (46.33, 166.0),
                (46.44, 167.0),
                (46.55, 168.0),
                (46.66, 169.0),
                (46.77, 170.0),
                (46.88, 171.0),
                (47.08, 172.0),
                (47.2, 173.0),
                (47.3, 174.0),
                (47.4, 175.0),
                (47.56, 176.0),
                (47.7, 177.0),
                (47.85, 178.0),
                (47.98, 179.0),
                (48.12, 180.0),
                (48.25, 181.0),
                (48.4, 182.0),
                (48.56, 183.0),
                (48.71, 184.0),
                (48.85, 185.0),
                (48.99, 186.0),
                (49.12, 187.0),
                (49.26, 188.0),
                (49.41, 189.0),
                (49.56, 190.0),
                (49.72, 191.0),
                (49.84, 192.0),
                (49.96, 193.0),
                (50.1, 194.0),
                (50.23, 195.0),
                (50.4, 196.0),
                (50.5, 197.0),
                (50.68, 230.0),
                (51.24, 235.0),
                (51.81, 240.0),
                (52.37, 245.0),
                (52.94, 250.0),
                (53.5, 255.0),
                (53.85, 260.0),
                (54.25, 265.0),
                (54.75, 270.0),
                (55.22, 275.0),
                (55.68, 280.0),
                (56.79, 285.0),
                (57.75, 290.0),
                (58.05, 295.0),
                (58.39, 300.0),
                (59.04, 310.0),
                (59.64, 320.0),
                (60.22, 330.0),
                (60.66, 340.0),
                (61.19, 350.0),
                (61.61, 360.0),
                (62.04, 370.0),
                (62.33, 380.0),
                (62.81, 390.0),
                (63.16, 400.0),
                (63.74, 410.0),
                (63.99, 480.0),
                (64.25, 490.0),
                (65.62, 500.0),
                (65.75, 510.0),
                (65.91, 520.0),
                (65.98, 530.0),
                (66.15, 540.0),
                (66.3, 550.0),
                (66.51, 560.0),
                (66.82, 580.0),
                (66.88, 582.0),
                (67.2, 590.0),
                (67.26, 600.0),
                (67.74, 620.0),
                (67.96, 640.0),
                (68.4, 660.0),
                (68.93, 680.0),
                (69.44, 700.0),
                (70.62, 800.0),
                (71.54, 900.0),
                (72.41, 1000.0),
                (73.41, 1200.0),
                (78.79, 2400.0),
                (80.86, 2600.0),
                (83.79, 2890.0),
                (84.82, 3000.0),
                (86.62, 3200.0),
                (88.29, 3400.0),
                (90.06, 3630.0),
                (91.33, 3800.0),
                (92.75, 4000.0),
                (94.22, 4200.0),
                (95.54, 4400.0),
                (96.7, 4580.0))
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




