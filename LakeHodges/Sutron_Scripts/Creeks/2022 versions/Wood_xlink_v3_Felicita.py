from sl3 import *
import utime
import math

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

def get_pacing_weighting():
    if setup_read("M3 ACTIVE") == "On":
        pacing = "FLOW"
    elif setup_read("M4 ACTIVE") == "On":
        pacing = "TIME"
    else:
        pacing = "NONE"
    return pacing

def get_flow_units():
    # Flow units - cfs or gpm usually
    flow_pacing_data_source = setup_read("M3 META INDEX")
    flow_pacing_data_source_units = setup_read("M"+str(flow_pacing_data_source )+" UNITS")
    if flow_pacing_data_source_units == 'cfs':
        flow_pacing_units = 'cf'
    elif flow_pacing_data_source_units == 'gpm':
        flow_pacing_units = 'gal'
    elif flow_pacing_data_source_units == 'm3s':
        flow_pacing_units = 'm3'
    else:
        pass
    return flow_pacing_data_source_units, flow_pacing_units

def get_time_pacing_increment():
    # Time Pacing Units should be minutes, just need to know how many
    time_pacing_increment = int(setup_read("M4 MEAS INTERVAL").split(":")[1]) #time is formatted '00:01:00'
    return time_pacing_increment


## Pacing Weighting
pacing_weighting = get_pacing_weighting()

## Flow Units
flow_pacing_data_source_units, flow_pacing_units = get_flow_units()

## Time Pacing Increment
time_pacing_increment = get_time_pacing_increment()

# SampleOn - start/stop sampling
sampling_on = False

# Bottle Number (if pacing is changed bottle number will need to update)
bottle_num = float(gp_read_value_by_label("bottle_num"))

# Bottle volume - running total of volume in bottle
vol_in_bottle = 0.0

# We count how many aliquots have been collected in each bottle
aliquots_in_bottle = 0

# Sample pacing - keep a global one to check if there are any changes
#sample_pacing = gp_read_value_by_label("sample_pacing")  # or with Alarm: setup_read("M{} Alarm 1 Threshold".format(index()))
sample_pacing = float(gp_read_value_by_label("sample_pacing")) # SamplePacin is GenPurp variables

# Running total increment (time or volume)
if pacing_weighting == "FLOW":
    g_running_total = 0.0 # start at 0 and count up to pacing
elif pacing_weighting == "TIME":
    g_running_total = sample_pacing # start at time pacing and count down
else:
    g_running_total = sample_pacing

# Time sampler was triggered last.
time_last_sample = 0.0 ## good to know

# Sample log
sample_log = {'SampleEvent':{'IncrTotal':'','Bottle#':'','Aliquot#':'','SampleTime':''}}

## Get pacing
def get_sample_pacing():
    """ Returns the threshold at which the volume/time difference triggers the sampler.
    :return: sample_pacing, bottle_num
    :rtype: float, int """
    ## Get current bottle number and pacing
    global sample_pacing
    global bottle_num
    global aliquots_in_bottle
    global vol_in_bottle
    global flow_pacing_data_source_units
    global flow_pacing_units
    ## Flow units
    flow_pacing_data_source_units, flow_pacing_units = get_flow_units()
    # Check General Purpose Variables (which holds the desired pacing and bottle number) for changes
    # a change in  pacing may or may not also have a bottle change
    pacing_input = float(gp_read_value_by_label("sample_pacing")) # SamplePacin is GenPurp variables
    bottle_input = int(gp_read_value_by_label("bottle_num"))
    # Compare
    print("checking for pacing change...")
    # IF pacing is changed, go to bottle_and_pacing_change
    if sample_pacing != pacing_input:
        sample_pacing, bottle_num  = bottle_and_pacing_change(pacing_input,bottle_input) #returns new bottle number and pacing from change function
    # IF pacing is same, check if bottle num is changed
    else:
        print ("No pacing change...Current pacing: "+ "%.0f"%sample_pacing)
        print("")
        # Check for new bottle but without pacing change (just full bottle)
        # Bottle number is input manually so just use the manual entry
        print("checking for bottle number change...")
        if bottle_num != bottle_input:
            aliquots_in_bottle = 0  # reset aliquot counter to zero
            vol_in_bottle = 0
            print("New Bottle!")
            print("Previous bottle number: " + '%.0f' % bottle_num)
            bottle_num = bottle_input  # update global bottle_num from BottleNum M2 Offset
            print("New bottle number: " + '%.0f' % bottle_input)
            print("................Aliquots in bottle: " + "%.0f" % aliquots_in_bottle)
            print("................Volume in bottle: " + "%.0f" % vol_in_bottle + "mL")
        else:
            print("No bottle change...Current Bottle number: " + '%.0f' % bottle_num)
            print("................Aliquots in bottle: " + "%.0f" % aliquots_in_bottle)
            print("................Volume in bottle: " + "%.0f" % vol_in_bottle + "mL")
            # bottle number should always be whatever is in the GP variable
    return sample_pacing, bottle_num # return new/current pacing volume and new/current bottle number to main function

