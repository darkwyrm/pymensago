'''Module to implement contact management'''

from base64 import b85encode
import datetime
import os
import re
import tempfile
import time

from retval import ErrBadType, ErrBadValue, ErrNotFound, ErrOutOfRange, ErrUnimplemented, RetVal, ErrBadData 
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
	
	def get_field(self, fieldname: str) -> RetVal:
		'''Gets the value of the contact information field specified.'''
		return self._get_field(self.fields, fieldname)

	def set_field(self, fieldname: str, value: str) -> RetVal:
		'''Sets the contact information field for the user to the specified value.'''
		return self._set_field(self.fields, fieldname, value)

	def delete_field(self, fieldname: str) -> RetVal:
		'''Deletes the specified contact information field for the user'''
		return self._delete_field(self.fields, fieldname)

	def get_annotation(self, fieldname: str) -> RetVal:
		'''Gets the value of the annotation specified.'''

		if 'Annotations' not in self.fields:
			self.fields['Annotations'] = dict()
			return RetVal(ErrNotFound)
		return self._get_field(self.fields['Annotations'], fieldname)

	def annotate(self, fieldname: str, value: str) -> RetVal:
		'''Adds an annotation'''
		
		if 'Annotations' not in self.fields:
			self.fields['Annotations'] = dict()
		return self._set_field(self.fields['Annotations'], fieldname, value)

	def delete_annotation(self, fieldname: str) -> RetVal:
		'''Deletes an annotation for a contact'''
		
		if 'Annotations' not in self.fields:
			self.fields['Annotations'] = dict()
			return RetVal(ErrNotFound)
		return self._delete_field(self.fields['Annotations'], fieldname)

	def _set_field(self, target: dict, fieldname: str, value: str) -> RetVal:
		'''Internal method which sets a field in a dictionary. This does all the heavy lifting 
		when working with set_field() or annotate()'''
		if not fieldname or not value:
			return RetVal(ErrBadValue)
		
		if fieldname == 'Photo':
			return self._setphoto(target, value)

		parts = fieldname.split('.')
		for part in parts:
			if not part:
				return RetVal(ErrBadValue, 'bad field name')
		
		if len(parts) == 1:
			target[parts[0]] = value
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
				key = parts[1]
			
			if not (isinstance(key, int) or isinstance(key, str)):
				return RetVal(ErrBadType, 'second level key must be an integer or string')
			
			# If the top-level container exists, make sure the its type matches the key type
			if parts[0] in target:
				if not (keytype == 'i' and isinstance(target[parts[0]], list) 
						or (keytype == 's' and isinstance(target[parts[0]], dict))):
					return RetVal(ErrBadType, 'second level key does not match container type')
			else:
				if keytype == 'i':
					target[parts[0]] = list()
				else:
					target[parts[0]] = dict()

			if keytype == 'i':
				if key < 0:
					target[parts[0]].append(value)
				elif key >= len(target[parts[0]]):
					return RetVal(ErrOutOfRange)
				else:
					target[parts[0]][key] = value
			else:
				target[parts[0]][key] = value

			return RetVal()
		
		elif len(parts) == 3:
			# As of this writing, the schema only utilizes top-level fields which are lists of
			# dictionaries, but we will write this code to handle lists or dictionaries nested
			# inside a list or dictionary in case the schema changes at some point.
			# keys have to either be an integer index (for a list) or a string

			# This variable isn't absolutely necessary, but it makes the code clearer
			field = parts[0]

			# Set the type and value of the middle field index
			indextype = 'i'
			try:
				index = int(parts[1])
			except:
				indextype = 's'
				index = parts[1]

			# Set the type and value of the third field index
			subkeytype = 'i'
			try:
				subkey = int(parts[2])
			except:
				subkeytype = 's'
				subkey = parts[2]

			# Now that we have the middle index, check that the field exists
			if field in target:
				# Field exists, does the index match its type?
				if indextype == 'i' and type(target[field]).__name__ != 'list' \
					or indextype == 's' and type(target[field]).__name__ != 'dict':
					return RetVal(ErrBadType, "second level index doesn't match container type")
			else:
				# Field doesn't exist. Create a container based on the index's type
				if indextype == 'i':
					target[field] = list()
				else:
					target[field] = dict()
			
			# Here's where it gets complicated. `field` always refers to a dictionary item. `index`,
			# however, can be a list *or* dictionary item, which makes checking to see if `subkey`
			# is in the second level container much trickier. We will break this down into dealing
			# with lists and dictionaries separately so that the code is easier to follow
			if indextype == 'i':
				if index >=0 and index < len(target[field]):
					# Index refers to an item which exists. Check to make sure that the subkey's
					# type matches
					if subkeytype == 'i' and type(target[field][index]).__name__ != 'list' \
						or subkeytype == 's' and type(target[field][index]).__name__ != 'dict':
						return RetVal(ErrBadType, "third level index doesn't match container type")
				else:
					if subkeytype == 'i':
						newitem = list()
					else:
						newitem = dict()
					
					target[field].append(newitem)
			else:
				if index in target[field]:
					# Index refers to an item which exists. Check to make sure that the subkey's
					# type matches
					if subkeytype == 'i' and type(target[field][index]).__name__ != 'list' \
						or subkeytype == 's' and type(target[field][index]).__name__ != 'dict':
						return RetVal(ErrBadType, "third level index doesn't match container type")
				else:
					if subkeytype == 'i':
						newitem = list()
					else:
						newitem = dict()
					
					target[field][index] = newitem

			# Having gotten this far, we know the following:
			# 1) Contact[field] exists and `index` matches the type of Contact[field]
			# 2) Contact[field][index] exists and `subkey` matches the type of Contact[field][index]
			
			# Now we just need to check if Contact[field][index][subkey] exists and either set it
			# or add it
			if subkeytype == 'i':
				if subkey >=0 and subkey < len(target[field][index]):
					target[field][index][subkey] = value
				else:
					target[field][index].append(value)
			else:
				target[field][index][subkey] = value
			
			return RetVal()
			
		return RetVal(ErrBadValue, "bad field name")

	def _delete_field(self, target: dict, fieldname: str) -> RetVal:
		'''Internal method which does all the heavy lifting for delete_field() and 
		delete_annotation()'''

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

	def _get_field(self, target: dict, fieldname: str) -> RetVal:
		'''Gets the value for the specified field. Note that it is perfectly legal to obtain 
		dictionaries or lists of values this way. The field 'type' will be populated with 
		the value `str`, `dict`, or `list` based on the type of value. The field `value` will 
		contain the returned data. Photos obtained via this method will be in the internal 
		storage format and not as an image.'''

		if not fieldname:
			return RetVal(ErrBadValue)
		
		parts = fieldname.split('.')
		for part in parts:
			if not part:
				return RetVal(ErrBadValue, 'bad field name')
		
		if len(parts) == 1:
			if parts[0] in target:
				return RetVal().set_values({
					'value':target[parts[0]],
					'type':type(target[parts[0]]).__name__
				})
			return RetVal(ErrNotFound)
		
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
				key = parts[1]
			
			if not (isinstance(key, int) or isinstance(key, str)):
				return RetVal(ErrBadType, 'second level key must be an integer or string')
			
			# If the top-level container exists, make sure the its type matches the key type
			if parts[0] in target:
				if not (keytype == 'i' and isinstance(target[parts[0]], list) 
						or (keytype == 's' and isinstance(target[parts[0]], dict))):
					return RetVal(ErrBadType, 'second level key does not match container type')
			else:
				return RetVal(ErrNotFound)

			return RetVal().set_values({
				'value':target[parts[0]][key],
				'type':type(target[parts[0]][key]).__name__
			})
		
		elif len(parts) == 3:
			# As of this writing, the schema only utilizes top-level fields which are lists of
			# dictionaries, but we will write this code to handle lists or dictionaries nested
			# inside a list or dictionary in case the schema changes at some point.
			# keys have to either be an integer index (for a list) or a string

			# This variable isn't absolutely necessary, but it makes the code clearer
			field = parts[0]

			# Set the type and value of the middle field index
			indextype = 'i'
			try:
				index = int(parts[1])
			except:
				indextype = 's'
				index = parts[1]

			# Set the type and value of the third field index
			subkeytype = 'i'
			try:
				subkey = int(parts[2])
			except:
				subkeytype = 's'
				subkey = parts[2]

			# Now that we have the middle index, check that the field exists
			if field in target:
				# Field exists, does the index match its type?
				if indextype == 'i' and type(target[field]).__name__ != 'list' \
					or indextype == 's' and type(target[field]).__name__ != 'dict':
					return RetVal(ErrBadType, "second level index doesn't match container type")
			else:
				return RetVal(ErrNotFound)
			
			# Here's where it gets complicated. `field` always refers to a dictionary item. `index`,
			# however, can be a list *or* dictionary item, which makes checking to see if `subkey`
			# is in the second level container much trickier. We will break this down into dealing
			# with lists and dictionaries separately so that the code is easier to follow
			if indextype == 'i':
				if index >=0 and index < len(target[field]):
					# Index refers to an item which exists. Check to make sure that the subkey's
					# type matches
					if subkeytype == 'i' and type(target[field][index]).__name__ != 'list' \
						or subkeytype == 's' and type(target[field][index]).__name__ != 'dict':
						return RetVal(ErrBadType, "third level index doesn't match container type")
				else:
					return RetVal(ErrNotFound)
			else:
				if index in target[field]:
					# Index refers to an item which exists. Check to make sure that the subkey's
					# type matches
					if subkeytype == 'i' and type(target[field][index]).__name__ != 'list' \
						or subkeytype == 's' and type(target[field][index]).__name__ != 'dict':
						return RetVal(ErrBadType, "third level index doesn't match container type")
				else:
					return RetVal(ErrNotFound)

			# Having gotten this far, we know the following:
			# 1) Contact[field] exists and `index` matches the type of Contact[field]
			# 2) Contact[field][index] exists and `subkey` matches the type of Contact[field][index]
			
			# Now we just need to check if Contact[field][index][subkey] exists and either set it
			# or add it
			
			return RetVal().set_values({
				'value':target[parts[0]][index][subkey],
				'type':type(target[parts[0]][index][subkey]).__name__
			})
			
		return RetVal(ErrBadValue, "bad field name")

	def _setphoto(self, target: dict, path: str) -> RetVal:
		'''Given a file path, encode and store the data in the contact structure'''

		if path == '' and 'Photo' in self:
			del target['Photo']
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
		target['Photo'] = {
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
