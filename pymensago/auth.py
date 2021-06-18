'''This module encapsulates authentication, credentials, and session management'''

import base64
import sqlite3

from retval import ErrEmptyData, RetVal, ErrNotFound, ErrExists, ErrBadValue

from pymensago.encryption import CryptoKey, SecretKey, EncryptionPair, Password, \
	ErrUnsupportedAlgorithm
from pymensago.utils import WAddress

def get_credentials(db: sqlite3.Connection, addr: WAddress) -> RetVal:
	'''Returns the stored login credentials for the requested wid'''
	cursor = db.cursor()
	cursor.execute('''SELECT password,pwhashtype FROM workspaces WHERE wid=? AND domain=?''',
		(addr.id,addr.domain))
	results = cursor.fetchone()
	if not results or not results[0]:
		return RetVal(ErrNotFound)
	
	out = Password()
	status = out.assign(results[0])
	status['password'] = out
	return status


def set_credentials(db, addr: WAddress, pw: Password) -> RetVal:
	'''Sets the password and hash type for the specified workspace. A boolean success 
	value is returned.'''
	cursor = db.cursor()
	cursor.execute("SELECT wid FROM workspaces WHERE wid=? AND domain=?", (addr.id, addr.domain))
	results = cursor.fetchone()
	if not results or not results[0]:
		return RetVal(ErrNotFound)

	cursor = db.cursor()
	cursor.execute("UPDATE workspaces SET password=?,pwhashtype=? WHERE wid=? AND domain=?",
		(pw.hashstring, pw.hashtype, addr.wid, addr.domain))
	db.commit()
	return RetVal()


def add_device_session(db, address: WAddress, devid: str, devpair: EncryptionPair, 
	devname='') -> RetVal:
	'''Adds a device to a workspace'''

	if not address.is_valid():
		return RetVal(ErrBadValue, 'bad address')
	if address.id_type == 2:
		return RetVal(ErrBadValue, 'workspace address is required')
	
	if not devid:
		return RetVal(ErrEmptyData)
	
	if devpair.enctype != 'CURVE25519':
		return RetVal(ErrUnsupportedAlgorithm, "enctype must be 'CURVE25519'")

	devid = devid.casefold()
	
	# address has to be valid and existing already
	cursor = db.cursor()
	cursor.execute("SELECT wid FROM workspaces WHERE wid=?",(address.id,))
	results = cursor.fetchone()
	if not results or not results[0]:
		return RetVal(ErrNotFound)

	# Can't have a session on the server already
	cursor.execute("SELECT address FROM sessions WHERE address=?", (address.as_string(),))
	results = cursor.fetchone()
	if results:
		return RetVal(ErrExists)
	
	cursor = db.cursor()
	if devname:
		cursor.execute('''INSERT INTO sessions(
				address, devid, enctype, public_key, private_key, devname) 
				VALUES(?,?,?,?,?,?)''',
				(address.as_string(), devid.casefold, devpair.enctype, devpair.public_key, 
				devpair.private_key, devname))
	else:
		cursor.execute('''INSERT INTO sessions(
				address, devid, enctype, public_key, private_key) 
				VALUES(?,?,?,?,?)''',
				(address.as_string(), devid, devpair.enctype, devpair.public_key, 
				devpair.private_key))
	db.commit()
	return RetVal()


def remove_device_session(db, devid: str) -> RetVal:
	'''
	Removes an authorized device from the workspace. Returns a boolean success code.
	'''
	devid = devid.casefold()

	cursor = db.cursor()
	cursor.execute("SELECT devid FROM sessions WHERE devid=?", (devid,))
	results = cursor.fetchone()
	if not results or not results[0]:
		return RetVal(ErrNotFound)

	cursor.execute("DELETE FROM sessions WHERE devid=?", (devid,))
	db.commit()
	return RetVal()


def get_session_public_key(db: sqlite3.Connection, addr: WAddress) -> RetVal:
	'''Returns the public key for the device for a session'''
	cursor = db.cursor()
	cursor.execute("SELECT public_key FROM sessions WHERE address=?", (addr.as_string(),))
	results = cursor.fetchone()
	if not results or not results[0]:
		return RetVal(ErrNotFound)
	return RetVal().set_value('key', results[0])


def get_session_private_key(db: sqlite3.Connection, addr: WAddress) -> RetVal:
	'''Returns the private key for the device for a session'''
	cursor = db.cursor()
	cursor.execute("SELECT private_key FROM sessions WHERE address=?", (addr.as_string(),))
	results = cursor.fetchone()
	if not results or not results[0]:
		return RetVal(ErrNotFound)
	return RetVal().set_value('key', results[0])


def add_key(db: sqlite3.Connection, key: CryptoKey, address: str) -> RetVal:
	'''Adds an encryption key to a workspace.
	Parameters:
	key: CryptoKey from encryption module
	address: full Mensago address, i.e. wid + domain
	
	Returns:
	error : string
	'''
	cursor = db.cursor()
	cursor.execute("SELECT keyid FROM keys WHERE keyid=?", (key.get_id(),))
	results = cursor.fetchone()
	if results:
		return RetVal(ErrExists)
	
	if key.enctype == 'XSALSA20':
		cursor.execute('''INSERT INTO keys(keyid,address,type,category,private,algorithm)
			VALUES(?,?,?,?,?,?)''', (key.get_id(), address, 'symmetric', '',
				key.get_key(), key.enctype))
		db.commit()
		return RetVal()
	
	if key.enctype == 'CURVE25519':
		cursor.execute('''INSERT INTO keys(keyid,address,type,category,private,public,algorithm)
			VALUES(?,?,?,?,?,?,?)''', (key.get_id(), address, 'asymmetric', '',
				key.private.as_string(), key.public.as_string(), key.enctype))
		db.commit()
		return RetVal()
	
	return RetVal(ErrBadValue, "Key must be 'asymmetric' or 'symmetric'")


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
		return RetVal(ErrNotFound)

	cursor.execute("DELETE FROM keys WHERE keyid=?", (keyid,))
	db.commit()
	return RetVal()


def get_key(db: sqlite3.Connection, keyid: str) -> RetVal:
	'''Gets the specified key.
	Parameters:
	keyid : uuid

	Returns:
	'error' : string
	'key' : CryptoKey object
	'''

	cursor = db.cursor()
	cursor.execute('''
		SELECT address,type,category,private,public,algorithm
		FROM keys WHERE keyid=?''',
		(keyid,))
	results = cursor.fetchone()
	if not results or not results[0]:
		return RetVal(ErrNotFound)
	
	if results[1] == 'asymmetric':
		public = base64.b85decode(results[4])
		private = base64.b85decode(results[3])
		key = EncryptionPair(public,	private)
		return RetVal().set_value('key', key)
	
	if results[1] == 'symmetric':
		private = base64.b85decode(results[3])
		key = SecretKey(private)
		return RetVal().set_value('key', key)
	
	return RetVal(ErrBadValue, "Key must be 'asymmetric' or 'symmetric'")
