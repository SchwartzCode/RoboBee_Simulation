import numpy as np
import quaternion #95% sure I no longer need this, going to leave it for a bit just in case
import matplotlib.pyplot as plt
import math
import control
import scipy
from random import seed, random

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

    def rotation_matrix(self, axis, theta):
        """
        Return the rotation matrix associated with counterclockwise rotation about
        the given axis by theta radians.

        I DID NOT MAKE THIS, FOUND IT ON STACKOVERFLOW. LINK:
        https://stackoverflow.com/questions/6802577/rotation-of-3d-vector
        """
        axis = np.asarray(axis)
        axis = axis / math.sqrt(np.dot(axis, axis))
        a = math.cos(theta / 2.0)
        b, c, d = -axis * math.sin(theta / 2.0)
        aa, bb, cc, dd = a * a, b * b, c * c, d * d
        bc, ad, ac, ab, bd, cd = b * c, a * d, a * c, a * b, b * d, c * d

        return np.array([[aa + bb - cc - dd, 2 * (bc + ad), 2 * (bd - ac)],
                         [2 * (bc - ad), aa + cc - bb - dd, 2 * (cd + ab)],
                         [2 * (bd + ac), 2 * (cd - ab), aa + dd - bb - cc]])



    def updateState_PD_Control(self, state, dt):
        """
        This function will calculate the new state using the current state
        and only a large matrix of coefficients

        This is what state space is like, where x_dot is derivative of x, which is the
        state vector, i is the input vector, and A and B are coefficient matrices:

                            x_dot = A*x + B*i


        ==== ARGUMENTS ====
        state = current state (12 double numpy 1D array)
            state[0] = theta (angle of rotation from intertial to global coords in 2D)
            state[1] = theta_dot (change in theta per unit time)
            state[2] = x axis position in global coordinates
            state[3] = x_dot (x axis velocity)
        dt = time step [seconds], usually 1/120 (wings flap at 120 Hz)
        """

        #These are 'inputs' because the torque controller is proportional to theta
        #and theta_dot (it's a PD controller if you've taken a controls course)
        #    In the future this will be elsewhere, just keeping it to evaluate
        #    This controller against the analytical one I

        u = np.zeros(4)
        u[0] = state[0]
        u[1] = state[1]


        A = np.zeros((4, 4))
        B = np.zeros((4, 4))
        #Derivative of angular positon is angular velocity
        A[0,1] = 1
        #Derivative of position is velocity
        A[2,3] = 1

        # V_x_dot terms
        A[3,0] = self.g*self.LIFT_COEFFICIENT
        A[3,3] = -self.B_w

        # Theta_dot term(s)
        A[1,3] = -self.Rw*self.B_w / self.Jz


        #Apply input torque (as of now this is just the torque generated by torque
        #controller that keeps robot upright)
        torque_constant_prop = 4e-7
        torque_constant_deriv = 0.7e-7
        B[1,0] = -torque_constant_prop / self.Jz
        B[1,1] = -torque_constant_deriv / self.Jz


        state_dot = A.dot(state) + B.dot(u)

        #applied torque is returned and stored as data to train a neural network
        torque_applied = B.dot(u)[1]

        new_state = state.copy() + state_dot.copy() * dt

        return new_state, torque_applied


    def updateState_LQR_Control(self, state, dt, state_desired):
        """
        This function will calculate the new state using the current state
        and only a large matrix of coefficients, this is necessary
        in order to use LQR control.

        This is what state space is like, where x_dot is deriv of x, which is the
        state vector, i is the input vector, and A and B are coefficient matrices:

                            x_dot = A*x + B*i


        ==== ARGUMENTS ====
        state = current state (12 double numpy 1D array)
            state[0] = theta (angle of rotation from intertial to global coords in 2D)
            state[1] = theta_dot (change in theta per unit time)
            state[2] = x axis position in global coordinates
            state[3] = x_dot (x axis velocity)
            state[4] = z axis position in global coordinates
            state[5] = z_dot (z axis velocity)
        dt = time step [seconds], usually 1/120 (wings flap at 120 Hz)
        """

        #These are 'inputs' because the torque controller is proportional to theta
        #and theta_dot (it's a PD controller if you've taken a controls course)
        #    In the future this will be elsewhere, just keeping it to evaluate
        #    This controller against the analytical one I


        A = np.zeros((4, 4))
        B = np.zeros(4).reshape(4,1)
        #Derivative of angular positon is angular velocity
        A[0,1] = 1
        #Derivative of position is velocity
        A[2,3] = 1

        # V_x_dot terms
        A[3,0] = self.g*self.LIFT_COEFFICIENT
        A[3,3] = -self.B_w / self.MASS

        # Theta_dot term(s)
        A[1,3] = -self.Rw*self.B_w / self.Jz

        #Note: There are no terms in the A matrix for V_z_dot because that is
        #   controlled by the altitude controller which is decoupled from this
        #   controller (the latitude controller)


        #Coefficients for input matrix B
        B[1] = 1 #/ self.Jz

        Q = np.zeros((4,4))
        #impose larger penalty on theta and theta_dot for deviating than position
        #because these deviating will cause robot to become unstable and state will diverge
        Q[0,0] = 1000
        Q[1,1] = 100
        Q[2,2] = 1
        Q[3,3] = 0.1

        R = 0.01


        gains, ricatti, eigs = control.lqr(A, B, Q, R)

        state_dot_lat = (A - (B * gains)) * state[:4] + B * gains * state_desired[:4]

        """  ALTITUDE CONTROLLER
                All it does is adjust the lift force based on where the robot is
                is to its desired altitude
        """


        adjustment = 0.02
        if (state[5] > 0 and state[5] > (state_desired[4] - state[4])):
            state[5] -= adjustment
        elif (state[5] < 0 and state[5] < (state_desired[4] - state[4])):
            state[5] += adjustment
        else:
            self.LIFT_COEFFICIENT = 1 + (state_desired[4] - state[4])

        if (self.LIFT_COEFFICIENT > 1.5):
            self.LIFT_COEFFICIENT = 1.5
        elif (self.LIFT_COEFFICIENT < 0.5):
            self.LIFT_COEFFICIENT = 0.5
        #self.LIFT_COEFFICIENT = 1 +  (state_desired[4] - state[4])
        #print(self.LIFT_COEFFICIENT)

        state_dot_alt = np.array([state[5], self.MASS*self.g*(self.LIFT_COEFFICIENT*np.cos(state[0]) - 1)]).reshape(2,1)


        state_dot = np.vstack([state_dot_lat, state_dot_alt])

        print("STATE DOT")
        print(state_dot)

        new_state = state + state_dot*dt

        return new_state, state_dot_lat[1]


    def updateState_analytical(self, u, dt):
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

        #generating torque opposing angular velocity keep robot upright
        TORQUE_CONTROLLER_CONSTANT = 0.9e-7
        torque_gen = -self.TORQUE_CONTROLLER_CONSTANT*u[9:]


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
                rotation = np.dot(rotation, self.rotation_matrix(self.inertial_frame[i], theta_vals[i]))
            else:
                rotation = self.rotation_matrix(self.inertial_frame[i], theta_vals[i])
                rot_exists = True

        if rot_exists:
            u[6:9] = np.dot(rotation,(u[6:9]))
            for j in range(3):
                self.inertial_frame[j] = np.dot(rotation, self.inertial_frame[j])
                self.sensor_orientations[j] = np.dot(rotation, self.sensor_orientations[j])
            self.sensor_orientations[3] = np.dot(rotation, self.sensor_orientations[3])

        return u

    def run_lqr(self, timesteps):

        state = np.zeros(6).reshape(6,1)
        state_desired = np.array([0.0, 0.0, 2, 0.0, 2, 0.0]).reshape(6,1)


        for i in range(timesteps):
            print(i, ":\t", state)

            if (i==0):
                state_data = np.vstack([ state, state_desired[2] ])
            else:
                state_data = np.hstack([ state_data, np.vstack([state, state_desired[2]])  ])


            state, torque_gen = self.updateState_LQR_Control(state.copy(), self.dt, state_desired)

            if (i==0):
                torque_data = np.array(torque_gen)
            else:
                torque_data = np.append(torque_data, torque_gen)


        state_data = np.array(state_data)
        t = np.linspace(0, self.dt*state_data.shape[1], state_data.shape[1])



        plt.figure(figsize=[10,7])
        #plt.suptitle("LQR Controller - Position (Desired Position x=%4.2f, y=%4.2f)" % (state_desired[2], state_desired[4]))
        plt.suptitle("LQR Controller (Prioritizing Theta)")
        plt.subplot(1,2,1)
        #plt.plot(state_data[2,:], state_data[4,:])
        #plt.ylabel('Y [m]')
        #plt.xlabel('X [m]')
        plt.plot(t, state_data[2,:])
        plt.xlabel('X [m]')
        plt.ylabel("t [sec]")
        plt.grid()



        plt.subplot(1,2,2)
        plt.plot(t, state_data[0,:], label='Theta  [rad]')
        plt.plot(t, state_data[1,:], label='Omega (Theta Dot)  [rad/sec]')
        plt.xlim(0,1) #angle usually congeres within first 100 time steps of simulation
        plt.ylim(-5,5)
        plt.xlabel("Time [sec]")
        plt.ylabel("Magnitude")
        plt.legend()
        plt.show()


        return np.transpose(state_data), torque_data


    def run_pd(self, timesteps):
        seed(0) #initializes random number generator
        state = np.zeros(4)

        state[1] = -10 + (random() * 20)

        for i in range(timesteps):
            print(i, ":\t", state)

            if(i % 250 == 0):
                #this conditional occasionally varies angular vel to validate functionality
                #of torque controller
                state[1] = -10 + (random() * 20)



            if (i==0):
                state_data = np.array(state)
            else:
                state_data = np.vstack([state_data, np.array(state)])

            state, torque_applied = self.updateState_PD_Control(state.copy(), self.dt)


            if (i==0):
                torques_data = np.array(torque_applied)
            else:
                torques_data = np.append(torques_data, torque_applied)

        t = np.linspace(0, self.dt*len(state_data[:,0]), len(state_data[:,0]))

        plt.plot(t, state_data[:,3], label='Velocity [m/s]')
        plt.plot(t, state_data[:,1], label='Angular Velocity [rad/s]')
        plt.grid()
        plt.legend()
        #plt.ylim(-10, 10)
        plt.ylabel("Magnitude")
        plt.xlabel("time [sec]")
        #plt.yscale("log") #tried this once, it looked awful
        plt.title("State Space - PD Controller")
        plt.show()

        return state_data, torques_data


    def run_analytical(self, timesteps):
        """
        THIS NEEDS TO BE RECONFIGURED TO WORK WITH THE NEW QUATERNION LIBRARY
        """
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
                self.readSensors(state)
                print(i, "POS:", state[:3], "\t--ORIENTATION:", state[6:9], "\t--VEL:", state[3:6])
            if i%500 == 0 and i != 0:
                #this conditional occasionally varies angular vel to validate functionality
                #of torque controller
                state[-3] = 15.0
                print("OOGA BOOGA")
                print(state)

            half_state = self.updateState_analytical(state.copy(), self.dt/2)
            state = self.updateState_analytical(half_state, self.dt)

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

        """
        # ~~~ THIS PLOTS ORIENTATION ANGLE vs TIME, DID THIS TO SEE IF SMALL
        # ~~~ ANGLE APPROXIMATION WAS VALID
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        plt.plot(a, orientation_angle)
        plt.title("Angle of Orientation versus Initial Position")
        plt.xlabel("Time [sec]")
        plt.ylabel("Angle [rad]")
        plt.show()
        """

    def readSensors(self, state):
        self.light_vec = np.subtract(self.light_source_loc, state[0:3])
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
