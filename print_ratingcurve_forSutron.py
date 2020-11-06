# -*- coding: utf-8 -*-
"""
Created on Thu Oct 29 13:08:50 2020

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

#site = 'DELDIOS'
#site = 'FELICITA'
#site = 'KITCARSON'
site = 'CLOVERDALE'
#site = 'GREENVALLEY'
#site = 'MOONSONG'
#site = 'SDG_CRK'


datadir = 'C:/Users/alex.messina/Documents/GitHub/Sutron_scripts/Data Download/'

rating_curves = pd.ExcelFile(datadir+'Current_RatingCurves.xlsx')
rating_curve = rating_curves.parse(sheetname='4. San Dieguito',skiprows=1,header=0)
rating_curve = rating_curve.round(2)
rating_curve.index = rating_curve['Stage (in)']

STAGETBL = zip(rating_curve['Stage (in)'].values,rating_curve['Q Total (cfs)'].values)
    
for i in STAGETBL:
    print str((float('%.2f'%i[0]), float('%.2f'%i[1])))+','