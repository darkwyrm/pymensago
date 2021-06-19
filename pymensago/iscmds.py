from base64 import b85encode
import re
import secrets
import time

from pycryptostring import CryptoString
from retval import RetVal, ErrBadValue, ErrExists, ErrServerError, ErrUnimplemented

from pymensago.encryption import DecryptionFailure, EncryptionPair, PublicKey, SigningPair
from pymensago.errorcodes import *	# pylint: disable=unused-wildcard-import,wildcard-import
from pymensago.keycard import EntryBase, Keycard, OrgEntry
from pymensago.serverconn import ServerConnection, server_response, wrap_server_error
import pymensago.utils as utils

def addentry(conn: ServerConnection, entry: EntryBase, ovkey: CryptoString,
	spair: SigningPair) -> RetVal:
	'''Handles the process to upload an entry to the server.'''

	status = conn.send_message({
		'Action' : "ADDENTRY",
		'Data' : { 'Base-Entry' : entry.make_bytestring(0).decode() }
	})
	if status.error():
		return status

	response = conn.read_response(server_response)
	if response['Code'] != 100:
		return wrap_server_error(response)

	for field in ['Organization-Signature', 'Hash', 'Previous-Hash']	:
		if field not in response['Data']:
			return RetVal(ErrServerError, f"Server did not return required field {field}")

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

	status = conn.send_message({
		'Action' : "ADDENTRY",
		'Data' : { 'User-Signature' : entry.signatures['User'] }
	})
	if status.error():
		return status
	
	response = conn.read_response(server_response)
	if response['Code'] != 200:
		return wrap_server_error(response)

	return RetVal()


def cancel(conn: ServerConnection):
	'''Returns the session to a state where it is ready for the next command'''
	status = conn.send_message({ 'Action' : "CANCEL", 'Data' : {}})
	if status.error():
		return status
	
	response = conn.read_response(None)
	if response.error():
		return response
	
	if response['Code'] == 200:
		return RetVal()
	return wrap_server_error(response)


def device(conn: ServerConnection, devid: utils.UUID, devpair: EncryptionPair) -> RetVal:
	'''Completes the login process by submitting device ID and its session string.'''
	if not devid.is_valid():
		return RetVal(MsgBadRequest, 'Invalid device ID').set_value('status', 400)

	status = conn.send_message({
		'Action' : "DEVICE",
		'Data' : { 
			'Device-ID' : devid.as_string(),
			'Device-Key' : devpair.public.as_string()
		}
	})
	if status.error():
		return status

	# Receive, decrypt, and return the server challenge
	response = conn.read_response(server_response)
	if response.error():
		return response
	
	if response['Code'] != 100:
		return wrap_server_error(response)

	if 'Challenge' not in response['Data']:
		return RetVal(ErrServerError, 'server did not return a device challenge')
	
	status = devpair.decrypt(response['Data']['Challenge'])
	if status.error():
		cancel(conn)
		return RetVal(DecryptionFailure, 'failed to decrypt device challenge')

	status = conn.send_message({
		'Action' : "DEVICE",
		'Data' : { 
			'Device-ID' : devid.as_string(),
			'Device-Key' : devpair.public.as_string(),
			'Response' : status['data']
		}
	})
	if status.error():
		return status

	response = conn.read_response(None)
	if response.error():
		return response
	
	if response['Code'] == 200:
		return RetVal()
	
	return wrap_server_error(response)


def devkey(conn: ServerConnection, devid: utils.UUID, oldpair: EncryptionPair, newpair: EncryptionPair):
	'''Replaces the specified device's key stored on the server'''
	if not devid.is_valid():
		return RetVal(MsgBadRequest, 'Invalid device ID').set_value('status', 400)

	status = conn.send_message({
		'Action' : "DEVKEY",
		'Data' : { 
			'Device-ID': devid.as_string(),
			'Old-Key': oldpair.public.as_string(),
			'New-Key': newpair.public.as_string()
		}
	})
	if status.error():
		return status

	# Receive, decrypt, and return the server challenge
	response = conn.read_response(server_response)
	if response.error():
		return response
	
	if response['Code'] != 100:
		return wrap_server_error(response)

	if 'Challenge' not in response['Data'] or 'New-Challenge' not in response['Data']:
		return RetVal(ErrServerError, 'server did not return both device challenges')
	
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
	status = conn.send_message(request)
	if status.error():
		return status

	response = conn.read_response(None)
	if response.error():
		return response
	
	if response['Code'] == 200:
		return RetVal()
	
	return wrap_server_error(response)


