# -*- coding: utf-8 -*-
"""
Created on Mon Jun 28 13:35:00 2021

@author: alex.messina
"""


import pandas as pd
from matplotlib import pyplot as plt
import datetime as dt
import numpy as np
## Set Pandas display options
pd.set_option('display.large_repr', 'truncate')
pd.set_option('display.width', 180)
pd.set_option('display.max_rows', 40)
pd.set_option('display.max_columns', 13)
plt.ion()

def rating_table(rating_curve,stage_in):
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
    STAGETBL = list( zip(rating_curve.index.values,rating_curve['Flow (cfs)'].values) ) # Python 3 needs list()
    if np.isnan(stage_in):
        flow_cfs = np.nan
        
    # Test for out of bounds stage values
    if stage_in < STAGETBL[0][0]:  # below
        flow_cfs = STAGETBL[0][0]
    elif stage_in > STAGETBL[-1][0]:  # above
        #flow_cfs = -99.99 #error value
        flow_cfs = STAGETBL[-1][1] #max value
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
#    print ("")
#    print("Flow: {}".format("%.3f"%flow_cfs))
#    print("Stage: {}".format("%.2f"%stage_in))
#    print("")
    return flow_cfs

datadir = 'C:/Users/alex.messina/Documents/GitHub/Sutron_scripts/LakeHodges/Creek data/'

ratings = pd.ExcelFile(datadir + 'Rating Curves 7_2_2021.xlsx')

data_xl = pd.ExcelFile(datadir  + 'Compiled_Creek_Level_data.xlsx')
sheets = data_xl.sheet_names

measurements = data_xl.parse(sheet_name='Manual_Measurements',index_col=0)

#%%
all_df = pd.DataFrame(index=pd.date_range(dt.datetime(2020,1,1,0,0),dt.datetime(2021,7,1,0,0),freq='5Min'))
for sheet in [s for s in sheets if s not in ['Manual_Measurements','USGS_Guejito']]:


    print (sheet)
    rating_curve = ratings.parse(sheet_name = sheet,index_col=0,skiprows=1)
    
    if sheet == 'GreenValley':
        meas_N = measurements.loc['GreenValleyN',:].set_index('EVENT DATE')
        meas_S = measurements.loc['GreenValleyS',:].set_index('EVENT DATE')
        meas_N = meas_N.sort_index()
        df = data_xl.parse(sheet_name = sheet,index_col=0)
        df = df.resample('5Min').mean()
        df = df.interpolate(limit=12)
        df['Flow_cfs_N'] = df['Level_North_in'].apply(lambda x: rating_table(rating_curve,x) )
        df['Flow_cfs_S'] = df['Level_South_in'].apply(lambda x: rating_table(rating_curve,x) )
        df['Flow_cfs'] = df['Flow_cfs_N'] + df['Flow_cfs_S']
        
#        ## Plot levels together
#        df[['Level_North_in','Level_South_in']].plot()
#        # Plot North
#        df[['Level_North_in','Flow_cfs_N']].plot(alpha=0.5)
#        meas_N[meas_N['Source'] == 'Wood']['FLOW (CFS)'].plot(ls='None',marker='o',c='b',label='N Flow meas by Wood')
#        # Plot South
#        df[['Level_South_in','Flow_cfs_S']].plot(alpha=0.5)
#        meas_S[meas_S['Source'] == 'Wood']['FLOW (CFS)'].plot(ls='None',marker='o',c='g',label='S Flow meas by Wood')
#        ## Plot total flow with PUD measurements of total flow
#        df[['Flow_cfs']].plot(alpha=0.5)
#        meas_N[meas_N['Source'] == 'PUD']['FLOW (CFS)'].plot(ls='None',marker='o',c='r',label='Flow meas by PUD')
        
    else:   
        meas = measurements.loc[sheet,:].set_index('EVENT DATE')
        meas = meas.sort_index()
        df = data_xl.parse(sheet_name = sheet,index_col=0)
        df = df.resample('5Min').mean()
        df = df.interpolate(limit=12)
        df['Flow_cfs'] = df['Level_in'].apply(lambda x: rating_table(rating_curve,x) )
    
   
