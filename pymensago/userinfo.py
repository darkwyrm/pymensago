'''This module manages the user's contact information'''

import sqlite3

from pymensago.utils import UUID
from pymensago.contact import Name
from retval import ErrBadType, RetVal, ErrBadValue, ErrNotFound, ErrUnimplemented


def load_user_field(db: sqlite3.Connection, fieldname: str) -> RetVal:
	'''Loads a user info field from the database. Fieldname is expected to be in dot-separated 
	format. If the fieldname is an asterisk (*), all fields are loaded and value is a list, 
	not a string'''

	if not fieldname or not db:
		return RetVal(ErrBadValue)
	
	cursor = db.cursor()
	if fieldname == '*':
		cursor.execute('''SELECT fieldname,fieldvalue FROM userinfo''')
		results = cursor.fetchall()
		if not results or not results[0][0]:
			return RetVal(ErrNotFound)
		
		outnames = list()
		outvalues = list()
		for result in results:
			outnames.append(result[0])
			outvalues.append(result[1])
		return RetVal().set_values({'name':outnames, 'value':outvalues})
	else:
		cursor.execute(
			'''SELECT fieldvalue FROM userinfo WHERE fieldname=?''', (fieldname,))
		results = cursor.fetchone()
		if not results or not results[0]:
			return RetVal(ErrNotFound)

	return RetVal().set_values({ 'value':results[0]})


def save_user_field(db: sqlite3.Connection, fieldname: str, fieldvalue: str) -> RetVal:
	'''Saves a user info field to the database. Fieldname is expected to be in dot-separated 
	format.'''

	cursor = db.cursor()
	cursor.execute('DELETE FROM userinfo WHERE fieldname=?', (fieldname,))
	cursor.execute('INSERT INTO userinfo (fieldname, fieldvalue) VALUES(?,?)',
			(fieldname, fieldvalue))
	db.commit()

	return RetVal()


def delete_user_field(db: sqlite3.Connection, fieldname: str) -> RetVal:
	'''Deletes a user info field from the database. Fieldname is expected to be in dot-separated 
	format.'''

	if not fieldname or not db:
		return RetVal(ErrBadValue)
	
	cursor = db.cursor()
	cursor.execute('DELETE FROM userinfo WHERE fieldname=?', (fieldname,))
	db.commit()

	return RetVal()


def load_user_list_field(db: sqlite3.Connection, fieldname: str) -> RetVal:
	'''Loads a field which is a list and returns it as such'''
	if not fieldname:
		return ErrBadValue
	
	cursor = db.cursor()
	cursor.execute("""SELECT fieldname,fieldvalue FROM userinfo WHERE fieldname LIKE ? 
		ORDER BY fieldname""", (fieldname + '.%',))
	results = cursor.fetchone()
	if not results or not results[0]:
		return RetVal(ErrNotFound)
	
	out = list()
	while results and results[0]:
		out.append(results[1])
		results = cursor.fetchone()
		
	return RetVal().set_value('values', out)


def save_user_list_field(db: sqlite3.Connection, fieldname: str, fieldvalues: list) -> RetVal:
	'''Saves a list object into the database as a list'''

	if not fieldname:
		return ErrBadValue
	
	if fieldvalues and not isinstance(fieldvalues[0], str):
		return RetVal(ErrBadType, 'list must contain strings')

	cursor = db.cursor()
	cursor.execute("""DELETE FROM userinfo WHERE fieldname LIKE ?""", (fieldname + '.%',))

	if not fieldvalues:
		db.commit()
		return RetVal()

	for i in range(len(fieldvalues)):
		cursor.execute('INSERT INTO userinfo (fieldname, fieldvalue) VALUES(?,?)',
				(f"{fieldname}.{str(i)}", fieldvalues[i]))
	
	db.commit()
		
	return RetVal()


def delete_user_list_field(db: sqlite3.Connection, fieldname: str) -> RetVal:
	'''Deletes a field which is a list'''
	
	if not fieldname:
		return ErrBadValue
	
	cursor = db.cursor()
	cursor.execute("""DELETE FROM userinfo WHERE fieldname LIKE ?""", (fieldname + '.%',))
	db.commit()
	return RetVal()


def save_name(db: sqlite3.Connection, name: Name) -> RetVal:
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
		status = delete_user_list_field(db, fieldname)
		if status.error():
			return status

		if fieldvalue:
			status = save_user_list_field(db, fieldname, fieldvalue)
			if status.error():
				return status


