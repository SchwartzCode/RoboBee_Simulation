import numpy as np
from pyquaternion import Quaternion

class roboBee(object):
    """  CONSTANTS & ROBOT SPECS   """
    B_w = 0.0002 #drag constant [Ns/m]
    R_w = np.array([0.0, 0.0, 0.009]) #z distance between center of mass and wings
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
    ROTATION_MIN = 0.01 #minimum angle of rotation required for robot orientaiton to be changed [radians]
    GLOBAL_FRAME = np.identity(3)
    inertial_frame = GLOBAL_FRAME
    LIFT = np.array([0.0, MASS*g, 0.0]) #lift force generated by wings [N]


    pos = np.array([0.0, 0.0, 0.0]) #(x,y,z) position coords [mm]
    vel = np.array([0.0, 0.0, 0.0]) #(x,y,z) velocity components [mm/s]
    accel = np.array([0.0, 0.0, 0.0]) #(x,y,z) acceleration components [mm^2/s]
    INITIAL_ORIENTATION = np.array([0.0, 1.0, 0.0]) #orientation vector of robot if it is pointing straight upwards (x, y, z)
    angular_vel = np.zeros(3) #velocity of robot in (x, y, z) [rad/s]
    angular_accel = np.zeros(3)

    orientation = INITIAL_ORIENTATION #vector of direction robot's head is pointing (x, y, z)


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
        self.pos = np.array([0.0, 0.0, 0.0])
        self.vel = np.array([0.0, 1.0, 0.0])
        self.accel = np.array([0.0, 0.0, 0.0])
        self.orientation = np.array([0.0, 0.0, 0.0])
        self.angular_vel = np.array([0.0, 0.0, 0.0])
        self.angular_accel = np.array([0.0, 0.0, 0.0])

    def normalize(self, x):
        normalized = x / np.linalg.norm(x)
        return normalized

    def update_accels(self):

        drag_force = -self.B_w*(self.vel + np.cross(self.angular_vel, self.R_w))
        drag_torque = np.cross(-self.R_w, drag_force)

        gravity = np.array([0.0, -self.g, 0.0])
        gravity_inertial = np.array([np.dot(gravity, self.inertial_frame[0]), #this might be unneccesary
                                        np.dot(gravity, self.inertial_frame[1]),
                                        np.dot(gravity, self.inertial_frame[2])])


        torque_drag = np.cross(-self.R_w, drag_force)


        torque_gen = np.array([0.0, 0.0, 0.0]) #the torque controller will generate this
        self.angular_accel = (torque_gen - torque_drag + np.cross(self.R_w, drag_force)
                            - np.cross(self.angular_vel, self.Jz*self.angular_vel))/self.Jz

        self.accel = ((drag_force + self.LIFT) / self.MASS + gravity_inertial -
                            np.cross(self.angular_vel, self.vel))


        #print(drag_force)

    def updateState(self):

        #=== update position from velocity vector ===
        vel_global = np.zeros(3)
        for i in range(3):
            if self.vel[i] > 15:
                self.vel[i] = 15.
            elif self.vel[i] < -15:
                self.vel[i] = -15.
            vel_global[i] = np.dot(self.vel, self.GLOBAL_FRAME[i])


        print("AAAAA   ", self.vel)
        #print("++++++++", self.accel, self.vel, self.angular_accel)
        self.pos = self.pos + self.dt*vel_global


        #=== generate and apply rotations from angular velocities ===
            # rotates orientation, inertial frame, sensor vectors
        new_orientation = np.zeros(3, dtype = float)
        theta_vals = np.zeros(3, dtype=float)

        rot_exists = False
        for i in range(3):
            theta_vals[i] = self.dt*self.angular_vel[i] #calculate angle to rotate about orientaiton axes
            if abs(theta_vals[i]) > self.ROTATION_MIN and rot_exists:
                rotation = rotation * Quaternion(axis=self.inertial_frame[i], angle=theta_vals[i])
            elif abs(theta_vals[i] > self.ROTATION_MIN):
                rotation = Quaternion(axis=self.inertial_frame[i], angle=theta_vals[i])
                rot_exists = True

        if rot_exists:
            self.orientation = rotation.rotate(self.orientation)
            for j in range(3):
                self.inertial_frame[j] = rotation.rotate(self.inertial_frame[j])
                self.sensor_orientations[j] = rotation.rotate(self.sensor_orientations[j])
            self.sensor_orientations[3] = rotation.rotate(self.sensor_orientations[3])


        #call function to update translational and rotational acceleration
        #and then use the newly calculated accels to adjust velocity vectors
        self.update_accels()
        self.vel = self.vel + self.dt*self.accel
        self.angular_vel = self.dt*self.angular_accel


    def updateState_verbose(self):
        #update position based on velocity, must convert velocity from inertial
        #reference frame to global frame in order for position to make sense
        vel_global = np.zeros(3)
        for i in range(3):
            vel_global[i] = np.dot(self.vel, self.GLOBAL_FRAME[i])
        self.pos = self.pos + self.dt*vel_global

        new_orientation = np.zeros(3, dtype = float)
        theta_vals = np.zeros(3, dtype=float)

        for i in range(3):
            theta_vals[i] = self.dt*self.angular_vel[i]


        for i in range(3):
            if abs(theta_vals[i]) > 0.01:
                print("=== BEFORE ROTATING ===")
                print("Orientation: ", self.orientation)
                print("Inertial Frame: ")
                print(self.inertial_frame)
                print("Sensors: ")
                print(self.sensor_orientations)

                rotation = Quaternion(axis=self.inertial_frame[i], angle=theta_vals[i])

                self.orientation = rotation.rotate(self.orientation)
                for j in range(3):
                    self.inertial_frame[j] = rotation.rotate(self.inertial_frame[j])
                    self.sensor_orientations[j] = rotation.rotate(self.sensor_orientations[j])
                self.sensor_orientations[3] = rotation.rotate(self.sensor_orientations[3])


                if theta_vals[i] > self.ROTATION_MIN:
                    print("\nAngle: ", theta_vals[i], "Axis: ", i, "\n")

                print("=== AFTER ROTATING ===")
                print("Orientation: ", self.orientation)
                print("Inertial Frame: ")
                print(self.inertial_frame)
                print("Sensors: ")
                print(self.sensor_orientations)

    def run(self, timesteps):
        data = np.array(self.pos[0], self.pos[1])
        for i in range(timesteps):
            if(i%10 == 0 and i != 0):
                #np.append(data, [self.pos[0], self.pos[1]])
                print(i, "POS:", self.pos, "----- ORIENTATION:", self.orientation)
            self.updateState()
        print("hi", data)



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
        print("ORIENTATION:  [", self.orientation[0], ", ", self.orientation[1],
            ", ", self.orientation[2], "]  (format: [x-y, x-z, y-z plane angles])\n")
