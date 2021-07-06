'''Module to implement contact management'''

from base64 import b85encode
import os
import tempfile
import time

from retval import ErrBadType, ErrBadValue, RetVal, ErrBadData 
from PIL import Image
from pymensago.utils import UUID

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


class Contact:
	'''Class to hold and manage contact information'''
	def __init__(self):
		self.id = UUID()
		self.fields = dict()
		self.empty()
	
	def __contains__(self, key):
		return key in self.fields['Public'] or key in self.fields['Private'] \
			or key in self.fields['Secret'] or key in self.fields['Annotations']

	def __delitem__(self, key):
		del self.fields[key]

	def __getitem__(self, key):
		return self.fields[key]
	
	def __iter__(self):
		return self.fields.__iter__()
	
	def __setitem__(self, key, value):
		self.fields[key] = value

	# TODO: implement __str__ to dump a nicely-formatted multiline string of contact info
	# def __str__(self):
	# 	return '\n'.join(out)

	def empty(self):
		'''Empties the object of all values'''
		
		self.fields = {
			'Header': {
				'Version': '1.0',
				'EntityType': 'individual',
			},
			'Public': dict(),
			'Private': dict(),
			'Secret': dict(),
			'Annotations': dict()
		}
		return self

	def count(self) -> int:
		'''Returns the number of contact fields contained by the return value'''
		
		return len(self.fields['Public']) + len(self.fields['Private']) \
			+ len(self.fields['Secret']) + len(self.fields['Annotations'])

	def merge(self, contact, clobber=False) -> RetVal:
		'''Imports information from another contact, optionally overwriting'''
		if not isinstance(contact, Contact):
			return RetVal(ErrBadType, 'bad contact type')

		# This call enables recursion
		_merge_dict(self.fields, contact.fields, clobber)
		
		return RetVal()
		
	def get_data(self, privacy: str) -> dict:
		'''Returns a dictionary containing all the data at the specified sensitivity level or less, 
		filling in data from the overlay as appropriate'''
		out = dict()

		# TODO: finish implementing Contact.get_data()
		return out

	def setphoto(self, path: str, privacy: str) -> RetVal:
		'''Given a file path, encode and store the data in the contact structure'''

		if privacy not in ['Public', 'Private', 'Secret', 'Annotations']:
			return RetVal(ErrBadValue, 'bad privacy value')
		
		if path == '' and 'Photo' in self:
			del self['Photo']
			return RetVal()
			
		try:
			fileinfo = os.stat(path)
		except Exception as e:
			return RetVal().wrap_exception(e)
		
		if fileinfo.st_size > 512_000:
			return RetVal(ErrBadData, 'file too large')
		
		try:
			img = Image.open(path)
		except Exception as e:
			return RetVal().wrap_exception(e)
		
		# Now that we have the image opened, let's make sure it uses one of the three formats:
		# WEBP, JPEG, or PNG. If it isn't one of these three, convert it to WEBP. Then again, we'll
		# also convert PNG to save on file size. ;-)
		temppath = ''
		filetype = img.get_format_mimetype()
		if filetype not in ['image/jpeg', 'image/webp']:
			temphandle, temppath = tempfile.mkstemp(suffix='.webp')
			os.close(temphandle)
			try:
				img.save(temppath, 'WEBP', lossless=True, quality=3)
			except Exception as e:
				os.remove(temppath)
				return RetVal().wrap_exception(e)
			filetype = 'image/webp'
		img.close()

		fhandle = None
		if temppath:
			fhandle = open(temppath, 'rb')
		else:
			fhandle = open(path, 'rb')
		
		rawdata = fhandle.read()
		fhandle.close()
		self.fields[privacy]['Photo'] = {
			'Mime': filetype,
			'Data': b85encode(rawdata).decode()
		}

		if temppath:
			os.remove(temppath)

		return RetVal()

# TODO: Create JSON schemas for contacts and the contact request message type
