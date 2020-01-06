import numpy as np
from pyquaternion import Quaternion
import matplotlib.pyplot as plt

class roboBee(object):
    """  CONSTANTS & ROBOT SPECS   """
    TORQUE_CONTROLLER_CONSTANT = 0.9e-7
    B_w = 0.0002 #drag constant [Ns/m]
    Rw = 0.009
    R_w = np.array([0.0, Rw, 0.0]) #z distance between center of mass and wings [m]
    MASS = 0.08 #mass [g]
    g = 9.81 #gravity
    Jz = 0.45e-9 #Z Axis Rotational Moment of Inertia [kg*m^2]
    FLAPPING_FREQ = 120.0 #[Hz]
    WING_LENGTH = 15.0 #[mm]
    MEAN_CHORD_LENGTH = 3.46 #[mm]
    AREA = 55 #[mm^2]
    WING_INERTIA = 45.3 #inertia of wing about flapping axis [mg/mm^2]
    WING_MASS = 1.0 #[mg]
    SENSOR_NOMINAL_VAL = 1.1 #[mA]
    GLOBAL_FRAME = np.identity(3)
    inertial_frame = GLOBAL_FRAME
    LIFT_COEFFICIENT = 1.0
    LIFT = np.array([0.0, LIFT_COEFFICIENT*MASS*g, 0.0]) #lift force generated by wings [N]
    increased = False


    pos = np.array([0.0, 0.0, 0.0]) #(x,y,z) position coords [m]
    vel = np.array([0.0, 0.0, 0.0]) #(x,y,z) velocity components [m/s]
    accel = np.array([0.0, 0.0, 0.0]) #(x,y,z) acceleration components [m^2/s]
    INITIAL_ORIENTATION = np.array([0.0, 1.0, 0.0]) #orientation vector of robot if it is pointing straight upwards (x, y, z)
    angular_vel = np.zeros(3) #velocity of robot in (x, y, z) [rad/s]
    angular_accel = np.zeros(3)


    dt = 1/120 #1/120 #time step in seconds; represents one step at 120 Hz
    light_source_loc = np.array([0.0, 1000.0, 0.0]) #location of light source [mm]
    sensor_readings = np.array([0.0, 0.0, 0.0, 0.0]) #current flowing from phototransistors, between 1.1mA and 100 nA
    INITIAL_SENSOR_ORIENTATIONS = np.array([ [np.sqrt(0.75),   0.5,  0.0], #vectors normal to each sensor face at initial orientation (x,y,z)
                                          [0.0,             0.5,  np.sqrt(0.75)],
                                          [-np.sqrt(0.75),  0.5,  0.0],
                                          [0.0,             0.5,  -np.sqrt(0.75)]])
    sensor_orientations = INITIAL_SENSOR_ORIENTATIONS


    def __init__(self):
        self.state = np.array([0.0, 10.0, 0.0,   #position (x, y, z)
                               0.0, 0.0, 0.0,   #velocity
                               0.0, 1.0, 0.0,   #orientation (basically theta)
                               1.0, 0.0, 0.0])  #angular velocity

    def normalize(self, x):
        normalized = x / np.linalg.norm(x)
        return normalized

    def real_state_space(self, u, dt):
        """
        This function will calculate the new state using the current state
        and only a large matrix of coefficients, this is necessary
        in order to use LQR control.

        This is what state space is like, where x_dot is deriv of x, which is the
        state vector, i is the input vector, and A and B are coefficient matrices:

                            x_dot = A*x + B*i


        ==== ARGUMENTS ====
        u = current state (12 double numpy 1D array)
            u[0] = theta (angle of rotation from intertial to global coords in 2D)
            u[1] = theta_dot (change in theta per unit time)
            u[2] = x axis position in global coordinates
            u[3] = z axis position in global coordinates
            u[4] = x_dot (x axis velocity)
            u[5] = z_dot (z axis velocity)
        dt = time step [seconds], usually 1/120 (wings flap at 120 Hz)
        """

        A = np.zeros((6, 6))
        B = np.zeros(6)
        #Derivative of angular positon is angular velocity
        A[0,1] = 1
        #Derivative of position is velocity
        A[2,4] = 1
        A[3,5] = 1

        # V_x_dot terms
        A[4,0] = self.g*(self.LIFT_COEFFICIENT - 1)
        A[4,4] = -self.B_w

        # Theta_dot term(s)
        A[1,4] = -self.R_w*self.B_w

        #Note: There are no terms in the A matrix for V_z_dot because that is
        #   controlled by the altitude controller which is decoupled from this
        #   controller (the latitude controller)


        #Apply input torque (as of now this is just the torque generated by torque
        #controller that keeps robot upright)
        B[1] = -self.TORQUE_CONTROLLER_CONSTANT

        """
        #Calculating Angular Acceleration terms
        A[9,5] = self.Rw / self.Jz
        A[9,9] = self.Rw**2 / self.Jz

        A[11,3] = -self.Rw / self.Jz
        A[11,11] = self.Rw**2 / self.Jz

        #Adding torque inputs to angular acceleration terms
        B[9,0] = 1 / self.Jz
        B[10,1] = 1 / self.Jz
        B[11,2] = 1 / self.Jz
        """

        print(A)
        print(B)



        return u


    def update_state(self, u, dt):
        """
        This function generates translational and angular accelerations
        based on the current state (position, orientation, velocities) of the
        robot. It then uses these to calculate the new state_dot

        u = current state (12 double numpy 1D array)
            u[:3]  = position in global coordinates [m]
            u[3:6] = velocity in inertial frame [m/s]
            u[6:9] = orientation vector (in global coords)
            u[9:]  = angular velocities about inertial reference frame [rad/sec]
        dt = time step [seconds], usually 1/120 (wings flap at 120 Hz)
        """


        #this ensures the robot's altitude doesn't get too low or high
        if u[1] < 10.0 and not self.increased:
            self.LIFT *= 1.003
            self.increased = True
        elif u[1] > 10.0 and self.increased:
            self.LIFT /= 1.003
            self.increased = False


        state_dot = np.zeros(12)

        drag_force = -self.B_w*(u[3:6] + np.cross(u[9:], self.R_w))
        drag_torque = np.cross(-self.R_w, drag_force)

        gravity = np.array([0.0, -self.g, 0.0])
        gravity_inertial = np.array([np.dot(gravity, self.inertial_frame[0]), #this might be unneccesary
                                        np.dot(gravity, self.inertial_frame[1]),
                                        np.dot(gravity, self.inertial_frame[2])])


        torque_gen = -self.TORQUE_CONTROLLER_CONSTANT*u[9:]  #np.array([0.0, 0.0, 0.0]) #the torque controller will generate this


        state_dot[:3] = u[3:6]     #derivative of position is velocity
        state_dot[6:9] = u[9:]   #derivative of orientation is angular velocity

        #TRANSLATIONAL ACCELERATION (in ineratial frame)
        state_dot[3:6] = ((drag_force + self.LIFT) / self.MASS + gravity_inertial -
                            np.cross(u[9:], u[3:6]))
        #ROTATIONAL ACCELERATION (about inertial frame axes)
        state_dot[9:] = ((torque_gen - drag_torque + np.cross(self.R_w, drag_force)
                            - np.cross(u[9:], self.Jz*u[9:]))/self.Jz)


        u[3:6] += dt*state_dot[3:6]   #update vel based on acceleration
        u[9:] += dt*state_dot[9:]     #update angular vel based on angular accel


        #=== convert vel from inertial frame to global ===
        vel_global = np.zeros(3)
        for i in range(3):
            for j in range(3):
                vel_global[i] += u[3+i]*np.dot(self.inertial_frame[j], self.GLOBAL_FRAME[i])
        #=== update position from velocity vector ===
        u[:3] += dt*vel_global

        #calculate rotation from angular vels, then use quaternions to apply
        #them to orientation, sensors, and inertial frame
        theta_vals = np.zeros(3, dtype=float)
        rot_exists = False

        for i in range(3):
            theta_vals[i] = dt*u[9+i] #calculate angle to rotate about orientaiton axes
            if rot_exists:
                rotation = rotation * Quaternion(axis=self.inertial_frame[i], angle=theta_vals[i])
            else:
                rotation = Quaternion(axis=self.inertial_frame[i], angle=theta_vals[i])
                rot_exists = True

        if rot_exists:
            u[6:9] = rotation.rotate(u[6:9])
            for j in range(3):
                self.inertial_frame[j] = rotation.rotate(self.inertial_frame[j])
                self.sensor_orientations[j] = rotation.rotate(self.sensor_orientations[j])
            self.sensor_orientations[3] = rotation.rotate(self.sensor_orientations[3])

        return u


    def run(self, timesteps):
        vel_data = [ np.linalg.norm(self.state[3:6]) ]
        aVel_data = [ np.linalg.norm(self.state[9:])]
        orientation_angle = [ self.state[7] ]
        state = self.state.copy()

        for i in range(timesteps):
            if(state[1] <= 0.0):
                print("\n\nBANG BOOM CRASH OH NO!")
                self.state = state
                self.getState()
                break
            if(i%10 == 0):
                self.readSensors()
                print(i, "POS:", state[:3], "\t--ORIENTATION:", state[6:9], "\t--VEL:", state[3:6])
            if i%500 == 0 and i != 0:
                state[-3] = 15.0
                print("OOGA BOOGA")
                print(state)

            half_state = self.update_state(state.copy(), self.dt/2)
            state = self.update_state(half_state, self.dt)

            vel_data.append(np.linalg.norm(state[3:6]))
            aVel_data.append(np.linalg.norm(state[9:]))
            orientation_angle.append(state[7])

        a = np.linspace(0,self.dt*len(vel_data),len(vel_data))
        plt.plot(a, vel_data, label='Velocity [m/s]')
        plt.plot(a, aVel_data, label='Angular Velocity [rad/s]')
        plt.grid()
        plt.legend()
        #plt.ylim(0, 1000)
        plt.ylabel("Magnitude")
        plt.xlabel("time [sec]")
        plt.title("k = {0:.1e}".format(self.TORQUE_CONTROLLER_CONSTANT))
        plt.show()

        plt.plot(a, orientation_angle)
        plt.title("Angle of Orientation versus Initial Position")
        plt.xlabel("Time [sec]")
        plt.ylabel("Angle [rad]")
        plt.show()

    def lateralController(self):
        """calculate output of lateral controller and apply it"""
        print('lat control')

    def readSensors(self):
        self.light_vec = np.subtract(self.light_source_loc, self.pos)
        self.light_vec = self.normalize(self.light_vec)
        print(self.light_vec)

        """make sure to take into account vehicle orientation when doing dot products;
        the sensor vectors are relative to the orientation of the 'bee'"""
        for i in range(len(self.sensor_readings)):
            #finding angle between light rays and vectors normal to each sensor's surface
            #sensor_vec = (add robot orientation and sensor vectors)
            light_output = 850 #output of light in lumens

            angle = np.arccos(np.dot(self.sensor_orientations[i], self.light_vec) /
                              (np.linalg.norm(self.sensor_orientations[i] * np.linalg.norm(self.light_vec))))
            #self.sensor_readings[i] = angle

            illuminance = np.sin(angle)*light_output
            current = illuminance / 1000.0 #rough estimate for current from datasheet
                                           #where 1000 lux = 1 mA
            self.sensor_readings[i] = current

            print(self.sensor_readings[i], end=' -- ')
        print()



    def getState(self):
        print("===ROBOBEE STATE===")
        print("POSITION:\t", self.state[:3])
        print("VELOCITY:\t", self.state[3:6])
        print("ORIENTATION:\t", self.state[6:9])
        print("ANGULAR VEL:\t", self.state[9:], "\n")
