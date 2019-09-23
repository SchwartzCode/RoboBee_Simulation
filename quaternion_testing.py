from pyquaternion import Quaternion
import numpy as np

#think of x and y as axes on paper and z as axis coming out of paper

def initial_test():
    my_quat = Quaternion(axis=[1,0,0], angle=3.14159)

    print(my_quat)

    z_hat = np.array([0,0,1])
    z_prime = my_quat.rotate(z_hat)
    #print(z_hat)
    #print(z_prime)

def basic_rotation():
    v = np.array([0.,0.,1.])

    x_rot = Quaternion(axis=[1,0,0], angle=3.14159265/2) #rotate 90 degrees about X
    y_rot = Quaternion(axis=[0,1,0], angle=3.14159265/2) #rotate 90 degrees about Y
    total_rot = y_rot*x_rot #performs x_rot then y_rot
    #print("a", total_rot)
    v_rot = total_rot.rotate(v)
    v_reverse = (x_rot*y_rot).rotate(v) #performs y_rot then x_rot
    print(v_rot)
    print(v_reverse)

def increment_rotation(n_val):
    #this did not work as I expected; I didn't realize the changing relation between the x/y/z axes and
    #the orientation vector meant the amount of the rotation would change
    v = np.array([0., 0., 1.])
    n = n_val
    half_pi = np.pi / 2

    x_rot = Quaternion(axis=[1,0,0], angle=half_pi/n) #rotate 90 degrees about X
    y_rot = Quaternion(axis=[0,1,0], angle=half_pi/n) #rotate 90 degrees about Y

    for i in range(n):
        v_new = (x_rot*y_rot).rotate(v)
        v = v_new
        print(v)




print("hi")
increment_rotation(10)
