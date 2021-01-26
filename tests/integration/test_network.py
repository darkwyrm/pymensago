from integration_setup import setup_test, config_server
import pyanselus.serverconn as serverconn # pylint: disable=import-error

import pyanselus.serverconn as serverconn

def test_connect():
	'''Tests just the basic connection to the server and parsing the greeting'''
	conn = serverconn.ServerConnection()
	status = conn.connect('localhost', 2001)

	assert not status.error(), f"test_connect(): failed to connect to server: {status.info()}"
	conn.disconnect()


def test_login():
	'''Test the PLAIN login process functions'''

	dbconn = setup_test()
	config = config_server(dbconn)

	conn = serverconn.ServerConnection()
	status = conn.connect('localhost', 2001)
	assert not status.error(), f"test_login(): failed to connect to server: {status.info()}"

	status = serverconn.login(conn, config['admin_wid'], config['oekey'])
	assert not status.error(), f"test_login(): login failed: {status.info()}"

	# TODO: finish once serverconn.regcode is implemented

	conn.disconnect()

if __name__ == '__main__':
	test_connect()