def bottle_and_pacing_change(pacing_input,bottle_input):
    """ Updates the bottle number (composite) and resets aliquot counts etc
    :return: bottle_num, sample_pacing"""
    global sample_pacing
    global bottle_num
    global aliquots_in_bottle
    global vol_in_bottle
    global flow_pacing_data_source_units
    global flow_pacing_units
    # Update global values
    sample_pacing = float(pacing_input) # update global sample_pacing from GP variable
    bottle_num = bottle_input  # update global bottle_num from BottleNum M2 Offset
    ## Reset aliquot count and volume (may only be dumping out some volume and changing pacing but reset anyway)
    aliquots_in_bottle = 0.
    vol_in_bottle = 0.0
    # Print new parameters
    print("Pacing changed! New Pacing: " + "%.0f"%sample_pacing + flow_pacing_units) # should be updated above
    print("................New Bottle number: "+ "%.0f" % bottle_num) # should be updated above
    print("................Aliquots in bottle: " + "%.0f" %aliquots_in_bottle)
    print("................Volume in bottle: " + "%.0f" % vol_in_bottle +"mL")
    print("")
    # write a log entry
    event_label = " NewPacing: "+"%.0f"%sample_pacing+"  NewBottle: "+ "%.0f" % bottle_num
    reading = Reading(label=event_label, time=utime.time(),etype='E', value=bottle_num,right_digits=0)
    reading.write_log()
    return sample_pacing, bottle_num


def trigger_sampler():
    """ Call to attempt to trigger the sampler.
    Certain conditions may prevent the triggering.
    :return: True if sampler was triggered."""
    global bottle_capacity
    global aliquot_vol_mL
    global aliquots_in_bottle
    global vol_in_bottle
    global time_last_sample
    ## Set trigger to True
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
        print ('Sampler Triggered')
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
            day = '0' + day
        if len(minute) == 1:
            minute = '0' + minute
        sample_time = str(t[1]) + '/' + day + '/' + str(t[0]) + ' ' + str(t[3]) + ':' + minute
        reading = Reading(label="Triggered Sampler", time=time_scheduled(),
                          etype='E', value=aliquots_in_bottle,
                          right_digits=0, quality='G')  # 'E' = event, 'M' = measurement, 'D' = debug
        reading.write_log()
        ## Write display log entries
        global sample_log
        global bottle_num
        global sample_pacing
        pacing_units = setup_read("M1 Units")
        sample_log[sample_time] = {'Pacing': '%.0f' % sample_pacing+pacing_units, 'Bottle#': str(int(bottle_num)),
                                   'Aliquot#': str(int(aliquots_in_bottle)), 'SampleTime': sample_time}
        return True
    # If conditions are NOT met, then DONOT trigger the sampler
    else:
        return False  # Sampler was NOT triggered.

