'''This module manages the user's contact information'''

import sqlite3

from pymensago.utils import UUID, Name
from retval import RetVal, ErrBadValue, ErrNotFound, ErrUnimplemented


def load_user_field(db: sqlite3.Connection, fieldname: str) -> RetVal:
	'''Loads a user info field from the database. Fieldname is expected to be in dot-separated 
	format. If the fieldname is an asterisk (*), all fields are loaded and value is a list, 
	not a string'''

	if not id.is_valid() or not fieldname or not db:
		return RetVal(ErrBadValue)
	
	cursor = db.cursor()
	if fieldname == '*':
		cursor.execute('''SELECT fieldname,fieldvalue FROM userinfo''')
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
			'''SELECT fieldvalue FROM userinfo WHERE fieldname=?''',
			(id.as_string(),fieldname))
		results = cursor.fetchone()
		if not results or not results[0]:
			return RetVal(ErrNotFound)

	return RetVal().set_values({ 'value':results[0], 'group':results[1] })


def save_user_field(db: sqlite3.Connection, fieldname: str, fieldvalue: str) -> RetVal:
	'''Saves a user info field to the database. Fieldname is expected to be in dot-separated 
	format.'''

	cursor = db.cursor()
	cursor.execute('DELETE FROM userinfo WHERE fieldname=?', (id.as_string(),fieldname))
	cursor.execute('INSERT INTO userinfo (fieldname, fieldvalue) VALUES(?,?)',
			(id.as_string(), fieldname, fieldvalue))
	db.commit()

	return RetVal()


def delete_user_field(db: sqlite3.Connection, fieldname: str) -> RetVal:
	'''Deletes a user info field from the database. Fieldname is expected to be in dot-separated 
	format.'''

	if not fieldname or not db:
		return RetVal(ErrBadValue)
	
	cursor = db.cursor()
	cursor.execute('DELETE FROM userinfo WHERE fieldname=?', (id.as_string(),fieldname))

	return RetVal()


def load_user_list_field(db: sqlite3.Connection, id: UUID, fieldname: str) -> RetVal:
	'''Loads a field which is a list and returns it as such'''
	# TODO: implement load_user_list_field()
	return RetVal(ErrUnimplemented)


def save_user_list_field(db: sqlite3.Connection, id: UUID, fieldname: str, fieldvalue: list, 
	group: str) -> RetVal:
	'''Saves a list object into the database as a list'''

	# TODO: implement save_user_list_field()
	return RetVal(ErrUnimplemented)


def delete_user_list_field(db: sqlite3.Connection, id: UUID, fieldname: str) -> RetVal:
	'''Deletes a field which is a list'''
	
	# TODO: implement delete_user_list_field()
	return RetVal(ErrUnimplemented)


def save_name(db: sqlite3.Connection, id: UUID, name: Name) -> RetVal:
	'''Saves the name passed into the database. Note that all name-related fields will be 
	synchronized with the values in the object passed, so empty name fields will be deleted and 
	missing name fields will be added. Thus all name information will be deleted if this function 
	is passed an empty Name object. Note that this call does not affect the Nicknames field.'''

	single_fields = {
		'GivenName' : name.given,
		'FamilyName' : name.family,
		'Prefix' : name.prefix,
		'FormattedName': name.formatted
	}
	for fieldname, fieldvalue in single_fields.items():
		status = delete_user_field(db, fieldname)
		if status.error():
			return status
		
		if fieldvalue:
			status = save_user_field(db, fieldname, fieldvalue)
			if status.error():
				return status
	
	list_fields = {
		'Suffixes' : name.suffixes,
		'AdditionalNames' : name.additional
	}
	for fieldname, fieldvalue in list_fields.items():
		status = delete_user_list_field(db, id, fieldname)
		if status.error():
			return status

		if fieldvalue:
			status = save_user_list_field(db, id, fieldname, fieldvalue)
			if status.error():
				return status


