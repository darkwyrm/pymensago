'''Module to implement contact management in the database'''

import datetime
import re
import time

from pymensago.utils import UUID
from retval import RetVal, ErrBadValue, ErrNotFound, ErrUnimplemented
import sqlite3

_long_date_pattern = re.compile(r'([1-3]\d{3})([0-1]\d)([0-3]\d)')
_short_date_pattern = re.compile(r'([0-1]\d)([0-3]\d)')

def load_field(db: sqlite3.Connection, id: UUID, fieldname: str) -> RetVal:
	'''Loads a field from the database. Fieldname is expected to be in dot-separated format. If the 
	fieldname is an asterisk (*), all fields are loaded and value is a list, not a string'''

	if not id.is_valid() or not fieldname or not db:
		return RetVal(ErrBadValue)
	
	cursor = db.cursor()
	if fieldname == '*':
		cursor.execute('''SELECT fieldname,fieldvalue,contactgroup FROM contactinfo''')
		results = cursor.fetchall()
		if not results or not results[0][0]:
			return RetVal(ErrNotFound)
		
		outnames = list()
		outvalues = list()
		outgroups = list()
		for result in results:
			outnames.append(result[0])
			outvalues.append(result[1])
			outgroups.append(result[2])
		return RetVal().set_values({'name':outnames, 'value':outvalues, 'group':outgroups})
	else:
		cursor.execute(
			'''SELECT fieldvalue,contactgroup FROM contactinfo WHERE id=? AND fieldname=?''',
			(id.as_string(),fieldname))
		results = cursor.fetchone()
		if not results or not results[0]:
			return RetVal(ErrNotFound)

	return RetVal().set_values({ 'value':results[0], 'group':results[1] })


def save_field(db: sqlite3.Connection, id: UUID, fieldname: str, fieldvalue: str, 
	group: str) -> RetVal:
	'''Saves a field to the database. Fieldname is expected to be in dot-separated format.'''

	cursor = db.cursor()
	cursor.execute('''DELETE FROM contactinfo WHERE id=? AND fieldname=?''',
		(id.as_string(),fieldname))
	cursor.execute('''INSERT INTO contactinfo (id, fieldname, fieldvalue, contactgroup) 
			VALUES(?,?,?,?)''',
			(id.as_string(), fieldname, fieldvalue, group))
	db.commit()

	return RetVal()


def load_list_field(db: sqlite3.Connection, id: UUID, fieldname: str) -> RetVal:
	'''Loads a field which is a list and returns it as such'''
	# TODO: implement load_list_field()
	return RetVal(ErrUnimplemented)


def save_list_field(db: sqlite3.Connection, id: UUID, fieldname: str, fieldvalue: list, 
	group: str) -> RetVal:
	'''Saves a list object into the database as a list'''

	# TODO: implement save_list_field()
	return RetVal(ErrUnimplemented)


def delete_list_field(db: sqlite3.Connection, id: UUID, fieldname: str) -> RetVal:
	'''Deletes a field which is a list'''
	
	# TODO: implement delete_list_field()
	return RetVal(ErrUnimplemented)


def delete_field(db: sqlite3.Connection, id: UUID, fieldname: str) -> RetVal:
	'''Deletes a field from the database. Fieldname is expected to be in dot-separated format.'''

	if not id.is_valid() or not fieldname or not db:
		return RetVal(ErrBadValue)
	
	cursor = db.cursor()
	cursor.execute('''DELETE FROM contactinfo WHERE id=? AND fieldname=?''',
		(id.as_string(),fieldname))
	db.commit()

	return RetVal()


def clear_contacts(db: sqlite3.Connection, fieldname: str, fieldvalue: str) -> RetVal:
	'''Deletes all contacts from the database.'''
	if not id.is_valid() or not fieldname or not db:
		return RetVal(ErrBadValue)
	
	cursor = db.cursor()
	cursor.execute('''DELETE FROM contactinfo WHERE contactgroup!='self' ''',
		(id.as_string(),fieldname))

	return RetVal()
	

def load_contact(db: sqlite3.Connection, id: UUID) -> RetVal:
	'''Loads a contact from the database, given an ID. The contact object is returned in the field 
	'value' if successful.'''
	return RetVal(ErrUnimplemented)


def save_contact(db: sqlite3.Connection, id: UUID, clobber: bool) -> RetVal:
	'''Saves a contact to the database. If clobber is false, fields that are in the contact object 
	are updated or added. If clobber is true, all existing data for the contact is deleted first, 
	ensuring that the database copy exactly matches that of the contact object.'''
	return RetVal(ErrUnimplemented)


def find_contact(db: sqlite3.Connection, fieldname: str, fieldvalue: str) -> RetVal:
	'''Finds the ID for a contact with the specified dot-notated field name and value. If found, 
	the application's internal ID -- not the contact's workspace ID -- is returned in the field 
	'value'.'''
	return RetVal(ErrUnimplemented)


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


def print_contact(c: dict) -> str:
	'''Creates a pretty-printed string from a contact'''

	# TODO: rework print_contact to handle dot notation
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


