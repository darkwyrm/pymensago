import datetime
import re
import sqlite3

from retval import RetVal, ErrServerError, ErrUnimplemented
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
	
	if item['Type'] not in [ 'Create', 'Move', 'Delete', 'Rotate' ]:
		return False
	
	try:
		ts = int(item['Time'])
	except:
		return False
	
	if item['Type'] in [ 'Create', 'Delete' ] and filePattern.match() == None:
		return False
	
	# Validating 'Move' is tricky
	if item['Type'] == 'Move':
		paths = item['Data'].strip().split('/')
		if len(paths) != 3:
			return False
		
		if not filePattern.match('/'+paths[1]) or not folderPattern.match('/'+paths[2]):
			return False

	return False


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
	if res['Code'] != '200':
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
		if res['Code'] != '200':
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
