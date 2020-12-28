'''This module contains CryptoString, a class for bundling cryptographic keys and hashes with 
their algorithms in a text-friendly way. The algorithm name may be no longer than 15 characters 
and use only capital ASCII letters, numbers, and dashes.'''

import base64

from pyanselus.retval import RetVal, BadData, BadParameterValue

class CryptoString:
	'''This class encapsulates code for working with strings associated with an algorithm. This 
	includes hashes and encryption keys.'''
	def __init__(self, data=''):
		if data:
			self.set(data)
		else:
			self.prefix = ''
			self.data = ''
	
	def set(self, data: str) -> RetVal:
		'''Initializes the instance from data passed to it. The string is expected to follow the 
		format ALGORITHM:DATA, where DATA is assumed to be base85-encoded raw byte data'''
		
		self.prefix = self.data = ''

		parts = data.split(':', 1)
		if len(parts) == 1:
			return RetVal(BadParameterValue, 'data is not colon-separated')
		
		# TODO: Enforce prefix characters and length
		
		try:
			_ = base64.b85decode(parts[1])
		except:
			return RetVal(BadParameterValue, 'error decoding data')
		
		self.prefix = parts[0]
		self.data = parts[1]
		return RetVal()

	def set_bytes(self, data: bytes) -> RetVal:
		'''Initializes the instance from a byte string'''
		try:
			return self.set(data.decode())
		except Exception as e:
			return RetVal(BadData, e)
	
	def __str__(self):
		return '%s:%s' % (self.prefix, self.data)
	
	def __eq__(self, b):
		return self.prefix == b.prefix and self.data == b.data

	def __ne__(self, b):
		return self.prefix != b.prefix or self.data != b.data

	def as_string(self):
		'''Returns the instance information as a string'''
		return str(self)
	
	def as_bytes(self) -> bytes:
		'''Returns the instance information as a byte string'''
		return b'%s:%s' % (self.prefix, self.data)
	
	def raw_data(self) -> bytes:
		'''Decodes the internal data and returns it as a byte string.'''
		return base64.b85decode(self.data)
	
	def is_valid(self) -> bool:
		'''Returns false if the prefix and/or the data is missing'''
		return self.prefix and self.data
	
	def make_empty(self):
		'''Makes the entry empty'''
		self.prefix = ''
		self.data = ''
