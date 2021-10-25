'''This module contains the functions needed by any Mensago client for communications. Commands 
largely map 1-to-1 to the commands outlined in the spec.'''

import io
import json
import os
import socket
from typing import Type

import jsonschema
from retval import RetVal, ErrBadValue, ErrBadType, ErrFilesystemError, ErrNetworkError, \
	ErrOutOfRange, ErrServerError

from pycryptostring import CryptoString
from pymensago.errorcodes import *	# pylint: disable=wildcard-import
from pymensago.hash import hashfile
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
READ_BUFFER_SIZE = 16384

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
			return RetVal().wrap_exception(e)
		
		try:
			sock.connect((address, port))
			
			# absorb the hello string
			_ = sock.recv(READ_BUFFER_SIZE)

		except Exception as e:
			sock.close()
			return RetVal().wrap_exception(e)

		# Set a timeout of 30 minutes
		sock.settimeout(1800.0)
		
		self.socket = sock
		return RetVal()

	def is_connected(self) -> bool:
		'''Returns whether or not the instance is connected to a server'''
		return not bool(self.socket is None)

	def disconnect(self) -> RetVal:
		'''Disconnects by sending a QUIT command to the server'''
		status = self.send_message({'Action':'QUIT','Data':{}})
		if not status.error():
			self.socket = None
		return status

	def send_message(self, command : dict) -> RetVal:
		'''Sends a message to the server with command sent as JSON data'''
		cmdstr = json.dumps(command) + '\r\n'
		
		if not self.socket:
			return RetVal(ErrNetworkError, 'not connected')
		
		try:
			self.socket.send(cmdstr.encode())
		except Exception as e:
			self.socket.close()
			return RetVal().wrap_exception(e)
		
		return RetVal()

	def read_response(self, schema: dict=None) -> RetVal:
		'''Reads a server response and returns a separated code and string'''
		
		if not self.socket:
			return None
		
		if schema is None:
			schema = server_response

		# We don't actually handle the possible exceptions because we *want* to have them crash --
		# the test will fail and give us the cause of the exception. If we have a successful test, 
		# exceptions weren't thrown
		try:
			rawdata = self.socket.recv(READ_BUFFER_SIZE)
			rawstring = rawdata.decode()
			rawresponse = json.loads(rawstring)
			if schema:
				jsonschema.validate(rawresponse, schema)
		except Exception as e:
			return RetVal().wrap_exception(e)

		response = RetVal().set_values({
			'Code': rawresponse['Code'],
			'Status': rawresponse['Status'],
			'Info': rawresponse['Info'],
			'Data': rawresponse['Data']
		})
		return response
	
	def read(self) -> str:
		'''Reads a string from the network connection'''
		
		if not self.socket:
			return None
		
		rawdata = self.socket.recv(READ_BUFFER_SIZE)
		return rawdata.decode()

	def write(self, text: str) -> RetVal:
		'''Sends a string over a socket'''

		if not self.socket:
			return RetVal(ErrNetworkError, 'Invalid connection')
		
		try:
			self.socket.send(text.encode())
		except Exception as e:
			self.socket.close()
			return RetVal().wrap_exception(e)
		
		return RetVal()


def wrap_server_error(response) -> RetVal:
	'''Wraps a server response into a RetVal object'''
	out = RetVal(__errcode_map.get(response['Code'],ErrServerError), response.info())
	for key in ['Code', 'Status', 'Info', 'Data']:
		if key in response:
			out[key] = response[key]
	if not response.info() and 'Status' in response:
			out.set_info(response['Status'])
	return out


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
	status = conn.send_message(request)
	if status.error():
		return status

	response = conn.read_response(server_response)
	if response.error():
		return response
	
	if response['Code'] != 200:
		return wrap_server_error(response)
	
	return RetVal().set_value('name', response['Data']['NewName'])


