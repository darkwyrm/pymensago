# Yet another iteration in the saga to find the right storage format for contact information
# JSON is an object notation format, so why not actually *use* objects instead of just lists
# and dictionaries?

FIELD_VALUE = 0
FIELD_LIST = 1
FIELD_DICT = 2

class Field:
	def __init__(self, name = '') -> None:
		self.name = ''
		self.value = ''
		self.type = FIELD_VALUE
		self.is_container = False
	
	def __str__(self) -> str:
		return f"{self.name}:{self.value}"


class FieldContainer (Field):
	def __init__(self, name) -> None:
		super().__init__(name=name)
		self.is_container = True
	
	def get_iterator():
		'''Returns an iterator to the data in the field container'''
		return None

	def count() -> int:
		'''Returns the number of items in the container'''
		return 0
	
	def merge(self, o: object) -> bool:
		'''Merges another FieldContainer, list, or dictionary into the object'''
		return False


class FieldList (FieldContainer):
	def __init__(self, name) -> None:
		super().__init__(name)
		self.values = list()
	
	def __contains__(self, key):
		return key in self.values

	def __delitem__(self, key):
		del self.values[key]

	def __getitem__(self, key):
		return self.values[key]
	
	def __iter__(self):
		return self.values.__iter__()
	
	def __setitem__(self, key, value):
		self.values[key] = value
	
	def __add__(self, o: object):
		if isinstance(o, list):
			return self.values + o
		
		raise TypeError(f"Adding a {type(o)} to a FieldList is not supported")
	
	def __eq__(self, o: object) -> bool:
		return self.values == o
	
	def __ne__(self, o: object) -> bool:
		return self.values != o
	
	def merge(self, o: object) -> bool:
		if isinstance(o, list):
			self.values.extend(o)
		elif isinstance(o, FieldList):
			self.values.extend(o.values)
		else:
			self.values.append(o)


class FieldDict (FieldContainer):
	def __init__(self, name) -> None:
		super().__init__(name)
	
	# [] operator
	# == operator
	# merge()
	# __str__()


class Contact:
	def __init__(self) -> None:
		self.info = FieldDict()
		self.annotations = FieldDict()
	# save()
	# load()
