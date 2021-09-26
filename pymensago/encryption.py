'''Holds classes designed for working with encryption keys'''
import base64
import json
import os
import re
import uuid

import jsonschema
from pycryptostring import CryptoString
from retval import RetVal, ErrBadData, ErrBadValue, ErrBadType, ErrInternalError, ErrExists, \
	ErrNotFound

import nacl.public
import nacl.pwhash
import nacl.secret
import nacl.signing
import nacl.utils
from pymensago.hash import blake2hash

VerificationError = 'VerificationError'
DecryptionFailure = 'DecryptionFailure'
ErrUnsupportedAlgorithm = 'ErrUnsupportedAlgorithm'

# JSON schemas used to validate keyfile data
__encryption_pair_schema = {
	'type' : 'object',
	'properties' : {
		'PublicKey' : { 'type' : 'string' },
		'PrivateKey' : { 'type' : 'string' },
	}
}

__signing_pair_schema = {
	'type' : 'object',
	'properties' : {
		'VerificationKey' : { 'type' : 'string' },
		'SigningKey' : { 'type' : 'string' },
	}
}

__secret_key_schema = {
	'type' : 'object',
	'properties' : {
		'SecretKey' : { 'type' : 'string' }
	}
}

class CryptoKey:
	'''Defines a generic interface to an Mensago encryption key, which contains more
	information than just the key itself'''
	def __init__(self):
		self.pubhash = ''
		self.privhash = ''
		self.enctype = ''
		self.type = ''
	
	def get_encryption_type(self):
		'''Returns the name of the encryption used, such as rsa, aes256, etc.'''
		return self.enctype

	def get_type(self):
		'''Returns the type of key, such as asymmetric or symmetric'''
		return self.type


class PublicKey (CryptoKey):
	'''Represents a public encryption key'''
	def __init__(self, public):
		super().__init__()
		if not isinstance(public, CryptoString):
			raise TypeError
		self.public = public
		self.pubhash = blake2hash(self.public.data.encode())
	
	def as_string(self):
		'''Returns the key as a string'''
		return self.public.as_string()

	def encrypt(self, data : bytes) -> RetVal:
		'''Encrypt the passed data using the public key and return the Base85-encoded data in the 
		field 'data'.'''
		if not isinstance(data, bytes):
			return RetVal(ErrBadType, 'bytes expected')
		
		try:
			sealedbox = nacl.public.SealedBox(nacl.public.PublicKey(self.public.as_raw()))
			encrypted_data = sealedbox.encrypt(data, Base85Encoder).decode()
		except Exception as e:
			return RetVal().wrap_exception(e)
		
		return RetVal().set_values({'prefix':self.public.prefix, 'data':encrypted_data})