def delete(conn: ServerConnection, path_list: list) -> RetVal:
	'''Deletes one or more server-side files'''

	if not isinstance(path_list, list):
		raise TypeError('path_list must be a list')
	
	if len(path_list) < 1:
		return RetVal()
	
	queue = list(path_list)

	while len(queue) > 0:
		request = { 'Action' : 'DELETE', 'Data' : {} }

		# The baseline size for a DELETE message with 3 characters for the path count. We can make this
		# assumption because each path will be a minimum of 83 bytes, equating to a rough maximum
		# of 196 paths that can fit within the 16k max message size.
		reqsize = 47
		index = 0

		# We don't go all the way to 16384, the official max command size, to allow for a bit of
		# a 'fudge factor.'
		while len(queue) > 0 and reqsize < 16000:
			# entry: "Path":"",
			entrysize = 10 + len(str(index)) + len(queue[0])

			if reqsize + entrysize > 16384:
				# We increment the index just to make sure that PathCount is correct.
				index = index + 1
				break

			item = queue.pop(0)
			request['Data'][f'Path{index}'] = item
			reqsize = reqsize + entrysize
			index = index + 1
			

		request ['Data']['PathCount'] = str(index)
		status = conn.send_message(request)
		if status.error():
			return status

		response = conn.read_response(server_response)
		if response.error():
			return response
		
		if response['Code'] != 200:
			return wrap_server_error(response)
	
	return RetVal()


def download(conn: ServerConnection, server_path: str, local_path: str, offset=-1) -> RetVal:
	'''Downloads a file from the server. If an offset is given, resuming an interrupted download 
	is possible.'''

	try:
		handle = open(local_path, "wb")
	except Exception as e:
		return RetVal().wrap_exception(e)
	
	request = {
		'Action' : 'DOWNLOAD',
		'Data' : {
			'Path' : server_path
		}
	}
	if offset > 0:
		request['Data']['Offset'] = str(offset)
	
	status = conn.send_message(request)
	if status.error():
		handle.close()
		return status
	
	response = conn.read_response(server_response)
	if response.error():
		handle.close()
		return response

	if response['Code'] != 100:
		handle.close()
		return wrap_server_error(response)

	if 'Size' not in response['Data']:
		handle.close()
		return RetVal(ErrServerError, "Server gave invalid response: missing Size field")
	
	# This might seem silly at first, but adding the Size field is the client's way of confirming
	# readiness to download the file	
	try:
		sizeToRead = int(response['Data']['Size'])
	except:
		handle.close()
		return RetVal(ErrServerError, "Server gave invalid response: bad Size field")

	if offset > 0:
		handle.seek(offset)
		sizeToRead = sizeToRead - offset	

	request['Data']['Size'] = response['Data']['Size']

	status = conn.send_message(request)
	if status.error():
		handle.close()
		return status

	rawdata = conn.read()
	sizeRead = len(rawdata)
	while rawdata and sizeToRead > 0:
		handle.write(rawdata.encode())
		sizeToRead = sizeToRead - sizeRead
		if sizeToRead == 0:
			break
		rawdata = conn.read()
		sizeRead = len(rawdata)

	handle.close()
	return RetVal().set_value('Size', int(request['Data']['Size']))


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


def getquotainfo(conn: ServerConnection, wid: utils.UUID) -> RetVal:
	'''Gets the disk usage and limit for the current workspace. If in an administrator session, 
	another workspace may be specified.'''
	if not wid.is_empty() and not wid.is_valid():
		return RetVal(MsgBadRequest).set_value('Status', 400)
	
	request = {
		'Action' : 'GETQUOTAINFO',
		'Data' : {}
	}
	if wid:
		request['Data']['Workspace-ID'] = wid.as_string()
	status = conn.send_message(request)
	if status.error():
		return status

	response = conn.read_response(server_response)
	if response.error():
		return response
	
	if response['Code'] != 200:
		return wrap_server_error(response)
	
	return RetVal().set_values({'usage': response['Data']['DiskUsage'], 
		'quota': response['Data']['QuotaSize']})


def listfiles(conn: ServerConnection, path='', epochTime=0) -> RetVal:
	'''Obtains a list of entries in the current directory. If epochTime is specified, all files 
	created after the specified time are returned.'''

	request = {
		'Action' : 'LIST',
		'Data' : {}
	}
	if path:
		request['Data']['Path'] = path
	if epochTime > 0:
		request['Data']['Time'] = str(epochTime)
	status = conn.send_message(request)
	if status.error():
		return status

	response = conn.read_response(server_response)
	if response.error():
		return response
	
	if response['Code'] != 200:
		return wrap_server_error(response)
	
	return RetVal().set_value('files', response['Data']['Files'])
	

