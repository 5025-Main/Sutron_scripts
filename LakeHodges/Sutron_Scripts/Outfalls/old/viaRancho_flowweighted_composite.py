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
    """Returns Label of the general purpose variable.
    :param gp_index: A number between 1 and gp_count
    :type gp_index: int
    :return: the Label of the specified gp
    :rtype: str """
    if gp_index_valid(gp_index):
        return setup_read("GP{} label".format(gp_index))
    else:
        raise ValueError("GP index invalid: ", gp_index)
def gp_find_index(label):
    """ Tells you the index of the general purpose with said label
    Returns zero if no such label is found
    :param label: the customer set label for the gp
    :type label: string
    :return: gp index if a match is found.  zero if no match is found
    :rtype: int """
    for gp_index in range(1, gp_count + 1):
        if label.upper() == gp_read_label(gp_index).upper():
            return gp_index
    return 0  # no gp with that label found
def gp_read_value_by_index(gp_index):
    """ Returns the customer set Value of the general purpose variable.
    :param gp_index: A number between 1 and gp_count
    :type gp_index: int
    :return: the Value of the specified p
    :rtype: float """
    if gp_index_valid(gp_index):
        return float(setup_read("GP{} value".format(gp_index)))
    else:
        raise ValueError("GP index invalid: ", gp_index)
def gp_read_value_by_label(label):
    """ Returns the Value associated with the Label of the general purpose variable.
    :param label: the user set Label of the general purpose variable
    :type label: str
    :return: the Value of the general purpose variable
    :rtype: float  """
    gp_index = gp_find_index(label)
    if gp_index_valid(gp_index):
        # we found a match.  return associated value
        gp_value = "GP{} value".format(gp_index)
        return float(setup_read(gp_value))
    else:
        raise ValueError("GP Label not found: ", label)
        return -999.9  # return this if no match is found
def gp_write_value_by_label(label, value):
    """ Writes a new Value to the general purpose variable associated with the label
    :param label: the user set Label of the general purpose variable
    :type label: str
    :param value: the new Value of the general purpose variable
    :type value: float """
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

## Checks if sample_on is True or False
def sample_on_true_or_false(inval):
    """ Checks if sample_on is True or False
    :param inval:
    :return: True or False (Boolean)
    """
    if inval == 1:
        print("Manually triggered to log at 1 minute interval (FAST)")
        return True
    if inval == 0:
        print("Manually triggered to log at 5 minute interval (SLOW)")
        return False