@MEASUREMENT
def HvF_table(stage_in):
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
    # SITE: Felicita Creek
    # DATE: 4/27/2022
    STAGETBL = ((00.00,00.00),
(00.10,00.01),
(00.20,00.01),
(00.30,00.02),
(00.40,00.03),
(00.50,00.03),
(00.60,00.04),
(00.70,00.05),
(00.80,00.05),
(00.90,00.06),
(01.00,00.07),
(01.10,00.07),
(01.20,00.08),
(01.30,00.09),
(01.40,00.09),
(01.50,00.10),
(01.60,00.12),
(01.70,00.14),
(01.80,00.16),
(01.90,00.18),
(02.00,00.20),
(02.10,00.22),
(02.20,00.24),
(02.30,00.27),
(02.40,00.30),
(02.50,00.33),
(02.60,00.36),
(02.70,00.39),
(02.80,00.43),
(02.90,00.47),
(03.00,00.51),
(03.10,00.55),
(03.20,00.58),
(03.30,00.63),
(03.40,00.68),
(03.50,00.73),
(03.60,00.78),
(03.70,00.83),
(03.80,00.89),
(03.90,00.95),
(04.00,01.01),
(04.10,01.08),
(04.20,01.15),
(04.30,01.22),
(04.40,01.29),
(04.50,01.37),
(04.60,01.45),
(04.70,01.53),
(04.80,01.63),
(04.90,01.73),
(05.00,01.82),
(05.10,01.91),
(05.20,02.00),
(05.30,02.12),
(05.40,02.24),
(05.50,02.35),
(05.60,02.46),
(05.70,02.57),
(05.80,02.69),
(05.90,02.81),
(06.00,02.94),
(06.10,03.07),
(06.20,03.21),
(06.30,03.33),
(06.40,03.44),
(06.50,03.58),
(06.60,03.73),
(06.70,03.89),
(06.80,04.05),
(06.90,04.23),
(07.00,04.41),
(07.10,04.61),
(07.20,04.81),
(07.30,04.97),
(07.40,05.17),
(07.50,05.36),
(07.60,05.53),
(07.70,05.69),
(07.80,05.87),
(07.90,06.06),
(08.00,06.27),
(08.10,06.48),
(08.20,06.73),
(08.30,06.96),
(08.40,07.18),
(08.50,07.41),
(08.60,07.65),
(08.70,07.89),
(08.80,08.13),
(08.90,08.38),
(09.00,08.63),
(09.10,08.86),
(09.20,09.10),
(09.30,09.35),
(09.40,09.61),
(09.50,09.86),
(09.60,10.13),
(09.70,10.42),
(09.80,10.68),
(09.90,10.97),
(10.00,11.33),
(10.10,11.71),
(10.20,12.04),
(10.30,12.38),
(10.40,12.69),
(10.50,13.00),
(10.60,13.32),
(10.70,13.66),
(10.80,14.00),
(10.90,14.25),
(11.00,14.57),
(11.10,14.96),
(11.20,15.31),
(11.30,15.63),
(11.40,16.00),
(11.50,16.45),
(11.60,16.75),
(11.70,17.17),
(11.80,17.55),
(11.90,18.04),
(12.00,18.46),
(12.10,18.95),
(12.20,19.39),
(12.30,19.72),
(12.40,20.13),
(12.50,20.60),
(12.60,21.06),
(12.70,21.45),
(12.80,21.85),
(12.90,22.35),
(13.00,22.87),
(13.10,23.47),
(13.20,24.08),
(13.30,24.68),
(13.40,25.28),
(13.50,25.89),
(13.60,26.49),
(13.70,27.09),
(13.80,27.70),
(13.90,28.30),
(14.00,28.90),
(14.10,29.51),
(14.20,30.11),
(14.30,30.71),
(14.40,31.32),
(14.50,31.92),
(14.60,32.52),
(14.70,33.12),
(14.80,33.73),
(14.90,34.33),
(15.00,34.93),
(15.10,35.54),
(15.20,36.14),
(15.30,36.74),
(15.40,37.35),
(15.50,37.95),
(15.60,38.55),
(15.70,39.16),
(15.80,39.76),
(15.90,40.50),
(16.00,41.33),
(16.10,42.16),
(16.20,42.99),
(16.30,43.82),
(16.40,44.65),
(16.50,45.48),
(16.60,46.31),
(16.70,47.14),
(16.80,47.97),
(16.90,48.80),
(17.00,49.63),
(17.10,50.46),
(17.20,51.29),
(17.30,52.12),
(17.40,52.95),
(17.50,53.78),
(17.60,54.61),
(17.70,55.44),
(17.80,56.27),
(17.90,57.22),
(18.00,58.25),
(18.10,59.28),
(18.20,60.40),
(18.30,61.75),
(18.40,63.09),
(18.50,64.43),
(18.60,65.77),
(18.70,67.11),
(18.80,68.46),
(18.90,69.80),
(19.00,71.14),
(19.10,72.48),
(19.20,73.83),
(19.30,75.17),
(19.40,76.51),
(19.50,77.85),
(19.60,79.20),
(19.70,80.46),
(19.80,81.61),
(19.90,82.76),
(20.00,83.91),
(20.10,85.06),
(20.20,86.21),
(20.30,87.36),
(20.40,88.51),
(20.50,89.66),
(20.60,90.81),
(20.70,91.95),
(20.80,93.10),
(20.90,94.25),
(21.00,95.40),
(21.10,96.55),
(21.20,97.70),
(21.30,98.85),
(21.40,100.00),
(21.50,101.04),
(21.60,102.07),
(21.70,103.11),
(21.80,104.15),
(21.90,105.18),
(22.00,106.22),
(22.10,107.25),
(22.20,108.29),
(22.30,109.33),
(22.40,110.36),
(22.50,111.40),
(22.60,112.44),
(22.70,113.47),
(22.80,114.51),
(22.90,115.54),
(23.00,116.58),
(23.10,117.62),
(23.20,118.65),
(23.30,119.69),
(23.40,120.75),
(23.50,121.83),
(23.60,122.90),
(23.70,123.98),
(23.80,125.05),
(23.90,126.13),
(24.00,127.20),
(24.10,128.28),
(24.20,129.36),
(24.30,130.43),
(24.40,131.51),
(24.50,132.58),
(24.60,133.66),
(24.70,134.73),
(24.80,135.81),
(24.90,136.88),
(25.00,137.96),
(25.10,139.03),
(25.20,140.11),
(25.30,141.24),
(25.40,142.36),
(25.50,143.48),
(25.60,144.61),
(25.70,145.73),
(25.80,146.85),
(25.90,147.98),
(26.00,149.10),
(26.10,150.23),
(26.20,151.35),
(26.30,152.47),
(26.40,153.60),
(26.50,154.72),
(26.60,155.84),
(26.70,156.97),
(26.80,158.09),
(26.90,159.21),
(27.00,160.37),
(27.10,161.58),
(27.20,162.80),
(27.30,164.02),
(27.40,165.24),
(27.50,166.45),
(27.60,167.67),
(27.70,168.89),
(27.80,170.10),
(27.90,171.32),
(28.00,172.54),
(28.10,173.76),
(28.20,174.98),
(28.30,176.20),
(28.40,177.43),
(28.50,178.65),
(28.60,179.88),
(28.70,181.15),
(28.80,182.42),
(28.90,183.69),
(29.00,184.97),
(29.10,186.24),
(29.20,187.52),
(29.30,188.79),
(29.40,190.06),
(29.50,191.34),
(29.60,192.61),
(29.70,193.89),
(29.80,195.16),
(29.90,196.43),
(30.00,197.71),
(30.10,198.98),
(30.20,200.27),
(30.30,201.60),
(30.40,202.93),
(30.50,204.27),
(30.60,205.60),
(30.70,206.93),
(30.80,208.27),
(30.90,209.60),
(31.00,210.93),
(31.10,212.27),
(31.20,213.60),
(31.30,214.93),
(31.40,216.27),
(31.50,217.60),
(31.60,218.93),
(31.70,220.27),
(31.80,221.63),
(31.90,222.99),
(32.00,224.35))


    # Test for out of bounds stage values
    if stage_in < STAGETBL[0][0]:  # if measured stage is BELOW the FIRST stage value in the FIRST stage,flow pair
        flow = STAGETBL[0][0] # Use lowest flow value in the stage,flow pairs
    elif stage_in > STAGETBL[-1][0]:  # if measured stage is ABOVE the LAST stage value in the LAST stage,flow pair
        flow = STAGETBL[-1][1] # Use last flow value in the stage,flow pairs
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
        flow = a_flow1 + (b_diff_stage / (c_stage2 - d_stage1)) * (e_flow2 - a_flow1)
    print ("")
    print("Stage: {}".format("%.2f" % stage_in) + ' in')
    print("Flow: {}".format("%.3f"%flow))
    print("")
    return flow