class EncryptionPair (CryptoKey):
	'''Represents an assymmetric encryption key pair'''
	def __init__(self, public=None, private=None):
		super().__init__()
		if public and private:
			if not (isinstance(public, CryptoString) and isinstance(private, CryptoString)):
				raise TypeError
			
			if public.prefix != private.prefix:
				raise ValueError
			
			self.enctype = public.prefix
			self.public = public
			self.private = private
		else:
			key = nacl.public.PrivateKey.generate()
			self.enctype = 'CURVE25519'
			self.public = CryptoString('CURVE25519', key.public_key.encode())
			self.private = CryptoString('CURVE25519', key.encode())
		self.pubhash = blake2hash(self.public.data.encode())
		self.privhash = blake2hash(self.private.data.encode())

	def __str__(self):
		return '\n'.join([
			self.public.as_string(),
			self.private.as_string()
		])

	def get_public_key(self) -> str:
		'''Returns the public key as a CryptoString string'''
		return self.public.as_string()
	
	def get_public_hash(self) -> str:
		'''Returns the hash of the public key as a CryptoString string'''
		return self.pubhash
	
	def get_private_key(self) -> str:
		'''Returns the private key as a CryptoString string'''
		return self.private.as_string()

	def get_private_hash(self) -> str:
		'''Returns the hash of the private key as a CryptoString string'''
		return self.privhash
	
	def save(self, path: str):
		'''Saves the keypair to a file'''
		if not path:
			return RetVal(ErrBadValue, 'path may not be empty')
		
		if os.path.exists(path):
			return RetVal(ErrExists, '%s exists' % path)

		outdata = {
			'PublicKey' : self.get_public_key(),
			'PublicHash' : self.pubhash,
			'PrivateKey' : self.get_private_key(),
			'PrivateHash' : self.privhash
		}
			
		try:
			fhandle = open(path, 'w')
			json.dump(outdata, fhandle, ensure_ascii=False, indent=1)
			fhandle.close()
		
		except Exception as e:
			return RetVal().wrap_exception(e)

		return RetVal()

	def encrypt(self, data : bytes) -> RetVal:
		'''Encrypt the passed data using the public key and return the Base85-encoded data in the 
		field 'data'.'''
		if not isinstance(data, bytes):
			return RetVal(ErrBadType, 'bytes expected')
		
		try:
			sealedbox = nacl.public.SealedBox(nacl.public.PublicKey(self.public.as_raw()))
			encrypted_data = sealedbox.encrypt(data, Base85Encoder).decode()
		except Exception as e:
			return RetVal().wrap_exception(e)
		
		return RetVal().set_values({'prefix':self.public.prefix, 'data':encrypted_data})

	def decrypt(self, data : str) -> RetVal:
		'''Decrypt the passed data using the private key and return the raw data in the field 
		'data'. Base85 decoding of the data is optional, but enabled by default.'''
		if not isinstance(data, str):
			return RetVal(ErrBadType, 'string expected')
		
		try:
			sealedbox = nacl.public.SealedBox(nacl.public.PrivateKey(self.private.as_raw()))
			decrypted_data = sealedbox.decrypt(data.encode(), Base85Encoder)
		except Exception as e:
			return RetVal().wrap_exception(e)
		
		return RetVal().set_value('data', decrypted_data.decode())


def load_encryptionpair(path: str) -> RetVal:
	'''Instantiates a keypair from a file'''
	if not path:
		return RetVal(ErrBadValue, 'path may not be empty')
	
	if not os.path.exists(path):
		return RetVal(ErrNotFound, '%s exists' % path)
	
	indata = None
	try:
		with open(path, "r") as fhandle:
			indata = json.load(fhandle)
	
	except Exception as e:
		return RetVal().wrap_exception(e)
	
	if not isinstance(indata, dict):
		return RetVal(ErrBadData, 'File does not contain an Mensago JSON keypair')

	try:
		jsonschema.validate(indata, __encryption_pair_schema)
	except jsonschema.ValidationError:
		return RetVal(ErrBadData, "file data does not validate")
	except jsonschema.SchemaError:
		return RetVal(ErrInternalError, "BUG: invalid EncryptionPair schema")

	public_key = CryptoString(indata['PublicKey'])
	private_key = CryptoString(indata['PrivateKey'])
	if not public_key.is_valid() or not private_key.is_valid():
		return RetVal(ErrBadData, 'Failure to base85 decode key data')
	
	return RetVal().set_value('keypair', EncryptionPair(public_key, private_key))


class VerificationKey (CryptoKey):
	'''Represents a public encryption key'''
	def __init__(self, public):
		super().__init__()
		if not isinstance(public, CryptoString):
			raise TypeError
		self.public = public
		self.pubhash = blake2hash(self.public.data.encode())

	def as_string(self):
		'''Returns the key as a string'''
		return self.public.as_string()

	def verify(self, data : bytes, data_signature : CryptoString) -> RetVal:
		'''Return a Base85-encoded signature for the supplied data in the field 'signature'.'''
		
		if not isinstance(data, bytes):
			return RetVal(ErrBadType, 'bytes expected for data')
		if not isinstance(data_signature, CryptoString):
			return RetVal(ErrBadType, 'signature parameter must be a CryptoString')
		
		key = nacl.signing.VerifyKey(self.public.as_raw())

		try:
			key.verify(data, data_signature.as_raw())
		except Exception as e:
			return RetVal(VerificationError, e)
		
		return RetVal()


