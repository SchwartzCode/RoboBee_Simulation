from pyquaternion import Quaternion
import numpy as np

my_quat = Quaternion(axis=[1,0,0], angle=3.14159)

print(my_quat)

z_hat = np.array([0,0,1])
z_prime = my_quat.rotate(z_hat)
#print(z_hat)
#print(z_prime)

v = np.array([0.,0.,1.])

x_rot = Quaternion(axis=[1,0,0], angle=3.14159265/2) #rotate 180 about X
y_rot = Quaternion(axis=[0,1,0], angle=3.14159265/2) #rotate 90 degrees about Y
total_rot = y_rot*x_rot #performs x_rot then y_rot
#print("a", total_rot)
v_rot = total_rot.rotate(v)
print(v_rot)
