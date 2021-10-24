import os
import random
import shutil
import time
import uuid

from retval import RetVal

from tests.integration.integration_setup import setup_test, init_server, load_server_config, \
	funcname, setup_profile_base, setup_profile, admin_profile_data, regcode_user
from pymensago.client import MensagoClient
import pymensago.updates as updates
from pymensago.utils import Domain

def make_test_file(path: str, file_size=-1, file_name='') -> RetVal:
	'''Generate a test file containing nothing but zeroes. If the file size is negative, a random 
	size between 1 and 10 Kb will be chosen. If the file name is empty, a random one will be 
	generated.'''
	
	if file_size < 0:
		file_size = random.randint(1,10) * 1024
	
	if file_name == '' or not file_name:
		file_name = f"{int(time.time())}.{file_size}.{str(uuid.uuid4())}"
	
	try:
		fhandle = open(os.path.join(path, file_name), 'w')
	except Exception as e:
		return RetVal().wrap_exception(e)
	
	fhandle.write('0' * file_size)
	fhandle.close()
	
	return RetVal().set_values({ 'name':file_name, 'size':file_size })


def setup_updates(dbconn, dbdata: dict) -> dict:
	'''Sets up the administrator workspace with some test files and adds records to the database 
	to enable testing the update/sync code'''
	
	admin_dir = os.path.join(dbdata['configfile']['global']['workspace_dir'], 
		dbdata['admin_wid'].as_string())

	dirinfo = [
		('new',os.path.join(admin_dir, 'new')),
		('messages',os.path.join(admin_dir, '11111111-1111-1111-1111-111111111111')),
		('contacts',os.path.join(admin_dir, '22222222-2222-2222-2222-222222222222')),
		('files', os.path.join(admin_dir, '33333333-3333-3333-3333-333333333333')),
		('attachments', os.path.join(admin_dir, '33333333-3333-3333-3333-333333333333',
									'11111111-1111-1111-1111-111111111111'))
	]
	dirs = {}
	for item in dirinfo:
		if os.path.exists(item[1]):
			shutil.rmtree(item[1])
		os.mkdir(item[1])
		dirs[item[0]] = item[1]

	now = int(time.time())
	cur = dbconn.cursor()
	
	files = {}
	files['new'] = []
	for i in range(100):
		status = make_test_file(dirs['new'])
		assert not status.error(), f"setup_updates: failed to create test file: {status.info}"
		files['new'].append(status['name'])
		
		path = f"/ {dbdata['admin_wid']} new {status['name']}"

		# we make the timestamp for each of the new files about a day apart
		filetime = now - ((100-i) * 86400)

		cur.execute("INSERT INTO updates(rid,wid,update_type,update_data,unixtime) VALUES("
			f"'{str(uuid.uuid4())}','{dbdata['admin_wid']}',1,'{path}','{filetime}')")
	
	dbconn.commit()

	return { 'dirs': dirs, 'files': files }


def test_download_updates():
	'''Tests the download_updates() command'''
	load_server_config()
	test_folder = setup_profile_base('test_download_updates')
	client = MensagoClient(test_folder)

	pgdb = setup_test()
	dbdata = init_server(pgdb)
	status = setup_profile(test_folder, dbdata, admin_profile_data)

	update_list = setup_updates(pgdb, dbdata)

	status = client.connect(Domain('example.com'))
	assert not status.error(), f"{funcname()}(): Couldn't connect to server"
	status = regcode_user(client.conn, dbdata, admin_profile_data, dbdata['admin_regcode'])
	assert not status.error(), f"{funcname()}(): Couldn't init admin"

	status = client.pman.get_active_profile()
	assert not status.error(), f"{funcname()}(): failed to get active profile"
	profile = status['profile']

	status = updates.download_updates(client.conn, profile.db)
	assert not status.error(), f"{funcname()}: failed to download updates"


if __name__ == '__main__':
		test_download_updates()