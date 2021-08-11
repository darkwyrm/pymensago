# Yet another iteration in the saga to find the right storage format for contact information
# JSON is an object notation format, so why not actually *use* objects instead of just lists
# and dictionaries?

import copy
import json

FIELD_VALUE = 0
FIELD_LIST = 1
FIELD_DICT = 2


class Field:
	def __init__(self, name = '') -> None:
		self.name = name
		self.value = ''
		self.type = FIELD_VALUE
		self.is_container = False
	
	def __str__(self) -> str:
		if self.name:
			return f'{json.dumps(str(self.name))}:{json.dumps(str(self.value))}'
		return json.dumps(str(self.value))
	
	def as_string(self) -> str:
		return str(self)


class FieldContainer (Field):
	def __init__(self, name) -> None:
		super().__init__(name=name)
		self.is_container = True
	
	def set(self, o: object):
		'''Sets the container to the specified value'''
		pass
	
	def get_iterator(self):
		'''Returns an iterator to the data in the field container'''
		return None

	def count(self) -> int:
		'''Returns the number of items in the container'''
		return 0
	
	def merge(self, o: object) -> bool:
		'''Merges another FieldContainer, list, or dictionary into the object'''
		return False


class FieldList (FieldContainer):
	def __init__(self, name) -> None:
		super().__init__(name)
		self.type = FIELD_LIST
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
			out = copy.deepcopy(self)
			out.values.extend(o)
			return out
		elif isinstance(o, FieldList):
			out = copy.deepcopy(self)
			out.values.extend(o.values)
			return out
		
		out = copy.deepcopy(self)
		out.values.append(o)
		return out
	
	def __eq__(self, o: object) -> bool:
		return self.values == o
	
	def __ne__(self, o: object) -> bool:
		return self.values != o
	
	def __str__(self) -> str:
		if len(self.values):
			return json.dumps(self.values, separators=(',',':'))

		return '[]'
	
	def set(self, o: object):
		'''Sets the value of the list to contain the contents of the value passed to it'''
		if isinstance(o, list):
			self.values = o
		elif isinstance(o, FieldList):
			self.values = o.values
		else:
			self.values = [ str(o) ]
	
	def as_string(self) -> str:
		return str(self)
	
	def get_iterator(self):
		'''Returns an iterator to the data in the field container'''
		return self.values.__iter__()

	def count(self) -> int:
		'''Returns the number of items in the container'''
		return len(self.values)
	
	def merge(self, o: object) -> bool:
		if isinstance(o, list):
			self.values.extend(o)
		elif isinstance(o, FieldList):
			self.values.extend(o.values)
		else:
			self.values.append(o)
		return True


class FieldDict (FieldContainer):
	def __init__(self, name) -> None:
		super().__init__(name)
		self.type = FIELD_DICT
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
		if isinstance(o, dict):
			out = self
			for k,v in o.items():
				out.values[k] = v
			return out
		elif isinstance(o, FieldDict):
			out = self
			for k,v in o.values.items():
				out.values[k] = v
			return out
		
		raise TypeError(f"Adding a {type(o)} to a FieldDict is not supported")
	
	def __eq__(self, o: object) -> bool:
		return self.values == o
	
	def __ne__(self, o: object) -> bool:
		return self.values != o
	
	def __str__(self) -> str:
		if len(self.values):
			return json.dumps(self.values,separators=(',',':'))

		return '{}'
	
	def set(self, o: object):
		'''Sets the value of the list to contain the contents of the value passed to it'''
		if isinstance(o, dict):
			self.values = o
		elif isinstance(o, FieldDict):
			self.values = o.values
		
		raise TypeError(f"Setting a FieldDict to a {type(o)} is not supported")
	
	def as_string(self) -> str:
		return str(self)
	
	def get_iterator(self):
		'''Returns an iterator to the data in the field container'''
		return self.values.__iter__()

	def count(self) -> int:
		'''Returns the number of items in the container'''
		return len(self.values)
	
	def merge(self, o: object) -> bool:
		if isinstance(o, dict):
			for k,v in o.items():
				self.values[k] = v
			return True
		elif isinstance(o, FieldList):
			for k,v in o.values.items():
				self.values[k] = v
			return True
		else:
			self.values.append(o)
		
		raise TypeError(f"Merging a {type(o)} into a FieldDict is not supported")


class Contact:
	def __init__(self) -> None:
		self.info = FieldDict()
		self.annotations = FieldDict()
	# save()
	# load()