#    if sheet == 'Guejito':
#        df_usgs = data_xl.parse(sheet_name = 'USGS_Guejito',index_col=2)
#        df_usgs = df_usgs.resample('5Min').interpolate()
#        df['USGS_Flow_cfs'] = df_usgs['USGS_Flow_cfs']
#        df[['USGS_Flow_cfs','Flow_cfs']].plot()
#        meas['FLOW (CFS)'].plot(ls='None',marker='o')
#        
#    
#    else:
#        #df['Flow_cfs'].plot()        
#        df[['Level_in','Flow_cfs']].plot(alpha=0.5)
#
#        meas[meas['Source'] == 'Wood']['FLOW (CFS)'].plot(ls='None',marker='o',c='b',label='Flow meas by Wood')
#        meas[meas['Source'] == 'PUD']['FLOW (CFS)'].plot(ls='None',marker='o',c='r',label='Flow meas by PUD')
#        
#        plt.legend()

    
    if sheet == 'GreenValley':
        ## No alterations
        all_df[sheet+'N_Level_in'] = df['Level_North_in']
        all_df[sheet+'S_Level_in'] = df['Level_South_in']
        
        all_df['Flow_cfs_N'] = df['Flow_cfs_N']
        all_df['Flow_cfs_S'] = df['Flow_cfs_S']
        all_df['GreenValley_Flow_cfs'] = df['Flow_cfs_N'] + df['Flow_cfs_S']
        
    elif sheet == 'KitCarson':
        ## cut erroneous data
        df.loc[dt.datetime(2020,7,6,22,0):dt.datetime(2020,8,1,2,30),'Level_in'] =np.nan ## PT sensor cut off from flowing channel
        ## Offset dry weather low flow
        df.loc[dt.datetime(2020,8,1,2,35):dt.datetime(2020,11,7,5,0),'Level_in'] =  df.loc[dt.datetime(2020,8,1,2,35):dt.datetime(2020,11,7,5,0),'Level_in'] + 0.5
        ## smooth out diurnal a bit
        df.loc[dt.datetime(2020,8,1,2,35):dt.datetime(2020,11,7,5,0),'Level_in'] =  df.loc[dt.datetime(2020,8,1,2,35):dt.datetime(2020,11,7,5,0),'Level_in'].rolling(288,min_periods=12,center=True).mean()
        ## Offset rest of 2021 data
        df.loc[dt.datetime(2020,11,7,5,0):,'Level_in'] =  df.loc[dt.datetime(2020,11,7,5,0):,'Level_in'] + 0.75
        df['Flow_cfs'] = df['Level_in'].apply(lambda x: rating_table(rating_curve,x) )
        
        all_df[sheet+'_Level_in'] = df['Level_in']
        all_df[sheet+'_Flow_cfs'] = df['Flow_cfs']
        
        
    elif sheet == 'Cloverdale':
        df.loc[dt.datetime(2021,1,23,12,0):,'Level_in'] = df.loc[dt.datetime(2021,1,23,12,0):,'Level_in'] -0.2 ## offset
       
        df['Flow_cfs'] = df['Level_in'].apply(lambda x: rating_table(rating_curve,x) )
       
#        df[['Level_in','Flow_cfs']].plot()
       
        all_df[sheet+'_Level_in'] = df['Level_in']
        all_df[sheet+'_Level_in'] = all_df[sheet+'_Level_in'].fillna(0) ## Fill NA with zero
        all_df[sheet+'_Level_in'] = all_df[sheet+'_Level_in'].where(all_df[sheet+'_Level_in']>=0, 0) 
        
        all_df[sheet+'_Flow_cfs'] = df['Flow_cfs']
        all_df[sheet+'_Flow_cfs'] = df['Flow_cfs'].fillna(0) ## Fill NA with zero
        
    
    elif sheet == 'Felicita':
        df.loc[dt.datetime(2020,11,22,18,10):dt.datetime(2020,12,13,15,5),['Level_in']] = df.loc[dt.datetime(2020,11,22,18,10):dt.datetime(2020,12,13,15,5),['Level_in']] -0.7 ## offset
        df.loc[dt.datetime(2021,1,26,4,10):dt.datetime(2021,4,5,18,0),['Level_in']] =  df.loc[dt.datetime(2021,1,26,4,10):dt.datetime(2021,4,5,18,0),['Level_in']]+1.1 ## offset

        df['Flow_cfs'] = df['Level_in'].apply(lambda x: rating_table(rating_curve,x) )
