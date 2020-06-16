"""
Author:     Jonathan Schwartz   [jonbs98@gmail.com]
Group:      GWU's Adaptive Devices and Microsystems Lab
Professor:  Doctor Gina Adam
Description:
    Robobee Simulator with a PD controller for stabilizing the robot and an LQR
    controller that directs the robot toward points in 3D space (while also keeping it
    adequately stable). The LQR function also includes the readSensors() and getAngularVel()
    functions, which simulate the robot reading data off of its 4 phototransistors and
    passes that data back to the robot. The robot uses this data to estimate its
    state, which is passed on to the control algorithm so the robot can make an
    informed decision as to its next move.

    This work was inspired by the work of Taylor S. Clawson and Doctors
    Silvia Ferrari and Robert Wood. More detail can be found here: https://ieeexplore.ieee.org/document/7798778
"""


import numpy as np
import matplotlib.pyplot as plt
import control
from random import seed, random

class roboBee(object):

    """  CONSTANTS & ROBOT SPECS   """
    B_w = 0.0002 #drag constant [Ns/m]
    Rw = 0.009 #distance from robot's Center of Mass to where its wings exert torques on its body [m]
    Jz = 0.45e-9 #Z Axis Rotational Moment of Inertia [kg*m^2]

    MASS = 0.08 #mass [g]
    g = 9.81 #gravity [m/s^2]
    dt = 1/120 #1/120 #time step in seconds; represents one step at 120 Hz

    LIFT_COEFFICIENT = 1.0
    last_sensor_readings = np.array([0.0, 0.0, 0.0, 0.0]).reshape(4,1)


    def updateState_PD_Control(self, state, dt):
        """
        This function will calculate the next state using the current state
        and the plant's physics (the plant is the transfer function from inputs to the
        Robobee system to its outputs).

        This is what state space is like (where x_dot is derivative of x, which is the
        state vector, u is the input vector, and A and B are coefficient matrices):

                            x_dot = A*x + B*u


        ==== ARGUMENTS ====
        state = current state (4 double numpy 1D array)
            state[0] = theta (angle of rotation from intertial to global coords in 2D)
            state[1] = theta_dot (change in theta per unit time)
            state[2] = x axis position in global coordinates
            state[3] = x_dot (x axis velocity)
        dt = time step = 1/120 [seconds] (wings flap at 120 Hz)

        ==== RETURNS ====
        new_state = The state of the robot one time-step (after dt [seconds]) in the future
        torque_applied = torque the robot decides to generate with its wings based
                         on its current state, this is returned and stored in an array.
                         This array is then used as the 'output' training data for the
                         neural network that will be used to replicate the controller.
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


    def updateState_LQR_Control(self, state, dt, state_desired, gains):
        """
        This function will calculate the new state using the current state
        and only a large matrix of coefficients, this is necessary
        in order to use LQR control.

        This is what state space is like, where x_dot is deriv of x, which is the
        state vector, i is the input vector, and A and B are coefficient matrices:

                            x_dot = A*x + B*i


        ==== ARGUMENTS ====
        state = current state (6 double numpy 1D array)
            state[0] = theta (angle of rotation from intertial to global coords in 2D)
            state[1] = theta_dot (change in theta per unit time)
            state[2] = x axis position in global coordinates
            state[3] = x_dot (x axis velocity)
            state[4] = z axis position in global coordinates
            state[5] = z_dot (z axis velocity)
        dt = time step [seconds], usually 1/120 (wings flap at 120 Hz)
        state_desired = final state the robot is trying to get to
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



        state_dot_lat = (A - (B * gains)) * state[:4] + B * gains * state_desired[:4]


        """  ALTITUDE CONTROLLER
                All it does is adjust the lift force based on where the robot is
                is to its desired altitude

            # JONATHAN: can probably make the logic here a bit simpler
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


        state_dot_alt = np.array([state[5], self.MASS*self.g*(self.LIFT_COEFFICIENT*np.cos(state[0]) - 1)]).reshape(2,1)


        state_dot = np.vstack([state_dot_lat, state_dot_alt])

        new_state = state + state_dot*dt

        return new_state, state_dot_lat[1]


    def LQR_gains(self):
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
        Q[0,0] = 100
        Q[1,1] = 1
        Q[2,2] = 100
        Q[3,3] = 0.1

        R = 0.001


        gains, ricatti, eigs = control.lqr(A, B, Q, R)

        return gains


    def run_lqr(self, timesteps, verbose = False, plots = True):
        print("Running Simulation with LQR controller...")

        state = np.zeros(6).reshape(6,1)
        state_desired = np.array([0.0, 0.0, 2, 0.0, 2, 0.0]).reshape(6,1)

        gains = self.LQR_gains()
        torque_gen = 0

        pointReached = False
        i = 0

        while i < timesteps and not pointReached:

            diff = sum( abs(state - state_desired) )
            if diff < 0.01:
                pointReached = True

            if (i==0):
                state_data = np.vstack([ state, state_desired[2], state_desired[4] ])
                sensor_data = np.array([0.0, 0.0]).reshape(2,1)
                aVelEstimates = np.array([0.0, 0.0]).reshape(2,1)
            else:
                state_data = np.hstack([ state_data, np.vstack([state, state_desired[2], state_desired[4] ])  ])
                new_reading = self.readSensors(state[0])
                aVelEstimates = self.getAngularVel(new_reading, torque_gen)
                sensor_data = np.hstack([ sensor_data, aVelEstimates ])

            if i%10 == 0 and verbose:
                print("State at time step", i, ":\t", state)
                if (i != 0):
                    print("A-Vel Estimates: ", aVelEstimates)

            estimated_state = state.copy()
            estimated_state[1] = aVelEstimates[0]




            state, torque_gen = self.updateState_LQR_Control(estimated_state, self.dt, state_desired, gains)

            if (i==0):
                torque_data = np.array(torque_gen)
            else:
                torque_data = np.append(torque_data, torque_gen)

            i += 1

        state_data = np.array(state_data)
        t = np.linspace(0, self.dt*state_data.shape[1], state_data.shape[1])

        if plots:
            plt.figure(figsize=[8,6])
            plt.title("Comparing Actual and Estimated Angular Velocity")
            plt.plot(t, sensor_data[0,:], label="Estimates from Sensors")
            plt.plot(t, state_data[1,:], label="Actual Angular Velocity Values")
            plt.plot(t, state_data[0,:], label="Actual Theta Value")
            plt.ylabel("Rotational Velocity [rad/sec]")
            plt.xlabel("Time [sec]")
            plt.xlim(0,1)
            #plt.ylim(-2,2)
            plt.legend()
            plt.show()

            plt.figure(figsize=[9,7])
            plt.suptitle("LQR Controller - Position (Desired Position x=%4.2f, y=%4.2f)" % (state_desired[2], state_desired[4]))
            #plt.suptitle("LQR Controller (R = 10)")
            plt.subplot(1,2,1)
            plt.plot(state_data[2,:], state_data[4,:])
            plt.ylabel('Y [m]')
            plt.xlabel('X [m]')
            #plt.plot(t, state_data[2,:])
            #plt.ylabel('X [m]')
            #plt.xlabel("t [sec]")
            plt.grid()


            plt.subplot(1,2,2)
            plt.plot(t, state_data[0,:], label='Theta  [rad]')
            plt.plot(t, state_data[1,:], label='Omega (Theta Dot)  [rad/sec]')
            plt.xlim(0,1) #angle usually congeres within first 100 time steps of simulation
            #plt.ylim(-0.5,0.5)
            plt.xlabel("Time [sec]")
            plt.ylabel("Magnitude")
            plt.legend()
            plt.show()

        print("Done!")
        if i == timesteps:
            print("Destination not reached in", i, "time steps.")
        else:
            print("Destination reached in", i, "time steps.")

        return np.transpose(state_data), torque_data


    def run_pd(self, timesteps, verbose = False, plots = True):
        print("Running simulation with PD controller...")
        seed(0) #initializes random number generator
        state = np.zeros(4)

        state[1] = -10 + (random() * 20)

        for i in range(timesteps):
            if state[0] > 0.176:
                print("WARNING: Robot has rotated so much that the error of the small angle approximation has exceeded 1%.")
                print("In a real experiment, this would likely result in the robot losing control and crashing.")
                print("Current state: ", state)

            if verbose:
                print("State at time step ", i, ":\t", state)

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

        if plots:
            plt.plot(t, state_data[:,3], label='Velocity [m/s]')
            plt.plot(t, state_data[:,1], label='Angular Velocity [rad/s]')
            plt.plot(t, state_data[:,0], label='Angular Position [rad]')
            plt.grid()
            plt.legend()
            #plt.ylim(-10, 10)
            plt.ylabel("Magnitude")
            plt.xlabel("time [sec]")
            plt.title("State Space - PD Controller")
            plt.show()


        print("Done!")
        return state_data, torques_data


    def readSensors(self, theta):
        """ NOTE: This is a very crude estimation. Thought behind it was to use
                  the light output of a typical lightbulb (seems to be around 850 lumens)
                  and then to have the brightness adjust proportionally
                  to the angle between the vector from the robot to the light and the
                  vector normal to the sensor's surface.

                  The reading is in lux (illuminance per square meter, and I'm saying the
                  light is 1 meter away, meaning the light's luminance is spread
                  over a sphere with surface area of 4*pi*[1]^2 = pi)
        """


        """ normalize light source vector so magnitude is 1
            light vector is assumed to always be directly above the robot since it
            is far enough away that lateral movement doesn't make a difference. Think of
            the sun in relation to you as you walk around outside """
        light_vec = [0,1,0]

        light_output = 850 #output of light in lumens, typical bulbs give off 600~1200ish lumens
        init_angle = 30 * np.pi / 180

        new_sensor_orientations = np.array([ [np.cos(init_angle - theta),       np.sin(init_angle - theta),       0],
                                         [np.sin(init_angle)*np.sin(theta), np.sin(init_angle)*np.cos(theta), np.cos(init_angle)],
                                         [-np.cos(init_angle + theta),      np.sin(init_angle + theta),       0],
                                         [np.sin(init_angle)*np.sin(theta), np.sin(init_angle)*np.cos(theta), -np.cos(init_angle)] ])


        sensor_readings = np.array([0.0, 0.0, 0.0, 0.0]).reshape(4,1)

        for i in range(new_sensor_orientations.shape[0]):

            angle = np.arccos(np.dot(light_vec, new_sensor_orientations[i]) /
                                np.linalg.norm(light_vec) * np.linalg.norm(new_sensor_orientations[i]))

            sensor_readings[i] = light_output * angle


        return sensor_readings


    def getAngularVel(self, new_readings, torque_gen):
        """
        For a derivation of the math used in this function, check out section 4 of 'Controlling free flight
        of a robotic fly using an onboard vision sensor inspired by insect ocelli' by
        S.B. Fuller et al. :
            https://royalsocietypublishing.org/doi/full/10.1098/rsif.2014.0281#d3e1883
        """

        diffs = new_readings - self.last_sensor_readings
        self.last_sensor_readings = new_readings

        # Original estimate was pi/850, added the 7468.8 to scale from obtained
        # values to desired values
        k = np.pi / (850) * 7468.8

        L = np.array([ [np.sqrt(3)/k,   0,  -np.sqrt(3)/k,    0,  ],
                       [0,  -np.sqrt(3)/k,  0,  np.sqrt(3)/k]       ])

        angular_vel_estimates = L.dot(diffs)

        angular_vel_estimates[0,0] += self.dt*torque_gen


        return angular_vel_estimates
