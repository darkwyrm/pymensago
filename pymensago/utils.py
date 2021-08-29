'''Houses just some different utility functions'''

import re
from typing import Type
import uuid

from retval import RetVal, ErrBadValue

_uuid_pattern = re.compile(
			r"[\da-fA-F]{8}-[\da-fA-F]{4}-[\da-fA-F]{4}-[\da-fA-F]{4}-[\da-fA-F]{12}")
_domain_pattern = re.compile(r'([a-zA-Z0-9\-]+\.)+[a-zA-Z0-9\-]+')
_illegal_pattern = re.compile(r'[\s\\/\"A-Z]')


class UUID:
	'''Although there already is a uuid module, this class makes interaction easier by keeping it 
	as a string and ensuring that the formatting is always lowercase and has dashes, two Mensago 
	requirements to ensure consistency and fewer bugs.'''
	def __init__(self, obj='') -> None:
		self.value = str(obj)

	def is_valid(self) -> bool:
		'''Returns true if the instance is a valid UUID'''
		global _uuid_pattern
		return _uuid_pattern.match(self.value)
	
	def is_empty(self) -> bool:
		return self.value == ''
	
	def generate(self) -> str:
		'''Generates a random (v4) UUID and assigns it to the instance'''
		self.value = str(uuid.uuid4())
		return self.value

	def set(self, obj) -> str:
		'''Sets a value to the UUID. String case is squashed, leading and trailing whitespace is 
		removed, and the value is validated. set() returns the object's final internal value or 
		an empty string if an error occurred.'''
		
		self.value = str(obj).strip().casefold()
		if self.is_valid():
			return self.value
		return ''

	def __str__(self) -> str:
		return self.value
	
	def as_string(self) -> str:
		return self.value


class UserID:
	def __init__(self, obj='') -> None:
		self.value = str(obj)
		self.widflag = False

	def as_wid(self) -> UUID:
		'''Returns the user ID as a UUID or None if not a valid workspace ID'''
		if not self.widflag:
			return None
		
		# By not passing the value to the constructor and assigning directly we avoid making an
		# unnecessary (and expensive) regex call
		out = UUID()
		out.value = self.value
		return out

	def is_valid(self) -> bool:
		'''Returns true if the instance is a valid Mensago user ID'''
		global _illegal_pattern
		if not self.value or _illegal_pattern.search(self.value):
			return False

		return len(self.value) <= 64
	
	def is_wid(self) -> bool:
		'''Returns true if the UserID is actually a workspace ID'''
		
		return self.widflag
	
	def is_empty(self) -> bool:
		return self.value == ''

	def set(self, obj) -> str:
		'''Sets a value to the user ID. String case is squashed, leading and trailing whitespace is 
		removed, and the value is validated. set() returns the object's final internal value or 
		an empty string if an error occurred.'''
		
		self.value = str(obj).strip().casefold()
		if self.is_valid():
			global _uuid_pattern
		
			self.widflag = bool(_uuid_pattern.match(self.value))
			return self.value
		
		self.is_wid = False
		return ''

	def __str__(self) -> str:
		return self.value
	
	def as_string(self) -> str:
		return self.value


class Domain:
	def __init__(self, obj='') -> None:
		self.value = str(obj)

	def is_valid(self) -> bool:
		'''Returns true if the instance is a valid Internet domain'''
		global _domain_pattern
		return _domain_pattern.match(self.value)
	
	def is_empty(self) -> bool:
		return self.value == ''
	
	def set(self, obj) -> str:
		'''Sets a value to the domain. String case is squashed, leading and trailing whitespace is 
		removed, and the value is validated. set() returns the object's final internal value or 
		an empty string if an error occurred.'''
		
		self.value = str(obj).strip().casefold()
		if self.is_valid():
			return self.value
		return ''

	def __str__(self) -> str:
		return self.value
	
	def as_string(self) -> str:
		return self.value


class MAddress:
	'''Represents a Mensago address'''
	
	def __init__(self, addr = ''):
		self.id = UserID()
		self.id_type = 0
		self.domain = Domain()
		if addr:
			self.set(addr)

	def set(self, addr: str) -> RetVal:
		'''Validates input and assigns the address. If the given address is invalid, no change is 
		made to the object'''
		
		parts = addr.split('/')
		if len(parts) != 2 or not parts[0] or not parts[1]:
			return RetVal(ErrBadValue, 'bad address given')
		
		if not self.id.set(parts[0]):
			return RetVal(ErrBadValue, 'bad workspace ID')
		
		if not self.domain.set(parts[1]):
			return RetVal(ErrBadValue, 'bad domain')

		if self.id.is_wid():
			self.id_type = 1
		else:
			self.id_type = 2
		
		return RetVal()

	def __str__(self) -> str:
		return self.id.as_string() + '/' + self.domain.as_string()
	
	def is_valid(self) -> bool:
		return self.id_type in [1,2] and self.id.is_valid() and self.domain.is_valid()
	
	def is_empty(self) -> bool:
		return self.id.is_empty() and self.domain.is_empty()

	def as_string(self) -> str:
		return self.id.as_string() + '/' + self.domain.as_string()
	
	def set_from_userid(self, uid: UserID, domain: Domain) -> RetVal:
		if not (uid.is_valid() and domain.is_valid()):
			return RetVal(ErrBadValue, 'bad parameter')
		self.id = uid
		self.domain = domain
		if uid.is_wid():
			self.id_type = 1
		else:
			self.id_type = 2
		return RetVal()
	
	def set_from_wid(self, wid: UUID, domain: Domain) -> RetVal:
		if not (wid.is_valid() and domain.is_valid()):
			return RetVal(ErrBadValue, 'bad parameter')
		self.id.set(wid.as_string())
		self.domain = domain
		self.id_type = 1
		return RetVal()


