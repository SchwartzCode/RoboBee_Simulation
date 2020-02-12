# -*- coding: utf-8 -*-
"""
Created on Mon Sep  9 18:52:30 2019

@author: jonbs
"""

#from roboBee_class import *
from roboBee_class_state_space import *

tester = roboBee()
#tester.run_analytical(1200)
#tester.run_pd(1200)

#tester.run_lqr(500)

"""
JIA: use the 'input' and 'output' variables below to train the neural network, if
    you want more data, just increaes x in run_pd(x) as that is the number of time
    steps the simulation will run
"""
input, output = tester.run_pd(1000)



"""
u_test = np.array([0, 0, 0, 10, 0, 0])
dt = 1/120
u_des = np.array([0, 0, 10, 5, 0, 0])
tester.updateState_LQR_Control(u_test, dt, u_des)
"""