def listdirs(conn: ServerConnection, path='') -> RetVal:
	'''Obtains a list of subdirectories in the current directory.'''

	request = {
		'Action' : 'LISTDIRS',
		'Data' : {}
	}
	if path:
		request['Data']['Path'] = path
	status = conn.send_message(request)
	if status.error():
		return status

	response = conn.read_response(server_response)
	if response.error():
		return response
	
	if response['Code'] != 200:
		return wrap_server_error(response)
	
	return RetVal().set_value('directories', response['Data']['Directories'])
	

def mkdir(conn: ServerConnection, path: str, encpath: CryptoString) -> RetVal:
	'''Creates one or more directories. The command ensures that the directory
	exists, creating any parent directories as needed.
	
	Parameters:
	  * path: (str) the server-side path
	  * encpath: (CryptoString) the encrypted client-side path
	
	Returns:
	  * None
	
	Notes:
	The encpath parameter contains the user-facing path, whereas path contains
	the corresponding server-side path which contains no identifying information.
	'''

	if not isinstance(encpath, CryptoString):
		return RetVal(ErrBadType)
	
	if not path or not encpath.is_valid():
		return RetVal(ErrBadValue)
	
	request = {
		'Action' : 'MKDIR',
		'Data' : {
			'Path': path,
			'ClientPath': encpath.as_string()
		}
	}
	status = conn.send_message(request)
	if status.error():
		return status

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
	status = conn.send_message(request)
	if status.error():
		return status

	response = conn.read_response(server_response)
	if response.error():
		return response
	
	if response['Code'] != 200:
		return wrap_server_error(response)
	
	return RetVal()


def replace(conn: ServerConnection, oldfile: str, localpath: str, newpath: str, tempname='',
	offset=-1, hashstr=''):
	'''Uploads a local file to the server to replace an existing one.
	
	Parameters:
		oldfile: (str) Mensago path of the file to replace
		localpath: (str) local path of the new file to upload
		newpath: (str) Mensago path of the folder for the replacement file
		tempname: (str) Resume only. Name of the temporary file returned by the server
			in the initial upload attempt.
		offset: (int) Resume only. Location in the file to continue uploading at.
		hashstr: CryptoString-formatted string containing the hash of the file
	
	Returns:
		sent: (int) Only when interrupted. Number of bytes sent to the server.
		tempname: (str) Only when interrupted. Name of the server-side temporary file
			needed when resuming
		filename: (str) Only on success. Mensago path of the replacement file
	'''

	try:	
		filesize = os.path.getsize(localpath)
	except OSError as e:
		return RetVal(ErrBadValue, str(e))
	except Exception as e:
		return RetVal().wrap_exception(e)
	
	if offset >= 0 and offset > filesize:
		return RetVal(ErrBadValue, 'bad offset')
	
	if (offset >= 0 and not tempname) or (offset < 0 and tempname):
		return RetVal(ErrBadValue, 'both tempname and offset must both be set')
	
	if not newpath:
		return RetVal(ErrBadValue, 'empty server path')
	
	if not hashstr:
		status = hashfile(localpath)
		if status.error():
			return status
		hashstr = status['hash']
	
	request = {
		'Action': 'REPLACE',
		'Data': {
			'OldPath': oldfile,
			'NewPath': newpath,
			'Size': str(filesize),
			'Hash': hashstr,
			'Path': newpath
		}
	}

	if offset >= 0:
		request['Data']['Offset'] = str(offset)
	
	if tempname:
		request['Data']['TempName'] = tempname
	
	status = conn.send_message(request)
	if status.error():
		return status

	response = conn.read_response(server_response)
	if response['Code'] != 100:
		return wrap_server_error(response)
	
	totalsent = 0
	try:
		handle = open(localpath, 'rb')
	except Exception as e:
		return RetVal(ErrFilesystemError, e)

	if offset > 0:
		handle.seek(offset)

	try:
		filedata = handle.read(io.DEFAULT_BUFFER_SIZE)
	except Exception as e:
		handle.close()
		return RetVal(ErrFilesystemError, e).set_values({
			'sent': totalsent,
			'tempname': response['TempName']
		})
	while filedata:
		try:
			sent_size = conn.socket.send(filedata)
		except Exception as e:
			handle.close()
			return RetVal(ErrNetworkError, e).set_values({
				'sent': totalsent,
				'tempname': response['TempName']
			})
		totalsent = totalsent + sent_size

		try:
			filedata = handle.read(io.DEFAULT_BUFFER_SIZE)
		except Exception as e:
			handle.close()
			return RetVal(ErrFilesystemError, e).set_values({
				'sent': totalsent,
				'tempname': response['TempName']
			})
	handle.close()

	response = conn.read_response(server_response)
	if response['Code'] != 200:
		return wrap_server_error(response)

	return RetVal().set_value("filename", response['Data']['FileName'])


