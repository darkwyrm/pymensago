import datetime
import os
import re
import sqlite3

from retval import ErrBadData, RetVal, ErrServerError, ErrUnimplemented
from pymensago.client import MensagoClient
import pymensago.config as config
import pymensago.dbfs as dbfs
from pymensago.serverconn import ServerConnection, wrap_server_error
from pymensago.userprofile import Profile
import pymensago.utils as utils

folderPattern = re.compile(r'/( new)?'
	r'( [\da-fA-F]{8}-[\da-fA-F]{4}-[\da-fA-F]{4}-[\da-fA-F]{4}-[\da-fA-F]{12})*')

filePattern = re.compile(r'/( new)?'
	r'( [\da-fA-F]{8}-[\da-fA-F]{4}-[\da-fA-F]{4}-[\da-fA-F]{4}-[\da-fA-F]{12})*'
	r'( [0-9]+\.[0-9]+\.[0-9a-fA-F]{8}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?'
		r'[0-9a-fA-F]{12})*')


def make_path_local(profile: Profile, path: str) -> RetVal:
	'''Converts a Mensago path to an absolute path that references the local filesystem

	Parameters:
		* profile: the active profile
		* path: a string containing a Mensago path
	
	Returns:
		* path: (str) The converted path
	'''
	
	# Load the folder mappings. We'll need these in a bit.
	status = dbfs.load_folder_maps(profile.db)
	if status.error():
		return status
	maps = status['maps']

	parts = path.strip().split('/ wsp ')[1:]
	
	for i in range(len(parts)):
		subparts = parts[i].strip().split(' ')
		for j in range(len(subparts)):
			if subparts[j] in maps:
				subparts[j] = maps[subparts[j]]
		parts[i] = os.path.join(profile.path,os.sep.join(subparts))

	return RetVal().set_value('path',' '.join(parts))


def _validate_update(item: dict()) -> bool:
	'''Confirms that an update record is valid'''

	fieldnames = [ 'ID', 'Type', 'Data', 'Time' ]
	for fieldname in fieldnames:
		if fieldname not in item:
			return False
	
	id = utils.UUID(item['ID'])
	if not id.is_valid():
		return False
	
	if item['Type'] not in [ 'CREATE', 'MOVE', 'DELETE', 'ROTATE' ]:
		return False
	
	try:
		ts = int(item['Time'])
	except:
		return False
	
	if item['Type'] in [ 'CREATE', 'DELETE' ] and filePattern.match(item['Data']) == None:
		return False
	
	# Validating 'Move' is tricky
	if item['Type'] == 'MOVE':
		paths = item['Data'].strip().split('/')
		if len(paths) != 3:
			return False
		
		if not filePattern.match('/'+paths[1]) or not folderPattern.match('/'+paths[2]):
			return False

	return True


def download_updates(conn: ServerConnection, dbconn: sqlite3.Connection) -> RetVal:
	'''Checks for updates on the server and downloads them into the local database.'''

	# First, check the update table for existing ones. 

	ts = config.get_str('last_update')
	
	if ts is None:
		last_check = '0'
	else:
		last_check = ts
	conn.send_message({
		'Action': 'IDLE',
		'Data': { 'CountUpdates': last_check }
	})

	res = conn.read_response()
	if res['Code'] != 200:
		return wrap_server_error(res)
	
	if 'UpdateCount' not in res['Data']:
		return RetVal(ErrServerError, "server didn't supply update count when requested")
	
	try:
		count = int(res['Data']['UpdateCount'])
	except Exception as e:
		return RetVal(ErrServerError, "server supplied invalid update count")
	
	if count == 0:
		config.set_str('last_update', str(int(datetime.datetime.utcnow().timestamp())))
		return RetVal()

	while True:
		conn.send_message({
			'Action': 'GETUPDATES',
			'Data': { 'Time': last_check }
		})

		res = conn.read_response()
		if res['Code'] != 200:
			return wrap_server_error(res)
		
		try:
			updates_received = len(res['Data']['Updates'])
			update_total = int(res['Data']['UpdateCount'])
		except Exception as e:
			return RetVal(ErrServerError, "server supplied invalid update parameter info")
		
		if updates_received > update_total:
			return RetVal(ErrServerError, "server returned invalid update info")
		
		last_item_time = last_check
		cur = dbconn.cursor()
		for item in res['Data']['Updates']:
			cur.execute('SELECT id FROM updates WHERE id=?', (item['ID'],))
			row = cur.fetchone()
			if row and len(row) > 0:
				continue
			
			if not _validate_update(item):
				config.set_str('last_update', last_item_time)
				return RetVal(ErrServerError, 'server supplied bad update')

			cur.execute('INSERT INTO updates (id,type,data,time) VALUES(?,?,?,?);',
				(item['ID'], item['Type'], item['Data'], item['Time']))
		dbconn.commit()

		last_item_time = item['Time']
		last_check = res['Data']['Updates'][-1]['Time']
		
		if updates_received == update_total:
			break

	config.set_str('last_update', str(int(datetime.datetime.utcnow().timestamp())))

	return RetVal()