@MEASUREMENT
def AV_PipeFLow_cfs(vel_fps):
    """ Takes velocity as input; meta index should correspond to the velocity measurement.
    returns the flow based on the pipe diameter in the general purpose values
    :param vel_fps:
    :return: flow_gpm or flow_cfs depending on units """

    pipe_diam = gp_read_value_by_label("pipe_diameter_in")
    stage_in = measure("Level_PT", READING_LAST).value
    radius = pipe_diam/2.
    angle = 2. * math.acos((radius - stage_in) / radius)
    area_sq_in = (radius ** 2 * (angle - math.sin(angle))) / 2
    area_sq_ft = area_sq_in * 0.00694444
    flow_cfs = area_sq_ft * vel_fps
    return flow_cfs

@MEASUREMENT
def AV_PipeFLow_gpm(vel_fps):
    """ Takes velocity as input; meta index should correspond to the velocity measurement.
    returns the flow based on the pipe diameter in the general purpose values
    :param vel_fps:
    :return: flow_gpm or flow_cfs depending on units """

    pipe_diam = gp_read_value_by_label("pipe_diameter_in")
    stage_in = measure("Level_PT", READING_LAST).value
    radius = pipe_diam/2.
    angle = 2. * math.acos((radius - stage_in) / radius)
    area_sq_in = (radius ** 2 * (angle - math.sin(angle))) / 2
    area_sq_ft = area_sq_in * 0.00694444
    flow_cfs = area_sq_ft * vel_fps
    flow_gpm = flow_cfs * 448.8325660485
    return flow_gpm


