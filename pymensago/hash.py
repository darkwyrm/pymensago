'''This module contains quick access to different hash functions'''

import base64
import hashlib

import blake3
from pycryptostring import CryptoString
from retval import RetVal, ErrBadValue

def blake2hash(data: bytes) -> str:
	'''Returns a CryptoString-format BLAKE2B-256 hash string of the passed data'''
	if data is None or data == '':
		return ''
	
	hasher=hashlib.blake2b(digest_size=32)
	hasher.update(data)
	return "BLAKE2B-256:" + base64.b85encode(hasher.digest()).decode()


def blake3hash(data: bytes) -> str:
	'''Returns a CryptoString-format BLAKE3-256 hash string of the passed data'''
	if data is None or data == '':
		return ''
	
	hasher = blake3.blake3() # pylint: disable=c-extension-no-member
	hasher.update(data)
	return "BLAKE3-256:" + base64.b85encode(hasher.digest()).decode()


def sha256hash(data: bytes) -> str:
	'''Returns a CryptoString-format SHA-256 hash string of the passed data'''
	if data is None or data == '':
		return ''
	
	hasher=hashlib.sha256()
	hasher.update(data)
	return "SHA-256:" + base64.b85encode(hasher.digest()).decode()


def sha3_256hash(data: bytes) -> str:
	'''Returns a CryptoString-format SHA3-256 hash string of the passed data'''
	if data is None or data == '':
		return ''
	
	hasher=hashlib.sha3_256()
	hasher.update(data)
	return "SHA3-256:" + base64.b85encode(hasher.digest()).decode()


def hashbuffer(data: bytes, algorithm: str) -> RetVal:
	'''Calculates a hash value for the memory buffer passed to it

	Parameters:
	  * data: an array of bytes
	  * algorithm: the hash algorithm to be used. This can be one of the following:
			- BLAKE2B-256 (default)
			- BLAKE3-256
			- SHA-256
			- SHA3-256
	
	Returns:
	  * hash: (CryptoString) the computed hash of the buffer
	'''
	if not data:
		return RetVal(ErrBadValue, 'bad path')
	
	hasher = None
	if algorithm == 'BLAKE2B-256':
		hasher = hashlib.blake2b(digest_size=32)
	elif algorithm == 'BLAKE3-256':
		hasher = blake3.blake3() # pylint: disable=c-extension-no-member
	elif algorithm == 'SHA-256':
		hasher = hashlib.sha256()
	elif algorithm == 'SHA3-256':
		hasher = hashlib.sha3_256()
	else:
		return RetVal('ErrUnsupported', 'unsupported algorithm')
	
	hasher.update(data)

	return RetVal().set_value('hash', 
		CryptoString(f"{algorithm}:{base64.b85encode(hasher.digest()).decode()}"))


def hashfile(path: str, algorithm='BLAKE2B-256') -> RetVal:
	'''Returns a RetVal containing the hash of the passed file in the 'hash' field. The algorithm 
	used may be specified, but defaults to BLAKE2B-256.'''
	if not path:
		return RetVal(ErrBadValue, 'bad path')
	
	hasher = None
	if algorithm == 'BLAKE2B-256':
		hasher = hashlib.blake2b(digest_size=32)
	elif algorithm == 'BLAKE3-256':
		hasher = blake3.blake3() # pylint: disable=c-extension-no-member
	elif algorithm == 'SHA-256':
		hasher = hashlib.sha256()
	elif algorithm == 'SHA3-256':
		hasher = hashlib.sha3_256()
	else:
		return RetVal(ErrBadValue, 'bad algorithm')
	
	try:
		handle = open(path, 'rb')
	except Exception as e:
		return RetVal().wrap_exception(e)

	filedata = handle.read(8192)
	while filedata:
		hasher.update(filedata)
		filedata = handle.read(8192)
	
	handle.close()

	return RetVal().set_value('hash', f"{algorithm}:{base64.b85encode(hasher.digest()).decode()}")
