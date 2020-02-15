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

tester.run_lqr(5)

"""
JIA: use the 'input' and 'output' variables below to train the neural network, if
    you want more data, just increaes x in run_pd(x) as that is the number of time
    steps the simulation will run
"""
#input, output = tester.run_pd(1000)