@MEASUREMENT
def flow_weighted_sampling(flow):
    """ This function needs to be associated with the total volume measurement.
    It will compute the total volume based on the current flow rate and past volume.
    The script will trigger the sampler if appropriate.
    :param flow: current flow rate
    :return: the current volume reading"""
    global sampling_on
    global sample_pacing
    global g_running_total
    global bottle_capacity
    global aliquot_vol_mL
    global bottle_num
    global aliquots_in_bottle
    global pacing_weighting
    ## Check if sampling is on
    gp_sampling_on = gp_read_value_by_label("sampling_on") ## Read value in GP
    if gp_sampling_on == 1:
        sampling_on =  True
    elif gp_sampling_on == 0:
        sampling_on = False

    # Aliquot volume
    aliquot_vol_mL = gp_read_value_by_label("aliquot_vol_mL")
    # The container can hold a maximum number of aliquots
    bottle_size_L = gp_read_value_by_label("bottle_size_L")
    # aliquots; 19L / 250mL = 76
    bottle_capacity = bottle_size_L / (aliquot_vol_mL/1000)

    ## Check if program is flow weighted
    pacing_weighting = get_pacing_weighting()
    ## FLow Units
    flow_pacing_data_source_units, flow_pacing_units = get_flow_units()

    if sampling_on == False and  pacing_weighting == "FLOW":
        print ('Sampling is OFF, Sample pacing is FLOW weighted')
        print('Flow:' + "%.2f" % flow + flow_pacing_data_source_units)
        print ("Current bottle number: "+"%.0f"%bottle_num)
        print ("Current pacing: "+"%.0f"%sample_pacing + flow_pacing_units)
        print("Aliquots in bottle: " + "%.0f"%aliquots_in_bottle)
        print("Bottle capacity: " + "%.0f"%bottle_capacity)

    elif sampling_on == True and  pacing_weighting == "FLOW":
        print ('sampling is ON, Sample pacing is FLOW weighted')
        # Measurement is at 1 minute, flow in cfs * 60 sec = cfm
        # flow = measure("Flow_cfs", READING_LAST).value  # what is the current flow rate?
        if flow_pacing_data_source_units == 'cfs' or flow_pacing_data_source_units == 'm3s':
            incremental_vol = flow * 60. # cfs x 60 sec = cf per minute
        elif flow_pacing_data_source_units == 'gpm':
            incremental_vol = flow

        # Add to running total volume
        g_running_total = g_running_total + incremental_vol # cf per minute, at minute intervals just total up

        print('Flow:' + "%.3f" % flow + flow_pacing_data_source_units, '  IncrVol:' + "%.2f" % incremental_vol + flow_pacing_units,
              '  RunningTotalVol:' + "%.2f" % g_running_total + flow_pacing_units)

        # Pacing - check pacing, if it's different this function will update everything
        sample_pacing, bottle_num = get_sample_pacing()

        # if the running total volume is higher than pacing volume, trigger sampler
        if g_running_total >= sample_pacing:
            print('Sample triggered by flow')
            if trigger_sampler():
                # sampler was triggered
                # Write a log entry indicating why sampler was triggered.
                reading = Reading(label="VolumeTrig", time=time_scheduled(),
                                  etype='E', value=g_running_total, quality='G')
                reading.write_log()

                # get remaining volume and keep in running total
                g_running_total = g_running_total - sample_pacing
                ## check to see if sampling is going too fast


        # add diagnostic info to the script status
        print ("Current bottle number: "+"%.0f"%bottle_num)
        print ("Current pacing: "+"%.0f"%sample_pacing)
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
    return g_running_total  # return the total volume (before clearing it)

