'''This modules houses basic data types and some utility functions

UUID, Domain, WAddress, and MAddress are used extensively by the reset of the
library. They are used primarily for validation and consistency in the API.
'''

import re
import time
import uuid

from retval import RetVal, ErrBadValue

_uuid_pattern = re.compile(
			r"[\da-fA-F]{8}-[\da-fA-F]{4}-[\da-fA-F]{4}-[\da-fA-F]{4}-[\da-fA-F]{12}")
_domain_pattern = re.compile(r'([a-zA-Z0-9\-]+\.)+[a-zA-Z0-9\-]+')
_illegal_pattern = re.compile(r'[\s\\/\"A-Z]')


class UUID:
	'''A string-based class for handling UUIDs.

	Notes:
		Although there already is a uuid module, this class makes interaction easier
		by keeping it as a string and ensuring that the formatting is always lowercase
		and has dashes, two Mensago requirements to ensure consistency and fewer bugs.
		The UUIDs themselves are also restricted to the randomly-generated type 4 UUIDs.
		This class exists mainly because User IDs are used for user-facing tasks and
		UUIDs are used internally almost exclusively.
	'''
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
		'''Sets the value for the UUID.
		
		Notes:
			String case is squashed, leading and trailing whitespace is removed, and the
			value is validated. set() returns the object's final internal value or an
			empty string if an error occurred.'''
		
		self.value = str(obj).strip().casefold()
		if self.is_valid():
			return self.value
		return ''

	def __str__(self) -> str:
		return self.value
	
	def as_string(self) -> str:
		return self.value


class UserID:
	'''A basic data type class for housing Mensago user IDs.

	Notes:
		User IDs on the Mensago platform must be no more than 64 Unicode code points. They
		may not contain whitespace, backslashes, forward slashes, or capital letters.
		Because of the relatively freeform format, it is possible for a workspace ID to
		also be a User ID. This class may contain either one.
	'''
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
		'''Returns true if the instance has no value'''
		return self.value == ''

	def set(self, obj) -> str:
		'''Sets a value for the user ID.
		
		Notes:
			String case is squashed, leading and trailing whitespace is removed, and the
			value is validated. set() returns the object's final internal value or an 
			empty string if an error occurred.'''
		
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
		'''Returns the value of the UserID as a string'''
		return self.value


class Domain:
	'''Basic data type representing an Internet domain.
	
	Notes:
		This class exists mainly to ensure valid domains are utilized across the library.
	'''
	def __init__(self, obj='') -> None:
		self.value = str(obj)

	def is_valid(self) -> bool:
		'''Returns true if the instance is a valid Internet domain'''
		global _domain_pattern
		return _domain_pattern.match(self.value)
	
	def is_empty(self) -> bool:
		'''Returns true if the instance has no value'''
		return self.value == ''
	
	def set(self, obj) -> str:
		'''Sets a value for the domain.
		
		Notes:
			String case is squashed, leading and trailing whitespace is removed, and the
			value is validated. set() returns the object's final internal value or an empty
			string if an error occurred.'''
		
		self.value = str(obj).strip().casefold()
		if self.is_valid():
			return self.value
		return ''

	def __str__(self) -> str:
		return self.value
	
	def as_string(self) -> str:
		'''Returns the value of the Domain as a string'''
		return self.value


class MAddress:
	'''Represents a full Mensago address.
	
	Notes:
		Like the UserID, this class can represent a standard alphabetic Mensago address
		or a workspace address. It simplifies validating an address and ensures
		consistently-valid data is used across the library.
	'''
	
	def __init__(self, addr = ''):
		self.id = UserID()
		self.id_type = 0
		self.domain = Domain()
		if addr:
			self.set(addr)

	def set(self, addr: str) -> RetVal:
		'''Sets a value for the object from a string.
		
		Returns:
		  * no additional fields

		Notes:
			Validates input, adjusts formatting, and assigns the address. Formatting is
			enforced as described for Domain and UserID.
		'''
		
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
		'''Returns true if the address is valid'''
		return self.id_type in [1,2] and self.id.is_valid() and self.domain.is_valid()
	
	def is_empty(self) -> bool:
		'''Returns true if the address has no value'''
		return self.id.is_empty() and self.domain.is_empty()

	def as_string(self) -> str:
		'''Returns the value of the address as a string'''
		return self.id.as_string() + '/' + self.domain.as_string()
	
	def set_from_userid(self, uid: UserID, domain: Domain) -> RetVal:
		'''Sets the value of the instance from separate components

		Parameters:
		  * uid: UserID instance for the username
		  * domain: Domain instance for the address domain
		
		Returns:
		  * No additional fields
		'''
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
		'''Sets the value of the instance from separate components

		Parameters:
		  * wid: UUID instance for the workspace ID
		  * domain: Domain instance for the address domain
		
		Returns:
		  * No additional fields
		'''
		if not (wid.is_valid() and domain.is_valid()):
			return RetVal(ErrBadValue, 'bad parameter')
		self.id.set(wid.as_string())
		self.domain = domain
		self.id_type = 1
		return RetVal()


class WAddress:
	'''Represents a workspace address.
	
	Notes:
		This class simplifies validating an address and ensures	consistently-valid data is
		used across the library.
	'''

	def __init__(self, addr='') -> None:
		self.id = UUID()
		self.domain = Domain()
		if addr:
			self.set(addr)
	
	def is_empty(self) -> bool:
		'''Returns true if the instance has no value'''
		return self.id.is_empty() and self.domain.is_empty()
		
	def set(self, addr: str) -> RetVal:
		'''Sets a value for the object from a string.
		
		Returns:
		  * no additional fields

		Notes:
			Validates input, adjusts formatting, and assigns the address. Formatting is
			enforced as described for Domain and UUID.
		'''
		
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
		'''Returns true if the instance is a valid workspace address'''
		return self.id and self.domain
	
	def as_string(self) -> str:
		'''Returns the value of the instance as a string'''
		return self.id.as_string() + '/' + self.domain.as_string()
	
	def as_maddress(self) -> MAddress:
		'''Returns an MAddress instance which has the same address value'''
		out = MAddress()
		out.set_from_wid(self.id, self.domain)
		return out


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


def generate_filename(size: int) -> str:
	'''Generates a unique filename for a file using the Mensago filename template.
	
	Notes:
		Mensago filenames are intended to convey no information about its contents. It
		consists of a UUID, the size of the file, and a timestamp. If None is passed
		as the file size, the file name only consists of a UUID and timestamp.
	'''
	parts = [ str(uuid.uuid4()) ]
	
	if size is not None:
		parts.append(str(size))
	
	parts.append(time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()))
	
	return '.'.join(parts)