def process_updates(client: MensagoClient) -> RetVal:
	'''Acts upon account updates in the database'''

	status = client.pman.get_active_profile()
	if status.error():
		return status
	profile = status['profile']

	out = RetVal()
	itemlist = list()

	handlers = {
		"CREATE":_process_create_update,
		"DELETE":_process_delete_update,
		"MOVE":_process_move_update,
		"ROTATE":_process_rotate_update,
		"MKDIR":_process_mkdir_update,
		"RMDIR":_process_rmdir_update
	}

	cur = profile.db.cursor()
	cur.execute('SELECT COUNT(ALL) FROM updates')
	row = cur.fetchone()
	if row == None or row[0] == 0:
		return RetVal()

	cur.execute('SELECT id,type,data FROM updates ORDER BY time')
	rows = cur.fetchall()
	
	for i in range(len(rows)):
		update_id = utils.UUID(rows[i][0])
		if not update_id.is_valid():
			out = RetVal(ErrBadData, 'bad update record found in database: ' + row[0])
			break
		
		if row[1] not in handlers:
			out = RetVal(ErrBadData, 'invalid record type ' + row[1])
			break

		if row[1] == "CREATE":
			# CREATE is one of the most complicated updates to process. When new messages come in,
			# the new item is downloaded and entry in / new is deleted because it will be replaced
			# with a new entry that is encrypted with the user's storage key, not an ephemeral one
			pass

		status = handlers[row[1]](row, profile)
		if status.error():
			out = status
			break
	
	# Remove the records for the items successfully processed
	for item in itemlist:
		cur.execute("DELETE FROM updates WHERE id=?", (item,))
	
	cur.commit()
	
	return out


def _process_create_update(data: tuple, maps: dict) -> RetVal:
	'''Handles downloading and creating items from CREATE records'''

	rawpath = data[2]
	if filePattern.match(rawpath) == None:
		return RetVal(ErrBadData, 'bad path in database ' + rawpath)
	
	# Processing Steps:
	# - Download item to temporary location
	#   - If item doesn't exist and is in 'new' directory, abort
	#     and save to see if it was deleted later on
	# - Decrypt item
	# - Validate data
	# - Process attachments
	# 	- Create attachment ID
	#   - Save attachment to filesystem
	#   - Add attachment record to database
	#   - Add attachment reference to item
	# - Save item data to database
	# - Delete item from server
	# - 

	# TODO: Implement _process_create_update()
	return RetVal(ErrUnimplemented)


def _process_delete_update(data: tuple, profile: Profile) -> RetVal:
	'''Handles deleting items from DELETE records'''
	
	status = dbfs.make_path_dblocal(profile, data[2])
	if status.error():
		return status
	
	return dbfs.delete(profile.db, status['path'])


def _process_move_update(data: tuple, profile: Profile) -> RetVal:
	'''Handles moving items around because of MOVE records'''
	
	# This unusual construct simultaneously splits the source and destination paths out while
	# stripping out the space in between them.
	paths = data[2].strip().split(' /')
	paths[1] = '/' + paths[1]
	
	status = dbfs.make_path_dblocal(profile, paths[0])
	if status.error():
		return status
	src = status['path']

	status = dbfs.make_path_dblocal(profile, paths[0])
	if status.error():
		return status
	dest = status['path']
	
	return dbfs.move(profile.db, src, dest)


def _process_rotate_update(data: tuple, profile: Profile) -> RetVal:
	'''Handles key rotation because of ROTATE records'''
	# TODO: Implement _process_rotate_update()
	return RetVal(ErrUnimplemented)


def _process_mkdir_update(data: tuple, profile: Profile) -> RetVal:
	'''Handles making folders'''

	status = dbfs.make_path_dblocal(profile, data[2])
	if status.error():
		return status
	
	return dbfs.mkdir(profile.db, status['path'])


def _process_rmdir_update(data: tuple, profile: Profile) -> RetVal:
	'''Handles removing folders'''
	
	status = dbfs.make_path_dblocal(profile, data[2])
	if status.error():
		return status
	
	return dbfs.rmdir(profile.db, status['path'])
