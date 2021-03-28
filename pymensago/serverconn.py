'''This module contains the functions needed by any Mensago client for 
communications. Commands largely map 1-to-1 to the commands outlined in the 
spec.'''

from base64 import b85encode
import json
import re
import secrets
import socket
import time
import uuid

import jsonschema

from pymensago.cryptostring import CryptoString
from pymensago.encryption import DecryptionFailure, EncryptionPair, PublicKey, SigningPair
from pymensago.errorcodes import *	# pylint: disable=wildcard-import
from pymensago.keycard import EntryBase
from pymensago.retval import RetVal, BadParameterValue, ExceptionThrown, NetworkError, \
	ResourceExists, ServerError
import pymensago.utils as utils

__errcode_map = {
	'100': MsgContinue,
	'101': MsgPending,
	'102': MsgItem,
	'103': MsgUpdate,
	'104': MsgTransfer,

	# Success Codes
	'200': MsgOK,
	'201': MsgRegistered,
	'202': MsgUnregistered,

	# Server Error Codes
	'300': MsgInternal,
	'301': MsgNotImplemented,
	'302': MsgServerMaint,
	'303': MsgServerUnavail,
	'304': MsgRegClosed,
	'305': MsgInterrupted,
	'306': MsgKeyFail,
	'307': MsgDeliveryFailLimit,
	'308': MsgDeliveryDelay,
	'309': MsgAlgoNotSupported,

	# Client Error Codes
	'400': MsgBadRequest,
	'401': MsgUnauthorized,
	'402': MsgAuthFailure,
	'403': MsgForbidden,
	'404': MsgNotFound,
	'405': MsgTerminated,
	'406': MsgPaymentReqd,
	'407': MsgUnavailable,
	'408': MsgResExists,
	'409': MsgQuotaInsuff,
	'410': MsgHashMismatch,
	'411': MsgBadKeycard,
	'412': MsgNonComKeycard,
	'413': MsgInvalidSig,
	'414': MsgLimitReached,
	'415': MsgExpired
}

server_response = {
	'title' : 'Mensago Server Response',
	'type' : 'object',
	'required' : [ 'Code', 'Status', 'Data' ],
	'properties' : {
		'Code' : {
			'type' : 'integer'
		},
		'Status' : {
			'type' : 'string'
		},
		'Data' : {
			'type' : 'object'
		}
	}
}

# Number of seconds to wait for a client before timing out
CONN_TIMEOUT = 900.0

# Size (in bytes) of the read buffer size for recv()
READ_BUFFER_SIZE = 8192

class ServerConnection:
	'''Mini class to simplify network communications'''
	def __init__(self):
		self.socket = None
	
	def connect(self, address: str, port: int) -> RetVal:
		'''Creates a connection to the server.'''
		try:
			sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			# Set a short timeout in case the server doesn't respond immediately,
			# which is the expectation as soon as a client connects.
			sock.settimeout(10.0)
		except Exception as e:
			return RetVal(ExceptionThrown, e)
		
		try:
			sock.connect((address, port))
			
			# absorb the hello string
			_ = sock.recv(8192)

		except Exception as e:
			sock.close()
			return RetVal(ExceptionThrown, e)

		# Set a timeout of 30 minutes
		sock.settimeout(1800.0)
		
		self.socket = sock
		return RetVal()

	def is_connected(self) -> bool:
		'''Returns whether or not the instance is connected to a server'''
		return bool(self.socket is None)

	def disconnect(self) -> RetVal:
		'''Disconnects by sending a QUIT command to the server'''
		return self.send_message({'Action':'QUIT','Data':{}})

	def send_message(self, command : dict) -> RetVal:
		'''Sends a message to the server with command sent as JSON data'''
		cmdstr = json.dumps(command) + '\r\n'
		
		if not self.socket:
			return RetVal(NetworkError, 'not connected')
		
		try:
			self.socket.send(cmdstr.encode())
		except Exception as e:
			self.socket.close()
			return RetVal(ExceptionThrown, e)
		
		return RetVal()

	def read_response(self, schema: dict) -> RetVal:
		'''Reads a server response and returns a separated code and string'''
		
		if not self.socket:
			return None
		
		# We don't actually handle the possible exceptions because we *want* to have them crash --
		# the test will fail and give us the cause of the exception. If we have a successful test, 
		# exceptions weren't thrown
		try:
			rawdata = self.socket.recv(8192)
			rawstring = rawdata.decode()
			rawresponse = json.loads(rawstring)
			if schema:
				jsonschema.validate(rawresponse, schema)
		except Exception as e:
			return RetVal(ExceptionThrown, e)

		response = RetVal()
		response['Code'] = rawresponse['Code']
		response['Status'] = rawresponse['Status']
		response['Info'] = rawresponse['Info']
		response['Data'] = rawresponse['Data']
		return response
	
	def read(self) -> str:
		'''Reads a string from the network connection'''
		
		if not self.socket:
			return None
		
		rawdata = self.socket.recv(8192)
		return rawdata.decode()

	def write(self, text: str) -> RetVal:
		'''Sends a string over a socket'''

		if not self.socket:
			return RetVal(NetworkError, 'Invalid connection')
		
		try:
			self.socket.send(text.encode())
		except Exception as exc:
			self.socket.close()
			return RetVal(ExceptionThrown, exc.__str__())
		
		return RetVal()