#        df[['Level_in','Flow_cfs']].plot()
        
        all_df[sheet+'_Level_in'] = df['Level_in']
        all_df[sheet+'_Flow_cfs'] = df['Flow_cfs']
    
        
    elif sheet == 'DelDios':
         df.loc[dt.datetime(2020,7,5,0,0):dt.datetime(2020,10,26,12,0),['Level_in']] = 0 ## cut out erroneous level
         df['Level_in'] = df['Level_in'].fillna(0)
         df['Level_in'] = df['Level_in'].where(df['Level_in']>=0, 0) 
         df['Flow_cfs'] = df['Level_in'].apply(lambda x: rating_table(rating_curve,x) )
#         df[['Level_in','Flow_cfs']].plot()
         
         all_df[sheet+'_Level_in'] = df['Level_in']
         all_df[sheet+'_Flow_cfs'] = df['Flow_cfs']
    
    ## if site goes dry then fill gaps with 0
    elif sheet in ['Sycamore','SanDieguito','Cloverdale','Guejito']:
        all_df[sheet+'_Level_in'] = df['Level_in']
        all_df[sheet+'_Level_in'] = all_df[sheet+'_Level_in'].fillna(0) ## Fill NA with zero
        all_df[sheet+'_Level_in'] = all_df[sheet+'_Level_in'].where(all_df[sheet+'_Level_in']>=0, 0) 
        
        all_df[sheet+'_Flow_cfs'] = df['Flow_cfs']
        all_df[sheet+'_Flow_cfs'] = df['Flow_cfs'].fillna(0) ## Fill NA with zero
    
    elif sheet == 'Moonsong':
        
        ## Cut out shitty data
        df.loc[dt.datetime(2020,5,19,18,0):dt.datetime(2020,5,29,19,20),:] = np.nan
      
        ## detrend the PT data
        from scipy import signal
        # part 1
        detrended2 = df.loc[dt.datetime(2020,5,6,18,30):dt.datetime(2020,5,19,17,55),['Level_in']].dropna()
        detrended2.loc[dt.datetime(2020,5,6,18,30):dt.datetime(2020,5,19,17,55),'Level_in_detrended'] = signal.detrend(detrended2['Level_in']) +2
        df.loc[dt.datetime(2020,5,6,18,30):dt.datetime(2020,5,19,17,55),'Level_in_detrended'] = detrended2.loc[dt.datetime(2020,5,6,18,30):dt.datetime(2020,5,19,17,55),'Level_in_detrended'] + 3.
#        df.loc[dt.datetime(2020,5,6,18,30):dt.datetime(2020,5,19,17,55),'Level_in_detrended'].plot(c='k')
        
        # part 2
        detrended1 = df.loc[dt.datetime(2020,6,9,19,20):dt.datetime(2020,6,27,17,25),['Level_in']].dropna()
        detrended1.loc[dt.datetime(2020,6,9,19,20):dt.datetime(2020,6,27,17,25),'Level_in_detrended'] = signal.detrend(detrended1['Level_in']) +1
        df.loc[dt.datetime(2020,6,9,19,20):dt.datetime(2020,6,27,17,25),'Level_in_detrended'] = detrended1.loc[dt.datetime(2020,6,9,19,20):dt.datetime(2020,6,27,17,25),'Level_in_detrended'] +1.
