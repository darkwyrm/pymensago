import datetime
import re
import sqlite3

from retval import ErrBadData, RetVal, ErrServerError, ErrUnimplemented
from pymensago.client import MensagoClient
import pymensago.config as config
from pymensago.serverconn import ServerConnection, wrap_server_error
import pymensago.utils as utils

folderPattern = re.compile(r'/( new)?'
	r'( [\da-fA-F]{8}-[\da-fA-F]{4}-[\da-fA-F]{4}-[\da-fA-F]{4}-[\da-fA-F]{12})*')

filePattern = re.compile(r'/( new)?'
	r'( [\da-fA-F]{8}-[\da-fA-F]{4}-[\da-fA-F]{4}-[\da-fA-F]{4}-[\da-fA-F]{12})*'
	r'( [0-9]+\.[0-9]+\.[0-9a-fA-F]{8}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?'
		r'[0-9a-fA-F]{12})*')


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

	cur = profile.db.cursor()
	cur.execute('SELECT id,type,data FROM updates ORDER BY time')
	for row in cur.fetchall():
		update_id = utils.UUID(row[0])
		if not update_id.is_valid():
			out = RetVal(ErrBadData, 'bad update record found in database: ' + row[0])
			break

		if row[1] == "CREATE":
			status = _process_create_update(row)
		elif row[1] == "DELETE":
			status = _process_delete_update(row)
		elif row[1] == "MOVE":
			status = _process_move_update(row)
		elif row[1] == "ROTATE":
			status = _process_rotate_update(row)
		else:
			out = RetVal(ErrBadData, 'invalid record type ' + row[1])
			break
		
		if status.error():
			out = status
			break
	
	# Remove the records for the items successfully processed
	for item in itemlist:
		cur.execute("DELETE FROM updates WHERE id=?", (item,))
	
	cur.commit()
	
	return out


def _process_create_update(data: tuple) -> RetVal:
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


def _process_delete_update(data: tuple) -> RetVal:
	'''Handles deleting items from DELETE records'''
	# TODO: Implement _process_delete_update()


def _process_move_update(data: tuple) -> RetVal:
	'''Handles moving items around because of MOVE records'''
	# TODO: Implement _process_move_update()


def _process_rotate_update(data: tuple) -> RetVal:
	'''Handles key rotation because of ROTATE records'''
	# TODO: Implement _process_rotate_update()
