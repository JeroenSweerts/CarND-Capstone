#!/usr/bin/env python
import rospy
from std_msgs.msg import Int32
from geometry_msgs.msg import PoseStamped, Pose
from styx_msgs.msg import TrafficLightArray, TrafficLight
from styx_msgs.msg import Lane
from sensor_msgs.msg import Image
from rosgraph_msgs.msg import Log   #added for Raz's debug
from cv_bridge import CvBridge
from light_classification.tl_classifier import TLClassifier
import tf
import cv2
import yaml
import math
from copy import deepcopy

STATE_COUNT_THRESHOLD = 3

class TLDetector(object):
    def __init__(self):
        rospy.init_node('tl_detector')

        self.pose = None
        self.waypoints = None
        self.camera_image = None
        self.lights = []

        sub1 = rospy.Subscriber('/current_pose', PoseStamped, self.pose_cb)
        sub2 = rospy.Subscriber('/base_waypoints', Lane, self.waypoints_cb)

        '''
        /vehicle/traffic_lights provides you with the location of the traffic light in 3D map space and
        helps you acquire an accurate ground truth data source for the traffic light
        classifier by sending the current color state of all traffic lights in the
        simulator. When testing on the vehicle, the color state will not be available. You'll need to
        rely on the position of the light and the camera image to predict it.
        '''
        sub3 = rospy.Subscriber('/vehicle/traffic_lights', TrafficLightArray, self.traffic_cb)     
        sub7 = rospy.Subscriber('/rosout', Log, self.image_cb)  #added for Raz's debug
        # sub6 = rospy.Subscriber('/image_color', Image, self.image_cb) #commented for Raz's debug

        config_string = rospy.get_param("/traffic_light_config")
        self.config = yaml.load(config_string)

        self.upcoming_red_light_pub = rospy.Publisher('/traffic_waypoint', Int32, queue_size=1)

        self.bridge = CvBridge()
        self.light_classifier = TLClassifier()
        self.listener = tf.TransformListener()

        self.state = TrafficLight.UNKNOWN
        self.last_state = TrafficLight.UNKNOWN
        self.last_wp = -1
        self.state_count = 0

        # initialize traffic lights as position objects

        stop_line_positions = self.config['stop_line_positions']

        self.stop_line_positions = []

        for i in range(len(stop_line_positions)):
            self.stop_line_positions.append(PoseStamped())
            self.stop_line_positions[i].pose.position.x=stop_line_positions[i][0]
            self.stop_line_positions[i].pose.position.y=stop_line_positions[i][1]
            self.stop_line_positions[i].pose.position.z=0



        rospy.spin()




    def pose_cb(self, msg):
        self.pose = msg

    def waypoints_cb(self, waypoints):
        self.waypoints=waypoints

    def traffic_cb(self, msg):
        self.lights = msg.lights

    def image_cb(self, msg):
        """Identifies red lights in the incoming camera image and publishes the index
            of the waypoint closest to the red light's stop line to /traffic_waypoint

        Args:
            msg (Image): image from car-mounted camera

        """
        # self.has_image = True     #commented for Raz's debug
        # self.camera_image = msg   #commented for Raz's debug
        light_wp, state = self.process_traffic_lights()

        
        light_wp = light_wp if state == TrafficLight.RED else -1        #added for Raz's debug

        rospy.loginfo(light_wp) #added for Raz's debug don't remove this 

        self.upcoming_red_light_pub.publish(Int32(light_wp))    #added for Raz's debug
        
        '''
        Publish upcoming red lights at camera frequency.
        Each predicted state has to occur `STATE_COUNT_THRESHOLD` number
        of times till we start using it. Otherwise the previous stable state is
        used.
        '''
        # if self.state != state:   #commented for Raz's debug -start
        #     self.state_count = 0
        #     self.state = state
        # elif self.state_count >= STATE_COUNT_THRESHOLD:
        #     self.last_state = self.state
        #     light_wp = light_wp if state == TrafficLight.RED else -1
        #     self.last_wp = light_wp
        #     self.upcoming_red_light_pub.publish(Int32(light_wp))
        # else:
        #     self.upcoming_red_light_pub.publish(Int32(self.last_wp))
        # self.state_count += 1  #commented for Raz's debug -end

    def get_closest_waypoint(self, pose):
        """Identifies the closest path waypoint to the given position
            https://en.wikipedia.org/wiki/Closest_pair_of_points_problem
        Args:
            pose (Pose): position to match a waypoint to

        Returns:
            int: index of the closest waypoint in self.waypoints

        """
        #TODO implement
        
        if self.waypoints==None:  
            return -1


        closest_distance_found = 10e9
        closest_index = -1
        

        for i in range(len(self.waypoints.waypoints)):
            curr_dist = self.distance(pose.position, self.waypoints.waypoints[i].pose.pose.position)
            if curr_dist < closest_distance_found:
                closest_distance_found = curr_dist
                closest_index = i

        return closest_index
        


    def distance(self, a, b):
        return math.sqrt((b.x - a.x) ** 2 + (b.y - a.y) ** 2 + (b.z - a.z) ** 2)

    def get_light_state(self, light):
        """Determines the current color of the traffic light

        Args:
            light (TrafficLight): light to classify

        Returns:
            int: ID of traffic light color (specified in styx_msgs/TrafficLight)

        """
        if(not self.has_image):
            self.prev_light_loc = None
            return False

        cv_image = self.bridge.imgmsg_to_cv2(self.camera_image, "bgr8")

        #Get classification
        return self.light_classifier.get_classification(cv_image)

    def process_traffic_lights(self):
        """Finds closest visible traffic light, if one exists, and determines its
            location and color

        Returns:
            int: index of waypoint closes to the upcoming stop line for a traffic light (-1 if none exists)
            int: ID of traffic light color (specified in styx_msgs/TrafficLight)

        """
        light_bool = None
        light_wp =None

        # List of positions that correspond to the line to stop in front of for a given intersection
        car_position_index=None

        if(self.pose):
            car_position_index = self.get_closest_waypoint(self.pose.pose)

        #TODO find the closest visible traffic light (if one exists)

        closest_traffic_light_index =10e9


        if(car_position_index):
            for stop_line_position in self.stop_line_positions:
                traffic_light_index= self.get_closest_waypoint(stop_line_position.pose)
                if traffic_light_index<closest_traffic_light_index and traffic_light_index>car_position_index:
                    closest_traffic_light_index=traffic_light_index
                    light_wp =closest_traffic_light_index
                    light_bool=True

        
        if light_bool:


            # start - remove code after classifier has been implemented
            for i in range(len(self.stop_line_positions)):
                if(abs(self.stop_line_positions[i].pose.position.x-self.waypoints.waypoints[light_wp].pose.pose.position.x)<10):
                    state = self.lights[i].state
            # end - remove code after classifier has been implemented

            #state = self.get_light_state(light)
            return light_wp, state
        return -1, TrafficLight.UNKNOWN




if __name__ == '__main__':
    try:
        TLDetector()
    except rospy.ROSInterruptException:
        rospy.logerr('Could not start traffic node.')