def wrap_server_error(response) -> RetVal:
	'''Wraps a server response into a RetVal object'''
	out = RetVal(__errcode_map.get(response['Code'],ServerError), response['Status']).set_values({
		'Code' : response['Code'],
		'Status' : response['Status'],
		'Info' : ''
	})
	
	if 'Info' in response:
		out['Info'] = response['Info']
	
	return out


def addentry(conn: ServerConnection, entry: EntryBase, ovkey: CryptoString,
	spair: SigningPair) -> RetVal:
	'''Handles the process to upload an entry to the server.'''

	conn.send_message({
		'Action' : "ADDENTRY",
		'Data' : { 'Base-Entry' : entry.make_bytestring(0).decode() }
	})

	response = conn.read_response(server_response)
	if response['Code'] != 100:
		return wrap_server_error(response)

	for field in ['Organization-Signature', 'Hash', 'Previous-Hash']	:
		if field not in response['Data']:
			return RetVal(ServerError, f"Server did not return required field {field}")

	entry.signatures['Organization'] =  response['Data']['Organization-Signature']

	# A regular client will check the entry cache, pull updates to the org card, and get the 
	# verification key. Because this is just an integration test, we skip all that and just use
	# the known verification key from earlier in the test.
	status = entry.verify_signature(ovkey, 'Organization')
	if status.error():
		return status
	
	entry.prev_hash = response['Data']['Previous-Hash']
	entry.hash = response['Data']['Hash']
	status = entry.verify_hash()
	if status.error():
		return status
	
	# User sign and verify
	status = entry.sign(spair.private, 'User')
	if status.error():
		return status

	status = entry.verify_signature(spair.public, 'User')
	if status.error():
		return status

	status = entry.is_compliant()
	if status.error():
		return status

	conn.send_message({
		'Action' : "ADDENTRY",
		'Data' : { 'User-Signature' : entry.signatures['User'] }
	})
	
	response = conn.read_response(server_response)
	if response['Code'] != 200:
		return wrap_server_error(response)

	return RetVal()


def cancel(conn: ServerConnection):
	'''Returns the session to a state where it is ready for the next command'''
	conn.send_message({ 'Action' : "CANCEL", 'Data' : {}})
	
	response = conn.read_response(None)
	if response.error():
		return response
	
	if response['Code'] == 200:
		return RetVal()
	return wrap_server_error(response)


def copy(conn: ServerConnection, srcfile: str, destdir: str) -> RetVal:
	'''Copies a file to the requested directory and returns the name of the new file'''
	if not srcfile or not destdir:
		return RetVal(MsgBadRequest).set_value('Status', 400)
	
	request = {
		'Action' : 'COPY',
		'Data' : {
			'SourceFile' : srcfile,
			'DestDir' : destdir
		}
	}
	conn.send_message(request)

	response = conn.read_response(server_response)
	if response.error():
		return response
	
	if response['Code'] != 200:
		return wrap_server_error(response)
	
	return RetVal().set_value('name', response['CopyName'])