#        df.loc[dt.datetime(2020,6,9,19,20):dt.datetime(2020,6,27,17,25),'Level_in_detrended'].plot(c='r')
        
         # part 3
        detrended3 = df.loc[dt.datetime(2020,6,27,17,25):dt.datetime(2020,8,14,0,0),['Level_in']].dropna()
        detrended3.loc[dt.datetime(2020,6,27,17,25):dt.datetime(2020,8,14,0,0),'Level_in_detrended'] = signal.detrend(detrended3['Level_in']) +1
        df.loc[dt.datetime(2020,6,27,17,25):dt.datetime(2020,8,14,0,0),'Level_in_detrended'] = detrended3.loc[dt.datetime(2020,6,27,17,25):dt.datetime(2020,8,14,0,0),'Level_in_detrended'] +1.
#        df.loc[dt.datetime(2020,6,27,17,25):dt.datetime(2020,8,14,0,0),'Level_in_detrended'].plot(c='r')
        
        # part 4
        detrended4 = df.loc[dt.datetime(2020,8,14,0,5):dt.datetime(2020,9,6,2,45),['Level_in']].dropna()
        detrended4.loc[dt.datetime(2020,8,14,0,5):dt.datetime(2020,9,6,2,45),'Level_in_detrended'] = signal.detrend(detrended4['Level_in'])
        df.loc[dt.datetime(2020,8,14,0,5):dt.datetime(2020,9,6,2,45),'Level_in_detrended'] = detrended4.loc[dt.datetime(2020,8,14,0,5):dt.datetime(2020,9,6,2,45),'Level_in_detrended'] +1.
#        df.loc[dt.datetime(2020,8,14,0,5):dt.datetime(2020,9,6,2,45),'Level_in_detrended'].plot(c='g')
        
        # part 5
        detrended5 = df.loc[dt.datetime(2020,9,6,2,50):dt.datetime(2020,10,7,0,30),['Level_in']].dropna()
        detrended5.loc[dt.datetime(2020,9,6,2,50):dt.datetime(2020,10,7,0,30),'Level_in_detrended'] = signal.detrend(detrended5['Level_in'])
        df.loc[dt.datetime(2020,9,6,2,50):dt.datetime(2020,10,7,0,30),'Level_in_detrended'] = detrended5.loc[dt.datetime(2020,9,6,2,50):dt.datetime(2020,10,7,0,30),'Level_in_detrended'] +1.
#        df.loc[dt.datetime(2020,9,6,2,50):dt.datetime(2020,10,7,0,30),'Level_in_detrended'].plot(c='g')
        
        # part 0
        detrended = df.loc[dt.datetime(2020,10,7,0,35):dt.datetime(2020,11,6,21,35),['Level_in']].dropna()
        detrended.loc[dt.datetime(2020,10,7,0,35):dt.datetime(2020,11,6,21,35),'Level_in_detrended'] = signal.detrend(detrended['Level_in'])
        df.loc[dt.datetime(2020,10,7,0,35):dt.datetime(2020,11,6,21,35),'Level_in_detrended'] = detrended.loc[dt.datetime(2020,10,7,0,35):dt.datetime(2020,11,6,21,35),'Level_in_detrended'] + 1.
#        df.loc[dt.datetime(2020,10,7,0,35):dt.datetime(2020,11,6,21,35),'Level_in_detrended'].plot(c='g')
        
        # smooth the shit out of it
        df['Level_in_detrended'] = df['Level_in_detrended'].rolling(10800, min_periods=3600,center=True).mean() -0.8
