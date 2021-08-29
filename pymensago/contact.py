'''This module contains functions to manage the dot-notated contact information used internally 
and transforming it to and from the JSON-based format described in the spec.'''
from base64 import b85encode
import os
import tempfile
from typing import Union

from PIL import Image
from retval import RetVal, ErrOutOfRange, ErrBadData, ErrBadType, ErrBadValue, ErrNotFound

# This module implements the transformation of a contact dictionary between the official format
# and the dot-notation format. An example of official format is as follows:
#
# {
# 	'Header' : {
# 		'Version': '1.0',
# 		'EntityType': 'individual'
# 	},
# 	'GivenName': 'Richard',
# 	'FamilyName': 'Brannan',
# 	'Nicknames' : [ 'Rick', 'Ricky', 'Rich'],
# 	'Gender': 'Male',
# 	'Website': { 'Personal':'https://www.example.com',
# 				'Mensago':'https://mensago.org' },
# 	'Phone': [	{	'Label':'Mobile',
# 					'Number':'555-555-1234',
# 					'Preferred':'yes'
# 				}
# 			],
# 	'Birthday': '19750415',
# 	'Anniversary': '0714',
# 	'Mensago': [
# 		{	'Label':'Home',
# 			'UserID':'cavs4life',
# 			'Workspace':'f9ccb1f5-85e4-487d-9861-51d371101917',
# 			'Domain':'example.com'
# 		},
# 		{	'Label':'Work',
# 			'UserID':'rbrannan',
# 			'Workspace':'9015c2ea-2d02-491b-aa1f-4d536cfc4878',
# 			'Domain':'contoso.com'
# 		}
# 	],
# 	'Annotations': {}
# }
#
# When converted to a single-level dictionary, the field names and indices of nested values are
# joined together by periods to denote the level of nesting. A flattened dictionary consists of
# only string keys and string values, as shown below:
#
# bar = {
# 	'Header.Version': '1.0',
# 	'Header.EntityType': 'individual',
# 	'GivenName': 'Richard',
# 	'FamilyName': 'Brannan',
# 	'Nicknames.0': 'Rick',
# 	'Nicknames.1': 'Ricky',
# 	'Nicknames.2': 'Rich',
# 	'Gender': 'Male',
# 	'Website.Personal': 'https://www.example.com',
# 	'Website.Mensago': 'https://mensago.org',
# 	'Phone.0.Label': 'Mobile',
# 	'Phone.0.Number': '555-555-1234',
# 	'Phone.0.Preferred': 'yes',
# 	'Birthday': '19750415',
# 	'Anniversary': '0714',
# 	'Mensago.0.Label': 'Home',
# 	'Mensago.0.UserID': 'cavs4life',
# 	'Mensago.0.Workspace': 'f9ccb1f5-85e4-487d-9861-51d371101917',
# 	'Mensago.0.Domain': 'example.com',
# 	'Mensago.1.Label': 'Work',
# 	'Mensago.1.UserID': 'rbrannan',
# 	'Mensago.1.Workspace': '9015c2ea-2d02-491b-aa1f-4d536cfc4878',
# 	'Mensago.1.Domain': 'contoso.com'
# }


def flatten(d: dict) -> RetVal:
	'''Flattens a dictionary in Contact format into a single-level dot-notated dictionary. All 
	fields are expected to be dictionaries, lists, or strings. The flattened result is returned 
	in the 'value' field unless there is an error.'''
	if not len(d):
		return RetVal().set_value('value', dict())
	
	if not isinstance(d, dict):
		return RetVal(ErrBadType)
	
	flattened = dict()
	for k,v in d.items():
		status = RetVal()
		if isinstance(v, str):
			flattened[k] = v
		elif isinstance(v, dict):
			status = _flatten_dict(flattened, [k], v)
		elif isinstance(v, list):
			status = _flatten_list(flattened, [k], v)
		else:
			return RetVal(ErrBadValue, f"field {k} is not dictionary, list, or string")
		
		if status.error():
			return status

	return RetVal().set_value('value', flattened)


def _flatten_dict(target: dict, levels: list, d: dict) -> RetVal:
	for k,v in d.items():
		status = RetVal()
		if isinstance(v, str):
			flatkey = f"{'.'.join(levels)}.{k}"
			target[flatkey] = v
		elif isinstance(v, dict):
			status = _flatten_dict(target, [k], v)
		elif isinstance(v, list):
			status = _flatten_list(target, [k], v)
		else:
			return RetVal(ErrBadValue, f"field {k} is not dictionary, list, or string")
		
		if status.error():
			return status

	return RetVal()

