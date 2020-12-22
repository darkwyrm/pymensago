'''Module for encapsulating Anselus' RPC protocol'''

import json
import socket

import jsonschema


from pyanselus.retval import RetVal, ExceptionThrown, NetworkError, \
	ResourceNotFound
import pyanselus.rpc_schemas

InvalidJSON = 'InvalidJSON'
InvalidMessage = 'InvalidMessage'
MessageTooLarge = 'MessageTooLarge'

# Number of seconds to wait for a client before timing out
CONN_TIMEOUT = 900.0

# Size (in bytes) of the read buffer size for recv()
READ_BUFFER_SIZE = 8192

class ServerConnection:
	'''Represents a connection to an Anselus server'''
	
	def __init__(self):
		self.__sock = None
		self.ip = None
		self.port = None
		self.version = ''
	
	def connect(self, host: str, port) -> RetVal:
		'''Creates a connection to the server.'''
		try:
			self.__sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			# Set a short timeout in case the server doesn't respond immediately,
			# which is the expectation as soon as a client connects.
			self.__sock.settimeout(10.0)
		except:
			return RetVal(NetworkError, "Couldn't create a socket")
		
		out_data = RetVal()
		out_data.set_value('socket', self.__sock)
		
		try:
			self.ip = socket.gethostbyname(host)
		except socket.gaierror:
			self.disconnect()
			return RetVal(ResourceNotFound, "Couldn't locate host %s" % host)
		
		try:
			self.__sock.connect((self.ip, port))
			self.port = port
			
			status = self.read_msg(pyanselus.rpc_schemas.greeting)
			if not status.error():
				self.version = status['msg']['version'].strip()

		except Exception as exc:
			self.disconnect()
			return RetVal(NetworkError, 
				f"Couldn't connect to host {host}: {exc}")

		# Set a timeout of 30 minutes
		self.__sock.settimeout(1800.0)
		return out_data

	def disconnect(self):
		'''Disconnects from a server'''
		self.__sock.close()
		self.__sock = None
		self.ip = None
		self.port = None

	def read_msg(self, schema=None) -> RetVal:
		'''Reads a message from the supplied socket'''

		if not self.__sock:
			return RetVal(NetworkError, 'No connection')
		
		try:
			rawdata = self.__sock.recv(READ_BUFFER_SIZE)
		except Exception as exc:
			self.__sock.close()
			return RetVal(ExceptionThrown, exc.__str__())
		
		try:
			rawstring = rawdata.decode()
		except Exception as exc:
			return RetVal(ExceptionThrown, exc.__str__())
		
		try:
			msg = json.loads(rawstring)
		except Exception as exc:
			return RetVal(InvalidJSON, exc.__str__())
		
		if schema:
			try:
				jsonschema.validate(msg, schema)
			except Exception as exc:
				return RetVal(InvalidMessage, exc.__str__())
		
		return RetVal().set_value('msg', msg)


	def send_msg(self, msg: dict) -> RetVal:
		'''Sends a message over a socket'''

		if not self.__sock:
			return RetVal(NetworkError, 'No connection')
		
		try:
			jsonstr = json.dumps(msg)
		except Exception as exc:
			self.disconnect()
			return RetVal(ExceptionThrown, exc.__str__())
		
		if len(jsonstr) > READ_BUFFER_SIZE:
			return RetVal(MessageTooLarge, "Message is larger than 8K")
		
		try:
			self.__sock.send(jsonstr.encode())
		except Exception as exc:
			self.disconnect()
			return RetVal(ExceptionThrown, exc.__str__())
		
		return RetVal()