def getwid(conn: ServerConnection, uid: utils.UserID, domain: utils.Domain) -> RetVal:
	'''Looks up a wid based on the specified user ID and optional domain'''

	if not uid.is_valid():
		return RetVal(ErrBadValue, 'bad user id')
	
	if domain.value and not domain.is_valid():
		return RetVal(ErrBadValue, 'bad domain')
	
	request = {
		'Action' : 'GETWID',
		'Data' : {
			'User-ID': uid.as_string()
		}
	}
	if domain.value:
		request['Data']['Domain'] = domain.as_string()
	
	status = conn.send_message(request)
	if status.error():
		return status
	
	response = conn.read_response(server_response)
	if response.error():
		return response
	
	if response['Code'] != 200:
		return wrap_server_error(response)
	
	return RetVal().set_value('Workspace-ID', utils.UUID(response['Data']['Workspace-ID']))


def iscurrent(conn: ServerConnection, index: int, wid: utils.UUID) -> RetVal:
	'''Finds out if an entry index is current. If wid is empty, the index is checked for the 
	organization.'''
	if not wid.is_empty() and not wid.is_valid():
		return RetVal(MsgBadRequest).set_value('status', 400)
	
	request = {
		'Action' : 'ISCURRENT',
		'Data' : {
			'Index' : str(index)
		}
	}
	if not wid.is_empty():
		request['Data']['Workspace-ID'] = wid.as_string()
	status = conn.send_message(request)
	if status.error():
		return status

	response = conn.read_response(server_response)
	if response.error():
		return response
	
	if response['Code'] != 200:
		return wrap_server_error(response)
	
	if 'Is-Current' not in response['Data']:
		return RetVal(ErrServerError, 'server did not return an answer')
	
	return RetVal().set_value('iscurrent', bool(response['Data']['Is-Current'] == 'YES'))


def login(conn: ServerConnection, wid: utils.UUID, serverkey: CryptoString) -> RetVal:
	'''Starts the login process by sending the requested workspace ID.'''
	if not wid.is_valid():
		return RetVal(ErrBadValue)

	challenge = b85encode(secrets.token_bytes(32))
	ekey = PublicKey(serverkey)
	status = ekey.encrypt(challenge)
	if status.error():
		return status

	status = conn.send_message({
		'Action' : "LOGIN",
		'Data' : {
			'Workspace-ID' : wid.as_string(),
			'Login-Type' : 'PLAIN',
			'Challenge' : status['data']
		}
	})
	if status.error():
		return status

	response = conn.read_response(server_response)
	if response.error():
		return response
	
	if response['Code'] != 100:
		return wrap_server_error(response)
	
	if response['Data']['Response'] != challenge.decode():
		return RetVal(ErrServerError, 'server failed to decrypt challenge')
	
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


def orgcard(conn: ServerConnection, start_index: int, end_index: int) -> RetVal:
	'''Obtains an organization's keycard'''

	status = conn.send_message({
		'Action': 'ORGCARD',
		'Data': {
			'Start-Index': str(start_index),
			'End-Index': str(end_index)
		}
	})
	if status.error():
		return status

	response = conn.read_response(server_response)
	data_size = int(response['Data']['Total-Size'])
	status = conn.send_message({'Action':'TRANSFER'})
	if status.error():
		return status

	chunks = list()
	tempstr = conn.read()
	data_read = len(tempstr)
	chunks.append(tempstr)
	while data_read < data_size:
		tempstr = conn.read()
		data_read = data_read + len(tempstr)
		chunks.append(tempstr)

	if data_read != data_size:
		return RetVal(ErrServerError, 'Mismatch in size of data returned from server')
	
	# Now that the data has been downloaded, we put it together and split it properly. 
	entry_strings = ''.join(chunks).split('----- END ORG ENTRY -----\r\n')
	if entry_strings[-1] == '':
		entry_strings.pop()
	
	card = Keycard()
	for entrystr in entry_strings:
		if entrystr.startswith('----- BEGIN ORG ENTRY -----\r\n'):
			entry = OrgEntry()
			status = entry.set(entrystr[29:].encode())
			if status.error():
				return status
			card.entries.append(entry)
	
	return RetVal().set_value('card', card)


