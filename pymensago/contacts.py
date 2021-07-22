'''Module to implement contact management'''

from base64 import b85encode
import datetime
import os
import re
import tempfile
import time

from retval import ErrBadType, ErrBadValue, ErrNotFound, RetVal, ErrBadData 
from PIL import Image
from pymensago.utils import UUID

_long_date_pattern = re.compile(r'([1-3]\d{3})([0-1]\d)([0-3]\d)')
_short_date_pattern = re.compile(r'([0-1]\d)([0-3]\d)')

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


def _date_to_str(date: str) -> str:
	'''Converts the short form UTC date format to a localized string'''
	
	global _long_date_pattern
	global _short_date_pattern

	mon, day, year = (0,0,0)
	match = _long_date_pattern.match(date)
	if match:
		mon = int(date[4:6])
		day = int(date[6:8])
		year = int(date[0:4])
	else: 				
		match = _short_date_pattern.match(date)
		if match:
			mon = int(date[0:2])
			day = int(date[2:4])
	
	if not mon or not day:	
		return ''
	
	if year:
		return time.strftime("%B %d %Y",datetime.datetime(year, mon, day).timetuple())
	else:
		return time.strftime("%B %d",datetime.datetime(datetime.datetime.today().year, mon, 
							day).timetuple())


class Contact:
	'''Class to hold and manage contact information'''
	def __init__(self, data: dict=dict()):
		self.id = UUID()
		self.fields = data
		if len(data) == 0:
			self.empty()
	
	def __contains__(self, key):
		return key in self.fields or key in self.fields['Annotations']

	def __delitem__(self, key):
		del self.fields[key]

	def __getitem__(self, key):
		return self.fields[key]
	
	def __iter__(self):
		return self.fields.__iter__()
	
	def __setitem__(self, key, value):
		self.fields[key] = value

	def to_string(self) -> str:
		return _dumps(self)

	def empty(self):
		'''Empties the object of all values'''
		
		self.fields = {
			'Header': {
				'Version': '1.0',
				'EntityType': 'individual',
			},
			'Annotations': dict()
		}
		return self

	def count(self) -> int:
		'''Returns the number of contact fields contained by the return value'''
		
		return len(self.fields)

	def merge(self, contact, clobber=False) -> RetVal:
		'''Imports information from another contact, optionally overwriting'''
		if isinstance(contact, Contact):
			_merge_dict(self.fields, contact.fields, clobber)
			return RetVal()

		if isinstance(contact, dict):
			_merge_dict(self.fields, contact, clobber)
			return RetVal()
		
		return RetVal(ErrBadType, 'bad contact type')
	
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


def _dumps(c: Contact) -> str:
	'''Creates a pretty-printed string from a contact'''

	out = list()
	if c['Header']['EntityType'] == 'org':
		out.append('Type: Organization')
	else:
		out.append(c['Header']['EntityType'].capitalize())
	
	data = c.fields

	if 'FormattedName' in data:
		out.append(f"Name: {data['FormattedName']}")
	else:	
		# TODO: POSTDEMO: Localize generated FormattedName in Contact._dumps()
		temp = ''
		if 'GivenName' in data:
			temp = data['GivenName']		
		
		if 'FamilyName' in data:
			if temp:
				temp = temp + ' ' + data['FamilyName']
			else:
				temp = data['FamilyName']
		
		if 'Prefix' in data and temp:
			temp = f"{data['Prefix']} {temp}"
		
		if 'Suffixes' in data and temp:
			parts = [ temp ]
			parts.extend(data['Suffixes'])
			temp = ', '.join(parts)
		
		if temp:
			out.append(f"Name: {temp}")
	
	if 'Nicknames' in data:
		out.append("Nicknames: %s" %  ', '.join(data['Nicknames']))
	
	if 'Gender' in data:
		out.append(f"Gender: {data['Gender']}")
	
	if 'MailingAddresses' in data:
		for k,addr in data['MailingAddresses'].items():
			preferred = False
			addrname = k
			if k.endswith('*'):
				addrname = k[:-1]
				preferred = True
			
			if len(addr) < 1:
				continue
			
			# TODO: POSTDEMO: Localize address output
			if preferred:
				out.append(f"{addrname} Address (Preferred)")
			else:
				out.append(f"{addrname} Address")

			if 'StreetAddress' in addr:
				out.append('  ' + addr['StreetAddress'])
			if 'ExtendedAddress' in addr:
				out.append('  ' + addr['ExtendedAddress'])
			
			line = ''
			if 'Locality' in addr:
				line = '  ' + addr['Locality']
			
			if 'Region' in addr:
				if line:
					line = line + f", {addr['Region']}"
				else:
					line = '  ' + addr['Region']
			
			if 'PostalCode' in addr:
				if line:
					line = line + f" {addr['PostalCode']}"
				else:
					line = '  ' + addr['PostalCode']
			if line:
				out.append(line)

			if 'Country' in addr:
				out.append('  ' + addr['Country'])			


	if 'Phone' in data:
		for k,v in data['Phone'].items():
			if k.endswith('*'):
				out.append(f"Phone ({k[:-1]}, Preferred): {v}")
			else:
				out.append(f"Phone ({k}): {v}")

	if 'Mensago' in data:
		for addrname in data['Mensago'].keys():
			if 'UserID' in data['Mensago'][addrname]:
				if addrname.endswith('*'):
					out.append(f"Mensago ({data['Mensago'][addrname[:-1]]}, Preferred): "
								f"{data['Mensago'][addrname]['UserID']}/"
								f"{data['Mensago'][addrname]['Domain']} ")
				else:
					out.append(f"Mensago ({addrname}): {data['Mensago'][addrname]['UserID']}/"
								f"{data['Mensago'][addrname]['Domain']}")
			else:
				if addrname.endswith('*'):
					out.append(f"Mensago ({data['Mensago'][addrname[:-1]]}, Preferred): "
								f"{data['Mensago'][addrname]['Workspace']}/"
								f"{data['Mensago'][addrname]['Domain']} ")
				else:
					out.append(f"Mensago ({addrname}): {data['Mensago'][addrname]['Workspace']}/"
								f"{data['Mensago'][addrname]['Domain']}")

	if 'Anniversary' in data:
		datestr = _date_to_str(data['Anniversary'])
		if datestr:
			out.append(f"Anniversary: {datestr}")
	
	if 'Birthday' in data:
		datestr = _date_to_str(data['Birthday'])
		if datestr:
			out.append(f"Birthday: {datestr}")
	
	if 'Email' in data:
		for k,v in data['Email'].items():
			if k.endswith('*'):
				out.append(f"E-mail ({k[:-1]}, Preferred): {v}")
			else:
				out.append(f"E-mail ({k}): {v}")
	
	if 'Organization' in data:
		out.append(f"Organization: {data['Organization']}")
	
	if 'Title' in data:
		out.append(f"Title: {data['Title']}")

	if 'Categories' in data:
		out.append("Categories: %s" %  ', '.join(data['Categories']))

	if 'Website' in data:
		out.append(f"Website: {data['Website']}")
	
	if 'Languages' in data:
		# TODO: translate language abbreviations to full names
		out.append("Languages: %s" %  ', '.join(data['Languages']))
	
	if 'Attachments' in data:
		for item in data['Attachments']:
			out.append(f"Attachment: {item['Name']} / {item['Mime']}")
	
	if 'Notes' in data:
		out.append(f"Notes:\n{data['Notes']}")

	return '\n'.join(out)

# TODO: Create JSON schemas for contacts and the contact request message type
