# -*- coding: utf-8 -*-
"""
Created on Mon Sep  9 18:52:30 2019

@author: jonbs
"""

#from roboBee_class import *
from roboBee_class_state_space import *

tester = roboBee()
#tester.getState()
#tester.readSensors()
#tester.updateState()
#print(tester.orientation)

#tester.run(1200)

"""
u_empty = np.zeros(6)
dt = 1 / 120
tester.real_state_space(u_empty, dt)
"""


#tester.run_real_state_space(1000)
#tester.run(1000)
u_test = np.array([0, 0, 0, 10, 0, 0])
dt = 1/120
u_des = np.array([0, 0, 10, 10, 0, 0])
tester.updateState_LQR_Control(u_test, dt, u_des)