class SigningPair:
	'''Represents an asymmetric signing key pair'''
	def __init__(self, public=None, private=None):
		super().__init__()

		if public and private:
			if type(public).__name__ != 'CryptoString' or \
				type(private).__name__ != 'CryptoString':
				raise TypeError
			
			if public.prefix != private.prefix:
				raise ValueError
			
			self.enctype = public.prefix
			self.public = public
			self.private = private
		else:
			key = nacl.signing.SigningKey.generate()
			self.enctype = 'ED25519'
			self.public = CryptoString('ED25519', key.verify_key.encode())
			self.private = CryptoString('ED25519', key.encode())
		self.pubhash = blake2hash(self.public.data.encode())
		self.privhash = blake2hash(self.private.data.encode())
		
	def __str__(self):
		return '\n'.join([
			self.public.as_string(),
			self.private.as_string()
		])

	def get_public_key(self) -> bytes:
		'''Returns the verification key as a CryptoString string'''
		return self.public.as_string()
	
	def get_public_hash(self) -> str:
		'''Returns the hash of the verification key as a CryptoString string'''
		return self.pubhash
	
	def get_private_key(self) -> str:
		'''Returns the signing key as a CryptoString string'''
		return self.private.as_string()
	
	def get_private_hash(self) -> str:
		'''Returns the hash of the signing key as a CryptoString string'''
		return self.privhash
	
	def save(self, path: str) -> RetVal:
		'''Saves the key to a file'''
		if not path:
			return RetVal(ErrBadValue, 'path may not be empty')
		
		if os.path.exists(path):
			return RetVal(ErrExists, '%s exists' % path)

		outdata = {
			'VerificationKey' : self.get_public_key(),
			'VerificationHash' : self.pubhash,
			'SigningKey' : self.get_private_key(),
			'SigningHash' : self.privhash
		}
			
		try:
			fhandle = open(path, 'w')
			json.dump(outdata, fhandle, ensure_ascii=False, indent=1)
			fhandle.close()
		
		except Exception as e:
			return RetVal().wrap_exception(e)

		return RetVal()
	
	def sign(self, data : bytes) -> RetVal:
		'''Return a Base85-encoded signature for the supplied data in the field 'signature'.'''
		if not isinstance(data, bytes):
			return RetVal(ErrBadType, 'bytes expected for data')
		
		key = nacl.signing.SigningKey(self.private.as_raw())

		try:
			signed = key.sign(data, Base85Encoder)
		except Exception as e:
			return RetVal().wrap_exception(e)
		
		return RetVal().set_value('signature', 'ED25519:' + signed.signature.decode())
	
	def verify(self, data : bytes, data_signature : CryptoString) -> RetVal:
		'''Return a Base85-encoded signature for the supplied data in the field 'signature'.'''
		
		if not isinstance(data, bytes):
			return RetVal(ErrBadType, 'bytes expected for data')
		if not isinstance(data_signature, CryptoString):
			return RetVal(ErrBadType, 'signature parameter must be a CryptoString')
		
		key = nacl.signing.VerifyKey(self.public.as_raw())

		try:
			key.verify(data, data_signature.as_raw())
		except Exception as e:
			return RetVal(VerificationError, e)
		
		return RetVal()


def signingpair_from_string(keystr : str) -> SigningPair:
	'''Intantiates a signing pair from a saved seed string that is used for the private key'''
	
	key = nacl.signing.SigningKey(base64.b85decode(keystr))
	return SigningPair(
		CryptoString('ED25519', key.verify_key.encode()),
		CryptoString('ED25519', key.encode())
	)