def delete(conn: ServerConnection, path: str) -> RetVal:
	'''Deletes a file'''
	if not path:
		return RetVal(MsgBadRequest).set_value('Status', 400)
	
	request = {
		'Action' : 'DELETE',
		'Data' : {
			'Path' : path
		}
	}
	conn.send_message(request)

	response = conn.read_response(server_response)
	if response.error():
		return response
	
	if response['Code'] != 200:
		return wrap_server_error(response)
	
	return RetVal()


def device(conn: ServerConnection, devid: str, devpair: EncryptionPair) -> RetVal:
	'''Completes the login process by submitting device ID and its session string.'''
	if not utils.validate_uuid(devid):
		return RetVal(MsgBadRequest, 'Invalid device ID').set_value('status', 400)

	conn.send_message({
		'Action' : "DEVICE",
		'Data' : { 
			'Device-ID' : devid,
			'Device-Key' : devpair.public.as_string()
		}
	})

	# Receive, decrypt, and return the server challenge
	response = conn.read_response(server_response)
	if response.error():
		return response
	
	if response['Code'] != 100:
		return wrap_server_error(response)

	if 'Challenge' not in response['Data']:
		return RetVal(ServerError, 'server did not return a device challenge')
	
	status = devpair.decrypt(response['Data']['Challenge'])
	if status.error():
		cancel(conn)
		return RetVal(DecryptionFailure, 'failed to decrypt device challenge')

	conn.send_message({
		'Action' : "DEVICE",
		'Data' : { 
			'Device-ID' : devid,
			'Device-Key' : devpair.public.as_string(),
			'Response' : status['data']
		}
	})

	response = conn.read_response(None)
	if response.error():
		return response
	
	if response['Code'] == 200:
		return RetVal()
	
	return wrap_server_error(response)


def devkey(conn: ServerConnection, devid: str, oldpair: EncryptionPair, newpair: EncryptionPair):
	'''Replaces the specified device's key stored on the server'''
	if not utils.validate_uuid(devid):
		return RetVal(MsgBadRequest, 'Invalid device ID').set_value('status', 400)

	conn.send_message({
		'Action' : "DEVKEY",
		'Data' : { 
			'Device-ID': devid,
			'Old-Key': oldpair.public.as_string(),
			'New-Key': newpair.public.as_string()
		}
	})

	# Receive, decrypt, and return the server challenge
	response = conn.read_response(server_response)
	if response.error():
		return response
	
	if response['Code'] != 100:
		return wrap_server_error(response)

	if 'Challenge' not in response['Data'] or 'New-Challenge' not in response['Data']:
		return RetVal(ServerError, 'server did not return both device challenges')
	
	status = oldpair.decrypt(response['Data']['Challenge'])
	if status.error():
		cancel(conn)
		return RetVal(DecryptionFailure, 'failed to decrypt device challenge for old key')

	request = {
		'Action' : "DEVKEY",
		'Data' : { 
			'Response' : status['data']
		}
	}

	status = newpair.decrypt(response['Data']['New-Challenge'])
	if status.error():
		cancel(conn)
		return RetVal(DecryptionFailure, 'failed to decrypt device challenge for new key')
	request['Data']['New-Response'] = status['data']
	conn.send_message(request)

	response = conn.read_response(None)
	if response.error():
		return response
	
	if response['Code'] == 200:
		return RetVal()
	
	return wrap_server_error(response)


def exists(conn: ServerConnection, path: str) -> RetVal:
	'''Checks to see if a path exists on the server side.'''
	if not path: 
		return RetVal().set_value('exists', False)
	
	status = conn.send_message({
		'Action' : 'EXISTS',
		'Data' : {
			'Path' : path
		}})
	if status.error():
		return status
	
	response = conn.read_response()
	if response.error():
		return response
	
	if response['Code'] == 200:
		return RetVal().set_value('exists', True)
	
	return RetVal().set_value('exists', True)