#        df['Level_in_detrended'].plot(c='y')
        
        ## Calculate flow from detrended smoothed data in summer 2020
        df.loc[dt.datetime(2020,5,6,18,30):dt.datetime(2020,11,6,21,35),'Flow_cfs_detrended'] = df.loc[dt.datetime(2020,5,6,18,30):dt.datetime(2020,11,6,21,35),'Level_in_detrended'].apply(lambda x: rating_table(rating_curve,x) ).interpolate()
        
        
        ## Offet 2020 Nov data to match measurements
        df.loc[dt.datetime(2020,11,6,21,40):dt.datetime(2020,11,10,19,55),'Level_in'] = df.loc[dt.datetime(2020,11,6,21,40):dt.datetime(2020,11,10,19,55),'Level_in'] - 1. ## offset
        df.loc[dt.datetime(2020,11,6,21,40):dt.datetime(2020,11,10,19,55),'Flow_cfs_offset'] = df.loc[dt.datetime(2020,11,6,21,40):dt.datetime(2020,11,10,19,55),'Level_in'].apply(lambda x: rating_table(rating_curve,x) ).interpolate()
        
        ## Detrend low flow Dec 2020
        detrended6 = df.loc[dt.datetime(2020,11,6,21,35):dt.datetime(2020,12,28,3,20),['Level_in']].dropna()
        detrended6.loc[dt.datetime(2020,11,6,21,35):dt.datetime(2020,12,28,3,20),'Level_in_detrended'] = signal.detrend(detrended6['Level_in'])
        df.loc[dt.datetime(2020,11,6,21,35):dt.datetime(2020,12,28,3,20),'Level_in_detrended'] = detrended6.loc[dt.datetime(2020,11,6,21,35):dt.datetime(2020,12,28,3,20),'Level_in_detrended'].rolling(576, min_periods=144,center=True).mean() + 0.7  ## smooth and then bump up  
        df.loc[dt.datetime(2020,11,6,21,35):dt.datetime(2020,12,28,3,20),'Flow_cfs_detrended'] = df.loc[dt.datetime(2020,11,6,21,35):dt.datetime(2020,12,28,3,20),'Level_in_detrended'].apply(lambda x: rating_table(rating_curve,x) ).interpolate()
        
        ## Offet 2020-21 data to match measurements
        df.loc[dt.datetime(2020,12,28,15,20):dt.datetime(2021,3,26,23,5),'Level_in'] = df.loc[dt.datetime(2020,12,28,15,20):dt.datetime(2021,3,26,23,5),'Level_in'] + 1 ## offset
        df.loc[dt.datetime(2020,12,28,15,20):dt.datetime(2021,3,26,23,5),'Flow_cfs_offset'] = df.loc[dt.datetime(2020,12,28,15,20):dt.datetime(2021,3,26,23,5),'Level_in'].apply(lambda x: rating_table(rating_curve,x) ).interpolate()
        
        ## Detrend low flow March 2021
        detrended7 = df.loc[dt.datetime(2021,3,26,22,50):dt.datetime(2021,4,25,16,25),['Level_in']].dropna()
        detrended7.loc[dt.datetime(2021,3,26,22,50):dt.datetime(2021,4,25,16,25),'Level_in_detrended'] = signal.detrend(detrended7['Level_in']) 
        df.loc[dt.datetime(2021,3,26,22,50):dt.datetime(2021,4,25,16,25),'Level_in_detrended'] = detrended7.loc[dt.datetime(2021,3,26,22,50):dt.datetime(2021,4,25,16,25),'Level_in_detrended'].rolling(576, min_periods=144,center=True).mean() + 1 ## smooth and then bump up  
        df.loc[dt.datetime(2021,3,26,22,50):dt.datetime(2021,4,25,16,25),'Flow_cfs_detrended'] = df.loc[dt.datetime(2021,3,26,22,50):dt.datetime(2021,4,25,16,25),'Level_in_detrended'].apply(lambda x: rating_table(rating_curve,x) ).interpolate()
        
        
        ## Detrend low flow April 2021
        detrended8 = df.loc[dt.datetime(2021,4,28,0,0):,['Level_in']].dropna()
        detrended8.loc[dt.datetime(2021,4,28,0,0):,'Level_in_detrended'] = signal.detrend(detrended8['Level_in'])
        df.loc[dt.datetime(2021,4,28,0,0):,'Level_in_detrended'] = detrended8.loc[dt.datetime(2021,4,28,0,0):,'Level_in_detrended'].rolling(576, min_periods=144,center=True).mean() + 1.## smooth and then bump up  
        df.loc[dt.datetime(2021,4,28,0,0):,'Flow_cfs_detrended'] = df.loc[dt.datetime(2021,4,28,0,0):,'Level_in_detrended'].apply(lambda x: rating_table(rating_curve,x) ).interpolate()

        
        
        ## compile final flow data from good data in 2020 winter, smoothed detrended summer data, and offset 2021 data
        df['Flow_cfs_final'] = df['Flow_cfs']
        ## detrended summer 2020
        df.loc[dt.datetime(2020,5,6,18,30):dt.datetime(2020,11,6,21,35),'Level_in'] =df.loc[dt.datetime(2020,5,6,18,30):dt.datetime(2020,11,6,21,35),'Level_in_detrended']
        df.loc[dt.datetime(2020,5,6,18,30):dt.datetime(2020,11,6,21,35),'Flow_cfs_final'] =df.loc[dt.datetime(2020,5,6,18,30):dt.datetime(2020,11,6,21,35),'Flow_cfs_detrended']
        ## offset Nov 2020
        df.loc[dt.datetime(2020,11,6,21,40):dt.datetime(2020,11,10,19,55),'Flow_cfs_final'] = df.loc[dt.datetime(2020,11,6,21,40):dt.datetime(2020,11,10,19,55),'Flow_cfs_offset']
        ## detrend low flow Dec 2020
        df.loc[dt.datetime(2020,11,10,20,0):dt.datetime(2020,12,28,3,20),'Level_in'] =df.loc[dt.datetime(2020,11,10,20,0):dt.datetime(2020,12,28,3,20),'Level_in_detrended']
        df.loc[dt.datetime(2020,11,10,20,0):dt.datetime(2020,12,28,3,20),'Flow_cfs_final'] =df.loc[dt.datetime(2020,11,10,20,0):dt.datetime(2020,12,28,3,20),'Flow_cfs_detrended']
        ## offset 2020-21
        df.loc[dt.datetime(2020,12,28,15,20):dt.datetime(2021,3,26,23,5),'Flow_cfs_final'] = df.loc[dt.datetime(2020,12,28,15,20):dt.datetime(2021,3,26,23,5),'Flow_cfs_offset']
        ## Detrend low flow march 2021
        df.loc[dt.datetime(2021,3,26,22,50):dt.datetime(2021,4,25,16,25),'Level_in'] =df.loc[dt.datetime(2021,3,26,22,50):dt.datetime(2021,4,25,16,25),'Level_in_detrended']
        df.loc[dt.datetime(2021,3,26,22,50):dt.datetime(2021,4,25,16,25),'Flow_cfs_final'] =df.loc[dt.datetime(2021,3,26,22,50):dt.datetime(2021,4,25,16,25),'Flow_cfs_detrended']
        ## Detrend low flow April 2021
        df.loc[dt.datetime(2021,4,28,0,0):,'Level_in'] =df.loc[dt.datetime(2021,4,28,0,0):,'Level_in_detrended']
        df.loc[dt.datetime(2021,4,28,0,0):,'Flow_cfs_final'] =df.loc[dt.datetime(2021,4,28,0,0):,'Flow_cfs_detrended']
        
