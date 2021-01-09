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
                (0.98, 0.25),
                (1.45, 0.5),
                (1.76, 0.75),
                (1.87, 1.0),
                (2.1, 1.25),
                (2.33, 1.5),
                (2.53, 1.75),
                (2.74, 2.0),
                (2.92, 2.25),
                (3.07, 2.5),
                (3.21, 2.75),
                (3.32, 3.0),
                (3.46, 3.25),
                (3.5, 3.5),
                (3.67, 3.75),
                (3.8, 4.0),
                (3.91, 4.25),
                (3.98, 4.5),
                (4.09, 4.75),
                (4.19, 5.0),
                (4.29, 5.25),
                (4.38, 5.5),
                (4.47, 5.75),
                (4.56, 6.0),
                (4.61, 6.25),
                (4.69, 6.5),
                (4.78, 6.75),
                (4.86, 7.0),
                (4.93, 7.25),
                (5.03, 7.5),
                (5.1, 7.75),
                (5.17, 8.0),
                (5.24, 8.25),
                (5.31, 8.5),
                (5.37, 8.75),
                (5.44, 9.0),
                (5.51, 9.25),
                (5.57, 9.5),
                (5.64, 9.75),
                (5.7, 10.0),
                (5.76, 10.25),
                (5.82, 10.5),
                (5.89, 10.75),
                (5.94, 11.0),
                (5.99, 11.25),
                (6.03, 11.5),
                (6.09, 11.75),
                (6.15, 12.0),
                (6.21, 12.25),
                (6.25, 12.5),
                (6.36, 12.75),
                (6.41, 13.0),
                (6.46, 13.25),
                (6.49, 13.5),
                (6.53, 13.75),
                (6.58, 14.0),
                (6.65, 14.25),
                (6.69, 14.5),
                (6.75, 14.75),
                (6.83, 15.0),
                (6.91, 15.25),
                (7.08, 15.5),
                (7.15, 15.75),
                (7.21, 16.0),
                (7.27, 16.25),
                (7.32, 16.5),
                (7.37, 16.75),
                (7.42, 17.0),
                (7.47, 17.25),
                (7.52, 17.5),
                (7.51, 17.75),
                (7.54, 18.0),
                (7.56, 18.25),
                (7.59, 18.5),
                (7.64, 18.75),
                (7.68, 19.0),
                (7.72, 19.25),
                (7.77, 19.5),
                (7.81, 19.75),
                (7.86, 20.0),
                (7.9, 20.25),
                (7.94, 20.5),
                (7.98, 20.75),
                (8.03, 21.0),
                (8.07, 21.25),
                (8.11, 21.5),
                (8.15, 21.75),
                (8.19, 22.0),
                (8.23, 22.25),
                (8.27, 22.5),
                (8.32, 22.75),
                (8.36, 23.0),
                (8.59, 25.0),
                (9.26, 30.0),
                (9.86, 35.0),
                (10.46, 40.0),
                (10.97, 47.7),
                (10.99, 47.77),
                (11.62, 50.0),
                (12.11, 55.0),
                (12.22, 60.0),
                (12.73, 65.0),
                (13.14, 70.0),
                (13.49, 75.0),
                (13.96, 80.0),
                (14.29, 85.0),
                (14.46, 90.0),
                (14.8, 95.0),
                (15.16, 100.0),
                (15.83, 110.0),
                (16.54, 120.0),
                (17.45, 130.0),
                (17.75, 143.0),
                (18.07, 150.0),
                (19.35, 160.0),
                (20.16, 170.0),
                (20.77, 180.0),
                (21.29, 190.0),
                (21.62, 200.0),
                (21.72, 210.0),
                (22.03, 223.0),
                (22.18, 230.0),
                (22.37, 240.0),
                (22.55, 250.0),
                (22.72, 260.0),
                (22.87, 270.0),
                (24.83, 280.0),
                (25.22, 290.0),
                (25.36, 300.0),
                (25.59, 310.0),
                (25.8, 320.0),
                (25.73, 327.0),
                (26.17, 340.0),
                (26.32, 350.0),
                (26.49, 360.0),
                (26.67, 370.0),
                (26.96, 380.0),
                (27.81, 390.0),
                (27.97, 400.0),
                (28.11, 410.0),
                (28.21, 420.0),
                (28.39, 430.0),
                (28.57, 440.0),
                (28.75, 450.0),
                (28.85, 460.0),
                (29.28, 470.0),
                (29.42, 480.0),
                (29.64, 495.0),
                (29.71, 500.0),
                (29.98, 520.0),
                (30.24, 540.0),
                (30.48, 560.0),
                (30.53, 587.0),
                (30.65, 600.0),
                (30.83, 620.0),
                (30.99, 640.0),
                (31.15, 660.0),
                (31.29, 680.0),
                (31.43, 693.0))


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
