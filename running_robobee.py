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

#tester.run(10000)


a1 = np.array([0, 1, 0])
a2 = np.array([np.sqrt(2)/2, np.sqrt(2)/2, 0])
print(np.dot(a1, a2))
u_empty = np.zeros(12)
dt = 1 / 120
tester.real_state_space(u_empty, dt)


#test = np.zeros((6,6))
#test[0,3] = 5
#print(test)
