import os
import random
import time
import uuid

from retval import RetVal

# pylint: disable=import-error
from integration_setup import setup_test, init_server, init_admin, reset_workspace_dir
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
		return RetVal.wrap_exception(e)
	
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

	status = serverconn.copy(conn, f"/ wsp {dbdata['admin_wid']} {testname}", 
		f"/ wsp {dbdata['admin_wid']} 11111111-1111-1111-1111-111111111111")
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

	status = serverconn.delete(conn, f"/ wsp {dbdata['admin_wid']} {testname}")
	assert not status.error(), f"test_delete(): error deleting test file: {status.info()}"

	conn.disconnect()


def test_download():
	'''Tests the DOWNLOAD command'''
	
	dbconn = setup_test()
	dbdata = init_server(dbconn)

	reset_workspace_dir(dbdata)

	conn = serverconn.ServerConnection()
	status = conn.connect('localhost', 2001)
	assert not status.error(), f"test_download: failed to connect to server: {status.info()}"

	status = init_admin(conn, dbdata)
	assert not status.error(), f"test_download: init_admin failed: {status.info()}"

	local_admin_dir = os.path.join(dbdata['configfile']['global']['workspace_dir'],
		dbdata['admin_wid'])
	local_inner_dir = os.path.join(local_admin_dir, '11111111-1111-1111-1111-111111111111')
	serverconn.mkdir(conn, local_inner_dir)

	status = make_test_file(local_admin_dir)
	assert not status.error(), f"test_download: error creating test file: {status.info()}"
	testname = status['name']

	status = serverconn.download(conn, f"/ wsp {dbdata['admin_wid']} {testname}", local_inner_dir)
	assert not status.error(), f"test_download: download failed: {status.info()}"

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

	status = serverconn.delete(conn, f"/ wsp {dbdata['admin_wid']} {testname}")
	assert not status.error(), f"test_exists(): error checking for test file: {status.info()}"

	conn.disconnect()


def test_getquotainfo():
	'''Tests the GETQUOTAINFO command'''

	dbconn = setup_test()
	dbdata = init_server(dbconn)

	reset_workspace_dir(dbdata)

	conn = serverconn.ServerConnection()
	status = conn.connect('localhost', 2001)
	assert not status.error(), f"test_getquotainfo(): failed to connect to server: {status.info()}"

	status = init_admin(conn, dbdata)
	assert not status.error(), f"test_getquotainfo: init_admin failed: {status.info()}"

	admin_dir = os.path.join(dbdata['configfile']['global']['workspace_dir'],
		dbdata['admin_wid'])

	status = make_test_file(admin_dir)
	assert not status.error(), f"test_getquotainfo(): error creating test file: {status.info()}"

	status = serverconn.getquotainfo(conn)
	assert not status.error(), f"test_getquotainfo(): error checking for test file: {status.info()}"

	conn.disconnect()


def test_listfiles():
	'''Tests the LIST command'''

	dbconn = setup_test()
	dbdata = init_server(dbconn)

	reset_workspace_dir(dbdata)

	conn = serverconn.ServerConnection()
	status = conn.connect('localhost', 2001)
	assert not status.error(), f"test_listfiles(): failed to connect to server: {status.info()}"

	status = init_admin(conn, dbdata)
	assert not status.error(), f"test_listfiles: init_admin failed: {status.info()}"

	admin_dir = os.path.join(dbdata['configfile']['global']['workspace_dir'],
		dbdata['admin_wid'])
	subdir = '11111111-1111-1111-1111-111111111111'

	os.mkdir(os.path.join(admin_dir, subdir))
	for i in range(1,6):
		tempname = '.'.join([str(1000 * i), '500', str(uuid.uuid4())])
		try:
			fhandle = open(os.path.join(admin_dir, subdir, tempname), 'w')
		except Exception as e:
			assert False, f"test_listfiles: failed to create test file: {str(e)}"
		
		fhandle.write('0' * 500)
		fhandle.close()

	status = serverconn.listfiles(conn, f"/ wsp {dbdata['admin_wid']} {subdir}", 3000)
	assert not status.error() and len(status['files']) == 3, \
		f"test_listfiles(): error listing test files: {status.info()}"

	conn.disconnect()


def test_listdirs():
	'''Tests the LISTDIRS command'''

	dbconn = setup_test()
	dbdata = init_server(dbconn)

	reset_workspace_dir(dbdata)

	conn = serverconn.ServerConnection()
	status = conn.connect('localhost', 2001)
	assert not status.error(), f"test_listdirs(): failed to connect to server: {status.info()}"

	status = init_admin(conn, dbdata)
	assert not status.error(), f"test_listdirs: init_admin failed: {status.info()}"

	admin_dir = os.path.join(dbdata['configfile']['global']['workspace_dir'],
		dbdata['admin_wid'])
	subdir = '11111111-1111-1111-1111-111111111111'

	os.mkdir(os.path.join(admin_dir, subdir))
	for i in range(2,7):
		tempname = '-'.join([(str(i) * 8), (str(i) * 4), (str(i) * 4), (str(i) * 4), (str(i) * 12)])
		try:
			os.mkdir(os.path.join(admin_dir, '11111111-1111-1111-1111-111111111111', tempname))
		except Exception as e:
			assert False, 'test_listdirs: failed to create test directory: ' + e
		
		make_test_file(os.path.join(admin_dir, '11111111-1111-1111-1111-111111111111'))

	status = serverconn.listdirs(conn, f"/ wsp {dbdata['admin_wid']} {subdir}")
	assert not status.error() and len(status['directories']) == 5, \
		f"test_listdirs(): error listing test directories: {status.info()}"

	conn.disconnect()


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

	status = serverconn.mkdir(conn, 
		f"/ wsp {dbdata['admin_wid']} 11111111-1111-1111-1111-111111111111")
	assert not status.error(), f"test_mkdir: mkdir failed: {status.info()}"

	conn.disconnect()


