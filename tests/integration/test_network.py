from integration_setup import setup_test, config_server
from pyanselus.pyanselus.cryptostring import CryptoString
from pyanselus.pyanselus.encryption import EncryptionPair
import pyanselus.pyanselus.serverconn as serverconn

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

	password = 'Linguini2Pegboard*Album'
	devid = '14142135-9c22-4d3e-84a3-2aa281f65714'
	keypair = EncryptionPair(
		CryptoString(r'CURVE25519:mO?WWA-k2B2O|Z%fA`~s3^$iiN{5R->#jxO@cy6{'),
		CryptoString(r'CURVE25519:2bLf2vMA?GA2?L~tv<PA9XOw6e}V~ObNi7C&qek>'	)
	)
	status = serverconn.regcode(conn, 'admin', config['admin_regcode'], password, devid, keypair,
		'')

	status = serverconn.login(conn, config['admin_wid'], config['oekey'])
	assert not status.error(), f"test_login(): login failed: {status.info()}"

	status = serverconn.password(conn, config['admin_wid'], password)
	assert not status.error(), f"test_password(): password phase failed: {status.info()}"

	status = serverconn.device(conn, devid, keypair)
	assert not status.error(), f"test_device(): device phase failed: {status.info()}"

	conn.disconnect()

if __name__ == '__main__':
	test_connect()
	test_login()
