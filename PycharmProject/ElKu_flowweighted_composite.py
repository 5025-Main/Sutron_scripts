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
                (0.12, 3.56),
                (0.24, 11.33),
                (0.36, 22.34),
                (0.48, 36.21),
                (0.6, 52.74),
                (0.72, 71.78),
                (0.84, 93.25),
                (0.96, 117.06),
                (1.08, 143.19),
                (1.2, 171.59),
                (1.32, 202.25),
                (1.44, 235.15),
                (1.56, 270.29),
                (1.68, 307.65),
                (1.8, 347.25),
                (1.92, 389.09),
                (2.04, 433.17),
                (2.16, 479.5),
                (2.28, 528.1),
                (2.4, 578.99),
                (2.52, 632.16),
                (2.64, 687.65),
                (2.76, 745.46),
                (2.88, 805.62),
                (3.0, 868.14),
                (3.12, 933.04),
                (3.24, 1000.35),
                (3.36, 1070.07),
                (3.48, 1142.24),
                (3.6, 1216.87),
                (3.72, 1293.98),
                (3.84, 1373.59),
                (3.96, 1455.73),
                (4.08, 1540.42),
                (4.2, 1627.67),
                (4.32, 1717.52),
                (4.44, 1809.97),
                (4.56, 1905.07),
                (4.68, 2002.82),
                (4.8, 2103.24),
                (4.92, 2206.38),
                (5.04, 2312.23),
                (5.16, 2420.83),
                (5.28, 2532.2),
                (5.4, 2646.36),
                (5.52, 2763.33),
                (5.64, 2883.14),
                (5.76, 3005.81),
                (5.88, 3131.35),
                (6.0, 3259.8),
                (6.12, 3391.18),
                (6.24, 3525.5),
                (6.36, 3662.8),
                (6.48, 3803.08),
                (6.6, 3946.38),
                (6.72, 4092.72),
                (6.84, 4242.12),
                (6.96, 4394.59),
                (7.08, 4550.18),
                (7.2, 4708.88),
                (7.32, 4870.74),
                (7.44, 5035.76),
                (7.56, 5203.97),
                (7.68, 5375.4),
                (7.8, 5550.06),
                (7.92, 5727.98),
                (8.04, 5909.18),
                (8.16, 6093.67),
                (8.28, 6281.49),
                (8.4, 6472.66),
                (8.52, 6667.18),
                (8.64, 6865.1),
                (8.76, 7066.42),
                (8.88, 7271.17),
                (9.0, 7479.37),
                (9.12, 7691.05),
                (9.24, 7906.21),
                (9.36, 8124.89),
                (9.48, 8347.11),
                (9.6, 8572.88),
                (9.72, 8802.24),
                (9.84, 9035.19),
                (9.96, 9271.75),
                (10.08, 9511.96),
                (10.2, 9755.83),
                (10.32, 10003.39),
                (10.44, 10254.64),
                (10.56, 10509.62),
                (10.68, 10768.35),
                (10.8, 11030.83),
                (10.92, 11297.11),
                (11.04, 11567.19),
                (11.16, 11841.09),
                (11.28, 12118.84),
                (11.4, 12400.46),
                (11.52, 12685.97),
                (11.64, 12975.38),
                (11.76, 13268.72),
                (11.88, 13566.01),
                (12.0, 13867.27),
                (12.12, 14172.52),
                (12.24, 14481.77),
                (12.36, 14795.05),
                (12.48, 15112.38),
                (12.6, 15433.78),
                (12.72, 15759.26),
                (12.84, 16088.86),
                (12.96, 16422.58),
                (13.08, 16760.44),
                (13.2, 17102.48),
                (13.32, 17448.7),
                (13.44, 17799.13),
                (13.56, 18153.78),
                (13.68, 18512.67),
                (13.8, 18875.84),
                (13.92, 19243.28),
                (14.04, 19615.03),
                (14.16, 19991.1),
                (14.28, 20371.52),
                (14.4, 20756.29),
                (14.52, 21145.45),
                (14.64, 21539.0),
                (14.76, 21936.98),
                (14.88, 22339.39),
                (15.0, 22746.26),
                (15.12, 23157.6),
                (15.24, 23573.44),
                (15.36, 23993.79),
                (15.48, 24418.68),
                (15.6, 24848.12),
                (15.72, 25282.13),
                (15.84, 25720.72),
                (15.96, 26163.93),
                (16.08, 26611.76),
                (16.2, 27064.24),
                (16.32, 27521.38),
                (16.44, 27983.21),
                (16.56, 28449.74),
                (16.68, 28920.98),
                (16.8, 29396.97),
                (16.92, 29877.71),
                (17.04, 30363.23),
                (17.16, 30853.54),
                (17.28, 31348.66),
                (17.4, 31848.62),
                (17.52, 32353.42),
                (17.64, 32863.09),
                (17.76, 33377.65),
                (17.88, 33897.11),
                (18.0, 34421.49),
                (18.12, 34950.81),
                (18.24, 35485.09),
                (18.36, 36024.34),
                (18.48, 36568.59),
                (18.6, 37117.86),
                (18.72, 37672.15),
                (18.84, 38231.49),
                (18.96, 38795.9),
                (19.08, 39365.39),
                (19.2, 39939.98),
                (19.32, 40519.69),
                (19.44, 41104.54),
                (19.56, 41694.55),
                (19.68, 42289.72),
                (19.8, 42890.09),
                (19.92, 43495.67),
                (20.04, 44106.47),
                (20.16, 44722.52),
                (20.28, 45343.83),
                (20.4, 45970.42),
                (20.52, 46602.3),
                (20.64, 47239.5),
                (20.76, 47882.03),
                (20.88, 48529.91),
                (21.0, 49183.15))

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




