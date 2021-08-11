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


class FieldList (FieldContainer):
	def __init__(self, name) -> None:
		super().__init__(name)
	
	# [] operator
	# == operator
	# merge()
	# __str__()


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
