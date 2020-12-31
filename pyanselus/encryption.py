'''Holds classes designed for working with encryption keys'''
import base64
import json
import os
import re
import uuid

import jsonschema

import nacl.public
import nacl.pwhash
import nacl.secret
import nacl.signing
import nacl.utils
from pyanselus.cryptostring import CryptoString
from pyanselus.hash import blake2hash
from pyanselus.retval import RetVal, BadData, BadParameterValue, ExceptionThrown, InternalError, \
		ResourceExists, ResourceNotFound

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
	'''Defines a generic interface to an Anselus encryption key, which contains more
	information than just the key itself'''
	def __init__(self):
		self.id = str(uuid.uuid4())
		self.pubhash = ''
		self.privhash = ''
		self.enctype = ''
		self.type = ''
	
	def get_id(self):
		'''Returns the ID of the key'''
		return self.id
	
	def get_encryption_type(self):
		'''Returns the name of the encryption used, such as rsa, aes256, etc.'''
		return self.enctype

	def get_type(self):
		'''Returns the type of key, such as asymmetric or symmetric'''
		return self.type


class EncryptionPair (CryptoKey):
	'''Represents an assymmetric encryption key pair'''
	def __init__(self, public=None, private=None):
		super().__init__()
		if public and private:
			if not isinstance(public, CryptoString) or not isinstance(private, CryptoString):
				raise TypeError
			
			if public.prefix != private.prefix:
				raise ValueError
			
			self.enctype = public.prefix
			self.public = public
			self.private = private
		else:
			key = nacl.public.PrivateKey.generate()
			self.enctype = 'CURVE25519'
			self.public = CryptoString('CURVE25519:' + \
					base64.b85encode(key.public_key.encode()).decode())
			self.private = CryptoString('CURVE25519:' + \
					base64.b85encode(key.encode()).decode())
		self.pubhash = blake2hash(self.public.data)
		self.privhash = blake2hash(self.private.data)

	def __str__(self):
		return '\n'.join([
			self.public.as_string(),
			self.private.as_string()
		])

	def get_public_key(self) -> str:
		'''Returns the public key encoded in base85'''
		return self.public.as_string()
	
	def get_private_key(self) -> str:
		'''Returns the private key encoded in base85'''
		return self.private.as_string()

	def save(self, path: str):
		'''Saves the keypair to a file'''
		if not path:
			return RetVal(BadParameterValue, 'path may not be empty')
		
		if os.path.exists(path):
			return RetVal(ResourceExists, '%s exists' % path)

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
			return RetVal(ExceptionThrown, str(e))

		return RetVal()


def load_encryptionpair(path: str) -> RetVal:
	'''Instantiates a keypair from a file'''
	if not path:
		return RetVal(BadParameterValue, 'path may not be empty')
	
	if not os.path.exists(path):
		return RetVal(ResourceNotFound, '%s exists' % path)
	
	indata = None
	try:
		with open(path, "r") as fhandle:
			indata = json.load(fhandle)
	
	except Exception as e:
		return RetVal(ExceptionThrown, e)
	
	if not isinstance(indata, dict):
		return RetVal(BadData, 'File does not contain an Anselus JSON keypair')

	try:
		jsonschema.validate(indata, __encryption_pair_schema)
	except jsonschema.ValidationError:
		return RetVal(BadData, "file data does not validate")
	except jsonschema.SchemaError:
		return RetVal(InternalError, "BUG: invalid EncryptionPair schema")

	public_key = CryptoString(indata['PublicKey'])
	private_key = CryptoString(indata['PrivateKey'])
	if not public_key.is_valid() or not private_key.is_valid():
		return RetVal(BadData, 'Failure to base85 decode key data')
	
	return RetVal().set_value('keypair', EncryptionPair(public_key, private_key))


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
			self.public = CryptoString('ED25519:' + \
					base64.b85encode(key.verify_key.encode()).decode())
			self.private = CryptoString('ED25519:' + \
					base64.b85encode(key.encode()).decode())		
		self.pubhash = blake2hash(self.public.data)
		self.privhash = blake2hash(self.private.data)
		
	def __str__(self):
		return '\n'.join([
			self.public.as_string(),
			self.private.as_string()
		])

	def get_public_key(self) -> bytes:
		'''Returns the binary data representing the public half of the key'''
		return self.public.as_string()
	
	def get_private_key(self) -> str:
		'''Returns the private key encoded in base85'''
		return self.private.as_string()
	
	def save(self, path: str) -> RetVal:
		'''Saves the key to a file'''
		if not path:
			return RetVal(BadParameterValue, 'path may not be empty')
		
		if os.path.exists(path):
			return RetVal(ResourceExists, '%s exists' % path)

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
			return RetVal(ExceptionThrown, str(e))

		return RetVal()
	
	def sign(self, data : bytes) -> RetVal:
		'''Return a Base85-encoded signature for the supplied data in the field 'signature'.'''
		
		key = nacl.signing.SigningKey(self.private.raw_data())

		try:
			signed = key.sign(data, Base85Encoder)
		except Exception as e:
			return RetVal(ExceptionThrown, e)
		
		return RetVal().set_value('signature', 'ED25519:' + signed.signature.decode())
	