def passcode(conn: ServerConnection, wid: utils.UUID, reset_code: str, pwhash: str) -> RetVal:
	'''Resets a workspace's password'''

	status = conn.send_message({
		'Action': 'PASSCODE',
		'Data': {
			'Workspace-ID': wid.as_string(),
			'Reset-Code': reset_code,
			'Password-Hash': pwhash
		}
	})
	if status.error():
		return status
	
	response = conn.read_response(server_response)
	if response['Code'] != 200:
		return wrap_server_error(response)
	
	return RetVal()


def password(conn: ServerConnection, pwhash: str) -> RetVal:
	'''Continues the login process sending a password hash to the server.'''
	
	status = conn.send_message({
		'Action' : "PASSWORD",
		'Data' : { 'Password-Hash' : pwhash }
	})
	if status.error():
		return status

	response = conn.read_response(server_response)
	if response.error():
		return response
	
	if response['Code'] != 100:
		return wrap_server_error(response)
	
	return RetVal()


def preregister(conn: ServerConnection, wid: utils.UUID, uid: utils.UserID, domain: utils.Domain) -> RetVal:
	'''Provisions a preregistered account on the server.'''
	request = { 'Action':'PREREG', 'Data':{} }

	if not wid.is_empty():
		request['Data']['Workspace-ID'] = wid.as_string()
	
	if not uid.is_empty():
			request['Data']['User-ID'] = uid.as_string()
	
	if not domain.is_empty():
		request['Data']['Domain'] = domain.as_string()

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
	for field in [ 'Domain', 'Workspace-ID', 'Reg-Code']:
		if field not in response['Data']:
			return RetVal(ErrServerError, 'server did not return all required fields')

	out['domain'] = utils.Domain(response['Data']['Domain'])
	out['wid'] = utils.UUID(response['Data']['Workspace-ID'])
	out['regcode'] = response['Data']['Reg-Code']

	if 'User-ID' in response['Data']:
		out['uid'] = utils.UserID(response['Data']['User-ID'])
		if not out['uid'].is_valid():
			return RetVal(ErrServerError, 'server returned invalid user ID')
	
	if not (out['domain'].is_valid() and out['wid'].is_valid()):
		return RetVal(ErrServerError, 'server returned invalid data')

	return out


def regcode(conn: ServerConnection, address: utils.MAddress, code: str, pwhash: str, 
	devpair: EncryptionPair) -> RetVal:
	'''Finishes registration of a workspace'''
	
	if not address.is_valid():
		return RetVal(ErrBadValue, 'bad address')
	
	devid = utils.UUID()
	devid.generate()

	request = {
		'Action':'REGCODE',
		'Data':{
			'Reg-Code': code,
			'Password-Hash': pwhash,
			'Device-ID': devid.as_string(),
			'Device-Key': devpair.public.as_string(),
			'Domain': address.domain.as_string()
		}
	}

	if address.id_type == 1:
		request['Data']['Workspace-ID'] = address.id.as_string()
	else:
		request['Data']['User-ID'] = address.id.as_string()
	
	status = conn.send_message(request)
	if status.error():
		return status
	
	response = conn.read_response(server_response)
	if response.error():
		return response
	
	if response['Code'] != 201:
		return wrap_server_error(response)
	
	return RetVal().set_values({
		'devid': devid,
		'wid': utils.UUID(response['Data']['Workspace-ID'])
	})
	

