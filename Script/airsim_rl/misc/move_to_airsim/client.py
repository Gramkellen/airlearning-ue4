from __future__ import print_function
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from utils import *
from .types import *

import msgpackrpc  # install as admin: pip install msgpack-rpc-python
import numpy as np  # pip install numpy
import msgpack
import time
import math
import logging
import airsim


class VehicleClient:
    def __init__(self, ip="", port=41451, timeout_value=30):
        if (ip == ""):
            self.ip = "127.0.0.1"
        else:
            self.ip = ip
        self.client = msgpackrpc.Client(msgpackrpc.Address(ip, port), timeout=timeout_value, pack_encoding='utf-8',
                                        unpack_encoding='utf-8')

    # -----------------------------------  Common vehicle APIs ---------------------------------------------

    @staticmethod
    def toEulerianAngle(q):
        z = q.z_val
        y = q.y_val
        x = q.x_val
        w = q.w_val
        ysqr = y * y

        # roll (x-axis rotation)
        t0 = +2.0 * (w * x + y * z)
        t1 = +1.0 - 2.0 * (x * x + ysqr)
        roll = math.atan2(t0, t1)

        # pitch (y-axis rotation)
        t2 = +2.0 * (w * y - z * x)
        if (t2 > 1.0):
            t2 = 1
        if (t2 < -1.0):
            t2 = -1.0
        pitch = math.asin(t2)

        # yaw (z-axis rotation)
        t3 = +2.0 * (w * z + x * y)
        t4 = +1.0 - 2.0 * (ysqr + z * z)
        yaw = math.atan2(t3, t4)

        return (pitch, roll, yaw)

    def reset(self):
        self.client.call('reset')

    def resetUnreal(self, sleep_time_before=.1, sleep_time_after=.1):
        time.sleep(sleep_time_before)  # not sure why we need this, but sometimes
        # we do
        self.client.call('resetUnreal')
        time.sleep(sleep_time_after)  # this is necessary because resetUnreal is done
        # through setting a local variable through RPC
        # and later reacting to it in SimMode
        # which means other rpc calls might take effect
        # before reset. Hence to ensure the order, we need
        # an extra sleep. With Behzad machines
        # it seems like 30 ms is enough sleep time
        # althought sometimes it needs 300 ms!!!!


    def ping(self):
        return self.client.call('ping')

    def getClientVersion(self):
        return 1  # sync with C++ client

    def getServerVersion(self):
        return self.client.call('getServerVersion')

    def getMinRequiredServerVersion(self):
        return 1  # sync with C++ client

    def getMinRequiredClientVersion(self):
        return self.client.call('getMinRequiredClientVersion')

    # basic flight control
    def enableApiControl(self, is_enabled, vehicle_name=''):
        return self.client.call('enableApiControl', is_enabled, vehicle_name)

    def isApiControlEnabled(self, vehicle_name=''):
        return self.client.call('isApiControlEnabled', vehicle_name)

    def armDisarm(self, arm, vehicle_name=''):
        return self.client.call('armDisarm', arm, vehicle_name)

    def simPause(self, is_paused):
        self.client.call('simPause', is_paused)

    def simIsPause(self):
        return self.client.call("simIsPaused")

    def simContinueForTime(self, seconds):
        self.client.call('simContinueForTime', seconds)

    def getHomeGeoPoint(self, vehicle_name=''):
        return GeoPoint.from_msgpack(self.client.call('getHomeGeoPoint', vehicle_name))

    def confirmConnection(self):
        if self.ping():
            print("Connected!")
        else:
            print("Ping returned false!")
        server_ver = self.getServerVersion()
        client_ver = self.getClientVersion()
        server_min_ver = self.getMinRequiredServerVersion()
        client_min_ver = self.getMinRequiredClientVersion()

        ver_info = "Client Ver:" + str(client_ver) + " (Min Req: " + str(client_min_ver) + \
                   "), Server Ver:" + str(server_ver) + " (Min Req: " + str(server_min_ver) + ")"

        if server_ver < server_min_ver:
            print(ver_info, file=sys.stderr)
            print("AirSim server is of older version and not supported by this client. Please upgrade!")
        elif client_ver < client_min_ver:
            print(ver_info, file=sys.stderr)
            print("AirSim client is of older version and not supported by this server. Please upgrade!")
        else:
            print(ver_info)
        print('')
        return self.ping()

    # time-of-day control
    def simSetTimeOfDay(self, is_enabled, start_datetime="", is_start_datetime_dst=False, celestial_clock_speed=1,
                        update_interval_secs=60, move_sun=True):
        return self.client.call('simSetTimeOfDay', is_enabled, start_datetime, is_start_datetime_dst,
                                celestial_clock_speed, update_interval_secs, move_sun)

    # weather
    def simEnableWeather(self, enable):
        return self.client.call('simEnableWeather', enable)

    def simSetWeatherParameter(self, param, val):
        return self.client.call('simSetWeatherParameter', param, val)

    # camera control
    # simGetImage returns compressed png in array of bytes
    # image_type uses one of the ImageType members
    def simGetImage(self, camera_name, image_type, vehicle_name=''):
        # todo: in future remove below, it's only for compatibility to pre v1.2
        camera_name = str(camera_name)

        # because this method returns std::vector<uint8>, msgpack decides to encode it as a string unfortunately.
        result = self.client.call('simGetImage', camera_name, image_type, vehicle_name)
        if (result == "" or result == "\0"):
            return None
        return result

    # camera control
    # simGetImage returns compressed png in array of bytes
    # image_type uses one of the ImageType members
    def simGetImages(self, requests, vehicle_name=''):
        responses_raw = self.client.call('simGetImages', requests, vehicle_name)
        return [ImageResponse.from_msgpack(response_raw) for response_raw in responses_raw]

    def simGetCollisionInfo(self, vehicle_name=''):
        return CollisionInfo.from_msgpack(self.client.call('simGetCollisionInfo', vehicle_name))

    def simSetVehiclePose(self, pose, ignore_collison, vehicle_name=''):
        self.client.call('simSetVehiclePose', pose, ignore_collison, vehicle_name)

    def simGetVehiclePose(self, vehicle_name=''):
        pose = self.client.call('simGetVehiclePose', vehicle_name)
        return Pose.from_msgpack(pose)

    def simGetObjectPose(self, object_name):
        pose = self.client.call('simGetObjectPose', object_name)
        return Pose.from_msgpack(pose)

    def simSetObjectPose(self, object_name, pose, teleport=True):
        return self.client.call('simSetObjectPose', object_name, pose, teleport)

    def simSetSegmentationObjectID(self, mesh_name, object_id, is_name_regex=False):
        return self.client.call('simSetSegmentationObjectID', mesh_name, object_id, is_name_regex)

    def simGetSegmentationObjectID(self, mesh_name):
        return self.client.call('simGetSegmentationObjectID', mesh_name)

    def simPrintLogMessage(self, message, message_param="", severity=0):
        return self.client.call('simPrintLogMessage', message, message_param, severity)

    def simGetCameraInfo(self, camera_name, vehicle_name=''):
        # TODO: below str() conversion is only needed for legacy reason and should be removed in future
        return CameraInfo.from_msgpack(self.client.call('simGetCameraInfo', str(camera_name), vehicle_name))

    def simSetCameraOrientation(self, camera_name, orientation, vehicle_name=''):
        # TODO: below str() conversion is only needed for legacy reason and should be removed in future
        self.client.call('simSetCameraOrientation', str(camera_name), orientation, vehicle_name)

    def simGetGroundTruthKinematics(self, vehicle_name=''):
        kinematics_state = self.client.call('simGetGroundTruthKinematics', vehicle_name)
        return KinematicsState.from_msgpack(kinematics_state)

    simGetGroundTruthKinematics.__annotations__ = {'return': KinematicsState}

    def simGetGroundTruthEnvironment(self, vehicle_name=''):
        env_state = self.client.call('simGetGroundTruthEnvironment', vehicle_name)
        return EnvironmentState.from_msgpack(env_state)

    simGetGroundTruthEnvironment.__annotations__ = {'return': EnvironmentState}

    # lidar APIs
    def getLidarData(self, lidar_name='', vehicle_name=''):
        return LidarData.from_msgpack(self.client.call('getLidarData', lidar_name, vehicle_name))

    # ----------- APIs to control ACharacter in scene ----------/
    def simCharSetFaceExpression(self, expression_name, value, character_name=""):
        self.client.call('simCharSetFaceExpression', expression_name, value, character_name)

    def simCharGetFaceExpression(self, expression_name, character_name=""):
        return self.client.call('simCharGetFaceExpression', expression_name, character_name)

    def simCharGetAvailableFaceExpressions(self):
        return self.client.call('simCharGetAvailableFaceExpressions')

    def simCharSetSkinDarkness(self, value, character_name=""):
        self.client.call('simCharSetSkinDarkness', value, character_name)

    def simCharGetSkinDarkness(self, character_name=""):
        return self.client.call('simCharGetSkinDarkness', character_name)

    def simCharSetSkinAgeing(self, value, character_name=""):
        self.client.call('simCharSetSkinAgeing', value, character_name)

    def simCharGetSkinAgeing(self, character_name=""):
        return self.client.call('simCharGetSkinAgeing', character_name)

    def simCharSetHeadRotation(self, q, character_name=""):
        self.client.call('simCharSetHeadRotation', q, character_name)

    def simCharGetHeadRotation(self, character_name=""):
        return self.client.call('simCharGetHeadRotation', character_name)

    def simCharSetBonePose(self, bone_name, pose, character_name=""):
        self.client.call('simCharSetBonePose', bone_name, pose, character_name)

    def simCharGetBonePose(self, bone_name, character_name=""):
        return self.client.call('simCharGetBonePose', bone_name, character_name)

    def simCharResetBonePose(self, bone_name, character_name=""):
        self.client.call('simCharResetBonePose', bone_name, character_name)

    def simCharSetFacePreset(self, preset_name, value, character_name=""):
        self.client.call('simCharSetFacePreset', preset_name, value, character_name)

    def simCharSetFacePresets(self, presets, character_name=""):
        self.client.call('simSetFacePresets', presets, character_name)

    def simCharSetBonePoses(self, poses, character_name=""):
        self.client.call('simSetBonePoses', poses, character_name)

    def simCharGetBonePoses(self, bone_names, character_name=""):
        return self.client.call('simGetBonePoses', bone_names, character_name)

    def cancelLastTask(self):
        self.client.call('cancelLastTask')

    def waitOnLastTask(self, timeout_sec=float('nan')):
        return self.client.call('waitOnLastTask', timeout_sec)

    # legacy handling
    # TODO: remove below legacy wrappers in future major releases
    upgrade_api_help = ""

    def simGetPose(self):
        # logging.warning("simGetPose API is renamed to simGetVehiclePose. Please update your code." + self.upgrade_api_help)
        return self.simGetVehiclePose()

    def simSetPose(self, pose, ignore_collison):
        # logging.warning("simSetPose API is renamed to simSetVehiclePose. Please update your code." + self.upgrade_api_help)
        return self.simSetVehiclePose(pose, ignore_collison)

    def getCollisionInfo(self):
        # logging.warning("getCollisionInfo API is renamed to simGetCollisionInfo. Please update your code." + self.upgrade_api_help)
        return self.simGetCollisionInfo()

    def getCameraInfo(self, camera_id):
        # logging.warning("getCameraInfo API is renamed to simGetCameraInfo. Please update your code." + self.upgrade_api_help)
        return self.simGetCameraInfo(camera_id)

    def setCameraOrientation(self, camera_id, orientation):
        # logging.warning("setCameraOrientation API is renamed to simSetCameraOrientation. Please update your code." + self.upgrade_api_help)
        return self.simSetCameraOrientation(camera_id, orientation)

    def getPosition(self):
        # logging.warning("getPosition API is deprecated. For ground-truth please use simGetGroundTruthKinematics() API." + self.upgrade_api_help)
        return self.simGetGroundTruthKinematics().position

    def getVelocity(self):
        # logging.warning("getVelocity API is deprecated. For ground-truth please use simGetGroundTruthKinematics() API." + self.upgrade_api_help)
        return self.simGetGroundTruthKinematics().linear_velocity

    def getOrientation(self):
        # logging.warning("getOrientation API is deprecated. For ground-truth please use simGetGroundTruthKinematics() API." + self.upgrade_api_help)
        return self.simGetGroundTruthKinematics().orientation

    def getPitchRollYaw(self):
        return self.toEulerianAngle(self.getOrientation())

    def getLandedState(self):
        raise Exception("getLandedState API is deprecated. Please use getMultirotorState() API")

    def getGpsLocation(self):
        # logging.warning("getGpsLocation API is deprecated. For ground-truth please use simGetGroundTruthKinematics() API." + self.upgrade_api_help)
        return self.simGetGroundTruthEnvironment().geo_point

    def takeoff(self, max_wait_seconds=15):
        raise Exception("takeoff API is deprecated. Please use takeoffAsync() API." + self.upgrade_api_help)

    def land(self, max_wait_seconds=60):
        raise Exception("land API is deprecated. Please use landAsync() API." + self.upgrade_api_help)

    def goHome(self):
        raise Exception("goHome API is deprecated. Please use goHomeAsync() API." + self.upgrade_api_help)

    def hover(self):
        raise Exception("hover API is deprecated. Please use hoverAsync() API." + self.upgrade_api_help)

    def moveByAngleZ(self, pitch, roll, z, yaw, duration):
        raise Exception("moveByAngleZ API is deprecated. Please use moveByAngleZAsync() API." + self.upgrade_api_help)

    def moveByAngleThrottle(self, pitch, roll, throttle, yaw_rate, duration):
        raise Exception(
            "moveByAngleThrottle API is deprecated. Please use moveByAngleThrottleAsync() API." + self.upgrade_api_help)

    def moveByVelocity(self, vx, vy, vz, duration, drivetrain=DrivetrainType.MaxDegreeOfFreedom, yaw_mode=YawMode()):
        raise Exception(
            "moveByVelocity API is deprecated. Please use moveByVelocityAsync() API." + self.upgrade_api_help)

    def moveByVelocityZ(self, vx, vy, z, duration, drivetrain=DrivetrainType.MaxDegreeOfFreedom, yaw_mode=YawMode()):
        raise Exception(
            "moveByVelocityZ API is deprecated. Please use moveByVelocityZAsync() API." + self.upgrade_api_help)

    def moveOnPath(self, path, velocity, max_wait_seconds=60, drivetrain=DrivetrainType.MaxDegreeOfFreedom,
                   yaw_mode=YawMode(), lookahead=-1, adaptive_lookahead=1):
        raise Exception("moveOnPath API is deprecated. Please use moveOnPathAsync() API." + self.upgrade_api_help)

    def moveToZ(self, z, velocity, max_wait_seconds=60, yaw_mode=YawMode(), lookahead=-1, adaptive_lookahead=1):
        raise Exception("moveToZ API is deprecated. Please use moveToZAsync() API." + self.upgrade_api_help)

    def moveToPosition(self, x, y, z, velocity, max_wait_seconds=60, drivetrain=DrivetrainType.MaxDegreeOfFreedom,
                       yaw_mode=YawMode(), lookahead=-1, adaptive_lookahead=1):
        raise Exception(
            "moveToPosition API is deprecated. Please use moveToPositionAsync() API." + self.upgrade_api_help)

    def moveByManual(self, vx_max, vy_max, z_min, duration, drivetrain=DrivetrainType.MaxDegreeOfFreedom,
                     yaw_mode=YawMode()):
        raise Exception("moveByManual API is deprecated. Please use moveByManualAsync() API." + self.upgrade_api_help)

    def rotateToYaw(self, yaw, max_wait_seconds=60, margin=5):
        raise Exception("rotateToYaw API is deprecated. Please use rotateToYawAsync() API." + self.upgrade_api_help)

    def rotateByYawRate(self, yaw_rate, duration):
        raise Exception(
            "rotateByYawRate API is deprecated. Please use rotateByYawRateAsync() API." + self.upgrade_api_help)

    def setRCData(self, rcdata=RCData()):
        raise Exception("setRCData API is deprecated. Please use moveByRC() API." + self.upgrade_api_help)


