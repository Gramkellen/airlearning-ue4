from __future__ import print_function
import msgpackrpc  # install as admin: pip install msgpack-rpc-python
import numpy as np  # pip install numpy


class MsgpackMixin:
	def __repr__(self):
		from pprint import pformat
		return "<" + type(self).__name__ + "> " + pformat(vars(self), indent=4, width=1)

	def to_msgpack(self, *args, **kwargs):
		return self.__dict__

	@classmethod
	def from_msgpack(cls, encoded):
		obj = cls()
		# obj.__dict__ = {k.decode('utf-8'): (from_msgpack(v.__class__, v) if hasattr(v, "__dict__") else v) for k, v in encoded.items()}
		obj.__dict__ = {k: (v if not isinstance(v, dict) else getattr(getattr(obj, k).__class__, "from_msgpack")(v)) for
		                k, v in encoded.items()}
		# return cls(**msgpack.unpack(encoded))
		return obj


class ImageType:
	Scene = 0
	DepthPlanner = 1
	DepthPerspective = 2
	DepthVis = 3
	DisparityNormalized = 4
	Segmentation = 5
	SurfaceNormals = 6
	Infrared = 7


class DrivetrainType:
	MaxDegreeOfFreedom = 0
	ForwardOnly = 1


class LandedState:
	Landed = 0
	Flying = 1


class WeatherParameter:
	Rain = 0
	Roadwetness = 1
	Snow = 2
	RoadSnow = 3
	MapleLeaf = 4
	RoadLeaf = 5
	Dust = 6
	Fog = 7
	Enabled = 8


class Vector3r(MsgpackMixin):
	x_val = 0.0
	y_val = 0.0
	z_val = 0.0

	def __init__(self, x_val=0.0, y_val=0.0, z_val=0.0):
		self.x_val = x_val
		self.y_val = y_val
		self.z_val = z_val

	@staticmethod
	def nanVector3r():
		return Vector3r(np.nan, np.nan, np.nan)

	def __add__(self, other):
		return Vector3r(self.x_val + other.x_val, self.y_val + other.y_val, self.z_val + other.z_val)

	def __sub__(self, other):
		return Vector3r(self.x_val - other.x_val, self.y_val - other.y_val, self.z_val - other.z_val)

	def __truediv__(self, other):
		if type(other) in [int, float] + np.sctypes['int'] + np.sctypes['uint'] + np.sctypes['float']:
			return Vector3r(self.x_val / other, self.y_val / other, self.z_val / other)
		else:
			raise TypeError('unsupported operand type(s) for /: %s and %s' % (str(type(self)), str(type(other))))

	def __mul__(self, other):
		if type(other) in [int, float] + np.sctypes['int'] + np.sctypes['uint'] + np.sctypes['float']:
			return Vector3r(self.x_val * other, self.y_val * other, self.z_val)
		else:
			raise TypeError('unsupported operand type(s) for *: %s and %s' % (str(type(self)), str(type(other))))

	def dot(self, other):
		if type(self) == type(other):
			return self.x_val * other.x_val + self.y_val * other.y_val + self.z_val * other.z_val
		else:
			raise TypeError('unsupported operand type(s) for \'dot\': %s and %s' % (str(type(self)), str(type(other))))

	def cross(self, other):
		if type(self) == type(other):
			cross_product = np.cross(self.to_numpy_array(), other.to_numpy_array())
			return Vector3r(cross_product[0], cross_product[1], cross_product[2])
		else:
			raise TypeError(
				'unsupported operand type(s) for \'cross\': %s and %s' % (str(type(self)), str(type(other))))

	def get_length(self):
		return (self.x_val ** 2 + self.y_val ** 2 + self.z_val ** 2) ** 0.5

	def distance_to(self, other):
		return ((self.x_val - other.x_val) ** 2 + (self.y_val - other.y_val) ** 2 + (
					self.z_val - other.z_val) ** 2) ** 0.5

	def to_Quaternionr(self):
		return Quaternionr(self.x_val, self.y_val, self.z_val, 0)

	def to_numpy_array(self):
		return np.array([self.x_val, self.y_val, self.z_val], dtype=np.float32)


