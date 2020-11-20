# -*- coding: utf-8 -*-
"""
Created on Thu Oct 29 13:24:32 2020

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

#datadir = 'P:/Projects-South/Environmental - Schaedler/5025-19-1029 City of SD TO 29 Hodges Nutrient Source Investigation/Data & Field Records/Flow data/Outfalls/Rating Curves/'
datadir = 'C:/Users/alex.messina/Documents/GitHub/Sutron_scripts/LakeHodges/Outfalls/'

fname= 'Oceans 11 Rating Curve.xlsx'

df = pd.read_excel(datadir +fname,sheetname='Flow Data',skiprows=[1],index_col=0)
df = df.rename(columns={'Level':'Level_in','Vel. 1':'Vel_fps','Flow 1':'Flow_gpm',"Manning's Flow":'Flow_Man_gpm'})
df = df[['Level_in','Vel_fps','Flow_gpm']]#,'Flow_Man_gpm']]
## Via Rancho is in cfs
if fname.startswith('Via Rancho'):
    df = df.rename(columns={'Flow_gpm':'Flow_cfs'})


## Remove duplicates
df=df[df.index.duplicated()==False]
## Reindex
df = df.reindex(pd.date_range(dt.datetime(2020,1,1,0,0),dt.datetime(2020,10,1,0,0),freq='5Min'))


## Copy level for offset
df['Level_in_offset'] = df['Level_in']

## Offset ElKu level
if fname == 'El Ku Rating Curve.xlsx':
    df['Level_in_offset'][dt.datetime(2020,3,10,0,15):dt.datetime(2020,4,4,17,25)] =  df['Level_in'][dt.datetime(2020,3,10,0,15):dt.datetime(2020,4,4,17,25)] - 0.875
    
    df['Level_in_offset'][dt.datetime(2020,4,7,2,10):dt.datetime(2020,4,9,0,0)] = df['Level_in'][dt.datetime(2020,4,7,2,10):dt.datetime(2020,4,9,0,0)] - 0.7

    #df = df[dt.datetime(2020,4,6,0,0):dt.datetime(2020,4,9,0,0)]
    
## Read in rating curve
rating_curve = pd.read_excel(datadir +fname,sheetname='HvF',index_col=0)

#%% TIME SERIES


fig, (ax1,ax2) = plt.subplots(2,1,sharex=True,figsize=(12,8))
ax1.plot_date(df.index,df['Level_in'],marker='None',ls='-',label='Level_in',c='b')
ax1.plot_date(df.index,df['Level_in_offset'],marker='None',ls='-',label='Level_in_offset',c='teal')

ax1_2 = ax1.twinx()
ax1_2.plot_date(df.index,df['Vel_fps'],marker='None',ls='-',label='Vel_fps',c='r')

ax1.set_ylim(0,7), ax1_2.set_ylim(0,7)

if fname.startswith('Via Rancho'):
    ax2.plot_date(df.index,df['Flow_cfs'],marker='None',ls='-',label='Flow_950',c='b')
else:
    ax2.plot_date(df.index,df['Flow_gpm'],marker='None',ls='-',label='Flow_950',c='b')
ax2_2 = ax2.twinx()
#ax2_2.plot_date(df.index,df['Flow_Man_gpm'],marker='None',ls='-',label='Flow_Mannings',c='orange')

ax1.xaxis.set_major_formatter(mpl.dates.DateFormatter('%m/%d/%y %H:%M'))
ax2.xaxis.set_major_formatter(mpl.dates.DateFormatter('%m/%d/%y %H:%M'))

ax1.legend(loc='upper left'),ax2.legend(loc='upper left')
ax1_2.legend(loc='upper right'),ax2_2.legend(loc='upper right')
plt.tight_layout()

#%%  SCATTER PLOT - LEVEL vs VEL

import matplotlib.dates as dates

fig, ax1 = plt.subplots(1,1)
fig.suptitle(fname)
ax1.scatter(df['Level_in'], df['Vel_fps'],marker='.',c='grey',label='Level_raw')
cmap = plt.cm.rainbow
t = pd.to_numeric(df.index.values)
im = ax1.scatter(df['Level_in_offset'], df['Vel_fps'],marker='.',c=t, cmap=cmap,label='Level_offset')

ax1.set_ylabel('Velocity (fps)',fontsize=14,fontweight='bold')
ax1.set_xlabel('Level (in)',fontsize=14,fontweight='bold')

## ColorBar
m = cm.ScalarMappable(norm=mpl.colors.Normalize(vmin=t[0], vmax=t[1]),cmap=cmap)
m._A = []
cb = fig.colorbar(im,ax=ax1)
cb.ax.set_yticklabels([pd.to_datetime(x).strftime("%m/%d %H:%M") for x in cb.get_ticks()])
cb.ax.invert_yaxis()

#%%
## Regression for Lomica
if fname.startswith('Lomica'):
    # Fitting Polynomial Regression to the dataset 
    from sklearn.linear_model import LinearRegression 
    from sklearn.preprocessing import PolynomialFeatures 
    df1 = df.dropna()
    df1 = df[df['Level_in']<3.5]
    X = df1.iloc[:, 0].values.reshape(-1, 1)  # values converts it into a numpy array
    y = df1.iloc[:, 1].values.reshape(-1, 1)  # -1 means that calculate the dimension of rows, but have 1 column
    
    ## Linear Regression
    lin = LinearRegression() 
    lin.fit(X,y) 
    y_pred = lin.predict(X)
    plt.plot(X,y_pred, color = 'red') 

    # Fitting Polynomial Regression to the dataset
    from sklearn.preprocessing import PolynomialFeatures
    poly = PolynomialFeatures(degree = 2)
    X_poly = poly.fit_transform(X)
    poly.fit(X_poly, y)
    lin2 = LinearRegression()
    lin2.fit(X_poly, y)
    x = df.dropna().iloc[:, 0].values.reshape(-1, 1)
    plt.plot(x, lin2.predict(poly.fit_transform(x)),marker='.',ls='None', color = 'blue', label='Linear Regression')

    # Exponential fit
    import numpy as np
    from scipy.optimize import curve_fit
    import matplotlib.pyplot as plt
    def func_exp(x, a, b, c):
            #c = 0
            return a * np.exp(b * x) + c
    def exponential_regression (x_data, y_data):
        popt, pcov = curve_fit(func_exp, x_data, y_data, p0 = (-1, 0.01, 1.))
        print(popt)
        #puntos = plt.plot(x_data, y_data, 'x', color='xkcd:maroon', label = "data")
        regr_line = plt.plot(x_data, func_exp(x_data, *popt)*1.2, color='xkcd:teal', label = "Exponential fit: {:.3f}, {:.3f}, {:.3f}".format(*popt),marker='.',ls='None')
        plt.legend()
        plt.show()
        return func_exp(x_data, *popt)
    df2 = df.dropna()
    #params = exponential_regression(df2['Level_in'],df2['Vel_fps'])[1]
    #a,b,c = params[0], params[1], params[2]
    
    a,b,c = -7.56796662, -0.36521798,  7.44258877
    print a, b, c
    
    df['Vel_fps_pred'] = ( a * np.exp(b * df['Level_in_offset']) +c ) *1.2
    ax1.scatter(df['Level_in_offset'], df['Vel_fps_pred'],marker='.',c='k') #,label='Predicted velocity')
    ## Predicted Flow from Predicted Velocity
    ## Area of partially full pipe: https://www.engineeringtoolbox.com/pipes-equations-d_873.html
    pipe_diam = 36
    radius = pipe_diam/2.
    df['angle'] = df['Level_in_offset'].apply(lambda x: 2 * math.acos((radius - x)/radius))
    df['Area_sq_in'] = df['angle'].apply(lambda x: (radius**2  * (x - math.sin(x)))/2)
    df['Area_sq_ft'] = df['Area_sq_in'] * 0.00694444
    df['Flow_cfs_pred'] = df['Area_sq_ft'] *  df['Vel_fps_pred'] 
    df['Flow_gpm_pred'] = df['Flow_cfs_pred'] * 448.8325660485


#%%  SCATTER PLOT - Vel vs Level

## Regression for Oceans11
import matplotlib.dates as dates

fig, ax1 = plt.subplots(1,1)
fig.suptitle(fname)
ax1.scatter(df['Vel_fps'],df['Level_in'], marker='.',c='grey',label='Level_raw')
cmap = plt.cm.rainbow
t = pd.to_numeric(df.index.values)
im = ax1.scatter(df['Vel_fps'], df['Level_in_offset'],marker='.',c=t, cmap=cmap,label='Level_offset')

ax1.set_xlabel('Velocity (fps)',fontsize=14,fontweight='bold')
ax1.set_ylabel('Level (in)',fontsize=14,fontweight='bold')

## ColorBar
m = cm.ScalarMappable(norm=mpl.colors.Normalize(vmin=t[0], vmax=t[1]),cmap=cmap)
m._A = []
cb = fig.colorbar(im,ax=ax1)
cb.ax.set_yticklabels([pd.to_datetime(x).strftime("%m/%d %H:%M") for x in cb.get_ticks()])
cb.ax.invert_yaxis()

## Regression for Oceans11
if fname.startswith('Oceans'):
    # Fitting Polynomial Regression to the dataset 
    from sklearn.linear_model import LinearRegression 
    df1 = df.dropna()
    df1 = df[df['Vel_fps']<1.8]
    X = df1.iloc[:, 1].values.reshape(-1, 1)  # values converts it into a numpy array
    y = df1.iloc[:, 0].values.reshape(-1, 1)  # -1 means that calculate the dimension of rows, but have 1 column
    
    ## Linear Regression
    lin = LinearRegression().fit(X,y) 
    x_range = np.arange(0,10,1).reshape(-1, 1)
    y_pred = lin.predict(x_range)
    plt.plot(x_range,y_pred, color = 'red') 

    df['Level_in_pred_linear'] = df['Vel_fps'] * lin.coef_[0]

    #ax1.scatter( df['Vel_fps'], df['Level_in_offset'],marker='.',c='k') #,label='Predicted velocity')
    

    # Exponential fit
    import numpy as np
    from scipy.optimize import curve_fit
    import matplotlib.pyplot as plt
    def func_exp(x, a, b, c):
            #c = 0
            return a * np.exp(b * x) + c
    def exponential_regression (x_data, y_data):
        popt, pcov = curve_fit(func_exp, x_data, y_data, p0 = (-1, 0.01, 1.))
        print(popt)
        #puntos = plt.plot(x_data, y_data, 'x', color='xkcd:maroon', label = "data")
        regr_line = plt.plot(x_data, func_exp(x_data, *popt), color='xkcd:teal', label = "Exponential fit: {:.3f}, {:.3f}, {:.3f}".format(*popt),marker='.',ls='None')
        plt.legend()
        plt.show()
        return func_exp(x_data, *popt), popt
    df2 = df1.dropna()
    params = exponential_regression(df2['Vel_fps'],df2['Level_in'])[1]
    a,b,c = params[0], params[1], params[2]
    print a, b, c
    df['Level_in_pred'] = ( a * np.exp(b * df['Vel_fps']) +c ) 
    ax1.scatter( df['Vel_fps'],df['Level_in_pred'],marker='.',c='k') #,label='Predicted velocity')
    
    ## Predicted Flow from Predicted Level (from velocity)
    ## Area of partially full pipe: https://www.engineeringtoolbox.com/pipes-equations-d_873.html
    pipe_diam = 24
    radius = pipe_diam/2.
    df['angle'] = df['Level_in_pred'].apply(lambda x: 2 * math.acos((radius - x)/radius))
    df['Area_sq_in'] = df['angle'].apply(lambda x: (radius**2  * (x - math.sin(x)))/2)
    df['Area_sq_ft'] = df['Area_sq_in'] * 0.00694444
    df['Flow_cfs_pred'] = df['Area_sq_ft'] *  df['Vel_fps'] 
    df['Flow_gpm_pred'] = df['Flow_cfs_pred'] * 448.8325660485

## FMT
ax1.legend(loc='lower right')
ax1.set_ylim(0,df['Level_in_pred'].max()*1.1), ax1.set_xlim(0,df['Vel_fps'].max()*1.1)

#%%  SCATTER PLOT - LEVEL vs FLOW

fig, ax1 = plt.subplots(1,1)
fig.suptitle(fname)

## Level vs Flow
if fname.startswith('Via Rancho'):
    ax1.scatter(df['Level_in'], df['Flow_cfs'],marker='.',c='grey',label='Level_raw')
else:
    ax1.scatter(df['Level_in'], df['Flow_gpm'],marker='.',c='grey',label='Level_raw')

cmap = plt.cm.rainbow
t = pd.to_numeric(df.index.values)


## Level_offset vs Flow
if fname.startswith('Via Rancho'):
    im = ax1.scatter(df['Level_in_offset'], df['Flow_cfs'],marker='.',c=t, cmap=cmap,label='Level_offset')
#    ax1.scatter(rating_curve.index,rating_curve['Flow (cfs)'],marker='.',s=1,c='grey',label='Rating Curve')
    ax1.set_xlim(0,1.1*df['Level_in'].max()), ax1.set_ylim(0,1.1*df['Flow_cfs'].max())
    
elif fname.startswith('Oceans 11'):
    im = ax1.scatter(df['Level_in_offset'], df['Flow_gpm'],marker='.',c=t, cmap=cmap,label='Level_offset')
    ax1.scatter(df['Level_in_pred'], df['Flow_gpm_pred'],marker='.',c='r',s=1,label='Predicted Flow (gpm)')
#    ax1.scatter(rating_curve.index,rating_curve['Flow (gpm)'],marker='.',c='k',label='Rating Curve')
    ax1.set_xlim(0,1.1*df['Level_in_offset'].max()), ax1.set_ylim(0,1.1*df['Flow_gpm'].max())
    
    
elif fname.startswith('El Ku'):
    im = ax1.scatter(df['Level_in_offset'], df['Flow_gpm'],marker='.',c=t, cmap=cmap,label='Level_offset')
    ax1.scatter(rating_curve.index,rating_curve['Flow (gpm)']*1.4,marker='.',c='k',s=1,label='Rating Curve (adjusted)')
    ax1.set_xlim(0,1.1*df['Level_in_offset'].max()), ax1.set_ylim(0,1.1*df['Flow_gpm'].max())
    
else:
    im = ax1.scatter(df['Level_in_offset'], df['Flow_gpm'],marker='.',c=t, cmap=cmap,label='Level_offset')
    ax1.scatter(rating_curve.index,rating_curve['Flow (gpm)'],marker='.',c='k',s=1,label='Rating Curve')
    ax1.set_xlim(0,1.1*df['Level_in_offset'].max()), ax1.set_ylim(0,1.1*df['Flow_gpm'].max())
    
    
## ColorBar
m = cm.ScalarMappable(norm=mpl.colors.Normalize(vmin=t[0], vmax=t[1]),cmap=cmap)
m._A = []
cb = fig.colorbar(im,ax=ax1)
cb.ax.set_yticklabels([pd.to_datetime(x).strftime("%m/%d %H:%M") for x in cb.get_ticks()])
cb.ax.invert_yaxis()

## FMT
if fname.startswith('Via Rancho'):
    ax1.set_ylabel('Flow (cfs)',fontsize=14,fontweight='bold')
else:
    ax1.set_ylabel('Flow (gpm)',fontsize=14,fontweight='bold')
ax1.set_xlabel('Level (in)',fontsize=14,fontweight='bold')
ax1.legend(loc='lower right')


#%% Print curve for Sutron
if fname.startswith('Via Rancho'):
    STAGETBL = zip(rating_curve.index.values,rating_curve['Flow (cfs)'].values)
    
elif fname.startswith('Lomica'):
    df_sort = df[df['Level_in_offset']  >= 0.].sort_values(by='Level_in_offset').drop_duplicates(subset='Level_in_offset')
    STAGETBL = zip(df_sort['Level_in_offset'].values, df_sort['Flow_gpm_pred'].values)

elif fname.startswith('Oceans 11'):
    print 'Oceans 11 rating curve from predicted level and predicted flow'
    df_sort = df[df['Level_in_pred']  >= 0.].sort_values(by='Level_in_pred').drop_duplicates(subset='Level_in_pred')
    STAGETBL = zip(df_sort['Level_in_pred'].values, df_sort['Flow_gpm_pred'].values)

elif fname.startswith('El Ku'):
    print 'El Ku rating curve with 1.4X adjustment'
    STAGETBL = zip(rating_curve.index.values,rating_curve['Flow (gpm)'].values * 1.4)

else:
    STAGETBL = zip(rating_curve.index.values,rating_curve['Flow (gpm)'].values)


for i in STAGETBL[::10]:
    print str((float('%.2f'%i[0]), float('%.2f'%i[1])))+','
    rating_df = pd.DataFrame.from_records(STAGETBL)
    if fname.startswith('Via Rancho') == False:
        rating_df.columns = ['Level_in','Flow_gpm']
    elif fname.startswith('Via Rancho'):
        rating_df.columns = ['Level_in','Flow_cfs']
    
    rating_df.to_csv(datadir+'Rating Curves from Python script/Rating_Curve_'+fname.replace(' Rating Curve.xlsx','')+' v1_0.csv')