## Get pacing
def get_volume_pacing():
    """ Returns the threshold at which the volume difference triggers the sampler.
    It is stored in the setup as Alarm 1 Threshold.
    :return: volume threshold
    :rtype: float """
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
    """ Call to attempt to trigger the sampler.
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
    if trigger == True:
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

    # trigger sampler by pulsing output for 0.5 seconds
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
    """ Given stage reading, find the closest stage/discharge pair in
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
                (0.1, 0.0),
                (0.2, 0.0),
                (0.3, 0.01),
                (0.4, 0.02),
                (0.5, 0.02),
                (0.6, 0.04),
                (0.7, 0.05),
                (0.8, 0.07),
                (0.9, 0.09),
                (1.0, 0.11),
                (1.1, 0.14),
                (1.2, 0.16),
                (1.3, 0.19),
                (1.4, 0.23),
                (1.5, 0.26),
                (1.6, 0.3),
                (1.7, 0.35),
                (1.8, 0.39),
                (1.9, 0.44),
                (2.0, 0.49),
                (2.1, 0.55),
                (2.2, 0.6),
                (2.3, 0.66),
                (2.4, 0.73),
                (2.5, 0.79),
                (2.6, 0.86),
                (2.7, 0.93),
                (2.8, 1.01),
                (2.9, 1.09),
                (3.0, 1.17),
                (3.1, 1.26),
                (3.2, 1.34),
                (3.3, 1.44),
                (3.4, 1.53),
                (3.5, 1.63),
                (3.6, 1.73),
                (3.7, 1.83),
                (3.8, 1.94),
                (3.9, 2.05),
                (4.0, 2.16),
                (4.1, 2.28),
                (4.2, 2.4),
                (4.3, 2.52),
                (4.4, 2.65),
                (4.5, 2.77),
                (4.6, 2.91),
                (4.7, 3.04),
                (4.8, 3.18),
                (4.9, 3.32),
                (5.0, 3.47),
                (5.1, 3.62),
                (5.2, 3.77),
                (5.3, 3.92),
                (5.4, 4.08),
                (5.5, 4.24),
                (5.6, 4.4),
                (5.7, 4.57),
                (5.8, 4.74),
                (5.9, 4.91),
                (6.0, 5.09),
                (6.1, 5.27),
                (6.2, 5.45),
                (6.3, 5.64),
                (6.4, 5.83),
                (6.5, 6.02),
                (6.6, 6.22),
                (6.7, 6.42),
                (6.8, 6.62),
                (6.9, 6.82),
                (7.0, 7.03),
                (7.1, 7.24),
                (7.2, 7.46),
                (7.3, 7.68),
                (7.4, 7.9),
                (7.5, 8.12),
                (7.6, 8.35),
                (7.7, 8.58),
                (7.8, 8.81),
                (7.9, 9.05),
                (8.0, 9.29),
                (8.1, 9.53),
                (8.2, 9.78),
                (8.3, 10.03),
                (8.4, 10.28),
                (8.5, 10.53),
                (8.6, 10.79),
                (8.7, 11.05),
                (8.8, 11.32),
                (8.9, 11.58),
                (9.0, 11.85),
                (9.1, 12.13),
                (9.2, 12.4),
                (9.3, 12.68),
                (9.4, 12.97),
                (9.5, 13.25),
                (9.6, 13.54),
                (9.7, 13.83),
                (9.8, 14.13),
                (9.9, 14.42),
                (10.0, 14.72),
                (10.1, 15.03),
                (10.2, 15.33),
                (10.3, 15.64),
                (10.4, 15.96),
                (10.5, 16.27),
                (10.6, 16.59),
                (10.7, 16.91),
                (10.8, 17.24),
                (10.9, 17.56),
                (11.0, 17.89),
                (11.1, 18.23),
                (11.2, 18.56),
                (11.3, 18.9),
                (11.4, 19.24),
                (11.5, 19.59),
                (11.6, 19.94),
                (11.7, 20.29),
                (11.8, 20.64),
                (11.9, 21.0),
                (12.0, 21.36),
                (12.1, 21.72),
                (12.2, 22.08),
                (12.3, 22.45),
                (12.4, 22.82),
                (12.5, 23.19),
                (12.6, 23.57),
                (12.7, 23.95),
                (12.8, 24.33),
                (12.9, 24.71),
                (13.0, 25.1),
                (13.1, 25.49),
                (13.2, 25.88),
                (13.3, 26.28),
                (13.4, 26.68),
                (13.5, 27.08),
                (13.6, 27.48),
                (13.7, 27.89),
                (13.8, 28.29),
                (13.9, 28.71),
                (14.0, 29.12),
                (14.1, 29.54),
                (14.2, 29.96),
                (14.3, 30.38),
                (14.4, 30.8),
                (14.5, 31.23),
                (14.6, 31.66),
                (14.7, 32.09),
                (14.8, 32.53),
                (14.9, 32.96),
                (15.0, 33.4),
                (15.1, 33.85),
                (15.2, 34.29),
                (15.3, 34.74),
                (15.4, 35.19),
                (15.5, 35.64),
                (15.6, 36.1),
                (15.7, 36.56),
                (15.8, 37.02),
                (15.9, 37.48),
                (16.0, 37.95),
                (16.1, 38.41),
                (16.2, 38.88),
                (16.3, 39.36),
                (16.4, 39.83),
                (16.5, 40.31),
                (16.6, 40.79),
                (16.7, 41.27),
                (16.8, 41.76),
                (16.9, 42.24),
                (17.0, 42.73),
                (17.1, 43.23),
                (17.2, 43.72),
                (17.3, 44.22),
                (17.4, 44.72),
                (17.5, 45.22),
                (17.6, 45.72),
                (17.7, 46.23),
                (17.8, 46.73),
                (17.9, 47.24),
                (18.0, 47.76),
                (18.1, 48.27),
                (18.2, 48.79),
                (18.3, 49.31),
                (18.4, 49.83),
                (18.5, 50.35),
                (18.6, 50.88),
                (18.7, 51.41),
                (18.8, 51.94),
                (18.9, 52.47),
                (19.0, 53.0),
                (19.1, 53.54),
                (19.2, 54.08),
                (19.3, 54.62),
                (19.4, 55.16),
                (19.5, 55.71),
                (19.6, 56.25),
                (19.7, 56.8),
                (19.8, 57.35),
                (19.9, 57.91),
                (20.0, 58.46),
                (20.1, 59.02),
                (20.2, 59.58),
                (20.3, 60.14),
                (20.4, 60.7),
                (20.5, 61.27),
                (20.6, 61.83),
                (20.7, 62.4),
                (20.8, 62.97),
                (20.9, 63.55),
                (21.0, 64.12),
                (21.1, 64.7),
                (21.2, 65.28),
                (21.3, 65.86),
                (21.4, 66.44),
                (21.5, 67.02),
                (21.6, 67.61),
                (21.7, 68.2),
                (21.8, 68.79),
                (21.9, 69.38),
                (22.0, 69.97),
                (22.1, 70.56),
                (22.2, 71.16),
                (22.3, 71.76),
                (22.4, 72.36),
                (22.5, 72.96),
                (22.6, 73.56),
                (22.7, 74.17),
                (22.8, 74.78),
                (22.9, 75.38),
                (23.0, 75.99),
                (23.1, 76.61),
                (23.2, 77.22),
                (23.3, 77.83),
                (23.4, 78.45),
                (23.5, 79.07),
                (23.6, 79.69),
                (23.7, 80.31),
                (23.8, 80.93),
                (23.9, 81.55),
                (24.0, 82.18),
                (24.1, 82.81),
                (24.2, 83.44),
                (24.3, 84.07),
                (24.4, 84.7),
                (24.5, 85.33),
                (24.6, 85.96),
                (24.7, 86.6),
                (24.8, 87.24),
                (24.9, 87.88),
                (25.0, 88.52),
                (25.1, 89.16),
                (25.2, 89.8),
                (25.3, 90.44),
                (25.4, 91.09),
                (25.5, 91.73),
                (25.6, 92.38),
                (25.7, 93.03),
                (25.8, 93.68),
                (25.9, 94.33),
                (26.0, 94.99),
                (26.1, 95.64),
                (26.2, 96.3),
                (26.3, 96.95),
                (26.4, 97.61),
                (26.5, 98.27),
                (26.6, 98.93),
                (26.7, 99.59),
                (26.8, 100.25),
                (26.9, 100.91),
                (27.0, 101.58),
                (27.1, 102.24),
                (27.2, 102.91),
                (27.3, 103.58),
                (27.4, 104.25),
                (27.5, 104.91),
                (27.6, 105.59),
                (27.7, 106.26),
                (27.8, 106.93),
                (27.9, 107.6),
                (28.0, 108.28),
                (28.1, 108.95),
                (28.2, 109.63),
                (28.3, 110.3),
                (28.4, 110.98),
                (28.5, 111.66),
                (28.6, 112.34),
                (28.7, 113.02),
                (28.8, 113.7),
                (28.9, 114.38),
                (29.0, 115.07),
                (29.1, 115.75),
                (29.2, 116.43),
                (29.3, 117.12),
                (29.4, 117.81),
                (29.5, 118.49),
                (29.6, 119.18),
                (29.7, 119.87),
                (29.8, 120.55),
                (29.9, 121.24),
                (30.0, 121.93),
                (30.1, 122.62),
                (30.2, 123.31),
                (30.3, 124.01),
                (30.4, 124.7),
                (30.5, 125.39),
                (30.6, 126.08),
                (30.7, 126.78),
                (30.8, 127.47),
                (30.9, 128.17),
                (31.0, 128.86),
                (31.1, 129.56),
                (31.2, 130.25),
                (31.3, 130.95),
                (31.4, 131.65),
                (31.5, 132.34),
                (31.6, 133.04),
                (31.7, 133.74),
                (31.8, 134.44),
                (31.9, 135.14),
                (32.0, 135.83),
                (32.1, 136.53),
                (32.2, 137.23),
                (32.3, 137.93),
                (32.4, 138.63),
                (32.5, 139.33),
                (32.6, 140.03),
                (32.7, 140.73),
                (32.8, 141.43),
                (32.9, 142.14),
                (33.0, 142.84),
                (33.1, 143.54),
                (33.2, 144.24),
                (33.3, 144.94),
                (33.4, 145.64),
                (33.5, 146.34),
                (33.6, 147.04),
                (33.7, 147.75),
                (33.8, 148.45),
                (33.9, 149.15),
                (34.0, 149.85),
                (34.1, 150.55),
                (34.2, 151.25),
                (34.3, 151.95),
                (34.4, 152.65),
                (34.5, 153.35),
                (34.6, 154.06),
                (34.7, 154.76),
                (34.8, 155.46),
                (34.9, 156.16),
                (35.0, 156.86),
                (35.1, 157.56),
                (35.2, 158.26),
                (35.3, 158.96),
                (35.4, 159.65),
                (35.5, 160.35),
                (35.6, 161.05),
                (35.7, 161.75),
                (35.8, 162.45),
                (35.9, 163.14),
                (36.0, 163.84),
                (36.1, 164.54),
                (36.2, 165.23),
                (36.3, 165.93),
                (36.4, 166.62),
                (36.5, 167.32),
                (36.6, 168.01),
                (36.7, 168.71),
                (36.8, 169.4),
                (36.9, 170.09),
                (37.0, 170.78),
                (37.1, 171.47),
                (37.2, 172.16),
                (37.3, 172.85),
                (37.4, 173.54),
                (37.5, 174.23),
                (37.6, 174.92),
                (37.7, 175.61),
                (37.8, 176.29),
                (37.9, 176.98),
                (38.0, 177.66),
                (38.1, 178.35),
                (38.2, 179.03),
                (38.3, 179.71),
                (38.4, 180.39),
                (38.5, 181.08),
                (38.6, 181.75),
                (38.7, 182.43),
                (38.8, 183.11),
                (38.9, 183.79),
                (39.0, 184.46),
                (39.1, 185.14),
                (39.2, 185.81),
                (39.3, 186.49),
                (39.4, 187.16),
                (39.5, 187.83),
                (39.6, 188.5),
                (39.7, 189.17),
                (39.8, 189.83),
                (39.9, 190.5),
                (40.0, 191.16),
                (40.1, 191.83),
                (40.2, 192.49),
                (40.3, 193.15),
                (40.4, 193.81),
                (40.5, 194.47),
                (40.6, 195.13),
                (40.7, 195.78),
                (40.8, 196.44),
                (40.9, 197.09),
                (41.0, 197.74),
                (41.1, 198.39),
                (41.2, 199.04),
                (41.3, 199.69),
                (41.4, 200.33),
                (41.5, 200.98),
                (41.6, 201.62),
                (41.7, 202.26),
                (41.8, 202.9),
                (41.9, 203.54),
                (42.0, 204.18),
                (42.1, 204.81),
                (42.2, 205.44),
                (42.3, 206.07),
                (42.4, 206.7),
                (42.5, 207.33),
                (42.6, 207.96),
                (42.7, 208.58),
                (42.8, 209.2),
                (42.9, 209.82),
                (43.0, 210.44),
                (43.1, 211.06),
                (43.2, 211.67),
                (43.3, 212.29),
                (43.4, 212.9),
                (43.5, 213.51),
                (43.6, 214.11),
                (43.7, 214.72),
                (43.8, 215.32),
                (43.9, 215.92),
                (44.0, 216.52),
                (44.1, 217.12),
                (44.2, 217.71),
                (44.3, 218.3),
                (44.4, 218.89),
                (44.5, 219.48),
                (44.6, 220.06),
                (44.7, 220.65),
                (44.8, 221.23),
                (44.9, 221.8),
                (45.0, 222.38),
                (45.1, 222.95),
                (45.2, 223.52),
                (45.3, 224.09),
                (45.4, 224.66),
                (45.5, 225.22),
                (45.6, 225.78),
                (45.7, 226.34),
                (45.8, 226.89),
                (45.9, 227.44),
                (46.0, 227.99),
                (46.1, 228.54),
                (46.2, 229.09),
                (46.3, 229.63),
                (46.4, 230.17),
                (46.5, 230.7),
                (46.6, 231.23),
                (46.7, 231.76),
                (46.8, 232.29),
                (46.9, 232.82),
                (47.0, 233.34),
                (47.1, 233.85),
                (47.2, 234.37),
                (47.3, 234.88),
                (47.4, 235.39),
                (47.5, 235.9),
                (47.6, 236.4),
                (47.7, 236.9),
                (47.8, 237.39),
                (47.9, 237.88))

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
    """ This function needs to be associated with the total volume measurement.
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
    setup_write("!M2 meas interval", "00:01:00")
    setup_write("!M3 meas interval", "00:01:00")
    setup_write("!M4 meas interval", "00:01:00")
    setup_write("!M5 meas interval", "00:01:00")
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
    setup_write("!M2 meas interval", "00:05:00")
    setup_write("!M3 meas interval", "00:05:00")
    setup_write("!M4 meas interval", "00:05:00")
    setup_write("!M5 meas interval", "00:05:00")
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




