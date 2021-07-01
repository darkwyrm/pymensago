'''Module to implement contact management'''

from base64 import b85decode, b85encode
import os
import tempfile
import time

from retval import RetVal, ErrBadData 
from PIL import Image

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
		self.fields = {
			'Version': '1.0',
			'Sensitivity': 'private',
			'EntityType': 'individual',
			'Source': 'owner',
			'Update': 'no',
			'ID': '',
			'Name.Given': '',
			'Name.Family': ''
		}
		self.overlay = dict()
	
	def __contains__(self, key):
		return key in self.fields

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

	def fields(self) -> list:
		return self.fields

	def set_overlay_values(self, values: dict):
		'''Adds multiple dictionary fields to the object's contact info overlay.'''
		
		for k,v in values.items():
			if k in [ '_error', '_info' ]:
				return False
			self.overlay[k] = v
		
		return self
	
	def set_values(self, values: dict):
		'''Adds multiple dictionary fields to the object.'''
		
		for k,v in values.items():
			if k in [ '_error', '_info' ]:
				return False
			self.fields[k] = v
		
		return self
	
	def has_value(self, s: str) -> bool:
		'''Tests if a specific value field has been returned'''
		
		return s in self.fields
	
	def has_overlay(self, s: str) -> bool:
		'''Tests if a specific value field has been returned'''
		
		return s in self.overlay
	
	def empty(self):
		'''Empties the object of all values and clears any errors'''
		
		self.fields = dict()
		self.overlay = dict()
		return self

	def count(self) -> int:
		'''Returns the number of values contained by the return value'''
		
		return len(self.fields)

	def merge(self, contact, clobber=False):
		'''Imports information from another contact, optionally overwriting'''

		# This call enables recursion
		_merge_dict(self.fields, contact.fields, clobber)
	
	def merge_overlay(self, contact, clobber=False):
		'''Imports information from another contact into the instance's overlay, optionally 
		overwriting'''

		# This call enables recursion
		_merge_dict(self.overlay, contact.fields, clobber)
	
	def get_data(self, sensitivity: str) -> dict:
		'''Returns a dictionary containing all the data at the specified sensitivity level or less, 
		filling in data from the overlay as appropriate'''
		out = dict()

		# TODO: finish implementing Contact.get_data()
		return out

	def setphoto(self, path: str) -> RetVal:
		'''Given a file path, encode and store the data in the contact structure'''
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
		self.fields['Photo'] = {
			'Mime': filetype,
			'Data': b85encode(rawdata).decode()
		}

		if temppath:
			os.remove(temppath)

		return RetVal()


class PIP(Contact):
	'''Class to hold a personal information profile'''
	def __init__(self) -> None:
		super().__init__()
		self['PIPName'] = ''


class ContactRequest1:
	'''Class which sets up the initial message in the Contact Request processs'''
	def __init__(self) -> None:
		# These are just the required fields. Others, like a name, are... useful. 😏

		# TODO: finish implementing ContactRequest1
		self.fields = {
			"Type" : "sysmessage",
			"Subtype" : "contactreq.1",
			"Version" : "1.0",
			"From" : "",
			"To" : "",
			"Date" : time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()),
			"Sensitivity" : "Public",
			"EntityType" : "",
		}
	

# TODO: Create JSON schemas for contacts and the contact request message type
