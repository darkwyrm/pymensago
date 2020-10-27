'''This module encapsulates authentication, credentials, and session management'''

import base64
import sqlite3

import encryption
import utils
from retval import RetVal, ResourceNotFound, ResourceExists, BadParameterValue

def get_credentials(db: sqlite3.Connection, wid: str, domain: str) -> RetVal:
	'''Returns the stored login credentials for the requested wid'''
	cursor = db.cursor()
	cursor.execute('''SELECT password,pwhashtype FROM workspaces WHERE wid=? AND domain=?''',
		(wid,domain))
	results = cursor.fetchone()
	if not results or not results[0]:
		return RetVal(ResourceNotFound)
	
	out = encryption.Password()
	status = out.Assign(results[0])
	status['password'] = out
	return status


def set_credentials(db, wid: str, domain: str, pw: encryption.Password) -> RetVal:
	'''Sets the password and hash type for the specified workspace. A boolean success 
	value is returned.'''
	cursor = db.cursor()
	cursor.execute("SELECT wid FROM workspaces WHERE wid=? AND domain=?", (wid,domain))
	results = cursor.fetchone()
	if not results or not results[0]:
		return RetVal(ResourceNotFound)

	cursor = db.cursor()
	cursor.execute("UPDATE workspaces SET password=?,pwhashtype=? WHERE wid=? AND domain=?",
		(pw.hashstring, pw.hashtype, wid, domain))
	db.commit()
	return RetVal()

def add_device_session(db, address: str, devid: str, enctype: str, public_key: str, 
		private_key: str, devname='') -> RetVal:
	'''Adds a device to a workspace'''

	if not address or not devid or not enctype or not public_key or not private_key:
		return RetVal(BadParameterValue, "Empty parameter")
	
	if enctype != 'curve25519':
		return RetVal(BadParameterValue, "enctype must be 'curve25519'")

	# Normally we don't validate the input, relying on the caller to ensure valid data because
	# in most cases, bad data just corrupts the database integrity, not crash the program.
	# We have to do some here to ensure there isn't a crash when the address is split.
	parts = utils.split_address(address)
	if parts.error():
		return parts
	
	# address has to be valid and existing already
	cursor = db.cursor()
	cursor.execute("SELECT wid FROM workspaces WHERE wid=?", (parts['wid'],))
	results = cursor.fetchone()
	if not results or not results[0]:
		return RetVal(ResourceNotFound)

	# Can't have a session on the server already
	cursor.execute("SELECT address FROM sessions WHERE address=?", (address,))
	results = cursor.fetchone()
	if results:
		return RetVal(ResourceExists)
	
	cursor = db.cursor()
	if devname:
		cursor.execute('''INSERT INTO sessions(
				address, devid, enctype, public_key, private_key, devname) 
				VALUES(?,?,?,?,?,?)''',
				(address, devid, enctype, public_key, private_key, devname))
	else:
		cursor.execute('''INSERT INTO sessions(
				address, devid, enctype, public_key, private_key) 
				VALUES(?,?,?,?,?)''',
				(address, devid, enctype, public_key, private_key))
	db.commit()
	return RetVal()


def remove_device_session(db, devid: str) -> RetVal:
	'''
	Removes an authorized device from the workspace. Returns a boolean success code.
	'''
	cursor = db.cursor()
	cursor.execute("SELECT devid FROM sessions WHERE devid=?", (devid,))
	results = cursor.fetchone()
	if not results or not results[0]:
		return RetVal(ResourceNotFound)

	cursor.execute("DELETE FROM sessions WHERE devid=?", (devid,))
	db.commit()
	return RetVal()


def get_session_public_key(db: sqlite3.Connection, address: str) -> RetVal:
	'''Returns the public key for the device for a session'''
	cursor = db.cursor()
	cursor.execute("SELECT public_key FROM sessions WHERE address=?", (address,))
	results = cursor.fetchone()
	if not results or not results[0]:
		return RetVal(ResourceNotFound)
	return RetVal().set_value('key', results[0])


def get_session_private_key(db: sqlite3.Connection, address: str) -> RetVal:
	'''Returns the private key for the device for a session'''
	cursor = db.cursor()
	cursor.execute("SELECT private_key FROM sessions WHERE address=?", (address,))
	results = cursor.fetchone()
	if not results or not results[0]:
		return RetVal(ResourceNotFound)
	return RetVal().set_value('key', results[0])


def add_key(db: sqlite3.Connection, key: encryption.EncryptionKey, address: str) -> RetVal:
	'''Adds an encryption key to a workspace.
	Parameters:
	key: EncryptionKey from encryption module
	address: full Anselus address, i.e. wid + domain
	
	Returns:
	error : string
	'''
	cursor = db.cursor()
	cursor.execute("SELECT keyid FROM keys WHERE keyid=?", (key.get_id(),))
	results = cursor.fetchone()
	if results:
		return RetVal(ResourceExists)
	
	if key.get_type() == 'symmetric':
		cursor.execute('''INSERT INTO keys(keyid,address,type,category,private,algorithm)
			VALUES(?,?,?,?,?,?)''', (key.get_id(), address, key.get_type(), key.get_category(),
				key.get_key85(), key.get_encryption_type()))
		db.commit()
		return RetVal()
	
	if key.get_type() == 'asymmetric':
		cursor.execute('''INSERT INTO keys(keyid,address,type,category,private,public,algorithm)
			VALUES(?,?,?,?,?,?,?)''', (key.get_id(), address, key.get_type(), key.get_category(),
				key.get_private_key85(), key.get_public_key85(), key.get_encryption_type()))
		db.commit()
		return RetVal()
	
	return RetVal(BadParameterValue, "Key must be 'asymmetric' or 'symmetric'")


def remove_key(db: sqlite3.Connection, keyid: str) -> RetVal:
	'''Deletes an encryption key from a workspace.
	Parameters:
	keyid : uuid

	Returns:
	error : string
	'''
	cursor = db.cursor()
	cursor.execute("SELECT keyid FROM keys WHERE keyid=?", (keyid,))
	results = cursor.fetchone()
	if not results or not results[0]:
		return RetVal(ResourceNotFound)

	cursor.execute("DELETE FROM keys WHERE keyid=?", (keyid,))
	db.commit()
	return RetVal()


def get_key(db: sqlite3.Connection, keyid: str) -> RetVal:
	'''Gets the specified key.
	Parameters:
	keyid : uuid

	Returns:
	'error' : string
	'key' : EncryptionKey object
	'''

	cursor = db.cursor()
	cursor.execute('''
		SELECT address,type,category,private,public,algorithm
		FROM keys WHERE keyid=?''',
		(keyid,))
	results = cursor.fetchone()
	if not results or not results[0]:
		return RetVal(ResourceNotFound)
	
	if results[1] == 'asymmetric':
		public = base64.b85decode(results[4])
		private = base64.b85decode(results[3])
		key = encryption.KeyPair(results[2],	public,	private, results[5])
		return RetVal().set_value('key', key)
	
	if results[1] == 'symmetric':
		private = base64.b85decode(results[3])
		key = encryption.SecretKey(results[2], private, results[5])
		return RetVal().set_value('key', key)
	
	return RetVal(BadParameterValue, "Key must be 'asymmetric' or 'symmetric'")