def getquotainfo(conn: ServerConnection, wid='') -> RetVal:
	'''Gets the disk usage and limit for the current workspace. If in an administrator session, 
	another workspace may be specified.'''
	if wid and not utils.validate_uuid(wid):
		return RetVal(MsgBadRequest).set_value('Status', 400)
	
	request = {
		'Action' : 'GETQUOTAINFO',
		'Data' : {}
	}
	if wid:
		request['Data']['Workspace-ID'] = wid
	conn.send_message(request)

	response = conn.read_response(server_response)
	if response.error():
		return response
	
	if response['Code'] != 200:
		return wrap_server_error(response)
	
	return RetVal().set_values({'usage': response['Data']['DiskUsage'], 
		'quota': response['Data']['QuotaSize']})


def getwid(conn: ServerConnection, uid: str, domain: str) -> RetVal:
	'''Looks up a wid based on the specified user ID and optional domain'''

	if re.findall(r'[\\\/\s"]', uid) or len(uid) >= 64:
		return RetVal(BadParameterValue, 'user id')
	
	if domain:
		m = re.match(r'([a-zA-Z0-9]+\.)+[a-zA-Z0-9]+', domain)
		if not m or len(domain) >= 64:
			return RetVal(BadParameterValue, 'bad domain value')
	
	request = {
		'Action' : 'GETWID',
		'Data' : {
			'User-ID': uid
		}
	}
	if domain:
		request['Data']['Domain'] = domain
	
	status = conn.send_message(request)
	if status.error():
		return status
	
	response = conn.read_response(server_response)
	if response.error():
		return response
	
	if response['Code'] != 200:
		return wrap_server_error(response)
	
	return RetVal().set_value('Workspace-ID', response['Data']['Workspace-ID'])


def iscurrent(conn: ServerConnection, index: int, wid='') -> RetVal:
	'''Finds out if an entry index is current. If wid is empty, the index is checked for the 
	organization.'''
	if wid and not utils.validate_uuid(wid):
		return RetVal(MsgBadRequest).set_value('status', 400)
	
	request = {
		'Action' : 'ISCURRENT',
		'Data' : {
			'Index' : str(index)
		}
	}
	if wid:
		request['Data']['Workspace-ID'] = wid
	conn.send_message(request)

	response = conn.read_response(server_response)
	if response.error():
		return response
	
	if response['Code'] != 200:
		return wrap_server_error(response)
	
	if 'Is-Current' not in response['Data']:
		return RetVal(ServerError, 'server did not return an answer')
	
	return RetVal().set_value('iscurrent', bool(response['Data']['Is-Current'] == 'YES'))


def listfiles(conn: ServerConnection, epochTime=0) -> RetVal:
	'''Obtains a list of entries in the current directory. If epochTime is specified, all files 
	created after the specified time are returned.'''

	request = {
		'Action' : 'LIST',
		'Data' : {}
	}
	if epochTime > 0:
		request['Data']['Time'] = epochTime
	conn.send_message(request)

	response = conn.read_response(server_response)
	if response.error():
		return response
	
	if response['Code'] != 200:
		return wrap_server_error(response)
	
	return RetVal().set_value('files', response['Data']['Files'])
	

def listdirs(conn: ServerConnection) -> RetVal:
	'''Obtains a list of subdirectories in the current directory.'''

	conn.send_message({'Action' : 'LISTDIRS','Data' : {}})
	response = conn.read_response(server_response)
	if response.error():
		return response
	
	if response['Code'] != 200:
		return wrap_server_error(response)
	
	return RetVal().set_value('directories', response['Data']['directories'])
	

