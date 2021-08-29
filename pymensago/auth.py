'''This module encapsulates authentication, credentials, and session management'''

import base64
import platform
import sqlite3
import time

import distro
from pycryptostring import CryptoString
from retval import ErrEmptyData, RetVal, ErrNotFound, ErrExists, ErrBadValue

from pymensago.encryption import CryptoKey, SecretKey, EncryptionPair, SigningPair, Password, \
	ErrUnsupportedAlgorithm
from pymensago.utils import WAddress, UUID

def get_credentials(db: sqlite3.Connection, addr: WAddress) -> RetVal:
	'''Returns the stored login credentials for the requested wid'''
	cursor = db.cursor()
	cursor.execute('''SELECT password,pwhashtype FROM workspaces WHERE wid=? AND domain=?''',
		(addr.id.as_string(),addr.domain.as_string()))
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


def add_device_session(db, address: WAddress, devid: UUID, devpair: EncryptionPair, 
	devname='') -> RetVal:
	'''Adds a device to a workspace'''

	if not address.is_valid():
		return RetVal(ErrBadValue, 'bad address')
	
	if not devid:
		return RetVal(ErrEmptyData)
	
	if devpair.enctype != 'CURVE25519':
		return RetVal(ErrUnsupportedAlgorithm, "enctype must be 'CURVE25519'")

	# address has to be valid and existing already
	cursor = db.cursor()
	cursor.execute("SELECT wid FROM workspaces WHERE wid=?",(address.id.as_string(),))
	results = cursor.fetchone()
	if not results or not results[0]:
		return RetVal(ErrNotFound)

	# Can't have a session on the server already
	cursor.execute("SELECT address FROM sessions WHERE address=?", (address.as_string(),))
	results = cursor.fetchone()
	if results:
		return RetVal(ErrExists)
	
	cursor = db.cursor()
	if not devname:
		devname = platform.node().casefold()
	
	osname = platform.system().casefold()

	# Use the name of the distro if running Linux
	if osname == 'linux' and distro.id():
		osname = distro.id().casefold()
		
	cursor.execute('''INSERT INTO sessions(
			address, devid, devname, public_key, private_key, os) 
			VALUES(?,?,?,?,?,?)''',
			(address.as_string(), devid.as_string(), devname, devpair.public.as_string(), 
			devpair.private.as_string(), osname))
	db.commit()
	return RetVal()


def remove_device_session(db, devid: UUID) -> RetVal:
	'''	Removes an authorized device from the workspace. Returns a boolean success code.'''

	cursor = db.cursor()
	cursor.execute("SELECT devid FROM sessions WHERE devid=?", (devid.as_string(),))
	results = cursor.fetchone()
	if not results or not results[0]:
		return RetVal(ErrNotFound)

	cursor.execute("DELETE FROM sessions WHERE devid=?", (devid.as_string(),))
	db.commit()
	return RetVal()


def get_session_keypair(db: sqlite3.Connection, addr: WAddress) -> RetVal:
	'''Returns the device key for a server session'''
	cursor = db.cursor()
	cursor.execute("SELECT public_key,private_key FROM sessions WHERE address=?", 
		(addr.as_string(),))
	results = cursor.fetchone()
	if not results or not (results[0] and results[1]):
		return RetVal(ErrNotFound)
	
	keypair = EncryptionPair(CryptoString(results[0]), CryptoString(results[1]))
	return RetVal().set_value('keypair', keypair)


def add_key(db: sqlite3.Connection, key: CryptoKey, address: str, category='') -> RetVal:
	'''Adds an encryption key to a workspace.
	Parameters:
	key: CryptoKey from encryption module
	address: full Mensago address, i.e. wid + domain
	
	Returns:
	error : string
	'''
	cursor = db.cursor()
	cursor.execute("SELECT keyid FROM keys WHERE keyid=?", (key.pubhash,))
	results = cursor.fetchone()
	if results:
		return RetVal(ErrExists)
	
	timestamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
	if key.enctype == 'XSALSA20':
		cursor.execute('''INSERT INTO keys(keyid,address,type,category,private,timestamp)
			VALUES(?,?,?,?,?,?)''', (key.pubhash, address, 'symmetric', category,
				key.get_key(), timestamp))
		db.commit()
		return RetVal()
	
	if key.enctype == 'CURVE25519':
		cursor.execute('''INSERT INTO keys(keyid,address,type,category,private,public,timestamp)
			VALUES(?,?,?,?,?,?,?)''', (key.pubhash, address, 'asymmetric', category,
				key.private.as_string(), key.public.as_string(), timestamp))
		db.commit()
		return RetVal()
	
	if key.enctype == 'ED25519':
		cursor.execute('''INSERT INTO keys(keyid,address,type,category,private,public,timestamp)
			VALUES(?,?,?,?,?,?,?)''', (key.pubhash, address, 'signing', category,
				key.private.as_string(), key.public.as_string(), timestamp))
		db.commit()
		return RetVal()
	
	return RetVal(ErrUnsupportedAlgorithm, f"Unsupported key algorithm {key.enctype}")


def remove_key(db: sqlite3.Connection, keyid: str) -> RetVal:
	'''Deletes an encryption key from a workspace.
	Parameters:
	keyid : CryptoString-formatted key hash

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
	'key' : CryptoKey object in (EncryptionPair|Secretkey|SigningPair)
	'''

	cursor = db.cursor()
	cursor.execute("SELECT address,type,category,private,public FROM keys WHERE keyid=?", (keyid,))
	results = cursor.fetchone()
	if not results or not results[0]:
		return RetVal(ErrNotFound)
	
	if results[1] == 'asymmetric':
		public = CryptoString(results[3])
		private = CryptoString(results[2])
		key = EncryptionPair(public,private)
		return RetVal().set_value('key', key)
	
	if results[1] == 'symmetric':
		private = CryptoString(results[2])
		key = SecretKey(private)
		return RetVal().set_value('key', key)

	if results[1] == 'signing':
		public = CryptoString(results[3])
		private = CryptoString(results[2])
		key = SigningPair(public,private)
		return RetVal().set_value('key', key)
	
	return RetVal(ErrBadValue, "Key must be 'asymmetric', 'symmetric', or 'signing'")


def get_key_by_type(db: sqlite3.Connection, keytype: str) -> RetVal:
	'''Returns the most recent key of the specified type.
	Parameters:
	keytype: str

	Currently keytype can be crsign, crencrypt, encrypt, sign, storage, or folder.

	Returns:
	'error' : string
	'key' : CryptoKey object
	'''

	cursor = db.cursor()
	cursor.execute('''SELECT address,type,private,public
		FROM keys WHERE category=? ORDER BY 'timestamp' DESC LIMIT 1''', (keytype,))
	results = cursor.fetchone()
	if not results or not results[0]:
		return RetVal(ErrNotFound)
	
	if results[1] == 'asymmetric':
		public = CryptoString(results[3])
		private = CryptoString(results[2])
		key = EncryptionPair(public,private)
		return RetVal().set_value('key', key)
	
	if results[1] == 'symmetric':
		private = CryptoString(results[2])
		key = SecretKey(private)
		return RetVal().set_value('key', key)

	if results[1] == 'signing':
		public = CryptoString(results[3])
		private = CryptoString(results[2])
		key = SigningPair(public,private)
		return RetVal().set_value('key', key)

	return RetVal(ErrBadValue, "Key type not an official type")
