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

"""
The run_lqr function will return two arrays of size (4, nt) where nt is the integer passed
to the run_lqr function that determines how many time steps are run. The output array should only
have values in its second row, as that corresponds to the only state the robot can directly
control. I can explain the physics behind this if you'd like, just ask me
"""

input, output = tester.run_analytical(2500)

print(input[0].shape, output.shape)


"""
JIA: use the 'input' and 'output' variables below to train the neural network, if
    you want more data, just increaes x in run_pd(x) as that is the number of time
    steps the simulation will run
"""
#input, output = tester.run_pd(1000)
