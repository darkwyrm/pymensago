'''Houses just some different utility functions'''

import re
import uuid

from retval import RetVal, ErrBadValue

_uuid_pattern = re.compile(
			r"[\da-fA-F]{8}-[\da-fA-F]{4}-[\da-fA-F]{4}-[\da-fA-F]{4}-[\da-fA-F]{12}")
_domain_pattern = re.compile(r'([a-zA-Z0-9\-]+\.)+[a-zA-Z0-9\-]+')
_illegal_pattern = re.compile(r'[\s\\/\"A-Z]')


class UserID(str):
	def __init__(self, obj) -> None:
		super().__init__(obj)
	
	def is_valid(self) -> bool:
		'''Returns true if the instance is a valid Mensago user ID'''
		global _illegal_pattern
		if not self or _illegal_pattern.search(self):
			return False

		return len(self) <= 64
	
	def set(self, obj) -> str:
		'''Sets a value to the user ID. String case is squashed, leading and trailing whitespace is 
		removed, and the value is validated. set() returns the object's final internal value or 
		an empty string if an error occurred.'''
		
		self = str(obj).strip().casefold()
		if self.is_valid():
			return self
		return ''


class Domain(str):
	def __init__(self, obj) -> None:
		super().__init__(obj)
	
	def is_valid(self) -> bool:
		'''Returns true if the instance is a valid Internet domain'''
		global _domain_pattern
		return _domain_pattern.match(self)
	
	def set(self, obj) -> str:
		'''Sets a value to the domain. String case is squashed, leading and trailing whitespace is 
		removed, and the value is validated. set() returns the object's final internal value or 
		an empty string if an error occurred.'''
		
		self = str(obj).strip().casefold()
		if self.is_valid():
			return self
		return ''


class UUID(str):
	'''Although there already is a uuid module, this class makes interaction easier by keeping it 
	as a string and ensuring that the formatting is always lowercase and has dashes, two Mensago 
	requirements to ensure consistency and fewer bugs.'''
	def __init__(self, obj) -> None:
		super().__init__(obj)
	
	def is_valid(self) -> bool:
		'''Returns true if the instance is a valid UUID'''
		global _uuid_pattern
		return _uuid_pattern.match(self)
	
	def generate(self) -> None:
		'''Generates a random (v4) UUID and assigns it to the instance'''
		self = str(uuid.uuid4())

	def set(self, obj) -> str:
		'''Sets a value to the UUID. String case is squashed, leading and trailing whitespace is 
		removed, and the value is validated. set() returns the object's final internal value or 
		an empty string if an error occurred.'''
		
		self = str(obj).strip().casefold()
		if self.is_valid():
			return self
		return ''


class AddressBase:
	def __init__(self):
		self.id = ''
		self.id_type = 0
		self.domain = ''

	def __str__(self) -> str:
		return self.as_string()
	
	def as_string(self) -> str:
		return self.id + '/' + self.domain

	def is_valid(self) -> bool:
		return self.id_type in [1,2] and self.id and self.domain


class WAddress(AddressBase):
	'''Represents a workspace address'''

	def __init__(self, addr='') -> None:
		super.__init__()
		if addr:
			self.set(addr)
		
	def set(self, addr: str) -> RetVal:
		'''Validates input and assigns the address. If the given address is invalid, no change is 
		made to the object'''
		
		parts = addr.split('/')
		if len(parts) != 2 or not parts[0] or not parts[1]:
			return RetVal(ErrBadValue, 'bad address given')
		
		id_type = 0
		if not _uuid_pattern.match(parts[0]):
			return RetVal(ErrBadValue, 'bad workspace ID')

		self.id_type = 1
		self.id = parts[0].casefold()
		self.domain = parts[1].casefold()

		return RetVal()
	

class MAddress(AddressBase):
	'''Represents a Mensago address'''
	
	def __init__(self, addr = ''):
		self.id = ''
		self.id_type = 0
		self.domain = ''
		if addr:
			self.set(addr)

	def set(self, addr: str) -> RetVal:
		'''Validates input and assigns the address. If the given address is invalid, no change is 
		made to the object'''
		
		parts = addr.split('/')
		if len(parts) != 2 or not parts[0] or not parts[1]:
			return RetVal(ErrBadValue, 'bad address given')
		
		if len(parts[0]) > 64:
			return RetVal(ErrBadValue, 'user id too long')
		
		id_type = 0
		if _uuid_pattern.match(parts[0]):
			id_type = 1
		else:
			if _illegal_pattern.search(parts[0]):
				return RetVal(ErrBadValue, 'illegal characters in user id')
			id_type = 2

		if not _domain_pattern.match(parts[1]):
			return RetVal(ErrBadValue, 'bad domain')
		
		self.id_type = id_type
		self.id = parts[0].casefold()
		self.domain = parts[1].casefold()

		return RetVal()
	

def validate_uuid(indata: str) -> bool:
	'''Validates a UUID's basic format. Does not check version information.'''

	return _uuid_pattern.match(indata)

def validate_userid(uid: str) -> bool:
	'''Checks to make sure a user ID is valid'''

	if not uid:
		return False
	
	if re.findall(r'[\\\/\s"]', uid) or len(uid) >= 64:
		return False
	
	return True


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
		return RetVal(ErrBadValue, 'Bad workspace address')
	out = RetVal()
	out.set_value('wid', parts[0])
	out.set_value('domain', parts[1])
	return out
