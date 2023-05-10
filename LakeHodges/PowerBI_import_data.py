# -*- coding: utf-8 -*-
"""
Created on Wed Nov 24 15:09:42 2021

@author: alex.messina
"""

import os
import pandas as pd

maindir = "C:/Users/alex.messina/Documents/LinkComm/Log Files/"

df_all = pd.DataFrame()
for f in os.listdir(maindir):
    #print (f)
    if "SYCAMORE_loggrp" in f:
        print (f)
        try:
            df =  pd.read_csv(maindir+f,index_col=0,header=0,skiprows=[1])
        except:
            print ("Can't open file")
        df_all = df_all.append(df)
