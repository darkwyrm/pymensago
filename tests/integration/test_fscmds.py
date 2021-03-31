import os
import random
import time
import uuid

# pylint: disable=import-error
from integration_setup import setup_test, init_server, init_admin, reset_workspace_dir
from pymensago.retval import RetVal, ExceptionThrown
import pymensago.serverconn as serverconn

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
		return RetVal(ExceptionThrown, e)
	
	fhandle.write('0' * file_size)
	fhandle.close()
	
	return RetVal().set_values({ 'name':file_name, 'size':file_size })


def test_copy():
	'''Tests the COPY command'''
	
	dbconn = setup_test()
	dbdata = init_server(dbconn)

	reset_workspace_dir(dbdata)

	conn = serverconn.ServerConnection()
	status = conn.connect('localhost', 2001)
	assert not status.error(), f"test_copy(): failed to connect to server: {status.info()}"

	status = init_admin(conn, dbdata)
	assert not status.error(), f"test_copy: init_admin failed: {status.info()}"

	admin_dir = os.path.join(dbdata['configfile']['global']['workspace_dir'],
		dbdata['admin_wid'])
	inner_dir = os.path.join(admin_dir, '11111111-1111-1111-1111-111111111111')
	os.mkdir(inner_dir)

	status = make_test_file(admin_dir)
	assert not status.error(), f"test_copy(): error creating test file: {status.info()}"
	testname = status['name']

	status = serverconn.copy(conn, f"/ {dbdata['admin_wid']} {testname}", 
		f"/ {dbdata['admin_wid']} 11111111-1111-1111-1111-111111111111")
	assert not status.error(), f"test_copy(): error copying test file: {status.info()}"

	conn.disconnect()


def test_delete():
	'''Tests the DELETE command'''

	dbconn = setup_test()
	dbdata = init_server(dbconn)

	reset_workspace_dir(dbdata)

	conn = serverconn.ServerConnection()
	status = conn.connect('localhost', 2001)
	assert not status.error(), f"test_delete(): failed to connect to server: {status.info()}"

	status = init_admin(conn, dbdata)
	assert not status.error(), f"test_delete: init_admin failed: {status.info()}"

	admin_dir = os.path.join(dbdata['configfile']['global']['workspace_dir'],
		dbdata['admin_wid'])

	status = make_test_file(admin_dir)
	assert not status.error(), f"test_delete(): error creating test file: {status.info()}"
	testname = status['name']

	status = serverconn.delete(conn, f"/ {dbdata['admin_wid']} {testname}")
	assert not status.error(), f"test_delete(): error deleting test file: {status.info()}"

	conn.disconnect()


def test_exists():
	'''Tests the EXISTS command'''

	dbconn = setup_test()
	dbdata = init_server(dbconn)

	reset_workspace_dir(dbdata)

	conn = serverconn.ServerConnection()
	status = conn.connect('localhost', 2001)
	assert not status.error(), f"test_exists(): failed to connect to server: {status.info()}"

	status = init_admin(conn, dbdata)
	assert not status.error(), f"test_exists: init_admin failed: {status.info()}"

	admin_dir = os.path.join(dbdata['configfile']['global']['workspace_dir'],
		dbdata['admin_wid'])

	status = make_test_file(admin_dir)
	assert not status.error(), f"test_exists(): error creating test file: {status.info()}"
	testname = status['name']

	status = serverconn.delete(conn, f"/ {dbdata['admin_wid']} {testname}")
	assert not status.error(), f"test_exists(): error checking for test file: {status.info()}"

	conn.disconnect()


# def test_getquotainfo():
# def test_list():
# def test_listdirs():


def test_mkdir():
	'''Tests the MKDIR command'''

	dbconn = setup_test()
	dbdata = init_server(dbconn)

	reset_workspace_dir(dbdata)

	conn = serverconn.ServerConnection()
	status = conn.connect('localhost', 2001)
	assert not status.error(), f"test_mkdir(): failed to connect to server: {status.info()}"

	status = init_admin(conn, dbdata)
	assert not status.error(), f"test_mkdir: init_admin failed: {status.info()}"

	status = serverconn.mkdir(conn, f"/ {dbdata['admin_wid']} 11111111-1111-1111-1111-111111111111")
	assert not status.error(), f"test_mkdir: mkdir failed: {status.info()}"

	conn.disconnect()

# def test_move():
# def test_rmdir():
# def test_select():
# def test_setquota():
# def test_upload():

if __name__ == '__main__':
	# test_copy()
	# test_delete()
	test_exists()
	# test_mkdir()
