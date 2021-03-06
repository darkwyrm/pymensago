'''This module contains quick access to different hash functions'''

import base64
import hashlib

import blake3

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