def load_signingpair(path: str) -> RetVal:
	'''Instantiates a signing pair from a file'''
	if not path:
		return RetVal(ErrBadValue, 'path may not be empty')
	
	if not os.path.exists(path):
		return RetVal(ErrNotFound, '%s exists' % path)
	
	indata = None
	try:
		with open(path, "r") as fhandle:
			indata = json.load(fhandle)
	
	except Exception as e:
		return RetVal().wrap_exception(e)
	
	if not isinstance(indata, dict):
		return RetVal(ErrBadData, 'File does not contain an Mensago JSON signing pair')

	try:
		jsonschema.validate(indata, __signing_pair_schema)
	except jsonschema.ValidationError:
		return RetVal(ErrBadData, "file data does not validate")
	except jsonschema.SchemaError:
		return RetVal(ErrInternalError, "BUG: invalid SigningPair schema")

	public_key = CryptoString(indata['VerificationKey'])
	private_key = CryptoString(indata['SigningKey'])
	if not public_key.is_valid() or not private_key.is_valid():
		return RetVal(ErrBadData, 'Failure to base85 decode key data')
	
	return RetVal().set_value('keypair', SigningPair(public_key, private_key))


class SecretKey (CryptoKey):
	'''Represents a secret key used by symmetric encryption'''
	def __init__(self, key=None):
		super().__init__()
		if key:
			if type(key).__name__ != 'CryptoString':
				raise TypeError
			self.enctype = key.prefix
			self.key = key
		else:
			self.enctype = 'XSALSA20'
			self.key = CryptoString('XSALSA20', nacl.utils.random(nacl.secret.SecretBox.KEY_SIZE))
		
		self.privhash = blake2hash(self.key.data.encode())
		self.pubhash = self.privhash

	def __str__(self):
		return self.get_key()

	def is_valid(self):
		return self.key.is_valid()

	def as_string(self) -> str:
		'''Returns the key encoded in base85'''
		return self.key.as_string()
	
	def get_key(self) -> str:
		'''Returns the key encoded in base85'''
		return self.key.as_string()
	
	def save(self, path: str) -> RetVal:
		'''Saves the key to a file'''
		if not path:
			return RetVal(ErrBadValue, 'path may not be empty')
		
		if os.path.exists(path):
			return RetVal(ErrExists, '%s exists' % path)

		outdata = {
			'SecretKey' : self.get_key()
		}

		try:
			fhandle = open(path, 'w')
			json.dump(outdata, fhandle, ensure_ascii=False, indent=1)
			fhandle.close()
		
		except Exception as e:
			return RetVal().wrap_exception(e)

		return RetVal()
	
	def decrypt(self, encdata : str) -> RetVal:
		'''Decrypts the Base85-encoded encrypted data and returns it as bytes. Returns None on 
		failure'''
		if encdata is None:
			return None
		
		if type(encdata).__name__ != 'str':
			raise TypeError

		secretbox = nacl.secret.SecretBox(self.key.as_raw())
		return RetVal().set_value('data', secretbox.decrypt(encdata, encoder=Base85Encoder))
	
	def encrypt(self, data : bytes) -> RetVal:
		'''Encrypts the passed data and returns it as a Base85-encoded string. Returns None on 
		failure'''
		if data is None:
			return None
		
		if type(data).__name__ != 'bytes':
			raise TypeError
		
		secretbox = nacl.secret.SecretBox(self.key.as_raw())
		mynonce = nacl.utils.random(nacl.secret.SecretBox.NONCE_SIZE)
		return RetVal().set_values({ 'prefix':'XSALSA20',
			'data':secretbox.encrypt(data,nonce=mynonce, encoder=Base85Encoder).decode()})
		

def load_secretkey(path: str) -> RetVal:
	'''Instantiates a secret key from a file'''
	if not path:
		return RetVal(ErrBadValue, 'path may not be empty')
	
	if not os.path.exists(path):
		return RetVal(ErrNotFound, '%s exists' % path)
	
	indata = None
	try:
		with open(path, "r") as fhandle:
			indata = json.load(fhandle)
	
	except Exception as e:
		return RetVal().wrap_exception(e)
	
	if not isinstance(indata, dict):
		return RetVal(ErrBadData, 'File does not contain an Mensago JSON secret key')

	try:
		jsonschema.validate(indata, __secret_key_schema)
	except jsonschema.ValidationError:
		return RetVal(ErrBadData, "file data does not validate")
	except jsonschema.SchemaError:
		return RetVal(ErrInternalError, "BUG: invalid SecretKey schema")

	key = CryptoString(indata['SecretKey'])
	if not key.is_valid():
		return RetVal(ErrBadData, 'Failure to base85 decode key data')
	
	return RetVal().set_value('key', SecretKey(key))


