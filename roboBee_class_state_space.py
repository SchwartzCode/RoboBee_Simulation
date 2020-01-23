import numpy as np
import quaternion #95% sure I no longer need this, going to leave it for a bit just in case
import matplotlib.pyplot as plt
import math
import control
import scipy

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
            state[3] = z axis position in global coordinates
            state[4] = x_dot (x axis velocity)
            state[5] = z_dot (z axis velocity)
        dt = time step [seconds], usually 1/120 (wings flap at 120 Hz)
        """

        #These are 'inputs' because the torque controller is proportional to theta
        #and theta_dot (it's a PD controller if you've taken a controls course)
        #    In the future this will be elsewhere, just keeping it to evaluate
        #    This controller against the analytical one I

        u = np.zeros(6)
        u[0] = state[0]
        u[1] = state[1]


        A = np.zeros((6, 6))
        B = np.zeros((6, 6))
        #Derivative of angular positon is angular velocity
        A[0,1] = 1
        #Derivative of position is velocity
        A[2,4] = 1
        A[3,5] = 1

        # V_x_dot terms
        A[4,0] = self.g*self.LIFT_COEFFICIENT
        A[4,4] = -self.B_w

        # Theta_dot term(s)
        A[1,4] = -self.Rw*self.B_w / self.Jz

        #Note: There are no terms in the A matrix for V_z_dot because that is
        #   controlled by the altitude controller which is decoupled from this
        #   controller (the latitude controller)


        #Apply input torque (as of now this is just the torque generated by torque
        #controller that keeps robot upright)
        torque_constant_prop = 6e-7
        torque_constant_deriv = 1.55e-7
        B[1,0] = -torque_constant_prop / self.Jz
        B[1,1] = -torque_constant_deriv / self.Jz


        #print(A)
        #print(B)

        state_dot = A.dot(state) + B.dot(u)

        new_state = state.copy() + state_dot.copy() * dt

        return new_state


    def dlqr(self,A,B,Q,R):
        """
        NOTE: I did not come up with this function myself, I borrowed it from stack overflow
        Solve the discrete time lqr controller.

        x[k+1] = A x[k] + B u[k]

        cost = sum x[k].T*Q*x[k] + u[k].T*R*u[k]
        """
        #ref Bertsekas, p.151

        #first, try to solve the ricatti equation
        X = np.matrix(scipy.linalg.solve_discrete_are(A, B, Q, R))

        #compute the LQR gain
        K = np.matrix(scipy.linalg.inv(B.T*X*B+R)*(B.T*X*A))

        eigVals, eigVecs = scipy.linalg.eig(A-B*K)

        return K, X, eigVals


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
            state[3] = z axis position in global coordinates
            state[4] = x_dot (x axis velocity)
            state[5] = z_dot (z axis velocity)
        dt = time step [seconds], usually 1/120 (wings flap at 120 Hz)
        """

        #These are 'inputs' because the torque controller is proportional to theta
        #and theta_dot (it's a PD controller if you've taken a controls course)
        #    In the future this will be elsewhere, just keeping it to evaluate
        #    This controller against the analytical one I


        A = np.zeros((6, 6))
        B = np.zeros(6).reshape(6,1)
        #Derivative of angular positon is angular velocity
        A[0,1] = 1
        #Derivative of position is velocity
        A[2,4] = 1
        A[3,5] = 1

        # V_x_dot terms
        A[4,0] = self.g*self.LIFT_COEFFICIENT
        A[4,4] = -self.B_w / self.MASS

        # Theta_dot term(s)
        #A[1,4] = -self.Rw*self.B_w / self.Jz

        #Note: There are no terms in the A matrix for V_z_dot because that is
        #   controlled by the altitude controller which is decoupled from this
        #   controller (the latitude controller)


        #Coefficients for input matrix B
        B[1] = 1 / self.Jz
        #B[1,0] = 1 / self.Jz

        Q = np.zeros((6,6))
        #impose larger penalty on theta and theta_dot for deviating than position
        #because these deviating will cause robot to become unstable and state will diverge
        Q[0,0] = 1
        Q[2,2] = 1
        #Q[1,1] = 1e9

        R = 0.001

        """
        #Will delete this once I finish debugging
        print("A: ", A, "\n")
        print("B: ", B, "\n")
        print("Q: ", Q, "\n")
        print("R: ", R, "\n")
        print(A.shape, B.shape)
        """

        gains, ricatti, eigs = control.lqr(A, B, Q, R)


        state_dot = np.dot((A - np.dot(B, gains)), state) + np.dot(np.dot(B, gains), state_desired)

        new_state = state + state_dot*dt

        """
        #will delete these prints when I finish debugging
        print("gains: ", gains, "\n")
        print(state_dot, "\n")
        print(new_state, "\n")
        print(gains)
        """


        return new_state


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
        state[1] = 1
        vel_data = [ np.linalg.norm(state[4:]) ]
        aVel_data = [ state[1] ]


        state_desired = np.array([0.0, 0.0, 10, 0.0, 0.0, 0.0]).reshape(6,1)


        for i in range(timesteps):
            print(i, ":\t", state)

            half_state = self.updateState_LQR_Control(state.copy(), self.dt/2, state_desired)
            state = self.updateState_LQR_Control(half_state, self.dt, state_desired)

            vel_data.append(np.linalg.norm(state[4:]))
            aVel_data.append(state[1])

        t = np.linspace(0, self.dt*len(vel_data), len(vel_data))

        plt.plot(t, vel_data, label='Velocity [m/s]')
        plt.plot(t, aVel_data, label='Angular Velocity [rad/s]')
        plt.grid()
        plt.legend()
        #plt.ylim(-10, 10)
        plt.ylabel("Magnitude")
        plt.xlabel("time [sec]")
        #plt.yscale("log") #tried this once, it looked awful
        plt.title("k = {0:.1e}".format(self.TORQUE_CONTROLLER_CONSTANT))
        plt.show()


    def run_pd(self, timesteps):
        state = np.zeros(6)
        state[3] = 10.0 #setting robobee height so it doesn't immeadiately crash
        state[1] = 1
        vel_data = [ np.linalg.norm(state[4:]) ]
        aVel_data = [ state[1] ]

        for i in range(timesteps):
            print(i, ":\t", state)


            if(state[3] <= 0.0):
                print("\n\nBANG BOOM CRASH OH NO!")
                print(state)
                break
            elif(i % 250 == 0):
                #this conditional occasionally varies angular vel to validate functionality
                #of torque controller
                state[1] = 10

            half_state = self.updateState_PD_Control(state.copy(), self.dt/2)
            state = self.updateState_PD_Control(half_state, self.dt)

            vel_data.append(np.linalg.norm(state[4:]))
            aVel_data.append(state[1])

        t = np.linspace(0, self.dt*len(vel_data), len(vel_data))

        plt.plot(t, vel_data, label='Velocity [m/s]')
        plt.plot(t, aVel_data, label='Angular Velocity [rad/s]')
        plt.grid()
        plt.legend()
        #plt.ylim(-10, 10)
        plt.ylabel("Magnitude")
        plt.xlabel("time [sec]")
        #plt.yscale("log") #tried this once, it looked awful
        plt.title("k = {0:.1e}".format(self.TORQUE_CONTROLLER_CONSTANT))
        plt.show()


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



    def getState(self):
        print("===ROBOBEE STATE===")
        print("POSITION:\t", self.state[:3])
        print("VELOCITY:\t", self.state[3:6])
        print("ORIENTATION:\t", self.state[6:9])
        print("ANGULAR VEL:\t", self.state[9:], "\n")