def login(conn: ServerConnection, wid: str, serverkey: CryptoString) -> RetVal:
	'''Starts the login process by sending the requested workspace ID.'''
	if not utils.validate_uuid(wid):
		return RetVal(BadParameterValue)

	challenge = b85encode(secrets.token_bytes(32))
	ekey = PublicKey(serverkey)
	status = ekey.encrypt(challenge)
	if status.error():
		return status

	conn.send_message({
		'Action' : "LOGIN",
		'Data' : {
			'Workspace-ID' : wid,
			'Login-Type' : 'PLAIN',
			'Challenge' : status['data']
		}
	})

	response = conn.read_response(server_response)
	if response.error():
		return response
	
	if response['Code'] != 100:
		return wrap_server_error(response)
	
	if response['Data']['Response'] != challenge.decode():
		return RetVal(ServerError, 'server failed to decrypt challenge')
	
	return RetVal()


def logout(conn: ServerConnection) -> RetVal:
	'''Starts the login process by sending the requested workspace ID.'''
	status = conn.send_message({'Action':'LOGOUT', 'Data':{}})
	if status.error():
		return wrap_server_error(status)
	
	response = conn.read_response(server_response)
	if response['Code'] != 200:
		return wrap_server_error(response)
	
	return RetVal()


def mkdir(conn: ServerConnection, path: str) -> RetVal:
	'''Creates one or more directories. 'path' is a Mensago-style path and the command ensures that 
	the directory exists, creating any parent directories as needed. '''

	request = {
		'Action' : 'MKDIR',
		'Data' : {
			'Path': path
		}
	}
	conn.send_message(request)

	response = conn.read_response(server_response)
	if response.error():
		return response
	
	if response['Code'] != 200:
		return wrap_server_error(response)
	
	return RetVal()


def move(conn: ServerConnection, srcfile: str, destdir: str) -> RetVal:
	'''Moves the specified source file to the destination directory'''

	request = {
		'Action' : 'MOVE',
		'Data' : {
			'SourceFile': srcfile,
			'DestDir': destdir
		}
	}
	conn.send_message(request)

	response = conn.read_response(server_response)
	if response.error():
		return response
	
	if response['Code'] != 200:
		return wrap_server_error(response)
	
	return RetVal()


def passcode(conn: ServerConnection, wid: str, reset_code: str, pwhash: str) -> RetVal:
	'''Resets a workspace's password'''

	conn.send_message({
		'Action': 'PASSCODE',
		'Data': {
			'Workspace-ID': wid,
			'Reset-Code': reset_code,
			'Password-Hash': pwhash
		}
	})
	response = conn.read_response(server_response)
	if response['Code'] != 200:
		return wrap_server_error(response)
	
	return RetVal()


def password(conn: ServerConnection, wid: str, pwhash: str) -> RetVal:
	'''Continues the login process sending a password hash to the server.'''
	if not password or not utils.validate_uuid(wid):
		return RetVal(BadParameterValue)
	
	conn.send_message({
		'Action' : "PASSWORD",
		'Data' : { 'Password-Hash' : pwhash }
	})

	response = conn.read_response(server_response)
	if response.error():
		return response
	
	if response['Code'] != 100:
		return wrap_server_error(response)
	
	return RetVal()


def preregister(conn: ServerConnection, wid: str, uid: str, domain: str) -> RetVal:
	'''Provisions a preregistered account on the server.'''
	request = { 'Action':'PREREG', 'Data':{} }
	if wid:
		request['Data']['Workspace-ID'] = wid
	if uid:
		request['Data']['User-ID'] = uid
	if domain:
		request['Data']['Domain'] = domain

	status = conn.send_message(request)
	if status.error():
		return status
	
	response = conn.read_response(server_response)
	if response.error():
		return response
	
	if response['Code'] != 200:
		return wrap_server_error(response)

	out = RetVal()
	
	# Validate response fields
	fields = { 'Domain':'domain', 'Workspace-ID':'wid', 'Reg-Code':'regcode' }
	for k,v in fields.items():
		if k in response['Data']:
			if isinstance(response['Data'][k], str):
				out[v] = response['Data'][k]
			else:
				out.set_error(ServerError, 'server returned incorrect data')
		else:
			out.set_error(ServerError, 'server did not return all required fields')
	
	if 'User-ID' in response['Data']:
		if isinstance(response['Data']['User-ID'], str):
			out['uid'] = response['Data']['User-ID']
		else:
			out.set_error(ServerError, 'server returned incorrect data')
	
	return out


