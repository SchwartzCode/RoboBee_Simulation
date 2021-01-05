# -*- coding: utf-8 -*-
"""
Created on Mon Sep  9 18:52:30 2019

@author: jonbs
"""

import time

#from roboBee_class import *
from roboBee_class_PD_and_LQR import *

tester = roboBee()
#tester.run_analytical(1200)
#tester.run_pd(1200)




#print(input[0].shape, output.shape)


"""
JIA: use the 'input' and 'output' variables below to train the neural network, if
    you want more data, just increaes x in run_pd(x) as that is the number of time
    steps the simulation will run
"""
input, output = tester.run_lqr(3500, verbose=True)
#input1, output1 = tester.run_pd(1000)

"""
#Timing different method funcs, will probably delete eventually

start = time.time()
for i in range(2500):
    print(i)
end = time.time()
print("LQR controller: ", end - start)


start = time.time()
for i in range(10):
    tester.run_lqr(2500)
end = time.time()
print("LQR controller: ", end - start)

start = time.time()
for i in range(10):
    tester.run_pd(2500)
end = time.time()
print("PD controller: ", end - start)

start = time.time()
for i in range(10):
    tester.run_analytical(2500)
end = time.time()
print("Analytical controller: ", end - start)

"""