@MEASUREMENT
def time_weighted_sampling(input):
    """ This function runs a time-weighted sampling program
    The script will trigger the sampler if appropriate.
    :param
    :return: time to next sample"""
    global sampling_on
    global pacing_weighting
    global sample_pacing
    global g_running_total
    global bottle_capacity
    global aliquot_vol_mL
    global bottle_num
    global aliquots_in_bottle
    global vol_in_bottle

    ## Check if sampling is on
    gp_sampling_on = gp_read_value_by_label("sampling_on") ## Read value in GP
    if gp_sampling_on == 1:
        sampling_on =  True
    elif gp_sampling_on == 0:
        sampling_on = False

    # Aliquot volume
    aliquot_vol_mL = gp_read_value_by_label("aliquot_vol_mL")
    # The container can hold a maximum number of aliquots
    bottle_size_L = gp_read_value_by_label("bottle_size_L")
    # aliquots; 19L / 250mL = 76
    bottle_capacity = bottle_size_L / (aliquot_vol_mL/1000)

    ## Check if program is flow weighted
    pacing_weighting = get_pacing_weighting()
    sample_pacing = float(gp_read_value_by_label("sample_pacing")) # SamplePacin is GenPurp variables

    if sampling_on == False and  pacing_weighting == "TIME":
        print ('Sampling is OFF, Sample pacing is TIME weighted')
        print ("Current bottle number: "+"%.0f"%bottle_num)
        print ("Current pacing: "+str(sample_pacing) + "minutes")
        print("Aliquots in bottle: " + "%.0f"%aliquots_in_bottle)
        print("Bottle capacity: " + "%.0f"%bottle_capacity)

    elif sampling_on == True and  pacing_weighting == "TIME":
        print ('sampling is ON, Sample pacing is TIME weighted')
        # Measurement is some # of minutes - time_pacing_increment==meas_interval
        time_pacing_increment = get_time_pacing_increment()

        # Subtract the time_pacing_increment from the total time pacing running_total
        g_running_total = g_running_total - int(time_pacing_increment)  #

        print('  Time Pacing Increment: ' + str(time_pacing_increment) + "minutes",
              '  Time to Next Sample:' + "%.0f" % g_running_total + "minutes")

        # if the running total of minutes is 0 (or less) trigger sampler
        print (type(sample_pacing))
        print(sample_pacing)
        print (type(g_running_total))
        print (g_running_total)
        ## running_total is counting down, when it gets to 0 trigger a sample
        ## and reset running_total to the sample_pacing for the next countdown
        if g_running_total <= 0:
            print ('Countdown timer below sample_pacing')
            if trigger_sampler():
                print ('Sampler triggered by time pacing')
                # sampler was triggered
                # Write a log entry indicating why sampler was triggered.
                reading = Reading(label="TimeTrig", time=time_scheduled(),
                                  etype='E', value=g_running_total, quality='G')
                reading.write_log()

                # reset Time pacing to sample_pacing
                g_running_total = sample_pacing #reset to Sample Pacing eg 30min

        # add diagnostic info to the script status
        print ("Current bottle number: "+"%.0f"%bottle_num)
        print ("Current pacing: "+"%.0f"%sample_pacing)
        print("Aliquots in bottle: " + "%.0f"%aliquots_in_bottle)
        print("Bottle capacity: " + "%.0f"%bottle_capacity)
    else:
        print('sample not triggered yet')

    # Display log of samples taken
    global sample_log
    print ('Sample Log: ')
    for k in sorted(sample_log):
        print(sample_log[k])

    return g_running_total  # return the countdown timer