class FolderMapping:
	'''Represents the mapping of a server-side path to a local one'''
	def __init__(self):
		self.fid = ''
		self.address = ''
		self.keyid = ''
		self.path = ''
		self.permissions = ''
	
	def MakeID(self):
		'''Generates a FID for the object'''
		self.fid = str(uuid.uuid4())

	def Set(self, address, keyid, path, permissions):
		'''Sets the values of the object'''
		self.address = address
		self.keyid = keyid
		self.path = path
		self.permissions = permissions


def check_password_complexity(indata: str) -> RetVal:
	'''Checks the requested string as meeting the needed security standards.
	
	Returns: RetVal
	strength: string in [very weak', 'weak', 'medium', 'strong']
	'''
	if len(indata) < 8:
		return RetVal(ErrBadValue, 'Passphrase must be at least 8 characters.') \
			.set_value('strength', 'very weak')
	
	strength_score = 0
	strength_strings = [ 'error', 'very weak', 'weak', 'medium', 'strong', 'very strong']

	# Mensago *absolutely* permits UTF-8-encoded passwords. This greatly increases the
	# keyspace
	try:
		indata.encode().decode('ascii')
	except UnicodeDecodeError:
		strength_score = strength_score + 1
	
	if re.search(r"\d", indata):
		strength_score = strength_score + 1
	
	if re.search(r"[A-Z]", indata):
		strength_score = strength_score + 1
	
	if re.search(r"[a-z]", indata):
		strength_score = strength_score + 1

	if re.search(r"[~`!@#$%^&*()_={}/<>,.:;|'[\]\"\\\-\+\?]", indata):
		strength_score = strength_score + 1

	if (len(indata) < 12 and strength_score < 3) or strength_score < 2:
		# If the passphrase is less than 12 characters, require complexity
		status = RetVal(ErrBadValue, 'passphrase too weak')
		status.set_value('strength', strength_strings[strength_score])
		return status
	return RetVal().set_value('strength', strength_strings[strength_score])


class Password:
	'''Encapsulates hashed password interactions. Uses the Argon2id hashing algorithm.'''
	def __init__(self, text=''):
		self.hashtype = 'argon2id'
		self.strength = ''
		self.hashstring = ''
		if text:
			self.set(text)

	def set(self, text) -> RetVal:
		'''
		Takes the given password text, checks strength, and generates a hash
		Returns: RetVal
		On success, field 'strength' is also returned
		'''
		status = check_password_complexity(text)
		if status.error():
			return status
		self.strength = status['strength']
		self.hashstring = nacl.pwhash.argon2id.str(text.encode()).decode('ascii')
		
		return status
	
	def assign(self, pwhash) -> RetVal:
		'''
		Takes a PHC hash format string and assigns the password object to it.
		Returns: [dict]
		error : string
		'''
		self.hashstring = pwhash
		return RetVal()
	
	def Check(self, text) -> bool:
		'''
		Checks the supplied password against the stored hash.
		'''
		return nacl.pwhash.verify(self.hashstring.encode(), text.encode())
	
	def is_valid(self) -> bool:
		'''Returns true if the internal data is valid. Note that a password may be weak and still 
		valid.'''
		return self.strength and self.hashstring


class Base85Encoder:
	'''Base85 encoder for PyNaCl library'''
	@staticmethod
	def encode(data):
		'''Returns Base85 encoded data'''
		return base64.b85encode(data)
	
	@staticmethod
	def decode(data):
		'''Returns Base85 decoded data'''
		return base64.b85decode(data)
