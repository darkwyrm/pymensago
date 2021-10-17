import datetime
import os
import re
import sqlite3

from retval import ErrBadData, RetVal, ErrServerError, ErrUnimplemented
from pymensago.client import MensagoClient
import pymensago.config as config
import pymensago.dbfs as dbfs
import pymensago.mpath as mpath
from pymensago.serverconn import ServerConnection, wrap_server_error
from pymensago.userprofile import Profile
import pymensago.utils as utils

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
	
	if item['Type'] in [ 'CREATE', 'DELETE' ] and not mpath.validate_server_path(item['Data']):
		return False
	
	if item['Type'] == 'MOVE':
		paths = mpath.split(item['Data'])
		if len(paths) != 2:
			return False
		
		if not mpath.validate_server_path(paths[0]) or not mpath.validate_server_path(paths[1]):
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

	record_types = [ "CREATE", "DELETE", "MOVE", "REPLACE", "ROTATE", "MKDIR", "RMDIR" ]

	# To fully process updates, we first need to figure out what the end state should look like.
	# This dictionary will contain the operations needed to reach this state. By translating the
	# update list to this intermediate state, we can prevent errors, unnecessary item processing,
	# and even file transfers.
	fileops = dict()
	
	cur = profile.db.cursor()
	cur.execute('SELECT COUNT(ALL) FROM updates')
	row = cur.fetchone()
	if row == None or row[0] == 0:
		return RetVal()

	# TODO: refactor update processing to order by an arbitrary row ID, not time
	
	cur.execute('SELECT id,type,data FROM updates ORDER BY time')
	rows = cur.fetchall()
	
	for i in range(len(rows)):
		update_id = utils.UUID(rows[i][0])
		if not update_id.is_valid():
			out = RetVal(ErrBadData, 'bad update record found in database: ' + row[0])
			break
		
		if row[1] not in record_types:
			out = RetVal(ErrBadData, 'invalid record type ' + row[1])
			break
		
		# This is where it can get complicated
		if row[1] == 'CREATE':
			fileops[mpath.basename(row[2])] = { 'op':"CREATE", 'data':row[2], 'dest':row[2]}
		
		elif row[1] == 'DELETE':
			filename = mpath.basename(row[2])
			if filename in fileops:
				# This case is that if already instructed to create a file, but it was deleted
				# later on, which means we don't have to do anything.
				if fileops[filename]['op'] == 'CREATE':
					del fileops[filename]
				
				# If we've already been instructed to move an existing file to another location,
				# but now we're asked to delete it, we'll just simply delete it from the original
				# location
				elif fileops[filename]['op'] == 'MOVE':
					fileops[filename]['op'] == 'DELETE'
					fileops[filename]['data'] == fileops[filename]['src']
					del fileops[filename]['src']
					del fileops[filename]['dest']
				
				else:
					# We should *never* be here
					raise ValueError('BUG: Bad DELETE update state operation in process_updates()')

			else:
				fileops[filename] = { 'op':"DELETE", 'data':row[2] }
		
		elif row[1] == 'MOVE':
			paths = mpath.split(row[2])
			filename = mpath.basename(paths[0])
			if filename in fileops:
				# A file is already going to be downloaded from the server. Because of the MOVE,
				# we'll download it to the final location instead of the its original location
				# specified in the CREATE record
				if fileops[filename]['op'] == 'CREATE':
					fileops[filename]['dest'] = paths[1]
				
				elif fileops[filename]['op'] == 'MOVE':
					# The file was moved once, and now it has been moved again. Skip to the end. :)
					if fileops[filename]['dest'] == paths[0]:
						fileops[filename]['dest'] == paths[1]
					else:
						# We have a big problem. There is an existing op record to move the file
						# from a to b. Now we have another update record which says to move the same
						# file from c to d. This means that the server records are corrupted. The
						# solution here is to assume that the first record is legitimate and
						# the following ones are incorrect -- make no further changes until we're
						# confident of the final state.
						pass

				# This is silly and shouldn't happen. Nonetheless, if we're asked to move a file
				# scheduled for deletion, do nothing.
				elif fileops[filename]['op'] == 'DELETE':
					pass

			else:
				fileops[filename] = { 'op':"MOVE", 'data':row[2], 'src':paths[0], 'dest':paths[1] }
		
		elif row[1] == 'REPLACE':
			# Finding a REPLACE record in the mix means that a file has been deleted and another
			# has been created.
			paths = mpath.split(row[2])
			oldfile = mpath.basename(paths[0])
			newfile = mpath.basename(paths[1])
			
			# Handling the new file is, thankfully, really easy
			fileops[newfile] = { 'op':"CREATE", 'data':paths[1], 'dest':paths[1] }

			# Handling the old one is just like DELETE
			if oldfile in fileops:
				# This case is that a file has been created, but now it's being replaced, so
				# do nothing about the original update record
				if fileops[filename]['op'] == 'CREATE':
					del fileops[oldfile]
				
				# If we've already been instructed to move an existing file to another location,
				# but now it's been replaced. Once again we'll just simply delete it from the
				# original location and move on.
				elif fileops[filename]['op'] == 'MOVE':
					fileops[filename]['op'] == 'DELETE'
					fileops[filename]['data'] == fileops[filename]['src']
					del fileops[filename]['src']
					del fileops[filename]['dest']
				
				else:
					# We should *never* be here
					raise ValueError('BUG: Bad REPLACE update state operation in process_updates()')

			else:
				fileops[oldfile] = { 'op':"DELETE", 'data':paths[1] }
		
		elif row[1] == 'MKDIR':
			fileops[mpath.basename(row[2])] = { 'op':"MKDIR", 'data':row[2] }
		
		elif row[1] == 'RMDIR':
			dirname = mpath.basename(row[2])
			if dirname in fileops:
				if fileops[dirname]['op'] == 'MKDIR':
					del fileops[dirname]
				elif fileops[dirname]['op'] == 'RMDIR':
					# ignore duplicates
					pass
			else:
				fileops[dirname] = { 'op':'RMDIR', 'data':row[2] }

		elif row[1] == 'ROTATE':
			# TODO: Implement key rotation handling in process_updates()
			pass
	
	# Now that we have put together all the file operations
	

	# Remove the records for the items successfully processed
	for item in itemlist:
		cur.execute("DELETE FROM updates WHERE id=?", (item,))
	
	cur.commit()
	
	return out
