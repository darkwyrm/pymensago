'''This module contains the functions needed by any Anselus client for 
communications. Commands largely map 1-to-1 to the commands outlined in the 
spec.'''

import socket
import sys
import time
import uuid

import nacl.pwhash
import nacl.secret

from pyanselus.retval import RetVal, ExceptionThrown, ServerError, NetworkError, ResourceNotFound
import pyanselus.utils as utils

AnsBadRequest = '400-BadRequest'


# Number of seconds to wait for a client before timing out
CONN_TIMEOUT = 900.0

# Size (in bytes) of the read buffer size for recv()
READ_BUFFER_SIZE = 8192

def write_text(sock: socket.socket, text: str) -> RetVal:
	'''Sends a string over a socket'''

	if not sock:
		return RetVal(NetworkError, 'Invalid connection')
	
	try:
		sock.send(text.encode())
	except Exception as exc:
		sock.close()
		return RetVal(ExceptionThrown, exc.__str__())
	
	return RetVal()


def read_text(sock: socket.socket) -> RetVal:
	'''Reads a string from the supplied socket'''

	if not sock:
		return RetVal(NetworkError, 'Invalid connection')
	
	try:
		out = sock.recv(READ_BUFFER_SIZE)
	except Exception as exc:
		sock.close()
		return RetVal(ExceptionThrown, exc.__str__()).set_value('string','')
	
	try:
		out_string = out.decode()
	except Exception as exc:
		return RetVal(ExceptionThrown, exc.__str__()).set_value('string','')
	
	return RetVal().set_value('string', out_string)


def read_response(sock: socket.socket) -> RetVal:
	'''Reads a server response and returns a separated code and string'''
	
	response = read_text(sock)
	if response.error():
		return response
	
	try:
		status_code = int(response['string'][0:3])
	except:
		return RetVal(ServerError).set_value('response', response['string'])
	
	return RetVal().set_value('status', status_code).set_info(response['string'])

# Connect
#	Requires: host (hostname or IP)
#	Optional: port number
#	Returns: RetVal / socket, IP address, server version (if given), error string
#					
def connect(host: str, port=2001) -> dict:
	'''Creates a connection to the server.'''
	try:
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		# Set a short timeout in case the server doesn't respond immediately,
		# which is the expectation as soon as a client connects.
		sock.settimeout(10.0)
	except:
		return RetVal(NetworkError, "Couldn't create a socket")
	
	out_data = RetVal()
	out_data.set_value('socket', sock)
	
	try:
		host_ip = socket.gethostbyname(host)
	except socket.gaierror:
		sock.close()
		return RetVal(ResourceNotFound, "Couldn't locate host %s" % host)
	
	out_data.set_value('ip', host_ip)
	try:
		sock.connect((host_ip, port))
		
		hello = read_text(sock)
		if not hello.error():
			tempstr = hello['string'].strip().split()
			if len(tempstr) >= 3:
				out_data.set_value('version', tempstr[2])
			else:
				out_data.set_value('version', '')

	except Exception as exc:
		sock.close()
		return RetVal(NetworkError, "Couldn't connect to host %s: %s" % (host, exc))

	# Set a timeout of 30 minutes
	sock.settimeout(1800.0)
	return out_data
	
# Device
#	Requires: device ID, session string
#	Returns: RetVal / "code" : int, "error" : string
def device(sock: socket.socket, devid: str, session_str: str) -> RetVal:
	# TODO: refactor to match current spec
	'''Completes the login process by submitting device ID and its session string.'''
	if not utils.validate_uuid(devid):
		return RetVal(AnsBadRequest, 'Invalid device ID').set_value('status', 400)

	response = write_text(sock, 'DEVICE %s %s\r\n' % (devid, session_str))
	if response.error():
		return response
	
	return read_response(sock)


# Disconnect
#	Requires: socket
def disconnect(sock: socket.socket) -> RetVal:
	'''Disconnects by sending a QUIT command to the server'''
	return write_text(sock, 'QUIT\r\n'.encode())


# Exists
#	Requires: one or more names to describe the path desired
#	Returns: RetVal / "exists" : bool, "code" : int, "error" : string
def exists(sock: socket.socket, path: str) -> RetVal:
	'''Checks to see if a path exists on the server side.'''
	status = write_text(sock, "EXISTS %s\r\n" % path)
	if status.error():
		return status
	
	status = read_response(sock)
	if status['status'] == 200:
		return status.set_value('exists', True)
	
	return status.set_value('exists', False)


# Login
#	Requires: numeric workspace ID
#	Returns: RetVal / "code" : int, "error" : string
def login(sock: socket.socket, wid: str) -> RetVal:
	'''Starts the login process by sending the requested workspace ID.'''
	if not utils.validate_uuid(wid):
		return {
			'error' : 'BAD REQUEST',
			'status' : 400
		}

	response = write_text(sock, 'LOGIN %s\r\n' % wid)
	if not response['error']:
		return response
	
	return read_response(sock)