def regcode(conn: ServerConnection, regid: str, code: str, pwhash: str, devid: str, 
	devpair: EncryptionPair, domain: str) -> RetVal:
	'''Finishes registration of a workspace'''
	
	request = {
		'Action':'REGCODE',
		'Data':{
			'Reg-Code': code,
			'Password-Hash':pwhash,
			'Device-ID':devid,
			'Device-Key':devpair.public.as_string()
		}
	}

	if domain:
		request['Data']['Domain'] = domain

	if utils.validate_uuid(regid):
		request['Data']['Workspace-ID'] = regid
	else:
		request['Data']['User-ID'] = regid
	
	status = conn.send_message(request)
	if status.error():
		return status
	
	response = conn.read_response(server_response)
	if response.error():
		return response
	
	if response['Code'] != 201:
		return wrap_server_error(response)
	
	return RetVal()
	

def register(conn: ServerConnection, uid: str, pwhash: str, devicekey: CryptoString) -> RetVal:
	'''Creates an account on the server.'''
	
	if uid and len(re.findall(r'[\/" \s]',uid)) > 0:
		return RetVal(BadParameterValue, 'user id contains illegal characters')
		
	# This construct is a little strange, but it is to work around the minute possibility that
	# there is a WID collision, i.e. the WID generated by the client already exists on the server.
	# In such an event, it should try again. However, in the ridiculously small chance that the 
	# client keeps generating collisions, it should wait 3 seconds after 10 collisions to reduce 
	# server load.
	out = RetVal()
	devid = str(uuid.uuid4())
	wid = ''
	response = dict()
	tries = 1
	while not wid:
		if not tries % 10:
			time.sleep(3.0)
		
		# Technically, the active profile already has a WID, but it is not attached to a domain and
		# doesn't matter as a result. Rather than adding complexity, we just generate a new UUID
		# and always return the replacement value
		wid = str(uuid.uuid4())
		request = {
			'Action' : 'REGISTER',
			'Data' : {
				'Workspace-ID' : wid,
				'Password-Hash' : pwhash,
				'Device-ID' : devid,
				'Device-Key' : devicekey.as_string()
			}
		}
		if uid:
			request['Data']['User-ID'] = uid

		status = conn.send_message(request)
		if status.error():
			return status

		response = conn.read_response(server_response)
		if response.error():
			return response
		
		if response['Code'] in [ 101, 201]:		# Pending, Success
			out.set_values({
				'devid' : devid,
				'wid' : wid,
				'domain' : response['Data']['Domain'],
				'uid' : uid
			})
			break
		
		if response['Code'] == 408:	# WID or UID exists
			if 'Field' not in response['Data']:
				return RetVal(ServerError, 'server sent 408 without telling what existed')
			
			if response['Data']['Field'] not in ['User-ID', 'Workspace-ID']:
				return RetVal(ServerError, 'server sent bad 408 response').set_value( \
					'Field', response['Data']['Field'])

			if response['Data']['Field'] == 'User-ID':
				return RetVal(ResourceExists, 'user id')
			
			tries = tries + 1
			wid = ''
		else:
			# Something we didn't expect -- reg closed, payment req'd, etc.
			return wrap_server_error(response)
	
	return out


def reset_password(conn: ServerConnection, wid: str, reset_code='', expires='') -> RetVal:
	'''Resets a workspace's password'''

	conn.send_message({
		'Action': 'RESETPASSWORD',
		'Data': {
			'Workspace-ID': wid,
			'Reset-Code': reset_code,
			'Expires': expires
		}
	})
	response = conn.read_response(server_response)
	if response['Code'] != 200:
		return wrap_server_error(response)
	
	out = RetVal()
	out['resetcode'] = response['Data']['Reset-Code']
	out['expires'] = response['Data']['Expires']
	return out