def _flatten_list(target: dict, levels: list, l: list) -> RetVal:
	for i in range(len(l)):
		status = RetVal()
		if isinstance(l[i], str):
			flatkey = f"{'.'.join(levels)}.{str(i)}"
			target[flatkey] = l[i]
		elif isinstance(l[i], dict):
			status = _flatten_dict(target, levels + [str(i)], l[i])
		elif isinstance(l[i], list):
			status = _flatten_list(target, levels + [str(i)], l[i])
	
		if status.error():
			return status

	return RetVal()


def unflatten(d: dict) -> RetVal:
	'''Unflattens a dictionary from the format described for flatten()'''
	if not len(d):
		return RetVal().set_value('value', dict())
	
	if not isinstance(d, dict):
		return RetVal(ErrBadType)
	
	unflattened = dict()
	for k,v in d.items():
		status = unflatten_field(unflattened, k, v)
		if status.error():
			return status

	return RetVal().set_value('value', unflattened)


def unflatten_field(d: dict, fieldname: str, fieldvalue: str) -> RetVal:
	'''Unflattens a field into the target dictionary from the format described for flatten()'''
	if not isinstance(d, dict):
		return RetVal(ErrBadType)
	
	if not isinstance(fieldname, str):
		return RetVal(ErrBadType, 'fieldname must be a string')
	
	if not fieldname:
		return RetVal(ErrBadValue, "fieldname may not be empty")
	
	if not isinstance(fieldname, str):
		return RetVal(ErrBadType, 'values must be strings')
	
	if fieldname == 'Photo':
		return setphoto(d, fieldvalue)
	
	parts = fieldname.split('.')

	return _unflatten_recurse(d, parts, 0, fieldvalue)


def _unflatten_recurse(target: Union[dict,list], levels: list, levelindex: int, value: str) -> RetVal:
	'''This method continues to unpack a dot-notated string field. It is only called by itself or 
	unflatten(), so we will assume that parameter values are correct.'''

	if isinstance(target, list):
		target_is_list = True
		targetindex = int(levels[levelindex])
	else:
		target_is_list = False
		targetindex = levels[levelindex]

	if len(levels[levelindex:]) == 1:
		if target_is_list:
			value_index = int(levels[-1])
			
			if value_index == len(target):
				target.append(value)
			elif value_index < 0:
				return RetVal(ErrBadValue, f"negative list index for f{'.'.join(levels)}")
			elif value_index < len(target):
				target[value_index] = value
			elif value_index > len(target):
				return RetVal(ErrOutOfRange, f"list index for f{'.'.join(levels)} out of bounds")
		else:
			target[levels[-1]] = value
	else:
		value_index_is_int = True
		try:
			value_index = int(levels[levelindex+1])
		except:
			value_index = levels[levelindex+1]
			value_index_is_int = False

		if target_is_list:
			# Check to see if item is already in the list
			# if it exists, check index type against list. If not, add new container to list
			if targetindex == len(target):
				if value_index_is_int:
					target.append(list())
				else:
					target.append(dict())
			elif targetindex < 0:
				return RetVal(ErrBadValue, f"negative list index for f{'.'.join(levels)}")
			elif targetindex > len(target):
				return RetVal(ErrOutOfRange, f"list index for f{'.'.join(levels)} out of bounds")
			
			# Recurse into list as target
			return _unflatten_recurse(target[targetindex], levels, levelindex+1, value)
		else:
			# Check to see if item is already in the dictionary
			# if it exists, check index type against dictionary. If not, add new container
			# Recurse into new list as target
			if targetindex not in target:
				if isinstance(target, list):
					if value_index_is_int:
						target.append(list())
					else:
						target.append(dict())
				else:
					if value_index_is_int:
						target[targetindex] = list()
					else:
						target[targetindex] = dict()
			
			# Recurse into dict as target
			return _unflatten_recurse(target[targetindex], levels, levelindex+1, value)

	return RetVal()


