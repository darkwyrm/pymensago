'''Module to implement contact management'''

from base64 import b85encode
import datetime
import os
import re
import tempfile
import time

from retval import ErrBadType, ErrBadValue, ErrNotFound, ErrUnimplemented, RetVal, ErrBadData 
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

	def set_user_field(self, fieldname: str, value: str) -> RetVal:
		'''Sets the contact information field for the user to the specified value.'''
		if not fieldname or not value:
			return RetVal(ErrBadValue)
		
		parts = fieldname.split('.')
		for part in parts:
			if not part:
				return RetVal(ErrBadValue, 'bad field name')
		
		if len(parts) == 1:
			self.fields[parts[0]] = value
			return RetVal()
		
		elif len(parts) == 2:
			# This section handles top-level fields which are dictionaries or lists of strings
			# Adding an empty container as a field is not supported because empty data containers
			# are not supported.

			# Based on the values in parts, determined whether or not the first level needs to be
			# a list or a dictionary

			# keys have to either be an integer index (for a list) or a string
			keytype = 'i'
			try:
				key = int(parts[1])
			except:
				keytype = 's'
			
			if not (isinstance(key, int) or isinstance(key, str)):
				return RetVal(ErrBadType, 'second level key must be an integer or string')
			
			# If the top-level container exists, make sure the its type matches the key type
			if parts[0] in self.fields:
				if not (keytype == 'i' and isinstance(self.fields[parts[0]], list) 
						or (keytype == 's' and isinstance(self.fields[parts[0], dict]))):
					return RetVal(ErrBadType, 'second level key does not match container type')
			else:
				if keytype == 'i':
					self.fields[parts[0]] = list()
				else:
					self.fields[parts[0]] = dict()

				if keytype == 'i':
					if key < 0 or key >= len(self.fields[parts[0]]):
						self.fields[parts[0]].append(value)
					else:
						self.fields[parts[0]] = value
				else:
					self.fields[parts[0]] = value

			return RetVal()
		
		elif len(parts) == 3:
			# As of this writing, the schema only utilizes top-level fields which are lists of
			# dictionaries, but we will write this code to handle lists or dictionaries nested
			# inside a list or dictionary in case the schema changes at some point.
			# keys have to either be an integer index (for a list) or a string
			keytype = 'i'
			try:
				key = int(parts[1])
			except:
				keytype = 's'
			
			if not (isinstance(key, int) or isinstance(key, str)):
				return RetVal(ErrBadType, 'second level key must be an integer or string')

			keytype2 = 'i'
			try:
				key2 = int(parts[2])
			except:
				keytype2 = 's'
			
			if not (isinstance(key2, int) or isinstance(key2, str)):
				return RetVal(ErrBadType, 'third level key must be an integer or string')

			# If the top-level container exists, make sure the its type matches the key type
			if parts[0] in self.fields:
				if not (keytype == 'i' and isinstance(self.fields[parts[0]], list) 
						or (keytype == 's' and isinstance(self.fields[parts[0], dict]))):
					return RetVal(ErrBadType, 'second level key does not match container type')
			else:
				if keytype == 'i':
					self.fields[parts[0]] = list()
				else:
					self.fields[parts[0]] = dict()

			# If the second-level container exists, make sure the its type matches that of the
			# third-level key
			if parts[1] in self.fields[parts[0]]:
				if not (keytype2 == 'i' and isinstance(self.fields[parts[0]][parts[1]], list) 
						or (keytype2 == 's' and isinstance(self.fields[parts[0][parts[1]], dict]))):
					return RetVal(ErrBadType, 'third level key does not match container type')
			else:
				if keytype2 == 'i':
					self.fields[parts[0]][parts[1]] = list()
				else:
					self.fields[parts[0]][parts[1]] = dict()


			if keytype2 == 'i':
				if key2 < 0 or key2 >= len(self.fields[parts[0]][parts[1]]):
					self.fields[parts[0]][parts[1]].append(value)
				else:
					self.fields[parts[0]][parts[1]] = value
			else:
				self.fields[parts[0]][parts[1]] = value

			return RetVal()
			
		return RetVal(ErrBadValue, "bad field name")


	def delete_user_field(self, fieldname: str) -> RetVal:
		'''Deletes the specified contact information field for the user'''
		
		if not fieldname:
			return RetVal(ErrBadValue)
		
		parts = fieldname.split('.')
		if len(parts) == 1:
			if parts[0] in self.fields:
				del self.fields[parts[0]]
			return RetVal()
		
		elif len(parts) == 2:
			if isinstance(self.fields[parts[0]], str):
				return RetVal(ErrBadType, f"{parts[0]} is not a container")
			
			if isinstance(self.fields[parts[0]], list):
				# Field is a list of dictionaries. No other usage for lists exists in the schema
				# for contacts
				try:
					index = int(parts[1])
				except:
					return RetVal(ErrBadValue, "bad list index")
				
				if index >= 0 and index < len(self.fields[parts[0]]):
					del self.fields[parts[0]][index]
					return RetVal()
							
			if isinstance(self.fields[parts[0]], dict) and parts[0] in self.fields:
				# Field is a dictionary of string values
				del self.fields[parts[0]][parts[1]]
				return RetVal()
		
		elif len(parts) == 3:
			# This applies to deleting a field within a list of dictionaries
			if isinstance(self.fields[parts[0]], str):
				return RetVal(ErrBadType, f"{parts[0]} is not a container")
			
			if not isinstance(self.fields[parts[0]], list):
				return RetVal(ErrBadData, f"schema expects a {'.'.join(parts[0:2])} to be a list")
			
			try:
				index = int(parts[1])
			except:
				return RetVal(ErrBadValue, "bad list index")
			
			if index < 0 or index >= len(self.fields[parts[0]]):
				return RetVal(ErrBadValue, "list index out of range")
							
			if isinstance(self.fields[parts[0]][index], dict) \
				and parts[2] in self.fields[parts[0]][index]:
				
				# Field is a dictionary of string values
				del self.fields[parts[0]][index][parts[2]]
				return RetVal()
			
		return RetVal(ErrBadValue, "bad field name")

	def annotate(self, wid: UUID, fieldname: str) -> RetVal:
		'''Adds an annotation for a contact'''
		# TODO: Implement annotate()
		pass

	def delete_annotation(self, wid: UUID, fieldname: str) -> RetVal:
		'''Deletes an annotation for a contact'''
		# TODO: Implement delete_annotation()
		pass


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
		for addr in data['MailingAddresses']:
			
			if len(addr) < 1:
				continue
			
			if 'Preferred' in addr and (addr['Preferred'].casefold() == 'yes' \
										or addr['Preferred'].casefold() == 'true'):
				preferred = True
			else:
				preferred = False
			
			# TODO: POSTDEMO: Localize address output
			if preferred:
				out.append(f"{addr['Label']} Address (Preferred)")
			else:
				out.append(f"{addr['Label']} Address")

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
		for pn in data['Phone']:
			if 'Preferred' in pn and (pn['Preferred'].casefold() == 'yes' \
										or pn['Preferred'].casefold() == 'true'):
				out.append(f"Phone ({pn['Label']}, Preferred): {pn['Number']}")
			else:
				out.append(f"Phone ({pn['Label']}): {pn['Number']}")

	if 'Mensago' in data:
		for addr in data['Mensago']:
			if 'Preferred' in addr and (addr['Preferred'].casefold() == 'yes' \
										or addr['Preferred'].casefold() == 'true'):
				preferred = True
			else:
				preferred = False
			
			if 'UserID' in addr:
				if preferred:
					out.append(f"Mensago ({addr['Label']}, Preferred): "
								f"{addr['UserID']}/{addr['Domain']} ")
				else:
					out.append(f"Mensago ({addr['Label']}): {addr['UserID']}/{addr['Domain']}")
			else:
				if preferred:
					out.append(f"Mensago ({addr['Label']}, Preferred): "
								f"{addr['UserID']}/{addr['Domain']} ")
				else:
					out.append(f"Mensago ({addr['Label']}): {addr['Workspace']}/{addr['Domain']}")

	if 'Anniversary' in data:
		datestr = _date_to_str(data['Anniversary'])
		if datestr:
			out.append(f"Anniversary: {datestr}")
	
	if 'Birthday' in data:
		datestr = _date_to_str(data['Birthday'])
		if datestr:
			out.append(f"Birthday: {datestr}")
	
	if 'Email' in data:
		for addr in data['Phone']:
			if 'Preferred' in addr and (addr['Preferred'].casefold() == 'yes' \
										or addr['Preferred'].casefold() == 'true'):
				out.append(f"E-mail ({addr['Label']}, Preferred): {addr['Address']}")
			else:
				out.append(f"E-mail ({addr['Label']}): {addr['Address']}")
	
	if 'Organization' in data:
		out.append(f"Organization: {data['Organization']}")
	
	if 'Title' in data:
		out.append(f"Title: {data['Title']}")

	if 'Categories' in data:
		out.append("Categories: %s" %  ', '.join(data['Categories']))

	if 'Website' in data:
		for k,v in data['Website'].items():
			out.append(f"Website ({k}): {v}")
	
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