class Quaternionr(MsgpackMixin):
	w_val = 0.0
	x_val = 0.0
	y_val = 0.0
	z_val = 0.0

	def __init__(self, x_val=0.0, y_val=0.0, z_val=0.0, w_val=1.0):
		self.x_val = x_val
		self.y_val = y_val
		self.z_val = z_val
		self.w_val = w_val

	@staticmethod
	def nanQuaternionr():
		return Quaternionr(np.nan, np.nan, np.nan, np.nan)

	def __add__(self, other):
		if type(self) == type(other):
			return Quaternionr(self.x_val + other.x_val, self.y_val + other.y_val, self.z_val + other.z_val,
			                   self.w_val + other.w_val)
		else:
			raise TypeError('unsupported operand type(s) for +: %s and %s' % (str(type(self)), str(type(other))))

	def __mul__(self, other):
		if type(self) == type(other):
			t, x, y, z = self.w_val, self.x_val, self.y_val, self.z_val
			a, b, c, d = other.w_val, other.x_val, other.y_val, other.z_val
			return Quaternionr(w_val=a * t - b * x - c * y - d * z,
			                   x_val=b * t + a * x + d * y - c * z,
			                   y_val=c * t + a * y + b * z - d * x,
			                   z_val=d * t + z * a + c * x - b * y)
		else:
			raise TypeError('unsupported operand type(s) for *: %s and %s' % (str(type(self)), str(type(other))))

	def __truediv__(self, other):
		if type(other) == type(self):
			return self * other.inverse()
		elif type(other) in [int, float] + np.sctypes['int'] + np.sctypes['uint'] + np.sctypes['float']:
			return Quaternionr(self.x_val / other, self.y_val / other, self.z_val / other, self.w_val / other)
		else:
			raise TypeError('unsupported operand type(s) for /: %s and %s' % (str(type(self)), str(type(other))))

	def dot(self, other):
		if type(self) == type(other):
			return self.x_val * other.x_val + self.y_val * other.y_val + self.z_val * other.z_val + self.w_val * other.w_val
		else:
			raise TypeError('unsupported operand type(s) for \'dot\': %s and %s' % (str(type(self)), str(type(other))))

	def cross(self, other):
		if type(self) == type(other):
			return (self * other - other * self) / 2
		else:
			raise TypeError(
				'unsupported operand type(s) for \'cross\': %s and %s' % (str(type(self)), str(type(other))))

	def outer_product(self, other):
		if type(self) == type(other):
			return (self.inverse() * other - other.inverse() * self) / 2
		else:
			raise TypeError(
				'unsupported operand type(s) for \'outer_product\': %s and %s' % (str(type(self)), str(type(other))))

	def rotate(self, other):
		if type(self) == type(other):
			if other.get_length() == 1:
				return other * self * other.inverse()
			else:
				raise ValueError('length of the other Quaternionr must be 1')
		else:
			raise TypeError(
				'unsupported operand type(s) for \'rotate\': %s and %s' % (str(type(self)), str(type(other))))

	def conjugate(self):
		return Quaternionr(-self.x_val, -self.y_val, -self.z_val, self.w_val)

	def star(self):
		return self.conjugate()

	def inverse(self):
		return self.star() / self.dot(self)

	def sgn(self):
		return self / self.get_length()

	def get_length(self):
		return (self.x_val ** 2 + self.y_val ** 2 + self.z_val ** 2 + self.w_val ** 2) ** 0.5

	def to_numpy_array(self):
		return np.array([self.x_val, self.y_val, self.z_val, self.w_val], dtype=np.float32)


class Pose(MsgpackMixin):
	position = Vector3r()
	orientation = Quaternionr()

	def __init__(self, position_val=Vector3r(), orientation_val=Quaternionr()):
		self.position = position_val
		self.orientation = orientation_val

	@staticmethod
	def nanPose():
		return Pose(Vector3r.nanVector3r(), Quaternionr.nanQuaternionr())


class CollisionInfo(MsgpackMixin):
	has_collided = False
	normal = Vector3r()
	impact_point = Vector3r()
	position = Vector3r()
	penetration_depth = 0.0
	time_stamp = 0.0
	object_name = ""
	object_id = -1


class GeoPoint(MsgpackMixin):
	latitude = 0.0
	longitude = 0.0
	altitude = 0.0


class YawMode(MsgpackMixin):
	is_rate = True
	yaw_or_rate = 0.0

	def __init__(self, is_rate=True, yaw_or_rate=0.0):
		self.is_rate = is_rate
		self.yaw_or_rate = yaw_or_rate