def test_move():
	'''Tests the MOVE command'''
	
	dbconn = setup_test()
	dbdata = init_server(dbconn)

	reset_workspace_dir(dbdata)

	conn = serverconn.ServerConnection()
	status = conn.connect('localhost', 2001)
	assert not status.error(), f"test_move(): failed to connect to server: {status.info()}"

	status = init_admin(conn, dbdata)
	assert not status.error(), f"test_move: init_admin failed: {status.info()}"

	admin_dir = os.path.join(dbdata['configfile']['global']['workspace_dir'],
		dbdata['admin_wid'])
	inner_dir = os.path.join(admin_dir, '11111111-1111-1111-1111-111111111111')
	os.mkdir(inner_dir)

	status = make_test_file(admin_dir)
	assert not status.error(), f"test_move(): error creating test file: {status.info()}"
	testname = status['name']

	status = serverconn.copy(conn, f"/ wsp {dbdata['admin_wid']} {testname}", 
		f"/ wsp {dbdata['admin_wid']} 11111111-1111-1111-1111-111111111111")
	assert not status.error(), f"test_move(): error moving test file: {status.info()}"

	conn.disconnect()


def test_rmdir():
	'''Tests the RMDIR command'''

	dbconn = setup_test()
	dbdata = init_server(dbconn)

	reset_workspace_dir(dbdata)

	conn = serverconn.ServerConnection()
	status = conn.connect('localhost', 2001)
	assert not status.error(), f"test_rmdir: failed to connect to server: {status.info()}"

	status = init_admin(conn, dbdata)
	assert not status.error(), f"test_rmdir: init_admin failed: {status.info()}"

	status = serverconn.mkdir(conn, 
		f"/ wsp {dbdata['admin_wid']} 11111111-1111-1111-1111-111111111111")
	assert not status.error(), f"test_rmdir: rmdir failed: {status.info()}"

	conn.disconnect()
	

def test_select():
	'''Tests the SELECT command'''

	dbconn = setup_test()
	dbdata = init_server(dbconn)

	reset_workspace_dir(dbdata)

	conn = serverconn.ServerConnection()
	status = conn.connect('localhost', 2001)
	assert not status.error(), f"test_select: failed to connect to server: {status.info()}"

	status = init_admin(conn, dbdata)
	assert not status.error(), f"test_select: init_admin failed: {status.info()}"

	status = serverconn.mkdir(conn, 
		f"/ wsp {dbdata['admin_wid']} 11111111-1111-1111-1111-111111111111")
	assert not status.error(), f"test_select: directory change failed: {status.info()}"

	conn.disconnect()


def test_setquota():
	'''Tests the SETQUOTA command'''

	dbconn = setup_test()
	dbdata = init_server(dbconn)

	reset_workspace_dir(dbdata)

	conn = serverconn.ServerConnection()
	status = conn.connect('localhost', 2001)
	assert not status.error(), f"test_setquota: failed to connect to server: {status.info()}"

	status = init_admin(conn, dbdata)
	assert not status.error(), f"test_setquota: init_admin failed: {status.info()}"

	status = serverconn.setquota(conn, dbdata['admin_wid'], 10240)
	assert not status.error(), f"test_setquota: quota size change failed: {status.info()}"

	conn.disconnect()


def test_upload():
	'''Tests the UPLOAD command'''
	dbconn = setup_test()
	dbdata = init_server(dbconn)

	reset_workspace_dir(dbdata)

	conn = serverconn.ServerConnection()
	status = conn.connect('localhost', 2001)
	assert not status.error(), f"test_upload: failed to connect to server: {status.info()}"

	status = init_admin(conn, dbdata)
	assert not status.error(), f"test_upload: init_admin failed: {status.info()}"

	admin_dir = os.path.join(dbdata['configfile']['global']['workspace_dir'],
		dbdata['admin_wid'])
	inner_dir = f"/ wsp {dbdata['admin_wid']} 11111111-1111-1111-1111-111111111111"
	serverconn.mkdir(conn, inner_dir)

	status = make_test_file(admin_dir)
	assert not status.error(), f"test_upload: error creating test file: {status.info()}"
	testname = status['name']

	status = serverconn.upload(conn, f"{admin_dir}/{testname}", inner_dir)
	assert not status.error(), f"test_upload: upload failed: {status.info()}"
	assert "FileName" in status, "test_upload: file name missing"

	conn.disconnect()

if __name__ == '__main__':
	# test_copy()
	# test_delete()
	test_download()
	# test_exists()
	# test_getquotainfo()
	# test_listfiles()
	# test_listdirs()
	# test_mkdir()
	# test_move()
	# test_select()
	# test_setquota()
	# test_upload()
