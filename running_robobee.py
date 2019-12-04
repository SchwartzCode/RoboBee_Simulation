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

test = np.zeros((6,6))
test[0,3] = 5
print(test)