#        df['Flow_cfs_final'].plot(c='teal')
#        df['Flow_cfs_detrended'].plot(c='coral')
#        meas['FLOW (CFS)'].plot(ls='None',marker='o')
#        plt.legend()
        
        all_df[sheet+'_Level_in'] = df['Level_in']
        all_df[sheet+'_Flow_cfs'] = df['Flow_cfs_final']
        
    else:
        pass
    
    if sheet == 'GreenValley':
        df[['Level_North_in','GreenValley_Flow_cfs']].plot()   
        meas_N[meas_N['Source'] == 'PUD']['FLOW (CFS)'].plot(ls='None',marker='o',c='r',label='Flow meas by PUD')
        meas_N[meas_N['Source'] == 'Wood']['FLOW (CFS)'].plot(ls='None',marker='o',c='b',label='N Flow meas by Wood')
        plt.title(sheet)
    else:
        df[['Level_in','Flow_cfs']].plot()   
        meas[meas['Source'] == 'Wood']['FLOW (CFS)'].plot(ls='None',marker='o',c='b',label='Flow meas by Wood')
        meas[meas['Source'] == 'PUD']['FLOW (CFS)'].plot(ls='None',marker='o',c='r',label='Flow meas by PUD')
        plt.title(sheet)
        
        plt.legend()
        
