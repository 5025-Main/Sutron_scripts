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
                (0.13, 0.25),
                (0.2, 0.5),
                (0.27, 0.75),
                (0.32, 1.0),
                (0.37, 1.25),
                (0.42, 1.5),
                (0.47, 1.75),
                (0.51, 2.0),
                (0.55, 2.25),
                (0.59, 2.5),
                (0.63, 2.75),
                (0.67, 3.0),
                (0.71, 3.25),
                (0.74, 3.5),
                (0.78, 3.75),
                (0.81, 4.0),
                (0.85, 4.25),
                (0.88, 4.5),
                (0.91, 4.75),
                (0.94, 5.0),
                (0.97, 5.25),
                (1.01, 5.5),
                (1.04, 5.75),
                (1.07, 6.0),
                (1.15, 6.75),
                (1.18, 7.0),
                (1.21, 7.25),
                (1.24, 7.5),
                (1.26, 7.75),
                (1.29, 8.0),
                (1.32, 8.25),
                (1.34, 8.5),
                (1.37, 8.75),
                (1.4, 9.0),
                (1.42, 9.25),
                (1.45, 9.5),
                (1.47, 9.75),
                (1.5, 10.0),
                (1.52, 10.25),
                (1.55, 10.5),
                (1.57, 10.75),
                (1.6, 11.0),
                (1.67, 11.25),
                (1.79, 11.5),
                (1.91, 11.75),
                (2.03, 12.0),
                (2.14, 12.25),
                (2.25, 12.5),
                (2.36, 12.75),
                (2.47, 13.0),
                (2.58, 13.25),
                (2.69, 13.5),
                (2.79, 13.75),
                (2.9, 14.0),
                (3.0, 14.25),
                (3.11, 14.5),
                (3.21, 14.75),
                (3.31, 15.0),
                (3.41, 15.25),
                (3.5, 15.5),
                (3.6, 15.75),
                (3.7, 16.0),
                (3.79, 16.25),
                (3.89, 16.5),
                (3.99, 16.75),
                (4.08, 17.0),
                (4.17, 17.25),
                (4.26, 17.5),
                (4.35, 17.75),
                (4.44, 18.0),
                (4.53, 18.25),
                (4.62, 18.5),
                (4.7, 18.75),
                (4.79, 19.0),
                (4.87, 19.25),
                (4.96, 19.5),
                (5.04, 19.75),
                (5.12, 20.0),
                (5.29, 20.5),
                (5.45, 21.0),
                (5.61, 21.5),
                (5.76, 22.0),
                (5.92, 22.5),
                (6.07, 23.0),
                (6.22, 23.5),
                (6.37, 24.0),
                (6.56, 24.5),
                (6.7, 25.0),
                (6.84, 25.5),
                (6.97, 26.0),
                (7.11, 26.5),
                (7.24, 27.0),
                (7.38, 27.5),
                (7.51, 28.0),
                (7.64, 28.5),
                (7.78, 29.0),
                (7.9, 29.5),
                (8.03, 30.0),
                (8.16, 30.5),
                (8.28, 31.0),
                (8.4, 31.5),
                (8.56, 32.0),
                (8.64, 32.5),
                (8.76, 33.0),
                (8.88, 33.5),
                (8.99, 34.0),
                (9.11, 34.5),
                (9.22, 35.0),
                (9.34, 35.5),
                (9.45, 36.0),
                (9.57, 36.5),
                (9.68, 37.0),
                (9.8, 37.5),
                (9.91, 38.0),
                (10.02, 38.5),
                (10.13, 39.0),
                (10.24, 39.5),
                (10.35, 40.0),
                (10.56, 41.0),
                (10.77, 42.0),
                (10.98, 43.0),
                (11.19, 44.0),
                (11.39, 45.0),
                (11.59, 46.0),
                (11.79, 47.0),
                (11.98, 48.0),
                (12.16, 49.0),
                (12.35, 50.0),
                (12.54, 51.0),
                (12.73, 52.0),
                (12.91, 53.0),
                (13.12, 54.0),
                (13.29, 55.0),
                (13.46, 56.0),
                (13.62, 57.0),
                (13.78, 58.0),
                (13.98, 59.0),
                (14.12, 60.0),
                (14.27, 61.0),
                (14.43, 62.0),
                (14.59, 63.0),
                (14.79, 64.0),
                (14.95, 65.0),
                (15.1, 66.0),
                (15.26, 67.0),
                (15.41, 68.0),
                (15.56, 69.0),
                (15.71, 70.0),
                (15.87, 71.0),
                (16.02, 72.0),
                (16.16, 73.0),
                (16.31, 74.0),
                (16.46, 75.0),
                (16.6, 76.0),
                (16.74, 77.0),
                (16.88, 78.0),
                (17.02, 79.0),
                (17.16, 80.0),
                (17.3, 81.0),
                (17.43, 82.0),
                (17.57, 83.0),
                (17.71, 84.0),
                (17.84, 85.0),
                (17.97, 86.0),
                (18.11, 87.0),
                (18.24, 88.0),
                (18.37, 89.0),
                (18.5, 90.0),
                (18.63, 91.0),
                (18.76, 92.0),
                (18.89, 93.0),
                (19.01, 94.0),
                (19.14, 95.0),
                (19.26, 96.0),
                (19.37, 97.0),
                (19.49, 98.0),
                (19.61, 99.0),
                (19.72, 100.0),
                (19.83, 101.0),
                (24.83, 150.0),
                (29.25, 200.0),
                (33.26, 250.0),
                (36.92, 300.0),
                (38.78, 327.0),
                (40.31, 350.0),
                (43.45, 400.0),
                (46.41, 450.0),
                (49.2, 500.0),
                (51.12, 537.0),
                (51.78, 550.0),
                (54.23, 600.0),
                (56.55, 650.0),
                (58.76, 700.0),
                (60.84, 750.0),
                (62.86, 800.0),
                (64.18, 835.0),
                (64.74, 850.0),
                (66.59, 900.0),
                (68.38, 950.0),
                (70.13, 1000.0),
                (71.83, 1050.0),
                (73.16, 1090.0),
                (73.49, 1100.0),
                (76.72, 1200.0),
                (79.84, 1300.0),
                (81.67, 1360.0),
                (82.88, 1400.0),
                (85.88, 1500.0),
                (88.81, 1600.0),
                (90.49, 1660.0),
                (91.56, 1700.0),
                (94.2, 1800.0),
                (96.77, 1900.0),
                (99.22, 2000.0),
                (99.7, 2020.0))
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
                ## If incremental volume is still higher than pacing_vol

                if g_volume_total >= pacing_vol:
                    missed_samples = g_volume_total / pacing_vol
                    print ("Flow too high for pacing!!")
                    print ("Missed samples: " + float("%.2f%"%missed_samples))
                    g_volume_total = 0.

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
    vol_pacing_cf = gp_read_value_by_label("pacing_volume_cf")
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