# Password
#	Requires: workspace ID, password string
#	Returns: RetVal / "code" : int, "error" : string
def password(sock: socket.socket, wid: str, pword: str) -> RetVal:
	'''Continues the login process by hashing a password and sending it to the server.'''
	if not password or not utils.validate_uuid(wid):
		return RetVal(AnsBadRequest).set_value('status', 400)
	
	# The server will salt the hash we submit, but we'll salt anyway with the WID for extra safety.
	pwhash = nacl.pwhash.argon2id.kdf(nacl.secret.SecretBox.KEY_SIZE,
							bytes(pword, 'utf8'), wid,
							opslimit=nacl.pwhash.argon2id.OPSLIMIT_INTERACTIVE,
							memlimit=nacl.pwhash.argon2id.MEMLIMIT_INTERACTIVE)	
	response = write_text(sock, 'PASSWORD %s\r\n' % pwhash)
	if response.error():
		return response
	
	return read_response(sock)


# Preregister
#	Requires: none
#	Optional: user ID
#	Returns: RetVal / wid : string, regcode : string, 
def preregister(sock: socket.socket, uid: str) -> RetVal:
	'''Provisions a preregistered account on the server.'''
	if uid is None:
		uid = ''
	
	response = write_text(sock, 'PREREG %s\r\n' % uid)
	if response.error():
		return response
	
	response = read_response(sock)
	if response.error() or response['status'] != 200:
		return response

	# The response should take the form <code> <wid> <regcode> [<uid>]
	try:
		tokens = response.info().strip().split(' ')
	except:
		return RetVal(ServerError, 'BUG: bad response %s' % response.info())

	if len(tokens) not in [4, 5]:
		return RetVal(ServerError, 'BUG: bad response %s' % response.info())
	
	out = RetVal()
	out.set_values({ 'status':response['status'], 'wid':tokens[2], 'regcode':tokens[3], 'uid':'' })
	if len(tokens) == 5:
		out.set_value('uid', tokens[4])
	
	return out


# Register
#	Requires: valid socket, password hash
#	Returns: RetVal / "wid": string, "devid" : string, "session" : string, "code" : int,
# 			"error" : string
def register(sock: socket.socket, pwhash: str, keytype: str, devkey: str) -> RetVal:
	'''Creates an account on the server.'''
	
	# This construct is a little strange, but it is to work around the minute possibility that
	# there is a WID collision, i.e. the WID generated by the client already exists on the server.
	# In such an event, it should try again. However, in the ridiculously small chance that the 
	# client keeps generating collisions, it should wait 3 seconds after 10 collisions to reduce 
	# server load.
	devid = ''
	wid = ''
	response = dict()
	tries = 1
	while not devid:
		if not tries % 10:
			time.sleep(3.0)
		
		# Technically, the active profile already has a WID, but it is not attached to a domain and
		# doesn't matter as a result. Rather than adding complexity, we just generate a new UUID
		# and always return the replacement value
		wid = str(uuid.uuid4())
		response = write_text(sock, 'REGISTER %s %s %s %s\r\n' % (wid, pwhash, keytype, devkey))
		if response.error():
			return response
		
		response = read_response(sock)
		if response.error():
			return response
		
		if response['status'] in [ 304, 406 ]:	# Registration closed, Payment required
			break
		
		if response['status'] in [ 101, 201]:		# Pending, Success
			tokens = response.info().split()
			if len(tokens) != 3 or not utils.validate_uuid(tokens[2]):
				return { 'status' : 300, 'error' : 'INTERNAL SERVER ERROR' }
			response.set_value('devid', tokens[2])
			break
		
		if response['status'] == 408:	# WID exists
			tries = tries + 1
		else:
			# Something we didn't expect
			return RetVal(ServerError, "Unexpected server response")
	
	return response.set_value('wid', wid)


def unregister(sock: socket.socket, pwhash: str) -> RetVal:
	'''
	Deletes the online account at the specified server.
	Returns:
	error : string
	'''

	response = write_text(sock, 'UNREGISTER %s\r\n' % pwhash)
	if response.error():
		return response
	
	response = read_response(sock)

	# This particular command is very simple: make a request, because the server will return
	# one of three possible types of responses: success, pending (for private/moderated 
	# registration modes), or an error. In all of those cases there isn't anything else to do.
	return response


def progress_stdout(value: float):
	'''callback for upload() which just prints what it's given'''
	sys.stdout.write("Progress: %s\r" % value)


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

# def upload(sock: socket.socket, path, serverpath, progress):
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
