# pylint: disable=import-error
from integration_setup import setup_test, init_server, init_admin, reset_workspace_dir
import pymensago.serverconn as serverconn

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

if __name__ == '__main__':
	test_mkdir()