#        meas['Cont_Flow_cfs'] = df['Flow_cfs']
#        meas.plot.scatter(x='FLOW (CFS)',y='Cont_Flow_cfs',ls='None',marker='.')
#        plt.plot([0,100],[0,100],c='grey',ls='--')


#%% Resample rating curves for Creeks
        
rating_curves_compiled_creeks = pd.DataFrame(index=np.round(np.arange(0,100,0.1),2))

fig, ax = plt.subplots(1,1)
for sheet in ratings.sheet_names[1:10]:
    print (sheet)
    
    r = random.random()
    b = random.random()
    g = random.random()
    color = (r, g, b)
    if sheet == 'GreenValley':
        highest_stage = data_xl.parse(sheet_name = sheet,index_col=0)['Level_North_in'].max()
    else:
        highest_stage = data_xl.parse(sheet_name = sheet,index_col=0)['Level_in'].max()

    rating_curve = ratings.parse(sheet_name = sheet,index_col=0,skiprows=1)
    
    ## round rating curve to .01 stage and .001 cfs
    rating_curve_rd = pd.DataFrame({'Flow (cfs)':np.round(rating_curve['Flow (cfs)'].values,3)},index = np.round(rating_curve.index,2))
    ## drop duplicates
    rating_curve_rd = rating_curve_rd[rating_curve_rd.index.duplicated()==False]
    ## create new index from the first entry (should be 0.0in) to the last, in 0.01 in increements
    resampled_index = np.round(np.arange(rating_curve_rd.index[0],rating_curve_rd.index[-1], step=0.01),2)
    ## join the rating curve index with the new index, interpolate them

    rating_curve_resampled = rating_curve_rd.reindex(rating_curve_rd.index.union(resampled_index)).interpolate('values').loc[resampled_index]
    ## take every 10th entry to get in 0.1 in increments
    rating_curve_resampled = rating_curve_resampled[::10]
    ## round cfs to 0.001 cfs
    rating_curve_resampled['Flow (cfs)'] = rating_curve_resampled['Flow (cfs)'] .round(3)
    ## rename index
    rating_curve_resampled.index.rename(name = 'Stage (in)',inplace=True)
    
    
    
    ## for plotting
    rating_curve_plot = rating_curve[rating_curve.index <= highest_stage]
    rating_curve_resampled_plot = rating_curve_resampled[rating_curve_resampled.index <= highest_stage]
    
    ## compile with other creeks
    rating_curves_compiled_creeks[sheet+'_Flow_cfs'] = rating_curve_resampled_plot['Flow (cfs)']
    
    ax.plot(rating_curve_resampled_plot.index,rating_curve_resampled_plot['Flow (cfs)'],ls='-',marker='.',c=color,alpha=1,label=sheet+' resampled rating curve')
    plt.legend()
    ax.plot(rating_curve_plot.index,rating_curve_plot['Flow (cfs)'],ls='-',marker='.',c=color,alpha=0.5)
    
    
    ax.annotate(sheet,xy=(rating_curve_resampled_plot.index[-1],rating_curve_resampled_plot['Flow (cfs)'].values[-1]))
ax.set_xlabel('Level (inches)')
ax.set_ylabel('Flow (cfs)')
#ax.set_xscale('log')
#ax.set_yscale('log')
#ax.set_xlim(-1,100)
#ax.set_ylim(-1,100)

rating_curves_compiled_creeks.to_excel(datadir + 'Rating Curves 7_2_2021_creeks_resampled.xlsx')