# -----------------------------------  Multirotor APIs ---------------------------------------------
class MultirotorClient(VehicleClient, object):
    def __init__(self, ip="", port=41451, timeout_value=30):
        super(MultirotorClient, self).__init__(ip, port, timeout_value)

    def takeoffAsync(self, timeout_sec=20, vehicle_name=''):
        return self.client.call_async('takeoff', timeout_sec, vehicle_name)

    def landAsync(self, timeout_sec=60, vehicle_name=''):
        return self.client.call_async('land', timeout_sec, vehicle_name)

    def goHomeAsync(self, timeout_sec=3e+38, vehicle_name=''):
        return self.client.call_async('goHome', timeout_sec, vehicle_name)

    # APIs for control
    def moveByAngleZAsync(self, pitch, roll, z, yaw, duration, vehicle_name=''):
        return self.client.call_async('moveByAngleZ', pitch, roll, z, yaw, duration, vehicle_name)

    def moveByAngleThrottleAsync(self, pitch, roll, throttle, yaw_rate, duration, vehicle_name=''):
        return self.client.call_async('moveByAngleThrottle', pitch, roll, throttle, yaw_rate, duration, vehicle_name)

    def moveByVelocityAsync(self, vx, vy, vz, duration, drivetrain=DrivetrainType.MaxDegreeOfFreedom,
                            yaw_mode=YawMode(), vehicle_name=''):
        return self.client.call_async('moveByVelocity', vx, vy, vz, duration, drivetrain, yaw_mode, vehicle_name)

    def moveByVelocityZAsync(self, vx, vy, z, duration, drivetrain=DrivetrainType.MaxDegreeOfFreedom,
                             yaw_mode=YawMode(), vehicle_name=''):
        return self.client.call_async('moveByVelocityZ', vx, vy, z, duration, drivetrain, yaw_mode, vehicle_name)

    def moveOnPathAsync(self, path, velocity, timeout_sec=3e+38, drivetrain=DrivetrainType.MaxDegreeOfFreedom,
                        yaw_mode=YawMode(),
                        lookahead=-1, adaptive_lookahead=1, vehicle_name=''):
        return self.client.call_async('moveOnPath', path, velocity, timeout_sec, drivetrain, yaw_mode, lookahead,
                                      adaptive_lookahead, vehicle_name)

    def moveToPositionAsync(self, x, y, z, velocity, timeout_sec=3e+38, drivetrain=DrivetrainType.MaxDegreeOfFreedom,
                            yaw_mode=YawMode(),
                            lookahead=-1, adaptive_lookahead=1, vehicle_name=''):
        return self.client.call_async('moveToPosition', x, y, z, velocity, timeout_sec, drivetrain, yaw_mode, lookahead,
                                      adaptive_lookahead, vehicle_name)

    def getTripStats(self, vehicle_name=''):
        trip_stats_raw = self.client.call('getTripStats', vehicle_name)
        return TripStats.from_msgpack(trip_stats_raw)

    def moveToZAsync(self, z, velocity, timeout_sec=3e+38, yaw_mode=YawMode(), lookahead=-1, adaptive_lookahead=1,
                     vehicle_name=''):
        return self.client.call_async('moveToZ', z, velocity, timeout_sec, yaw_mode, lookahead, adaptive_lookahead,
                                      vehicle_name)

    def moveByManualAsync(self, vx_max, vy_max, z_min, duration, drivetrain=DrivetrainType.MaxDegreeOfFreedom,
                          yaw_mode=YawMode(), vehicle_name=''):
        """Read current RC state and use it to control the vehicles.

		Parameters sets up the constraints on velocity and minimum altitude while flying. If RC state is detected to violate these constraints
		then that RC state would be ignored.

		:param vx_max: max velocity allowed in x direction
		:param vy_max: max velocity allowed in y direction
		:param vz_max: max velocity allowed in z direction
		:param z_min: min z allowed for vehicle position
		:param duration: after this duration vehicle would switch back to non-manual mode
		:param drivetrain: when ForwardOnly, vehicle rotates itself so that its front is always facing the direction of travel. If MaxDegreeOfFreedom then it doesn't do that (crab-like movement)
		:param yaw_mode: Specifies if vehicle should face at given angle (is_rate=False) or should be rotating around its axis at given rate (is_rate=True)
		"""
        return self.client.call_async('moveByManual', vx_max, vy_max, z_min, duration, drivetrain, yaw_mode,
                                      vehicle_name)

    def moveByAngleRatesZAsync(self, roll_rate, pitch_rate, yaw_rate, z, duration, vehicle_name = ''):
        """
        - z is given in local NED frame of the vehicle.
        - Roll rate, pitch rate, and yaw rate set points are given in **radians**, in the body frame.
        - The body frame follows the Front Left Up (FLU) convention, and right-handedness.
        - Frame Convention:
            - X axis is along the **Front** direction of the quadrotor.
            | Clockwise rotation about this axis defines a positive **roll** angle.
            | Hence, rolling with a positive angle is equivalent to translating in the **right** direction, w.r.t. our FLU body frame.
            - Y axis is along the **Left** direction of the quadrotor.
            | Clockwise rotation about this axis defines a positive **pitch** angle.
            | Hence, pitching with a positive angle is equivalent to translating in the **front** direction, w.r.t. our FLU body frame.
            - Z axis is along the **Up** direction.
            | Clockwise rotation about this axis defines a positive **yaw** angle.
            | Hence, yawing with a positive angle is equivalent to rotated towards the **left** direction wrt our FLU body frame. Or in an anticlockwise fashion in the body XY / FL plane.
        Args:
            roll_rate (float): Desired roll rate, in radians / second
            pitch_rate (float): Desired pitch rate, in radians / second
            yaw_rate (float): Desired yaw rate, in radians / second
            z (float): Desired Z value (in local NED frame of the vehicle)
            duration (float): Desired amount of time (seconds), to send this command for
            vehicle_name (str, optional): Name of the multirotor to send this command to
        Returns:
            msgpackrpc.future.Future: future. call .join() to wait for method to finish. Example: client.METHOD().join()
        """
        return self.client.call_async('moveByAngleRatesZ', roll_rate, -pitch_rate, -yaw_rate, z, duration, vehicle_name)


    def rotateToYawAsync(self, yaw, timeout_sec=3e+38, margin=5, vehicle_name=''):
        return self.client.call_async('rotateToYaw', yaw, timeout_sec, margin, vehicle_name)

    def rotateByYawRateAsync(self, yaw_rate, duration, vehicle_name=''):
        return self.client.call_async('rotateByYawRate', yaw_rate, duration, vehicle_name)

    def hoverAsync(self, vehicle_name=''):
        return self.client.call_async('hover', vehicle_name)

    def moveByRC(self, rcdata=RCData(), vehicle_name=''):
        return self.client.call('moveByRC', rcdata, vehicle_name)

    # query vehicle state
    def getMultirotorState(self, vehicle_name=''):
        return MultirotorState.from_msgpack(self.client.call('getMultirotorState', vehicle_name))

    getMultirotorState.__annotations__ = {'return': MultirotorState}


# -----------------------------------  Car APIs ---------------------------------------------
class CarClient(VehicleClient, object):
    def __init__(self, ip="", port=41451, timeout_value=3600):
        super(CarClient, self).__init__(ip, port, timeout_value)

    def setCarControls(self, controls, vehicle_name=''):
        self.client.call('setCarControls', controls, vehicle_name)

    def getCarState(self, vehicle_name=''):
        state_raw = self.client.call('getCarState', vehicle_name)
        return CarState.from_msgpack(state_raw)