def signingpair_from_string(keystr : str) -> SigningPair:
	'''Intantiates a signing pair from a saved seed string that is used for the private key'''
	
	key = nacl.signing.SigningKey(base64.b85decode(keystr))
	return SigningPair(
		CryptoString('ED25519:' + base64.b85encode(key.verify_key.encode()).decode()),
		CryptoString('ED25519:' + base64.b85encode(key.encode()).decode())	
	)


def load_signingpair(path: str) -> RetVal:
	'''Instantiates a signing pair from a file'''
	if not path:
		return RetVal(BadParameterValue, 'path may not be empty')
	
	if not os.path.exists(path):
		return RetVal(ResourceNotFound, '%s exists' % path)
	
	indata = None
	try:
		with open(path, "r") as fhandle:
			indata = json.load(fhandle)
	
	except Exception as e:
		return RetVal(ExceptionThrown, e)
	
	if not isinstance(indata, dict):
		return RetVal(BadData, 'File does not contain an Anselus JSON signing pair')

	try:
		jsonschema.validate(indata, __signing_pair_schema)
	except jsonschema.ValidationError:
		return RetVal(BadData, "file data does not validate")
	except jsonschema.SchemaError:
		return RetVal(InternalError, "BUG: invalid SigningPair schema")

	public_key = CryptoString(indata['VerificationKey'])
	private_key = CryptoString(indata['SigningKey'])
	if not public_key.is_valid() or not private_key.is_valid():
		return RetVal(BadData, 'Failure to base85 decode key data')
	
	return RetVal().set_value('keypair', SigningPair(public_key, private_key))


