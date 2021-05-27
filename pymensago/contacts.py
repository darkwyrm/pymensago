'''Module to implement contact management'''

from base64 import b85decode, b85encode
import os
import tempfile

from pymensago.retval import BadData, ExceptionThrown, RetVal
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
	
	def setphoto(self, path: str) -> RetVal:
		'''Given a file path, encode and store the data in the contact structure'''
		if path == '' and 'Photo' in self:
			del self['Photo']
			return RetVal()
			
		try:
			fileinfo = os.stat(path)
		except Exception as e:
			return RetVal(ExceptionThrown, e)
		
		if fileinfo.st_size > 512_000:
			return RetVal(BadData, 'file too large')
		
		try:
			img = Image.open(path)
		except Exception as e:
			return RetVal(ExceptionThrown, e)
		
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
				return RetVal(ExceptionThrown, e)
			filetype = 'image/webp'
		img.close()

		fhandle = None
		if temppath:
			fhandle = open(temppath, 'rb')
		else:
			fhandle = open(path, 'rb')
		
		rawdata = fhandle.read()
		fhandle.close()
		self['Photo'] = {
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


