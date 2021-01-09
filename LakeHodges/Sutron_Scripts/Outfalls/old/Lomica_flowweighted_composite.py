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
                (0.19, 0.89),
                (0.21, 1.28),
                (0.23, 1.67),
                (0.26, 2.11),
                (0.28, 2.57),
                (0.3, 3.27),
                (0.32, 3.8),
                (0.35, 4.73),
                (0.37, 5.58),
                (0.4, 6.64),
                (0.43, 8.19),
                (0.46, 9.82),
                (0.49, 11.39),
                (0.52, 13.03),
                (0.54, 14.66),
                (0.56, 15.91),
                (0.58, 17.2),
                (0.59, 18.41),
                (0.61, 19.66),
                (0.63, 21.62),
                (0.65, 23.07),
                (0.68, 25.4),
                (0.7, 27.85),
                (0.72, 29.72),
                (0.75, 32.6),
                (0.76, 34.09),
                (0.79, 36.75),
                (0.81, 38.69),
                (0.82, 40.69),
                (0.84, 42.5),
                (0.85, 44.48),
                (0.87, 46.12),
                (0.88, 48.45),
                (0.9, 50.04),
                (0.91, 51.93),
                (0.92, 53.72),
                (0.94, 55.54),
                (0.95, 57.25),
                (0.96, 58.84),
                (0.97, 60.75),
                (0.98, 62.7),
                (1.0, 64.68),
                (1.01, 66.38),
                (1.02, 68.1),
                (1.03, 69.85),
                (1.05, 72.59),
                (1.06, 74.73),
                (1.07, 76.9),
                (1.09, 78.94),
                (1.1, 81.52),
                (1.11, 83.8),
                (1.13, 86.64),
                (1.15, 89.54),
                (1.16, 91.56),
                (1.17, 93.79),
                (1.18, 96.24),
                (1.2, 99.1),
                (1.21, 101.24),
                (1.22, 103.78),
                (1.23, 106.17),
                (1.25, 108.58),
                (1.26, 112.66),
                (1.28, 115.77),
                (1.29, 118.08),
                (1.31, 121.69),
                (1.32, 125.37),
                (1.34, 128.22),
                (1.35, 131.1),
                (1.36, 133.56),
                (1.38, 136.95),
                (1.39, 139.93),
                (1.4, 142.95),
                (1.42, 146.93),
                (1.44, 150.98),
                (1.45, 154.84),
                (1.47, 158.75),
                (1.49, 162.7),
                (1.5, 165.45),
                (1.51, 169.49),
                (1.53, 173.84),
                (1.54, 177.2),
                (1.55, 180.6),
                (1.57, 184.02),
                (1.59, 189.36),
                (1.61, 194.77),
                (1.62, 198.88),
                (1.64, 203.87),
                (1.66, 208.91),
                (1.67, 212.6),
                (1.69, 216.89),
                (1.7, 221.8),
                (1.72, 226.48),
                (1.74, 231.5),
                (1.75, 236.87),
                (1.77, 241.39),
                (1.78, 245.66),
                (1.8, 250.88),
                (1.82, 256.15),
                (1.83, 260.85),
                (1.85, 266.23),
                (1.87, 273.26),
                (1.89, 278.11),
                (1.91, 283.98),
                (1.93, 293.24),
                (1.95, 299.26),
                (1.97, 306.7),
                (1.99, 312.51),
                (2.0, 317.68),
                (2.02, 322.54),
                (2.04, 329.19),
                (2.05, 334.13),
                (2.07, 339.11),
                (2.08, 345.2),
                (2.1, 350.25),
                (2.11, 355.34),
                (2.12, 360.09),
                (2.14, 367.47),
                (2.17, 376.41),
                (2.19, 382.8),
                (2.2, 388.48),
                (2.22, 394.59),
                (2.23, 401.12),
                (2.25, 406.93),
                (2.26, 412.77),
                (2.28, 420.62),
                (2.3, 426.95),
                (2.31, 432.92),
                (2.33, 440.95),
                (2.36, 450.25),
                (2.38, 458.42),
                (2.4, 465.83),
                (2.41, 473.29),
                (2.44, 482.89),
                (2.45, 488.36),
                (2.46, 495.13),
                (2.48, 503.65),
                (2.51, 514.39),
                (2.53, 523.49),
                (2.55, 530.91),
                (2.57, 542.34),
                (2.59, 548.55),
                (2.62, 564.18),
                (2.64, 573.66),
                (2.67, 586.39),
                (2.71, 604.34),
                (2.72, 610.37),
                (2.75, 622.05),
                (2.79, 640.92),
                (2.81, 652.36),
                (2.85, 670.17),
                (2.9, 692.1),
                (2.93, 708.86),
                (2.97, 727.29),
                (3.0, 742.88),
                (3.03, 759.12),
                (3.06, 774.48),
                (3.1, 793.07),
                (3.14, 818.14),
                (3.19, 844.59),
                (3.23, 863.3),
                (3.27, 885.43),
                (3.33, 918.22),
                (3.37, 939.78),
                (3.43, 972.77),
                (3.48, 1005.62),
                (3.57, 1055.11),
                (3.61, 1076.09),
                (3.66, 1107.26),
                (3.7, 1130.41),
                (3.74, 1154.94),
                (3.8, 1189.97),
                (3.85, 1218.64),
                (3.91, 1257.45),
                (3.95, 1283.57),
                (3.99, 1309.26),
                (4.04, 1338.92),
                (4.1, 1377.12),
                (4.16, 1414.41),
                (4.18, 1430.59),
                (4.22, 1457.26),
                (4.31, 1513.75),
                (4.38, 1559.6),
                (4.42, 1587.05),
                (4.47, 1619.4),
                (4.49, 1637.01),
                (4.55, 1675.84),
                (4.57, 1692.97),
                (4.61, 1717.72),
                (4.65, 1743.29),
                (4.69, 1775.24),
                (4.73, 1800.37),
                (4.77, 1827.73),
                (4.79, 1846.04),
                (4.83, 1868.65),
                (4.85, 1887.8),
                (4.89, 1912.71),
                (4.92, 1932.71),
                (4.95, 1958.51),
                (4.98, 1975.78),
                (5.01, 2003.2),
                (5.04, 2018.41),
                (5.06, 2037.29),
                (5.09, 2055.49),
                (5.12, 2078.12),
                (5.15, 2099.36),
                (5.17, 2118.46),
                (5.2, 2136.87),
                (5.22, 2152.37),
                (5.26, 2181.99),
                (5.28, 2199.07),
                (5.32, 2229.62),
                (5.35, 2251.3),
                (5.38, 2269.29),
                (5.39, 2284.31),
                (5.42, 2299.36),
                (5.45, 2321.99),
                (5.49, 2352.25),
                (5.51, 2371.23),
                (5.54, 2393.29),
                (5.56, 2406.25),
                (5.58, 2426.87),
                (5.62, 2458.28),
                (5.65, 2477.48),
                (5.67, 2496.73),
                (5.72, 2530.7),
                (5.74, 2543.86),
                (5.76, 2560.92),
                (5.8, 2595.13),
                (5.84, 2622.42),
                (5.87, 2645.88),
                (5.91, 2678.81),
                (5.94, 2703.98),
                (5.96, 2723.68),
                (5.99, 2743.42),
                (6.03, 2773.49),
                (6.06, 2798.09),
                (6.08, 2818.76),
                (6.12, 2850.64),
                (6.17, 2882.62),
                (6.2, 2913.87),
                (6.25, 2953.27),
                (6.28, 2975.84),
                (6.31, 2997.64),
                (6.34, 3020.3),
                (6.39, 3064.92),
                (6.42, 3089.33),
                (6.45, 3115.41),
                (6.48, 3138.28),
                (6.51, 3159.55),
                (6.53, 3176.76),
                (6.58, 3217.81),
                (6.6, 3237.56),
                (6.64, 3268.07),
                (6.67, 3289.54),
                (6.68, 3305.26),
                (6.73, 3340.89),
                (6.76, 3369.96),
                (6.82, 3414.92),
                (6.84, 3434.95),
                (6.87, 3460.02),
                (6.9, 3488.48),
                (6.94, 3519.52),
                (6.98, 3548.93),
                (7.02, 3589.36),
                (7.06, 3618.06),
                (7.1, 3656.13),
                (7.15, 3696.82),
                (7.19, 3730.81),
                (7.22, 3752.09),
                (7.27, 3796.43),
                (7.3, 3825.49),
                (7.34, 3857.16),
                (7.38, 3891.46),
                (7.42, 3928.4),
                (7.48, 3975.77),
                (7.53, 4018.93),
                (7.59, 4075.18),
                (7.63, 4104.67),
                (7.66, 4134.2),
                (7.69, 4162.03),
                (7.73, 4196.88),
                (7.76, 4224.8),
                (7.81, 4266.75),
                (7.87, 4321.05),
                (7.91, 4355.28),
                (7.95, 4383.41),
                (8.01, 4436.24),
                (8.06, 4486.54),
                (8.13, 4544.93),
                (8.16, 4570.63),
                (8.23, 4638.11),
                (8.31, 4707.56),
                (8.4, 4783.46),
                (8.46, 4843.45),
                (8.51, 4882.02),
                (8.67, 5032.35),
                (8.79, 5134.53),
                (8.89, 5230.71),
                (9.06, 5385.6),
                (9.26, 5569.73),
                (9.4, 5693.98),
                (9.49, 5782.61),
                (9.68, 5954.95),
                (9.8, 6064.7),
                (9.99, 6248.63),
                (10.19, 6427.76),
                (10.46, 6686.04),
                (10.79, 6998.1),
                (11.04, 7242.3),
                (11.24, 7433.88),
                (11.62, 7796.79),
                (12.02, 8177.42),
                (13.13, 9264.7),
                (16.16, 12288.43))

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