class WAddress:
	'''Represents a workspace address'''

	def __init__(self, addr='') -> None:
		self.id = UUID()
		self.domain = Domain()
		if addr:
			self.set(addr)
	
	def is_empty(self) -> bool:
		return self.id.is_empty() and self.domain.is_empty()
		
	def set(self, addr: str) -> RetVal:
		'''Validates input and assigns the address. If the given address is invalid, no change is 
		made to the object'''
		
		parts = addr.split('/')
		if len(parts) != 2 or not parts[0] or not parts[1]:
			return RetVal(ErrBadValue, 'bad address given')
		
		if not self.id.set(parts[0]):
			return RetVal(ErrBadValue, 'bad workspace ID')
		
		if not self.domain.set(parts[1]):
			return RetVal(ErrBadValue, 'bad domain')

		return RetVal()

	def __str__(self) -> str:
		return self.id.as_string() + '/' + self.domain.as_string
	
	def is_valid(self) -> bool:
		return self.id and self.domain
	
	def as_string(self) -> str:
		return self.id.as_string() + '/' + self.domain.as_string()
	
	def as_maddress(self) -> MAddress:
		out = MAddress()
		out.set_from_wid(self.id, self.domain)
		return out


class Name:
	'''This class is for storing the user's name. It is required because there are so many possible 
	pieces of information for the user's name, including prefix, suffixes, and formatting.'''
	def __init__(self, given_name: str, family_name: str, prefix: str='', suffixes=None,
				additional: list=None, family_first: bool=False) -> None:
		self.formatted = ''
		self.given = ''
		self.family = ''
		self.prefix = ''
		self.suffixes = list()
		self.additional = list()
		self.family_first = family_first
		self.set(given_name, family_name, prefix, suffixes, additional, family_first)
	
	def set(self, given_name: str, family_name: str, prefix: str='', suffixes=None,
		additional=None, family_first: bool=None) -> str:
		'''This method sets the user's name fields based on information'''
		self.given = given_name
		self.family = family_name
		self.prefix = prefix
		
		if suffixes:
			if isinstance(suffixes, str):
				self.suffixes = [suffixes]
			elif isinstance(suffixes, list):
				self.suffixes = suffixes
			else:
				raise TypeError('suffixes must be list of strings or a single string')
		else:
			self.suffixes = list()
		
		if additional:
			if isinstance(additional, str):
				self.additional = [additional]
			elif isinstance(additional, list):
				self.additional = additional
			else:
				raise TypeError('additional names must be list of strings or a single string')
		else:
			self.additional = list()
		
		self.family_first = family_first
		self._generate_formatted()

		return self.formatted

	def _generate_formatted(self):
		parts = list()
		
		if self.family_first:
			if self.family:
				parts.append(self.family)
			if self.given:
				parts.append(self.given)
			if self.additional:
				parts.extend(self.additional)
		else:
			if self.given:
				parts.append(self.given)
			if self.additional:
				parts.extend(self.additional)
			if self.family:
				parts.append(self.family)

		base = ' '.join(parts)
		if not base:
			return ''

		full = list()		
		if self.prefix:
			full.append(self.prefix + ' ')
		full.append(base)

		if self.suffixes:
			full.append(', ' + ', '.join(self.suffixes))
		
		self.formatted = ''.join(full)
		return self.formatted


def validate_domain(indata: str) -> bool:
	'''Validates a string as being a valid domain'''

	return _domain_pattern.match(indata)


def size_as_string(size: int) -> str:
	'''Converts the integer to a string in SI units'''
	
	if size < 0:
		size = 0
	
	size_list = [
		(1_000_000_000_000_000, 'PB'),
		(1_000_000_000_000, 'TB'),
		(1_000_000_000, 'GB'),
		(1_000_000, 'MB'),
		(1_000, 'KB'),
	]

	for size_pair in size_list:
		if size >= size_pair[0]:
			return str(round(size / size_pair[0], 2)) + size_pair[1]
	
	return str(size) + ' bytes'
