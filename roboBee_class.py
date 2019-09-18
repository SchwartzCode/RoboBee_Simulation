import numpy as np

class roboBee(object):
    """  CONSTANTS & ROBOT SPECS   """
    MASS = 80.0 #mass [mg]
    g = 9.81 #gravity
    Jx = 1.32 #X Axis Inertia [mg/mm^2]
    Jy= 1.42 #Y Axis Inertia [mg/mm^2]
    Jz = 0.45 #Z Axis Inertia [mg/mm^2]
    FLAPPING_FREQ = 120.0 #[Hz]
    WING_LENGTH = 15.0 #[mm]
    MEAN_CHORD_LENGTH = 3.46 #[mm]
    AREA = 55 #[mm^2]
    WING_INERTIA = 45.3 #inertia of wing about flapping axis [mg/mm^2]
    WING_MASS = 1.0 #[mg]
    SENSOR_NOMINAL_VAL = 1.1 #[mA]


    pos = np.array([0.0, 0.0, 0.0]) #(x,y,z) position coords [mm]
    vel = np.array([0.0, 0.0, 0.0]) #(x,y,z) velocity components [mm/s]
    accel = np.array([0.0, 0.0, 0.0]) #(x,y,z) acceleration components [mm^2/s]
    INITIAL_ORIENTATION = np.array([0.0, 0.0, 1.0]) #orientation vector of robot if it is pointing straight upwards (x, y, z)
    angular_vel = np.array([0.0, 0.0, 0.0]) #velocity of robot in (x, y, z) [rad/s]

    orientation = INITIAL_ORIENTATION #vector of direction robot's head is pointing (x, y, z)


    dt = 1/120 #time step in seconds; represents one step at 120 Hz
    light_source_loc = np.array([0.0, 0.0, 1000.0]) #location of light source [mm]
    sensor_readings = np.array([0.0, 0.0, 0.0, 0.0]) #current flowing from phototransistors, between 1.1mA and 100 nA
    INITIAL_SENSOR_POSITIONS = np.array([ [np.sqrt(0.75), 0.0, 0.5], #vectors normal to each sensor at initial orientation (x,y,z)
                                  [0.0, np.sqrt(0.75), 0.5],
                                  [-np.sqrt(0.75), 0.0, 0.5],
                                  [0.0, -np.sqrt(0.75), 0.5]])
    sensor_positions = INITIAL_SENSOR_POSITIONS

    """rework these intializer functions to make them more robust"""
    def __init__(self, x_pos, y_pos, z_pos, orientation_xy, orientation_xz, orientation_yz):
        self.pos = np.array([x_pos, y_pos, z_pos])
        self.vel = np.array([0.0, 0.0, 0.0])
        self.accel = np.array([0.0, 0.0, 0.0])
        self.orientation = np.array([orientation_xy, orientation_xz, orientation_yz])

    def __init__(self):
        self.pos = np.array([0.0, 0.0, 0.0])
        self.vel = np.array([0.0, 0.0, 0.0])
        self.accel = np.array([0.0, 0.0, 0.0])
        self.orientation = np.array([0.0, 0.0, 0.0])
        self.angular_vel = np.array([0.0, 0.0, 0.0])

    def normalize(self, x):
        normalized = x / np.linalg.norm(x)
        return normalized

    def updatePosition(self):
        print(self.pos)
        self.pos = self.pos + self.dt*self.vel
        self.orientation += self.dt*self.angular_vel
        print(self.pos)
        """adjust position and velocity accordingly"""
        print('iterate')

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

    def newState(self):
        print("calculating new state")

    def getState(self):
        print("===ROBOBEE STATE===")
        print("POSITION:     [", self.pos[0], ", ", self.pos[1], ", ", self.pos[2], "]")
        print("VELOCITY:     [", self.vel[0], ", ", self.vel[1], ", ", self.vel[2], "]")
        print("ACCELERATION: [", self.accel[0], ", ", self.accel[1], ", ", self.accel[2], "]")
        print("ORIENTATION:  [", self.orientation[0], ", ", self.orientation[1], ", ", self.orientation[2], "]  (format: [x-y, x-z, y-z plane angles])\n")
