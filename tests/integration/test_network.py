# pylint: disable=import-error
from integration_setup import setup_test, init_server, load_server_config_file, init_admin
from pyanselus.cryptostring import CryptoString
from pyanselus.encryption import EncryptionPair, Password
import pyanselus.serverconn as serverconn

def test_addentry():
	'''Tests the addentry() command'''
	dbconn = setup_test()
	dbdata = init_server(dbconn)

	conn = serverconn.ServerConnection()
	status = conn.connect('localhost', 2001)
	assert not status.error(), f"test_addentry(): failed to connect to server: {status.info()}"

	# Moved all the test code to integration_setup.init_admin(), because that kind of setup is 
	# needed for other tests.
	status = init_admin(conn, dbdata)
	assert not status.error(), f"test_addentry(): init_admin failed: {status.info()}"

	conn.disconnect()


def test_connect():
	'''Tests just the basic connection to the server and parsing the greeting'''
	conn = serverconn.ServerConnection()
	status = conn.connect('localhost', 2001)

	assert not status.error(), f"test_connect(): failed to connect to server: {status.info()}"
	conn.disconnect()


def test_getwid():
	'''Tests serverconn.getwid(), which returns a WID for an Anselus address'''

	dbconn = setup_test()
	dbdata = init_server(dbconn)

	conn = serverconn.ServerConnection()
	status = conn.connect('localhost', 2001)
	assert not status.error(), f"test_addentry(): failed to connect to server: {status.info()}"

	status = init_admin(conn, dbdata)
	assert not status.error(), f"test_addentry(): init_admin failed: {status.info()}"

	status = serverconn.getwid(conn, 'admin', 'example.com')
	assert not status.error(), f"test_getwid(): getwid failed: {status.info()}"
	assert status['Workspace-ID'] == dbdata['admin_wid'], "test_getwid(): admin wid mismatch"

	conn.disconnect()


def test_iscurrent_org():
	'''Tests the iscurrent() command'''

	dbconn = setup_test()
	init_server(dbconn)

	conn = serverconn.ServerConnection()
	status = conn.connect('localhost', 2001)
	assert not status.error(), f"test_login(): failed to connect to server: {status.info()}"

	status = serverconn.iscurrent(conn, 1)
	assert not status.error(), f"test_iscurrent(): org failure check failed: {status.info()}"

	status = serverconn.iscurrent(conn, 2)
	assert not status.error(), f"test_iscurrent(): org success check failed: {status.info()}"


def test_preregister_regcode():
	'''Test the preregister and regcode commands'''
	dbconn = setup_test()
	dbdata = init_server(dbconn)

	conn = serverconn.ServerConnection()
	status = conn.connect('localhost', 2001)
	assert not status.error(), f"test_login(): failed to connect to server: {status.info()}"

	password = Password('Linguini2Pegboard*Album')
	devid = '14142135-9c22-4d3e-84a3-2aa281f65714'
	keypair = EncryptionPair(
		CryptoString(r'CURVE25519:mO?WWA-k2B2O|Z%fA`~s3^$iiN{5R->#jxO@cy6{'),
		CryptoString(r'CURVE25519:2bLf2vMA?GA2?L~tv<PA9XOw6e}V~ObNi7C&qek>'	)
	)
	status = serverconn.regcode(conn, 'admin', dbdata['admin_regcode'], password.hashstring, 
		devid, keypair, '')
	assert not status.error(), f"test_preregister_regcode(): regcode failed: {status.info()}"

	status = serverconn.login(conn, dbdata['admin_wid'], CryptoString(dbdata['oekey']))
	assert not status.error(), f"test_preregister_regcode(): login phase failed: {status.info()}"

	status = serverconn.password(conn, dbdata['admin_wid'], password.hashstring)
	assert not status.error(), f"test_preregister_regcode(): password phase failed: {status.info()}"

	status = serverconn.device(conn, devid, keypair)
	assert not status.error(), "test_preregister_regcode(): device phase failed: " \
		f"{status.info()}"

	status = serverconn.preregister(conn, '', 'csimons', 'example.net')
	assert not status.error(), "test_preregister_regcode(): uid preregistration failed"
	assert status['domain'] == 'example.net' and 'wid' in status and 'regcode' in status and \
		status['uid'] == 'csimons', "test_preregister_regcode(): failed to return expected data"

	regdata = status
	password = Password('MyS3cretPassw*rd')
	devpair = EncryptionPair()
	status = serverconn.regcode(conn, 'csimons', regdata['regcode'], password.hashstring,
		'11111111-1111-1111-1111-111111111111', devpair, 'example.net')
	assert not status.error(), "test_preregister_regcode(): uid regcode failed"

	conn.disconnect()


def test_register():
	'''Test worskpace registration'''
	
	# Registration testing only works when the server uses either network or public mode
	serverdbdata = load_server_config_file()
	if serverdbdata['global']['registration'] not in ['network', 'public']:
		return

	dbconn = setup_test()
	init_server(dbconn)

	conn = serverconn.ServerConnection()
	status = conn.connect('localhost', 2001)
	assert not status.error(), f"test_login(): failed to connect to server: {status.info()}"
	
	password = Password('MyS3cretPassw*rd')
	devpair = EncryptionPair()
	status = serverconn.register(conn, 'csimons', password.hashstring, devpair.public)
	assert not status.error(), f"test_register: failed to register test account: {status.info()}"

	conn.disconnect()


if __name__ == '__main__':
	# test_connect()
	# test_login_regcode()
	# test_iscurrent()
	# test_addentry()
	# test_register()
	test_preregister_regcode()
