'''Houses just some different utility functions'''

import re

from pymensago.retval import RetVal, BadParameterValue

_uuid_pattern = re.compile(
			r"[\da-fA-F]{8}-?[\da-fA-F]{4}-?[\da-fA-F]{4}-?[\da-fA-F]{4}-?[\da-fA-F]{12}")
_domain_pattern = re.compile(r'([a-zA-Z0-9]+\.)+[a-zA-Z0-9]+')
_illegal_pattern = re.compile(r'[\s\\/\"]')


class MAddress:
	'''Represents a Mensago or workspace address'''
	
	def __init__(self, addr = ''):
		self.id = ''
		self.id_type = 0
		self.domain = ''

	def __str__(self) -> str:
		return self.id + '/' + self.domain

	def set(self, addr: str) -> RetVal:
		'''Validates input and assigns the address. If the given address is invalid, no change is 
		made to the object'''
		
		parts = addr.split('/')
		if len(parts) != 2 or not parts[0] or not parts[1]:
			return RetVal(BadParameterValue, 'bad address given')
		
		if len(parts[0]) > 64:
			return RetVal(BadParameterValue, 'user id too long')
		
		id_type = 0
		if _uuid_pattern.match(parts[0]):
			id_type = 1
		else:
			if _illegal_pattern.search(parts[0]):
				return RetVal(BadParameterValue, 'illegal characters in user id')
			id_type = 2

		if not _domain_pattern.match(parts[1]):
			return RetVal(BadParameterValue, 'bad domain')
		
		self.id_type = id_type
		self.id = parts[0].casefold()
		self.domain = parts[1].casefold()

		return RetVal()
	
	def is_valid(self) -> bool:
		return self.id_type in [1,2] and self.id and self.domain
	

def validate_uuid(indata: str) -> bool:
	'''Validates a UUID's basic format. Does not check version information.'''

	return _uuid_pattern.match(indata)


def validate_domain(indata: str) -> bool:
	'''Validates a string as being a valid domain'''

	return _domain_pattern.match(indata)


def split_address(address):
	'''Splits an Mensago numeric address into its two parts.'''
	parts = address.split('/')
	if len(parts) != 2 or \
		not parts[0] or \
		not parts[1] or \
		not validate_uuid(parts[0]):
		return RetVal(BadParameterValue, 'Bad workspace address')
	out = RetVal()
	out.set_value('wid', parts[0])
	out.set_value('domain', parts[1])
	return out