class RCData(MsgpackMixin):
	timestamp = 0
	pitch, roll, throttle, yaw = (0.0,) * 4  # init 4 variable to 0.0
	switch1, switch2, switch3, switch4 = (0,) * 4
	switch5, switch6, switch7, switch8 = (0,) * 4
	is_initialized = False
	is_valid = False

	def __init__(self, timestamp=0, pitch=0.0, roll=0.0, throttle=0.0, yaw=0.0, switch1=0,
	             switch2=0, switch3=0, switch4=0, switch5=0, switch6=0, switch7=0, switch8=0, is_initialized=False,
	             is_valid=False):
		self.timestamp = timestamp
		self.pitch = pitch
		self.roll = roll
		self.throttle = throttle
		self.yaw = yaw
		self.switch1 = switch1
		self.switch2 = switch2
		self.switch3 = switch3
		self.switch4 = switch4
		self.switch5 = switch5
		self.switch6 = switch6
		self.switch7 = switch7
		self.switch8 = switch8
		self.is_initialized = is_initialized
		self.is_valid = is_valid


class ImageRequest(MsgpackMixin):
	camera_name = '0'
	image_type = ImageType.Scene
	pixels_as_float = False
	compress = False

	def __init__(self, camera_name, image_type, pixels_as_float=False, compress=True):
		# todo: in future remove str(), it's only for compatibility to pre v1.2
		self.camera_name = str(camera_name)
		self.image_type = image_type
		self.pixels_as_float = pixels_as_float
		self.compress = compress


class ImageResponse(MsgpackMixin):
	image_data_uint8 = np.uint8(0)
	image_data_float = 0.0
	camera_position = Vector3r()
	camera_orientation = Quaternionr()
	time_stamp = np.uint64(0)
	message = ''
	pixels_as_float = 0.0
	compress = True
	width = 0
	height = 0
	image_type = ImageType.Scene


class CarControls(MsgpackMixin):
	throttle = 0.0
	steering = 0.0
	brake = 0.0
	handbrake = False
	is_manual_gear = False
	manual_gear = 0
	gear_immediate = True

	def __init__(self, throttle=0, steering=0, brake=0,
	             handbrake=False, is_manual_gear=False, manual_gear=0, gear_immediate=True):
		self.throttle = throttle
		self.steering = steering
		self.brake = brake
		self.handbrake = handbrake
		self.is_manual_gear = is_manual_gear
		self.manual_gear = manual_gear
		self.gear_immediate = gear_immediate

	def set_throttle(self, throttle_val, forward):
		if (forward):
			is_manual_gear = False
			manual_gear = 0
			throttle = abs(throttle_val)
		else:
			is_manual_gear = False
			manual_gear = -1
			throttle = - abs(throttle_val)


class KinematicsState(MsgpackMixin):
	position = Vector3r()
	orientation = Quaternionr()
	linear_velocity = Vector3r()
	angular_velocity = Vector3r()
	linear_acceleration = Vector3r()
	angular_acceleration = Vector3r()


class EnvironmentState(MsgpackMixin):
	position = Vector3r()
	geo_point = GeoPoint()
	gravity = Vector3r()
	air_pressure = 0.0
	temperature = 0.0
	air_density = 0.0


class CarState(MsgpackMixin):
	speed = 0.0
	gear = 0
	rpm = 0.0
	maxrpm = 0.0
	handbrake = False
	collision = CollisionInfo();
	kinematics_estimated = KinematicsState()
	timestamp = np.uint64(0)


class TripStats(MsgpackMixin):
	voltage = 0.0
	energy_consumed = 0.0
	flight_time = 2.0
	distance_traveled = 0.0
	collision_count = 0


class MultirotorState(MsgpackMixin):
	collision = CollisionInfo();
	kinematics_estimated = KinematicsState()
	gps_location = GeoPoint()
	timestamp = np.uint64(0)
	landed_state = LandedState.Landed
	rc_data = RCData()
	trip_stats = TripStats()


class ProjectionMatrix(MsgpackMixin):
	matrix = []


class CameraInfo(MsgpackMixin):
	pose = Pose()
	fov = -1
	proj_mat = ProjectionMatrix()


class LidarData(MsgpackMixin):
	point_cloud = 0.0
	time_stamp = np.uint64(0)
	pose = Pose()