#%% Resample rating curves for Outfalls

rating_curves_compiled_outfalls = pd.DataFrame(index=np.round(np.arange(0,60,0.1),1).tolist())

#outfall_data_xl = pd.ExcelFile(datadir  + 'Compiled_Outfall_Level_Flow_data.xlsx')

fig, ax = plt.subplots(1,1)
for sheet in ratings.sheet_names[10:]:
    print (sheet)
    
    r = random.random()
    b = random.random()
    g = random.random()
    color = (r, g, b)
    highest_stage = outfall_data_xl.parse(sheet_name = sheet,index_col=0)['Level_in'].max()

    rating_curve = ratings.parse(sheet_name = sheet,index_col=0,skiprows=1)
    
    ## round rating curve to .01 stage and .001 gpm
    rating_curve_rd = pd.DataFrame({'Flow (gpm)':np.round(rating_curve['Flow (gpm)'].values,3)},index = np.round(rating_curve.index,2))
    ## drop duplicates
    rating_curve_rd = rating_curve_rd[rating_curve_rd.index.duplicated()==False]
    ## create new index from the first entry (should be 0.0in) to the last, in 0.01 in increements
    resampled_index = np.arange(0.00, rating_curve_rd.index[-1], step=0.010)
    resampled_index = np.round(resampled_index.tolist(),2).tolist()
    ## join the rating curve index with the new index, interpolate them

    rating_curve_resampled = rating_curve_rd.reindex(rating_curve_rd.index.union(resampled_index)).interpolate('linear').loc[resampled_index]
    ## take every 10th entry to get in 0.1 in increments
    rating_curve_resampled = rating_curve_resampled[::10]
    ## round gpm to 0.001 gpm
    rating_curve_resampled['Flow (gpm)'] = rating_curve_resampled['Flow (gpm)'].round(3)
    ## rename index
    rating_curve_resampled.index.rename(name = 'Stage (in)',inplace=True)
    
    ## for plotting
    
    rating_curve_plot = rating_curve[rating_curve.index <= highest_stage]
    rating_curve_resampled_plot = rating_curve_resampled[rating_curve_resampled.index <= highest_stage]
    
    ## compile with other creeks
    rating_curves_compiled_outfalls[sheet+'_Flow_gpm'] = rating_curve_resampled_plot['Flow (gpm)']
    
    ax.plot(rating_curve_resampled_plot.index,rating_curve_resampled_plot['Flow (gpm)'],ls='-',marker='.',c=color,alpha=1,label=sheet+' resampled rating curve')
    plt.legend()
    ax.plot(rating_curve_plot.index,rating_curve_plot['Flow (gpm)'],ls='-',marker='.',c=color,alpha=0.5)
    
    
    
    ax.annotate(sheet,xy=(rating_curve_resampled_plot.index[-1],rating_curve_resampled_plot['Flow (gpm)'].values[-1]))
ax.set_xlabel('Level (inches)')
ax.set_ylabel('Flow (gpm)')

rating_curves_compiled_outfalls.to_excel(datadir + 'Rating Curves 7_2_2021_outfalls_resampled_gpm.xlsx')

rating_curves_compiled_outfalls_cfs = rating_curves_compiled_outfalls * 0.0022
rating_curves_compiled_outfalls_cfs.columns = [x.replace('gpm','cfs') for x in rating_curves_compiled_outfalls_cfs.columns]
rating_curves_compiled_outfalls_cfs.to_excel(datadir + 'Rating Curves 7_2_2021_outfalls_resampled_cfs.xlsx')

#%%

pd.concat([rating_curves_compiled_creeks,rating_curves_compiled_outfalls_cfs],axis=1).to_excel(datadir + 'Rating Curves 7_2_2021_ALL_resampled_cfs.xlsx')


#%%



df = outfall_data_xl.parse(sheet_name = 'Tazon',index_col=0)

rating_curve_man = ratings.parse(sheet_name = "Tazon_Mannings",index_col=0,skiprows=1)







