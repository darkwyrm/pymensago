'''This module contains CryptoString, a class for bundling cryptographic keys and hashes with 
their algorithms in a text-friendly way. The algorithm name may be no longer than 24 characters 
and use only capital ASCII letters, numbers, and dashes.'''

import base64
import re

def encode85(b: bytes, pad=False) -> str:
	'''A string-oriented version of the b85encode function in the base64 module'''
	return base64.b85encode(b, pad).decode()

def decode85(b) -> bytes:
	'''A string-oriented version of the b85decode function in the base64 module'''
	return base64.b85decode(b)

class CryptoString:
	'''This class encapsulates code for working with strings associated with an algorithm. This 
	includes hashes and encryption keys.'''

	def __init__(self, string='', data=None):
		self.prefix = ''
		self.data = ''
		
		if data and isinstance(data, bytes):
			self.set_raw(string, data)
		else:
			self.set(string)
	
	def set(self, data: str) -> bool:
		'''Initializes the instance from data passed to it. The string is expected to follow the 
		format ALGORITHM:DATA, where DATA is assumed to be base85-encoded raw byte data'''

		if not data:
			self.prefix = ''
			self.data = ''
			return True

		if not is_cryptostring(data):
			return False

		self.prefix, self.data = data.split(':', 1)
		return True

	def set_raw(self, prefix: str, data: bytes) -> str:
		'''Initializes the instance to some raw data and a prefix. It returns the resulting string 
		with the encoded data. If an error occurs, such as if the prefix is not formatted 
		correctly, an empty string is returned.'''

		if not (prefix and data):
			return ''
		
		encoded = encode85(data)

		if not is_cryptostring(f"{prefix}:{encoded}"):
			return ''
		
		self.prefix = prefix
		self.data = encoded
		return f"{prefix}:{encoded}"

	def __str__(self):
		return f"{self.prefix}:{self.data}"
	
	def __eq__(self, b):
		return self.prefix == b.prefix and self.data == b.data

	def __ne__(self, b):
		return self.prefix != b.prefix or self.data != b.data

	def as_string(self):
		'''Returns the instance information as a string'''

		return f"{self.prefix}:{self.data}"
	
	def as_bytes(self) -> bytes:
		'''Returns the instance information as a byte string'''

		return b'%s:%s' % (self.prefix, self.data)
	
	def as_raw(self) -> bytes:
		'''Decodes the internal data and returns it as a byte string.'''

		return base64.b85decode(self.data)
	
	def is_valid(self) -> bool:
		'''Returns false if the prefix and/or the data is missing'''

		return self.prefix and self.data
	
	def make_empty(self):
		'''Makes the entry empty'''

		self.prefix = ''
		self.data = ''


def is_cryptostring(string: str) -> bool:
	'''Checks a string to see if it matches the CryptoString format'''
	
	m = re.match(r'^[A-Z0-9-]{1,24}:', string)
	if not m:
		return False

	parts = string.split(':', 1)
	if len(parts) != 2:
		return False

	try:
		_ = base64.b85decode(parts[1])
	except ValueError:
		return False
	
	return True
	