@MEASUREMENT
def display_sample_pacing(input):
    global sample_pacing
    smaple_pacing = float(gp_read_value_by_label("sample_pacing"))
    print ('Sample Pacing: '+str(sample_pacing))
    return sample_pacing

@MEASUREMENT
def display_bottle_num(input):
    global bottle_num
    bottle_num = float(gp_read_value_by_label("bottle_num"))
    print ('Bottle number: '+str(bottle_num))
    return bottle_num

@MEASUREMENT
def number_of_aliquots(input):
    global aliquots_in_bottle
    print ('Number of aliquots in bottle: '+str(aliquots_in_bottle))
    return aliquots_in_bottle

@TASK
def turn_on_sampling():
    print("Started sampling!")
    for i in [i for i in range(5,14,1)]:
        setup_write("!M"+str(i)+" meas interval", "00:01:00")
    # Start sampling when level triggered
    gp_write_value_by_label("sampling_on", 1)  # 1=True

    ## Reset all params for start of event
    global sample_pacing
    global g_running_total
    global bottle_num
    global aliquots_in_bottle
    global vol_in_bottle
    ## get pacing
    sample_pacing = float(gp_read_value_by_label("sample_pacing")) # SamplePacin is GenPurp variables

    ## Reset parameters for event
    ## Check if program is flow weighted
    pacing_weighting = get_pacing_weighting()
    # Running total increment (time or volume)
    if pacing_weighting == "FLOW":
        g_running_total = 0.0  # start at 0 and count up to pacing
    if pacing_weighting == "TIME":
        g_running_total = sample_pacing  # start at time pacing and count down
    bottle_num = float(setup_read("M2 Offset"))
    aliquots_in_bottle = 0
    vol_in_bottle = 0
    return

@TASK
def turn_off_sampling():
    print ("Stopped sampling")
    # Stop sampling when level triggered
    gp_write_value_by_label("sampling_on", 0)  # 0=False
    ## Set data collection back to 5 min
    for i in [i for i in range(5, 14, 1)]:
        setup_write("!M" + str(i) + " meas interval", "00:05:00")

@TASK
def reset_sampling_params():
    print("Manually reset sampling parameters!")

    ## Reset all params for start of event
    global sample_pacing
    global g_running_total
    global bottle_num
    global aliquots_in_bottle
    global vol_in_bottle

    ## get pacing
    sample_pacing = float(gp_read_value_by_label("sample_pacing")) # SamplePacin is GenPurp variables
    bottle_num = int(gp_read_value_by_label("bottle_num"))
    ## Check if program is flow weighted
    pacing_weighting = get_pacing_weighting()
    # Running total increment (time or volume)
    if pacing_weighting == "FLOW":
        g_running_total = 0.0  # start at 0 and count up to pacing
    if pacing_weighting == "TIME":
        g_running_total = sample_pacing  # start at time pacing and count down

    aliquots_in_bottle = 0
    vol_in_bottle = 0

    # Sample log
    sample_log = {'SampleEvent': {'IncrTotal': '', 'Bottle#': '', 'Aliquot#': '', 'SampleTime': ''}}
    return
@TASK
def trigger_sampler_manually():
    """ Function triggers SW12 for two seconds in order to trigger a sampler"""

    # trigger sampler by pulsing output for 0.5 seconds
    power_control('SW1', True)
    utime.sleep(0.5)
    power_control('SW1', False)
    # write a log entry
    t = utime.localtime(time_scheduled())
    day, minute = str(t[2]), str(t[4])
    if len(day) == 1:
        day = '0' + day
    if len(minute) == 1:
        minute = '0' + minute
    sample_time = str(t[1]) + '/' + day + '/' + str(t[0]) + ' ' + str(t[3]) + ':' + minute
    reading = Reading(label="Trigger Manually", time=time_scheduled(),
                      etype='E', value=1,right_digits=0, quality='G')  # 'E' = event, 'M' = measurement, 'D' = debug
    reading.write_log()
    print ('Sampler triggered manually ' + sample_time)
    return True