def register(conn: ServerConnection, uid: utils.UserID, pwhash: str,
			devicekey: CryptoString) -> RetVal:
	'''Creates an account on the server.'''
	
	if not uid.is_valid():
		return RetVal(ErrBadValue, 'invalid user ID')
		
	# This construct is a little strange, but it is to work around the minute possibility that
	# there is a WID collision, i.e. the WID generated by the client already exists on the server.
	# In such an event, it should try again. However, in the ridiculously small chance that the 
	# client keeps generating collisions, it should wait 3 seconds after 10 collisions to reduce 
	# server load.
	out = RetVal()
	devid = utils.UUID()
	devid.generate()
	wid = utils.UUID()
	response = dict()
	tries = 1
	while wid.is_empty():
		if not tries % 10:
			time.sleep(3.0)
		
		# Technically, the active profile already has a WID, but it is not attached to a domain and
		# doesn't matter as a result. Rather than adding complexity, we just generate a new UUID
		# and always return the replacement value
		wid.generate()
		request = {
			'Action' : 'REGISTER',
			'Data' : {
				'Workspace-ID' : wid.as_string(),
				'Password-Hash' : pwhash,
				'Device-ID' : devid.as_string(),
				'Device-Key' : devicekey.as_string()
			}
		}
		if uid:
			request['Data']['User-ID'] = uid.as_string()

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
				'domain' : utils.Domain(response['Data']['Domain']),
				'uid' : uid
			})
			break
		
		if response['Code'] == 408:	# WID or UID exists
			if 'Field' not in response['Data']:
				return RetVal(ErrServerError, 'server sent 408 without telling what existed')
			
			if response['Data']['Field'] not in ['User-ID', 'Workspace-ID']:
				return RetVal(ErrServerError, 'server sent bad 408 response').set_value( \
					'Field', response['Data']['Field'])

			if response['Data']['Field'] == 'User-ID':
				return RetVal(ErrExists, 'user id')
			
			tries = tries + 1
			wid.set('')
		else:
			# Something we didn't expect -- reg closed, payment req'd, etc.
			return wrap_server_error(response)
	
	return out


def reset_password(conn: ServerConnection, wid: utils.UUID, reset_code='', expires='') -> RetVal:
	'''Resets a workspace's password'''

	status = conn.send_message({
		'Action': 'RESETPASSWORD',
		'Data': {
			'Workspace-ID': wid.as_string(),
			'Reset-Code': reset_code,
			'Expires': expires
		}
	})
	if status.error():
		return status
	
	response = conn.read_response(server_response)
	if response['Code'] != 200:
		return wrap_server_error(response)
	
	return RetVal().set_values({ 'resetcode': response['Data']['Reset-Code'],
								'expires': response['Data']['Expires'] })


def setpassword(conn: ServerConnection, pwhash: str, newpwhash: str) -> RetVal:
	'''Changes the password for the workspace'''
	
	status = conn.send_message({
		'Action' : 'SETPASSWORD',
		'Data' : {
			'Password-Hash': pwhash,
			'NewPassword-Hash': newpwhash
		}
	})
	if status.error():
		return status
	
	response = conn.read_response(server_response)
	if response['Code'] != 200:
		return wrap_server_error(response)
	
	return RetVal()


def setstatus(conn: ServerConnection, wid: utils.UUID, status: str):
	'''Sets the activity status of the workspace specified. Requires admin privileges'''
	if status not in ['active', 'disabled', 'approved']:
		return RetVal(ErrBadValue, "status must be 'active','disabled', or 'approved'")
	
	if not wid.is_valid():
		return RetVal(ErrBadValue, 'bad wid')

	status = conn.send_message({
		'Action' : 'SETSTATUS',
		'Data' : {
			'Workspace-ID': wid.as_string(),
			'Status': status
		}
	})
	if status.error():
		return status
	
	response = conn.read_response(server_response)
	if response['Code'] != 200:
		return wrap_server_error(response)

	return RetVal()


def unregister(conn: ServerConnection, pwhash: str, wid: utils.UUID) -> RetVal:
	'''Deletes the online account at the specified server.'''

	if not wid.is_empty() and not wid.is_valid():
		return RetVal(ErrBadValue, 'bad workspace id')
	
	request = {
		'Action' : 'UNREGISTER',
		'Data' : {
			'Password-Hash' : pwhash
		}
	}
	if not wid.is_empty():
		request['Data']['Workspace-ID'] = wid.as_string()
	
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

def usercard(conn: ServerConnection, start_index: int, end_index: int) -> RetVal:
	'''Obtains a user's keycard'''
	
	# TODO: implement usercard()
	return RetVal(ErrUnimplemented)