def rmdir(conn: ServerConnection, path: str) -> RetVal:
	'''Removes a directory. If recursive is True, all files and subdirectories are also deleted.'''

	request = {
		'Action' : 'RMDIR',
		'Data' : {
			'Path': path
		}
	}
	status = conn.send_message(request)
	if status.error():
		return status

	response = conn.read_response(server_response)
	if response.error():
		return response
	
	if response['Code'] != 200:
		return wrap_server_error(response)
	
	return RetVal()


def select(conn: ServerConnection, path: str) -> RetVal:
	'''Changes the working directory on the server'''

	request = {
		'Action' : 'SELECT',
		'Data' : {
			'Path': path
		}
	}
	status = conn.send_message(request)
	if status.error():
		return status

	response = conn.read_response(server_response)
	if response.error():
		return response
	
	if response['Code'] != 200:
		return wrap_server_error(response)
	
	return RetVal()


def sendfast(conn: ServerConnection, msgdata: str, domain: utils.Domain) -> RetVal:
	'''Works like send(), but only works for messages able to fit within the 16KiB command limit. 
	Note that this 16KiB includes all JSON formatting, so the actual message payload will need 
	to be smaller than this.'''
	
	# 49 is the number of bytes used in this message when minified without including the two
	# variables in the message: the domain size and the size of the message data
	totalsize = len(msgdata) + len(domain.as_string()) + 49
	if totalsize > 16384:
		return ErrOutOfRange

	status = conn.send_message({
		'Action': 'SENDFAST',
		'Data': {
			'Domain': domain.as_string(),
			'Message': msgdata
		}
	})
	if status.error():
		return status

	response = conn.read_response(server_response)
	if response['Code'] != 200:
		return wrap_server_error(response)
	
	return RetVal()


def send(conn: ServerConnection, localpath: str, domain: utils.Domain, tempname='', offset=-1,
	hashstr=''):
	'''Uploads a message to the server for delivery. tempname and offset are passed to the function if 
	resuming a previous upload. hashstr expects CryptoString-formatted data and can be passed 
	to the function to save recalculating the hash of the file data.'''

	try:	
		filesize = os.path.getsize(localpath)
	except OSError as e:
		return RetVal(ErrBadValue, str(e))
	except Exception as e:
		return RetVal().wrap_exception(e)
	
	if offset >= 0 and offset > filesize:
		return RetVal(ErrBadValue, 'bad offset')
	
	if (offset >= 0 and not tempname) or (offset < 0 and tempname):
		return RetVal(ErrBadValue, 'both tempname and offset must both be set')
	
	if not hashstr:
		status = hashfile(localpath)
		if status.error():
			return status
		hashstr = status['hash']
	
	status = conn.send_message({
		'Action': 'SEND',
		'Data': {
			'Size': str(filesize),
			'Hash': hashstr,
			'Domain': domain.as_string()
		}
	})
	if status.error():
		return status

	response = conn.read_response(server_response)
	if response['Code'] != 100:
		return wrap_server_error(response)
	
	totalsent = 0
	try:
		handle = open(localpath, 'rb')
	except Exception as e:
		return RetVal(ErrFilesystemError, e)

	if offset > 0:
		handle.seek(offset)

	try:
		filedata = handle.read(io.DEFAULT_BUFFER_SIZE)
	except Exception as e:
		handle.close()
		return RetVal(ErrFilesystemError, e).set_values({
			'sent': totalsent,
			'tempname': response['TempName']
		})
	while filedata:
		try:
			sent_size = conn.socket.send(filedata)
		except Exception as e:
			handle.close()
			return RetVal(ErrNetworkError, e).set_values({
				'sent': totalsent,
				'tempname': response['TempName']
			})
		totalsent = totalsent + sent_size

		try:
			filedata = handle.read(io.DEFAULT_BUFFER_SIZE)
		except Exception as e:
			handle.close()
			return RetVal(ErrFilesystemError, e).set_values({
				'sent': totalsent,
				'tempname': response['TempName']
			})
	handle.close()

	response = conn.read_response(server_response)
	if response['Code'] != 200:
		return wrap_server_error(response)

	return RetVal().set_value("FileName", response['Data']['FileName'])


