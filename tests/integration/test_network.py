#from integration_setup import setup_test
import pyanselus.serverconn as serverconn # pylint: disable=import-error

def test_connect():
	'''Tests just the basic connection to the server and parsing the greeting'''
	conn = serverconn.ServerConnection()
	status = conn.connect('localhost', 2001)

	assert not status.error(), f"test_connect(): failed to connect to server: {status.info()}"
	conn.disconnect()



if __name__ == '__main__':
	test_connect()