class SecretKey (CryptoKey):
	'''Represents a secret key used by symmetric encryption'''
	def __init__(self, key=None):
		super().__init__()
		if key:
			if type(key).__name__ != 'CryptoString':
				raise TypeError
			self.key = key
		else:
			self.enctype = 'XSALSA20'
			self.key = CryptoString('XSALSA20:' + \
					base64.b85encode(nacl.utils.random(nacl.secret.SecretBox.KEY_SIZE)).decode())
		
		self.hash = blake2hash(self.key.data)

	def __str__(self):
		return self.get_key()

	def get_key(self) -> str:
		'''Returns the key encoded in base85'''
		return self.key.as_string()
	
	def save(self, path: str) -> RetVal:
		'''Saves the key to a file'''
		if not path:
			return RetVal(BadParameterValue, 'path may not be empty')
		
		if os.path.exists(path):
			return RetVal(ResourceExists, '%s exists' % path)

		outdata = {
			'SecretKey' : self.get_key()
		}

		try:
			fhandle = open(path, 'w')
			json.dump(outdata, fhandle, ensure_ascii=False, indent=1)
			fhandle.close()
		
		except Exception as e:
			return RetVal(ExceptionThrown, str(e))

		return RetVal()
	
	def decrypt(self, encdata : str) -> bytes:
		'''Decrypts the Base85-encoded encrypted data and returns it as bytes. Returns None on 
		failure'''
		if encdata is None:
			return None
		
		if type(encdata).__name__ != 'str':
			raise TypeError

		secretbox = nacl.secret.SecretBox(self.key.raw_data())
		return secretbox.decrypt(encdata, encoder=Base85Encoder)
	
	def encrypt(self, data : bytes) -> str:
		'''Encrypts the passed data and returns it as a Base85-encoded string. Returns None on 
		failure'''
		if data is None:
			return None
		
		if type(data).__name__ != 'bytes':
			raise TypeError
		
		secretbox = nacl.secret.SecretBox(self.key.raw_data())
		mynonce = nacl.utils.random(nacl.secret.SecretBox.NONCE_SIZE)
		return secretbox.encrypt(data,nonce=mynonce, encoder=Base85Encoder).decode()
		

def load_secretkey(path: str) -> RetVal:
	'''Instantiates a secret key from a file'''
	if not path:
		return RetVal(BadParameterValue, 'path may not be empty')
	
	if not os.path.exists(path):
		return RetVal(ResourceNotFound, '%s exists' % path)
	
	indata = None
	try:
		with open(path, "r") as fhandle:
			indata = json.load(fhandle)
	
	except Exception as e:
		return RetVal(ExceptionThrown, e)
	
	if not isinstance(indata, dict):
		return RetVal(BadData, 'File does not contain an Anselus JSON secret key')

	try:
		jsonschema.validate(indata, __secret_key_schema)
	except jsonschema.ValidationError:
		return RetVal(BadData, "file data does not validate")
	except jsonschema.SchemaError:
		return RetVal(InternalError, "BUG: invalid SecretKey schema")

	key = CryptoString(indata['SecretKey'])
	if not key.is_valid():
		return RetVal(BadData, 'Failure to base85 decode key data')
	
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


def check_password_complexity(indata):
	'''Checks the requested string as meeting the needed security standards.
	
	Returns: RetVal
	strength: string in [very weak', 'weak', 'medium', 'strong']
	'''
	if len(indata) < 8:
		return RetVal(BadParameterValue, 'Passphrase must be at least 8 characters.') \
			.set_value('strength', 'very weak')
	
	strength_score = 0
	strength_strings = [ 'error', 'very weak', 'weak', 'medium', 'strong', 'very strong']

	# Anselus *absolutely* permits UTF-8-encoded passwords. This greatly increases the
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
		status = RetVal(BadParameterValue, 'passphrase too weak')
		status.set_value('strength', strength_strings[strength_score])
		return status
	return RetVal().set_value('strength', strength_strings[strength_score])


class Password:
	'''Encapsulates hashed password interactions. Uses the Argon2id hashing algorithm.'''
	def __init__(self):
		self.hashtype = 'argon2id'
		self.strength = ''
		self.hashstring = ''

	def Set(self, text):
		'''
		Takes the given password text, checks strength, and generates a hash
		Returns: RetVal
		On success, field 'strength' is also returned
		'''
		status = check_password_complexity(text)
		if status.error():
			return status
		self.strength = status['strength']
		self.hashstring = nacl.pwhash.argon2id.str(bytes(text, 'utf8')).decode('ascii')
		
		return status
	
	def Assign(self, pwhash):
		'''
		Takes a PHC hash format string and assigns the password object to it.
		Returns: [dict]
		error : string
		'''
		self.hashstring = pwhash
		return RetVal()
	
	def Check(self, text):
		'''
		Checks the supplied password against the stored hash and returns a boolean match status.
		'''
		return nacl.pwhash.verify(self.hashstring.encode(), text.encode())


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