def setquota(conn: ServerConnection, wid: str, size: int) -> RetVal:
	'''Admin-only: set size of a workspace's quota'''

	request = {
		'Action' : 'SETQUOTA',
		'Data' : {
			'Workspaces': wid,
			'Size': str(size)
		}
	}
	status = conn.send_message(request)
	if status.error():
		return status

	response = conn.read_response(server_response)
	if response.error():
		return response
	
	if response['Code'] != 200:
		return wrap_server_error(response)
	
	return RetVal()


def upload(conn: ServerConnection, localpath: str, serverpath: str, tempname='',
	offset=-1, hashstr=''):
	'''Uploads a local file to the server. tempname and offset are passed to the function if 
	resuming a previous upload. hashstr expects CryptoString-formatting data and can be passed 
	to the function to save recalculating the hash of the file data.'''

	try:	
		filesize = os.path.getsize(localpath)
	except OSError as e:
		return RetVal(ErrBadValue, str(e))
	except Exception as e:
		return RetVal().wrap_exception(e)
	
	if offset >= 0 and offset > filesize:
		return RetVal(ErrBadValue, 'bad offset')
	
	if (offset >= 0 and not tempname) or (offset < 0 and tempname):
		return RetVal(ErrBadValue, 'both tempname and offset must both be set')
	
	if not serverpath:
		return RetVal(ErrBadValue, 'empty server path')
	
	if not hashstr:
		status = hashfile(localpath)
		if status.error():
			return status
		hashstr = status['hash']
	
	status = conn.send_message({
		'Action': 'UPLOAD',
		'Data': {
			'Size': str(filesize),
			'Hash': hashstr,
			'Path': serverpath
		}
	})
	if status.error():
		return status

	response = conn.read_response(server_response)
	if response['Code'] != 100:
		return wrap_server_error(response)
	
	totalsent = 0
	try:
		handle = open(localpath, 'rb')
	except Exception as e:
		return RetVal(ErrFilesystemError, e)

	if offset > 0:
		handle.seek(offset)

	try:
		filedata = handle.read(io.DEFAULT_BUFFER_SIZE)
	except Exception as e:
		handle.close()
		return RetVal(ErrFilesystemError, e).set_values({
			'sent': totalsent,
			'tempname': response['TempName']
		})
	while filedata:
		try:
			sent_size = conn.socket.send(filedata)
		except Exception as e:
			handle.close()
			return RetVal(ErrNetworkError, e).set_values({
				'sent': totalsent,
				'tempname': response['TempName']
			})
		totalsent = totalsent + sent_size

		try:
			filedata = handle.read(io.DEFAULT_BUFFER_SIZE)
		except Exception as e:
			handle.close()
			return RetVal(ErrFilesystemError, e).set_values({
				'sent': totalsent,
				'tempname': response['TempName']
			})
	handle.close()

	response = conn.read_response(server_response)
	if response['Code'] != 200:
		return wrap_server_error(response)

	return RetVal().set_value("FileName", response['Data']['FileName'])
