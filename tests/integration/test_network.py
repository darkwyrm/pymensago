from integration_setup import setup_test, init_server
from pyanselus.cryptostring import CryptoString
from pyanselus.encryption import EncryptionPair, Password, SigningPair
from pyanselus.keycard import UserEntry
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
	config = init_server(dbconn)

	conn = serverconn.ServerConnection()
	status = conn.connect('localhost', 2001)
	assert not status.error(), f"test_login(): failed to connect to server: {status.info()}"

	password = Password('Linguini2Pegboard*Album')
	devid = '14142135-9c22-4d3e-84a3-2aa281f65714'
	keypair = EncryptionPair(
		CryptoString(r'CURVE25519:mO?WWA-k2B2O|Z%fA`~s3^$iiN{5R->#jxO@cy6{'),
		CryptoString(r'CURVE25519:2bLf2vMA?GA2?L~tv<PA9XOw6e}V~ObNi7C&qek>'	)
	)
	status = serverconn.regcode(conn, 'admin', config['admin_regcode'], password.hashstring, 
		devid, keypair, '')
	assert not status.error(), f"test_login(): regcode failed: {status.info()}"

	status = serverconn.login(conn, config['admin_wid'], CryptoString(config['oekey']))
	assert not status.error(), f"test_login(): login phase failed: {status.info()}"

	status = serverconn.password(conn, config['admin_wid'], password.hashstring)
	assert not status.error(), f"test_login(): password phase failed: {status.info()}"

	status = serverconn.device(conn, devid, keypair)
	assert not status.error(), f"test_login(): device phase failed: {status.info()}"

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


def test_addentry():
	'''Tests the addentry() command'''
	dbconn = setup_test()
	config = init_server(dbconn)

	conn = serverconn.ServerConnection()
	status = conn.connect('localhost', 2001)
	assert not status.error(), f"test_addentry(): failed to connect to server: {status.info()}"

	password = Password('Linguini2Pegboard*Album')
	devid = '14142135-9c22-4d3e-84a3-2aa281f65714'
	crepair = EncryptionPair(
		CryptoString(r'CURVE25519:mO?WWA-k2B2O|Z%fA`~s3^$iiN{5R->#jxO@cy6{'),
		CryptoString(r'CURVE25519:2bLf2vMA?GA2?L~tv<PA9XOw6e}V~ObNi7C&qek>'	)
	)

	crspair = SigningPair(
		CryptoString(r'ED25519:E?_z~5@+tkQz!iXK?oV<Zx(ec;=27C8Pjm((kRc|'),
		CryptoString(r'ED25519:u4#h6LEwM6Aa+f<++?lma4Iy63^}V$JOP~ejYkB;')
	)

	epair = EncryptionPair(
		CryptoString(r'CURVE25519:Umbw0Y<^cf1DN|>X38HCZO@Je(zSe6crC6X_C_0F'),
		CryptoString(r'CURVE25519:Bw`F@ITv#sE)2NnngXWm7RQkxg{TYhZQbebcF5b$'	)
	)

	status = serverconn.regcode(conn, 'admin', config['admin_regcode'], password.hashstring, 
		devid, crepair, '')
	assert not status.error(), f"test_addentry(): regcode failed: {status.info()}"

	status = serverconn.login(conn, config['admin_wid'], CryptoString(config['oekey']))
	assert not status.error(), f"test_addentry(): login phase failed: {status.info()}"

	status = serverconn.password(conn, config['admin_wid'], password.hashstring)
	assert not status.error(), f"test_addentry(): password phase failed: {status.info()}"

	status = serverconn.device(conn, devid, crepair)
	assert not status.error(), f"test_addentry(): device phase failed: {status.info()}"

	entry = UserEntry()
	entry.set_fields({
		'Name':'Administrator',
		'Workspace-ID':config['admin_wid'],
		'User-ID':'admin',
		'Domain':'example.com',
		'Contact-Request-Verification-Key':crspair.get_public_key(),
		'Contact-Request-Encryption-Key':crepair.get_public_key(),
		'Public-Encryption-Key':epair.get_public_key()
	})

	status = serverconn.addentry(conn, entry, CryptoString(config['ovkey']), crspair)	
	assert not status.error(), f"test_addentry: failed to add entry: {status.info()}"

	status = serverconn.iscurrent(conn, 1, config['admin_wid'])
	assert not status.error(), "test_addentry(): admin iscurrent() success check failed: " \
		f"{status.info()}"

	status = serverconn.iscurrent(conn, 2, config['admin_wid'])
	assert not status.error(), "test_addentry(): admin iscurrent() failure check failed: " \
		f"{status.info()}"

	conn.disconnect()


if __name__ == '__main__':
	# test_connect()
	# test_login()
	# test_iscurrent()
	test_addentry()
