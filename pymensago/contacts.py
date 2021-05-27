'''Module to implement contact management'''

class Contact(dict):
	'''Class to hold and manage contact information'''
	def __init__(self) -> None:
		self['Version'] = '1.0'
		self['Sensitivity'] = 'private'
		self['EntityType'] = 'individual'
		self['Source'] = 'owner'
		self['Update'] = 'no'
		self['ID'] = ''
		self['Name'] = { 'Given': '', 'Family': ''	}
	
	def merge(self, contact, clobber=False):
		'''Imports information from another contact, optionally overwriting'''

		# This call enables recursion
		_merge_dict(self, contact, clobber)
	

class PIP(Contact):
	'''Class to hold a personal information profile'''
	def __init__(self) -> None:
		super().__init__()
		self['PIPName'] = ''


def _merge_dict(dest: dict, source: dict, clobber: bool) -> None:
	for k in source:
		if isinstance(source[k], dict):
			if k not in dest:
				dest[k] = {}
			_merge_dict(dest[k], source[k], clobber)
		else:
			if k not in dest or (isinstance(source[k],str) and not dest[k]) \
				or (clobber and k in dest):
				dest[k] = source[k]

