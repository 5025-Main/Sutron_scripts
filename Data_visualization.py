# -*- coding: utf-8 -*-
"""
Created on Wed Feb 12 14:37:28 2020

@author: alex.messina
"""

import pandas as pd
from matplotlib import pyplot as plt
import datetime as dt
## Set Pandas display options
pd.set_option('display.large_repr', 'truncate')
pd.set_option('display.width', 180)
pd.set_option('display.max_rows', 40)
pd.set_option('display.max_columns', 13)
plt.ion()

datadir = 'C:/Users/alex.messina/Documents/GitHub/Sutron_scripts/Data Download/'
filename = 'LakeHodges_FELICITA_log_20200210_01.csv'
#%%

df_all = pd.DataFrame.from_csv(datadir+filename,header=5).reset_index()
df_all.columns=['Param','Date','Time','Result','Quality']
df_all['Datetime'] = df_all['Date']+' '+df_all['Time']

level = df_all[df_all['Param']=='PT Level'][['Datetime','Result']]
level['Datetime'] = pd.to_datetime(level['Datetime'])
level = level.set_index('Datetime')

#flow = df_all[df_all['Param']=='Flow_cfs'][['Datetime','Result']]
#flow['Datetime'] = pd.to_datetime(flow['Datetime'])
#flow = flow.set_index('Datetime')
#
#aliquots =  df_all[df_all['Param']=='Triggered S'][['Datetime','Result']]
#aliquots['Datetime'] = pd.to_datetime(aliquots['Datetime'])
#aliquots = aliquots.set_index('Datetime')
#aliquots['Flow'] = flow['Result']
#
#alarm_in = df_all[df_all['Param']=='Alarm In'][['Datetime','Result']]
#alarm_in['Datetime'] = pd.to_datetime(alarm_in['Datetime'])
#alarm_in = alarm_in.set_index('Datetime')
#
#alarm_out = df_all[df_all['Param']=='Alarm Out'][['Datetime','Result']]
#alarm_out['Datetime'] = pd.to_datetime(alarm_out['Datetime'])
#alarm_out = alarm_out.set_index('Datetime')


#%%
fig, ax1 = plt.subplots(1,1,figsize=(16,8))
fig.suptitle(filename,fontsize=14,fontweight='bold')

ax1.plot_date(level.index,level['Result'],ls='-',marker='None',c='r',label='Water Level from PT')
ax1.set_ylabel('Water Level (inches)',color='r',fontsize=14,fontweight='bold')
ax1.spines['left'].set_color('r')
ax1.tick_params(axis='y',colors='r',labelsize=14)
ax1.xaxis.set_major_formatter(mpl.dates.DateFormatter('%A \n %m/%d/%y %H:%M'))

# Delineate alarms
#ax1.axvline(alarm_in.index[0],c='g')
#ax1.axvline(alarm_out.index[0],c='r')



ax2 = ax1.twinx()
ax2.plot_date(flow.index,flow['Result'],ls='-',marker='None',c='b',label='Flow from HvF')
#ax2.plot_date(aliquots.index,aliquots['Flow'],ls='None',marker='o',c='k',label='Aliquots')
#for al in aliquots.iterrows():
#    print al
#    al_num = "%.0f"%al[1]['Result']
#    ax2.annotate(al_num,xy=(pd.to_datetime(al[0]),al[1]['Flow']*1.1),ha='center')

ax2.set_ylabel('Flow (cfs)',color='b',fontsize=14,fontweight='bold')
ax2.spines['right'].set_color('b')
ax2.tick_params(axis='y',colors='b',labelsize=14)


ax1.legend(fontsize=14,ncol=1,loc='upper left')
ax2.legend(fontsize=14,loc='upper right')

plt.tight_layout()
plt.subplots_adjust(top=0.95)

#%%