def _get_recurse(target: Union[dict,list], levels: list, levelindex: int, pop_value: bool) -> RetVal:
	'''This method walks an unflattened dictionary to obtain a field. If pop_value is True, the 
	value is removed from the dictionary when it is returned.'''

	if isinstance(target, list):
		target_is_list = True
		targetindex = int(levels[levelindex])
	else:
		target_is_list = False
		targetindex = levels[levelindex]

	if len(levels[levelindex:]) == 1:
		if target_is_list:
			value_index = int(levels[-1])
			
			if value_index > 0 and value_index < len(target) :
				out = target[value_index]
				if pop_value:
					del target[value_index]
				return RetVal().set_value('value', out)
			
			return RetVal(ErrOutOfRange, f"list index for f{'.'.join(levels)} out of bounds")
		else:
			if levels[-1] not in target:
				return RetVal(ErrNotFound, f"field f{'.'.join(levels)} not found")
			
			out = target[levels[-1]]
			if pop_value:
				del target[levels[-1]]
			return RetVal().set_value('value', out)
	else:
		if target_is_list:
			# Check to see if item is already in the list
			# if it exists, check index type against list. If not, add new container to list
			if targetindex > 0 and targetindex < len(target) :
				status = _unflatten_recurse(target[targetindex], levels, levelindex+1, pop_value)
				if not status.error() and pop_value and len(target[targetindex]) == 0:
					del target[targetindex]
				return status
			else:
				return RetVal(ErrOutOfRange, f"list index for f{'.'.join(levels)} out of bounds")
		else:
			# Check to see if item is already in the dictionary
			# if it exists, check index type against dictionary. If not, add new container
			# Recurse into new list as target
			if targetindex not in target:
				return RetVal(ErrNotFound, f"field f{'.'.join(levels)} not found")
			
			status = _unflatten_recurse(target[targetindex], levels, levelindex+1, pop_value)
			if not status.error() and pop_value and len(target[targetindex]) == 0:
				del target[targetindex]


	return RetVal()


def setphoto(target: dict, path: str) -> RetVal:
	'''Given a file path, encode and store the data in the contact structure'''

	if path == '' and 'Photo' in target:
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


def merge_dict(dest: dict, source: dict, clobber: bool) -> None:
	for k in source:
		if isinstance(source[k], dict):
			if k not in dest:
				dest[k] = {}
			merge_dict(dest[k], source[k], clobber)
		else:
			if k not in dest or (isinstance(source[k],str) and not dest[k]) \
				or (clobber and k in dest):
				dest[k] = source[k]


class Name:
	'''This class is for storing the user's name. It is required because there are so many possible 
	pieces of information for the user's name, including prefix, suffixes, and formatting.'''
	def __init__(self, given_name: str, family_name: str, prefix: str='', suffixes=None,
				additional: list=None, family_first: bool=False) -> None:
		self.formatted = ''
		self.given = ''
		self.family = ''
		self.prefix = ''
		self.suffixes = list()
		self.additional = list()
		self.family_first = family_first
		self.set(given_name, family_name, prefix, suffixes, additional, family_first)
	
	def set(self, given_name: str, family_name: str, prefix: str='', suffixes=None,
		additional=None, family_first: bool=None) -> str:
		'''This method sets the user's name fields based on information'''
		self.given = given_name
		self.family = family_name
		self.prefix = prefix
		
		if suffixes:
			if isinstance(suffixes, str):
				self.suffixes = [suffixes]
			elif isinstance(suffixes, list):
				self.suffixes = suffixes
			else:
				raise TypeError('suffixes must be list of strings or a single string')
		else:
			self.suffixes = list()
		
		if additional:
			if isinstance(additional, str):
				self.additional = [additional]
			elif isinstance(additional, list):
				self.additional = additional
			else:
				raise TypeError('additional names must be list of strings or a single string')
		else:
			self.additional = list()
		
		self.family_first = family_first
		self._generate_formatted()

		return self.formatted

	def _generate_formatted(self):
		parts = list()
		
		if self.family_first:
			if self.family:
				parts.append(self.family)
			if self.given:
				parts.append(self.given)
			if self.additional:
				parts.extend(self.additional)
		else:
			if self.given:
				parts.append(self.given)
			if self.additional:
				parts.extend(self.additional)
			if self.family:
				parts.append(self.family)

		base = ' '.join(parts)
		if not base:
			return ''

		full = list()		
		if self.prefix:
			full.append(self.prefix + ' ')
		full.append(base)

		if self.suffixes:
			full.append(', ' + ', '.join(self.suffixes))
		
		self.formatted = ''.join(full)
		return self.formatted


