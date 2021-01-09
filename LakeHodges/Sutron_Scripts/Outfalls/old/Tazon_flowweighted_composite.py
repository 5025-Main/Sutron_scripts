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
                (0.1, 0.19),
                (0.2, 0.84),
                (0.3, 2.01),
                (0.4, 4.84),
                (0.5, 13.46),
                (0.6, 23.0),
                (0.7, 33.44),
                (0.8, 44.76),
                (0.9, 56.93),
                (1.0, 69.95),
                (1.1, 83.8),
                (1.2, 98.46),
                (1.3, 113.9),
                (1.4, 130.13),
                (1.5, 147.11),
                (1.6, 164.84),
                (1.7, 183.29),
                (1.8, 202.46),
                (1.9, 222.32),
                (2.0, 242.87),
                (2.1, 264.09),
                (2.2, 285.96),
                (2.3, 308.47),
                (2.4, 331.6),
                (2.5, 355.35),
                (2.6, 379.69),
                (2.7, 404.62),
                (2.8, 430.12),
                (2.9, 456.18),
                (3.0, 482.79),
                (3.1, 509.93),
                (3.2, 537.6),
                (3.3, 565.78),
                (3.4, 594.45),
                (3.5, 623.61),
                (3.6, 653.25),
                (3.7, 683.35),
                (3.8, 713.91),
                (3.9, 744.91),
                (4.0, 776.34),
                (4.1, 808.19),
                (4.2, 840.46),
                (4.3, 873.13),
                (4.4, 906.19),
                (4.5, 939.63),
                (4.6, 973.45),
                (4.7, 1007.63),
                (4.8, 1042.16),
                (4.9, 1077.04),
                (5.0, 1112.26),
                (5.1, 1147.8),
                (5.2, 1183.67),
                (5.3, 1219.84),
                (5.4, 1256.32),
                (5.5, 1293.09),
                (5.6, 1330.15),
                (5.7, 1367.49),
                (5.8, 1405.09),
                (5.9, 1442.96),
                (6.0, 1481.09),
                (6.1, 1519.46),
                (6.2, 1558.08),
                (6.3, 1596.93),
                (6.4, 1636.01),
                (6.5, 1675.3),
                (6.6, 1714.81),
                (6.7, 1754.53),
                (6.8, 1794.45),
                (6.9, 1834.56),
                (7.0, 1874.86),
                (7.1, 1915.34),
                (7.2, 1955.99),
                (7.3, 1996.81),
                (7.4, 2037.8),
                (7.5, 2078.94),
                (7.6, 2120.24),
                (7.7, 2161.68),
                (7.8, 2203.26),
                (7.9, 2244.97),
                (8.0, 2286.81),
                (8.1, 2328.78),
                (8.2, 2370.86),
                (8.3, 2413.06),
                (8.4, 2455.36),
                (8.5, 2497.77),
                (8.6, 2540.28),
                (8.7, 2582.87),
                (8.8, 2625.56),
                (8.9, 2668.32),
                (9.0, 2715.01),
                (9.1, 2775.1),
                (9.2, 2835.77),
                (9.3, 2897.01),
                (9.4, 2958.82),
                (9.5, 3021.19),
                (9.6, 3084.12),
                (9.7, 3147.6),
                (9.8, 3211.64),
                (9.9, 3276.22),
                (10.0, 3341.35),
                (10.1, 3407.02),
                (10.2, 3473.22),
                (10.3, 3539.95),
                (10.4, 3607.21),
                (10.5, 3674.99),
                (10.6, 3743.29),
                (10.7, 3812.11),
                (10.8, 3881.43),
                (10.9, 3951.26),
                (11.0, 4021.6),
                (11.1, 4092.43),
                (11.2, 4163.75),
                (11.3, 4235.56),
                (11.4, 4307.86),
                (11.5, 4380.63),
                (11.6, 4453.89),
                (11.7, 4527.61),
                (11.8, 4601.8),
                (11.9, 4676.45),
                (12.0, 4751.56),
                (12.1, 4827.12),
                (12.2, 4903.13),
                (12.3, 4979.59),
                (12.4, 5056.48),
                (12.5, 5133.81),
                (12.6, 5211.57),
                (12.7, 5289.75),
                (12.8, 5368.35),
                (12.9, 5447.37),
                (13.0, 5526.8),
                (13.1, 5606.64),
                (13.2, 5686.88),
                (13.3, 5767.51),
                (13.4, 5848.53),
                (13.5, 5929.95),
                (13.6, 6011.74),
                (13.7, 6093.91),
                (13.8, 6176.46),
                (13.9, 6259.37),
                (14.0, 6342.64),
                (14.1, 6426.27),
                (14.2, 6510.25),
                (14.3, 6594.58),
                (14.4, 6679.25),
                (14.5, 6764.25),
                (14.6, 6849.59),
                (14.7, 6935.26),
                (14.8, 7021.24),
                (14.9, 7107.54),
                (15.0, 7194.16),
                (15.1, 7281.07),
                (15.2, 7368.29),
                (15.3, 7455.81),
                (15.4, 7543.61),
                (15.5, 7631.7),
                (15.6, 7720.06),
                (15.7, 7808.7),
                (15.8, 7897.61),
                (15.9, 7986.79),
                (16.0, 8076.21),
                (16.1, 8165.9),
                (16.2, 8255.82),
                (16.3, 8345.99),
                (16.4, 8436.4),
                (16.5, 8527.03),
                (16.6, 8617.89),
                (16.7, 8708.96),
                (16.8, 8800.25),
                (16.9, 8891.75),
                (17.0, 8983.45),
                (17.1, 9075.35),
                (17.2, 9167.43),
                (17.3, 9259.7),
                (17.4, 9352.15),
                (17.5, 9444.77),
                (17.6, 9537.56),
                (17.7, 9630.51),
                (17.8, 9723.62),
                (17.9, 9816.87),
                (18.0, 9910.27),
                (18.1, 10003.81),
                (18.2, 10097.48),
                (18.3, 10191.27),
                (18.4, 10285.19),
                (18.5, 10379.21),
                (18.6, 10473.35),
                (18.7, 10567.59),
                (18.8, 10661.92),
                (18.9, 10756.34),
                (19.0, 10850.85),
                (19.1, 10945.43),
                (19.2, 11040.08),
                (19.3, 11134.8),
                (19.4, 11229.57),
                (19.5, 11324.4),
                (19.6, 11419.27),
                (19.7, 11514.19),
                (19.8, 11609.13),
                (19.9, 11704.1),
                (20.0, 11799.09),
                (20.1, 11894.1),
                (20.2, 11989.11),
                (20.3, 12084.12),
                (20.4, 12179.13),
                (20.5, 12274.12),
                (20.6, 12369.09),
                (20.7, 12464.04),
                (20.8, 12558.96),
                (20.9, 12653.83),
                (21.0, 12748.66),
                (21.1, 12843.44),
                (21.2, 12938.15),
                (21.3, 13032.8),
                (21.4, 13127.38),
                (21.5, 13221.88),
                (21.6, 13316.28),
                (21.7, 13410.6),
                (21.8, 13504.81),
                (21.9, 13598.91),
                (22.0, 13692.9),
                (22.1, 13786.77),
                (22.2, 13880.5),
                (22.3, 13974.1),
                (22.4, 14067.55),
                (22.5, 14160.85),
                (22.6, 14253.99),
                (22.7, 14346.97),
                (22.8, 14439.77),
                (22.9, 14532.39),
                (23.0, 14624.82),
                (23.1, 14717.05),
                (23.2, 14809.08),
                (23.3, 14900.9),
                (23.4, 14992.5),
                (23.5, 15083.87),
                (23.6, 15175.0),
                (23.7, 15265.89),
                (23.8, 15356.54),
                (23.9, 15446.92),
                (24.0, 15537.03),
                (24.1, 15626.87),
                (24.2, 15716.43),
                (24.3, 15805.7),
                (24.4, 15894.66),
                (24.5, 15983.32),
                (24.6, 16071.66),
                (24.7, 16159.68),
                (24.8, 16247.37),
                (24.9, 16334.71),
                (25.0, 16421.7),
                (25.1, 16508.33),
                (25.2, 16594.6),
                (25.3, 16680.49),
                (25.4, 16765.99),
                (25.5, 16851.1),
                (25.6, 16935.8),
                (25.7, 17020.1),
                (25.8, 17103.97),
                (25.9, 17187.41),
                (26.0, 17270.41),
                (26.1, 17352.95),
                (26.2, 17435.04),
                (26.3, 17516.66),
                (26.4, 17597.8),
                (26.5, 17678.45),
                (26.6, 17758.61),
                (26.7, 17838.25),
                (26.8, 17917.37),
                (26.9, 17995.97),
                (27.0, 18074.02),
                (27.1, 18151.53),
                (27.2, 18228.47),
                (27.3, 18304.84),
                (27.4, 18380.63),
                (27.5, 18455.83),
                (27.6, 18530.42),
                (27.7, 18604.39),
                (27.8, 18677.74),
                (27.9, 18750.45),
                (28.0, 18822.51),
                (28.1, 18893.9),
                (28.2, 18964.62),
                (28.3, 19034.65),
                (28.4, 19103.98),
                (28.5, 19172.6),
                (28.6, 19240.49),
                (28.7, 19307.65),
                (28.8, 19374.05),
                (28.9, 19439.69),
                (29.0, 19504.55),
                (29.1, 19568.61),
                (29.2, 19631.87),
                (29.3, 19694.31),
                (29.4, 19755.91),
                (29.5, 19816.66),
                (29.6, 19876.54),
                (29.7, 19935.54),
                (29.8, 19993.64),
                (29.9, 20050.82),
                (30.0, 20107.07),
                (30.1, 20162.38),
                (30.2, 20216.71),
                (30.3, 20270.06),
                (30.4, 20322.41),
                (30.5, 20373.74),
                (30.6, 20424.02),
                (30.7, 20473.24),
                (30.8, 20521.38),
                (30.9, 20568.42),
                (31.0, 20614.33),
                (31.1, 20659.09),
                (31.2, 20702.69),
                (31.3, 20745.09),
                (31.4, 20786.26),
                (31.5, 20826.2),
                (31.6, 20864.86),
                (31.7, 20902.22),
                (31.8, 20938.25),
                (31.9, 20972.93),
                (32.0, 21006.22),
                (32.1, 21038.08),
                (32.2, 21068.49),
                (32.3, 21097.41),
                (32.4, 21124.81),
                (32.5, 21150.63),
                (32.6, 21174.85),
                (32.7, 21197.41),
                (32.8, 21218.28),
                (32.9, 21237.4),
                (33.0, 21254.72),
                (33.1, 21270.19),
                (33.2, 21283.75),
                (33.3, 21295.34),
                (33.4, 21304.88),
                (33.5, 21312.31),
                (33.6, 21317.55),
                (33.7, 21320.51),
                (33.8, 21321.1),
                (33.9, 21319.22),
                (34.0, 21314.76),
                (34.1, 21307.58),
                (34.2, 21297.56),
                (34.3, 21284.53),
                (34.4, 21268.33),
                (34.5, 21248.75),
                (34.6, 21225.57),
                (34.7, 21198.51),
                (34.8, 21167.27),
                (34.9, 21131.47),
                (35.0, 21090.65),
                (35.1, 21044.26),
                (35.2, 20991.59),
                (35.3, 20931.71),
                (35.4, 20863.37),
                (35.5, 20784.81),
                (35.6, 20693.37),
                (35.7, 20584.63),
                (35.8, 20450.15),
                (35.9, 20268.53))

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




