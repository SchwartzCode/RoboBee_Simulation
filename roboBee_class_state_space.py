import numpy as np
from pyquaternion import Quaternion
import matplotlib.pyplot as plt

class roboBee(object):
    """  CONSTANTS & ROBOT SPECS   """
    B_w = 0.0002 #drag constant [Ns/m]
    R_w = np.array([0.0, 0.009, 0.0]) #z distance between center of mass and wings [m]
    MASS = 0.08 #mass [g]
    g = 9.81 #gravity
    Jz = 1.42e-9 #Z Axis Rotational Moment of Inertia [kg*m^2]
    FLAPPING_FREQ = 120.0 #[Hz]
    WING_LENGTH = 15.0 #[mm]
    MEAN_CHORD_LENGTH = 3.46 #[mm]
    AREA = 55 #[mm^2]
    WING_INERTIA = 45.3 #inertia of wing about flapping axis [mg/mm^2]
    WING_MASS = 1.0 #[mg]
    SENSOR_NOMINAL_VAL = 1.1 #[mA]
    ROTATION_MIN = 0.0000001 #minimum angle of rotation required for robot orientaiton to be changed [radians]
    GLOBAL_FRAME = np.identity(3)
    inertial_frame = GLOBAL_FRAME
    LIFT = np.array([0.0, MASS*g, 0.0]) #lift force generated by wings [N]


    pos = np.array([0.0, 0.0, 0.0]) #(x,y,z) position coords [m]
    vel = np.array([0.0, 0.0, 0.0]) #(x,y,z) velocity components [m/s]
    accel = np.array([0.0, 0.0, 0.0]) #(x,y,z) acceleration components [m^2/s]
    INITIAL_ORIENTATION = np.array([0.0, 1.0, 0.0]) #orientation vector of robot if it is pointing straight upwards (x, y, z)
    angular_vel = np.zeros(3) #velocity of robot in (x, y, z) [rad/s]
    angular_accel = np.zeros(3)


    dt = 1/120 #1/120 #time step in seconds; represents one step at 120 Hz
    light_source_loc = np.array([0.0, 0.0, 1000.0]) #location of light source [mm]
    sensor_readings = np.array([0.0, 0.0, 0.0, 0.0]) #current flowing from phototransistors, between 1.1mA and 100 nA
    INITIAL_SENSOR_ORIENTATIONS = np.array([ [np.sqrt(0.75),   0.5,  0.0], #vectors normal to each sensor face at initial orientation (x,y,z)
                                          [0.0,             0.5,  np.sqrt(0.75)],
                                          [-np.sqrt(0.75),  0.5,  0.0],
                                          [0.0,             0.5,  -np.sqrt(0.75)]])
    sensor_orientations = INITIAL_SENSOR_ORIENTATIONS

    """rework these intializer functions to make them more robust"""
    def __init__(self, x_pos, y_pos, z_pos, orientation_xy, orientation_xz, orientation_yz):
        self.pos = np.array([x_pos, y_pos, z_pos])
        self.vel = np.array([0.0, 0.0, 0.0])
        self.accel = np.array([0.0, 0.0, 0.0])
        self.orientation = np.array([orientation_xy, orientation_xz, orientation_yz])

    def __init__(self):

        self.state = np.array([0.0, 10.0, 0.0,   #position (x, y, z)
                               0.0, 0.0, 0.0,   #velocity
                               0.0, 1.0, 0.0,   #orientation (basically theta)
                               0.0, 0.0, 1.0])  #angular velocity

    def normalize(self, x):
        normalized = x / np.linalg.norm(x)
        return normalized

    def update_state(self, u, dt):

        state_dot = np.zeros(12)

        drag_force = -self.B_w*(u[3:6] + np.cross(u[9:], self.R_w))
        drag_torque = np.cross(-self.R_w, drag_force)

        gravity = np.array([0.0, -self.g, 0.0])
        gravity_inertial = np.array([np.dot(gravity, self.inertial_frame[0]), #this might be unneccesary
                                        np.dot(gravity, self.inertial_frame[1]),
                                        np.dot(gravity, self.inertial_frame[2])])


        torque_gen = np.array([0.0, 0.0, 0.0]) #the torque controller will generate this
        #self.angular_accel = ((torque_gen - torque_drag + np.cross(self.R_w, drag_force)
        #                    - np.cross(self.angular_vel, self.Jz*self.angular_vel))/self.Jz)


        pizza = ((drag_force + self.LIFT) / self.MASS + gravity_inertial -
                            np.cross(u[9:], u[3:6]))

        state_dot[:3] = u[3:6]     #derivative of position is velocity
        state_dot[6:9] = u[9:12]   #derivative of orientation is angular velocity
        state_dot[3:6] = ((drag_force + self.LIFT) / self.MASS + gravity_inertial -
                            np.cross(u[9:], u[3:6]))
        state_dot[9:] = ((torque_gen - drag_torque + np.cross(self.R_w, drag_force)
                            - np.cross(u[9:], self.Jz*u[9:]))/self.Jz)


        u[3:6] += dt*state_dot[3:6]   #update vel based on acceleration
        u[9:] += dt*state_dot[9:]     #update angular vel based on angular accel


        #=== convert vel from inertial frame to global ===
        vel_global = np.zeros(3)
        for i in range(3):
            vel_global[i] = np.dot(u[3:6], self.GLOBAL_FRAME[i])
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
        state = self.state.copy()

        for i in range(timesteps):
            print(state)
            if(state[1] <= 0.0):
                print("\n\nBANG BOOM CRASH OH NO!")
                self.state = state
                self.getState()
                break
            if(i%10 == 0):
                print(i, "POS:", state[:3], "\t--ORIENTATION:", state[6:9], "\t--VEL:", state[3:6])
            state = self.update_state(state, self.dt)
            vel_data.append(np.linalg.norm(state[3:6]))
            aVel_data.append(np.linalg.norm(state[9:]))

        a = np.linspace(0,self.dt*len(vel_data),len(vel_data))
        plt.plot(a, vel_data, label='Velocity [m/s]')
        plt.plot(a, aVel_data, label='Angular Velocity [rad/s]')
        plt.grid()
        plt.legend()
        plt.ylim(0, 1000)
        plt.ylabel("Magnitude")
        plt.xlabel("time [sec]")
        plt.title("Input: angular vel=[0,0,1]")
        plt.show()



    def altitudeController(self):
        """calculate output of altitude controller and apply it
        (apply a torque proportional to w)"""
        print('alt control')

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
            angle = np.arccos(np.dot(self.sensor_positions[i], self.light_vec) /
                              (np.linalg.norm(self.sensor_positions[i] * np.linalg.norm(self.light_vec))))
            self.sensor_readings[i] = angle

            print(self.sensor_readings[i], end=' -- ')
        print()


    def getState(self):
        print("===ROBOBEE STATE===")
        print("POSITION:\t", self.state[:3])
        print("VELOCITY:\t", self.state[3:6])
        print("ORIENTATION:\t", self.state[6:9])
        print("ANGULAR VEL:\t", self.state[9:], "\n")