def rmdir(conn: ServerConnection, path: str, recursive: bool) -> RetVal:
	'''Removes a directory. If recursive is True, all files and subdirectories are also deleted.'''

	request = {
		'Action' : 'RMDIR',
		'Data' : {
			'Path': path
		}
	}
	if recursive:
		request['Data']['Recursive'] = 'True'
	conn.send_message(request)

	response = conn.read_response(server_response)
	if response.error():
		return response
	
	if response['Code'] != 200:
		return wrap_server_error(response)
	
	return RetVal()


def setpassword(conn: ServerConnection, pwhash: str, newpwhash: str) -> RetVal:
	'''Changes the password for the workspace'''
	
	conn.send_message({
		'Action' : 'SETPASSWORD',
		'Data' : {
			'Password-Hash': pwhash,
			'NewPassword-Hash': newpwhash
		}
	})
	response = conn.read_response(server_response)
	if response['Code'] != 200:
		return wrap_server_error(response)
	
	return RetVal()


def setstatus(conn: ServerConnection, wid: str, status: str):
	'''Sets the activity status of the workspace specified. Requires admin privileges'''
	if status not in ['active', 'disabled', 'approved']:
		return RetVal(BadParameterValue, "status must be 'active','disabled', or 'approved'")
	
	if not utils.validate_uuid(wid):
		return RetVal(BadParameterValue, 'bad wid')

	conn.send_message({
		'Action' : 'SETSTATUS',
		'Data' : {
			'Workspace-ID': wid,
			'Status': status
		}
	})
	response = conn.read_response(server_response)
	if response['Code'] != 200:
		return wrap_server_error(response)

	return RetVal()


def unregister(conn: ServerConnection, pwhash: str, wid: str) -> RetVal:
	'''Deletes the online account at the specified server.'''

	if wid and not utils.validate_uuid(wid):
		return RetVal(BadParameterValue, 'bad workspace id')
	
	request = {
		'Action' : 'UNREGISTER',
		'Data' : {
			'Password-Hash' : pwhash
		}
	}
	if wid:
		request['Data']['Workspace-ID'] = wid
	
	status = conn.send_message(request)
	if status.error():
		return status
	
	response = conn.read_response(server_response)

	if response['Code'] == 202:
		return RetVal()

	# This particular command is very simple: make a request, because the server will return
	# one of three possible types of responses: success, pending (for private/moderated 
	# registration modes), or an error. In all of those cases there isn't anything else to do.
	return wrap_server_error(response)


# pylint: disable=fixme
# Disable the TODO listings embedded in the disabled code until it is properly rewritten

# TODO: Refactor/update to match current spec
# Upload
#	Requires:	valid socket
#				local path to file
#				size of file to upload
#				server path to requested destination
#	Optional:	callback function for progress display
#
#	Returns: [dict] error code
#				error string

# def upload(conn: ServerConnection, path, serverpath, progress):
# 	'''Upload a local file to the server.'''
# 	chunk_size = 128

# 	# Check to see if we're allowed to upload
# 	filesize = os.path.getsize(path)
# 	write_text(sock, "UPLOAD %s %s\r\n" % (filesize, serverpath))
# 	response = read_text(sock)
# 	if not response['string']:
# 		# TODO: Properly handle no server response
# 		raise "No response from server"
	
# 	if response['string'].strip().split()[0] != 'PROCEED':
# 		# TODO: Properly handle not being allowed
# 		print("Unable to upload file. Server response: %s" % response)
# 		return

# 	try:
# 		totalsent = 0
# 		handle = open(path,'rb')
# 		data = handle.read(chunk_size)
# 		while data:
# 			write_text(sock, "BINARY [%s/%s]\r\n" % (totalsent, filesize))
# 			sent_size = sock.send(data)
# 			totalsent = totalsent + sent_size

# 			if progress:
# 				progress(float(totalsent / filesize) * 100.0)

# 			if sent_size < chunk_size:
# 				break
			
# 			data = handle.read(chunk_size)
# 		data.close()
# 	except Exception as exc:
# 		print("Failure uploading %s: %s" % (path, exc))
