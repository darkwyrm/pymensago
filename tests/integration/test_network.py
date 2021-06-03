from pycryptostring import CryptoString

from .integration_setup import setup_test, init_server, load_server_config_file, init_admin, \
	init_user
from pymensago.encryption import EncryptionPair, Password
import pymensago.iscmds as iscmds
import pymensago.serverconn as serverconn
from pymensago.utils import MAddress

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


def test_devkey():
	'''Tests the devkey() command'''
	dbconn = setup_test()
	dbdata = init_server(dbconn)

	conn = serverconn.ServerConnection()
	status = conn.connect('localhost', 2001)
	assert not status.error(), f"test_devkey(): failed to connect to server: {status.info()}"

	status = init_admin(conn, dbdata)
	assert not status.error(), f"test_devkey(): init_admin failed: {status.info()}"

	newdevpair = EncryptionPair(
		CryptoString(r'CURVE25519:mO?WWA-k2B2O|Z%fA`~s3^$iiN{5R->#jxO@cy6{'),
		CryptoString(r'CURVE25519:2bLf2vMA?GA2?L~tv<PA9XOw6e}V~ObNi7C&qek>'	)
	)

	status = iscmds.devkey(conn, dbdata['admin_devid'], dbdata['admin_devpair'], newdevpair)
	assert not status.error(), f"test_devkey(): error returned: {status.info()}"

	conn.disconnect()


def test_getwid():
	'''Tests iscmds.getwid(), which returns a WID for an Mensago address'''

	dbconn = setup_test()
	dbdata = init_server(dbconn)

	conn = serverconn.ServerConnection()
	status = conn.connect('localhost', 2001)
	assert not status.error(), f"test_getwid(): failed to connect to server: {status.info()}"

	status = init_admin(conn, dbdata)
	assert not status.error(), f"test_getwid(): init_admin failed: {status.info()}"

	status = iscmds.getwid(conn, 'admin', 'example.com')
	assert not status.error(), f"test_getwid(): getwid failed: {status.info()}"
	assert status['Workspace-ID'] == dbdata['admin_wid'], "test_getwid(): admin wid mismatch"

	conn.disconnect()


def test_iscurrent():
	'''Tests the iscurrent() command'''

	dbconn = setup_test()
	init_server(dbconn)

	conn = serverconn.ServerConnection()
	status = conn.connect('localhost', 2001)
	assert not status.error(), f"test_login(): failed to connect to server: {status.info()}"

	status = iscmds.iscurrent(conn, 1)
	assert not status.error(), f"test_iscurrent(): org failure check failed: {status.info()}"

	status = iscmds.iscurrent(conn, 2)
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
	status = iscmds.regcode(conn, MAddress('admin/example.com'), dbdata['admin_regcode'],
		password.hashstring, keypair)
	assert not status.error(), f"test_preregister_regcode(): regcode failed: {status.info()}"

	status = iscmds.login(conn, dbdata['admin_wid'], CryptoString(dbdata['oekey']))
	assert not status.error(), f"test_preregister_regcode(): login phase failed: {status.info()}"

	status = iscmds.password(conn, dbdata['admin_wid'], password.hashstring)
	assert not status.error(), f"test_preregister_regcode(): password phase failed: {status.info()}"

	status = iscmds.device(conn, devid, keypair)
	assert not status.error(), "test_preregister_regcode(): device phase failed: " \
		f"{status.info()}"

	status = iscmds.preregister(conn, '', 'csimons', 'example.com')
	assert not status.error(), "test_preregister_regcode(): uid preregistration failed"
	assert status['domain'] == 'example.com' and 'wid' in status and 'regcode' in status and \
		status['uid'] == 'csimons', "test_preregister_regcode(): failed to return expected data"

	regdata = status
	password = Password('MyS3cretPassw*rd')
	devpair = EncryptionPair()
	status = iscmds.regcode(conn, MAddress('csimons/example.com'), regdata['regcode'], 
		password.hashstring, devpair)
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
	status = iscmds.register(conn, 'csimons', password.hashstring, devpair.public)
	assert not status.error(), f"test_register: failed to register test account: {status.info()}"

	conn.disconnect()


def test_reset_password():
	'''Tests password reset code'''
	dbconn = setup_test()
	dbdata = init_server(dbconn)

	conn = serverconn.ServerConnection()
	status = conn.connect('localhost', 2001)
	assert not status.error(), f"test_login(): failed to connect to server: {status.info()}"

	password = Password('Linguini2Pegboard*Album')
	keypair = EncryptionPair(
		CryptoString(r'CURVE25519:mO?WWA-k2B2O|Z%fA`~s3^$iiN{5R->#jxO@cy6{'),
		CryptoString(r'CURVE25519:2bLf2vMA?GA2?L~tv<PA9XOw6e}V~ObNi7C&qek>'	)
	)
	status = iscmds.regcode(conn, MAddress('admin/example.com'), dbdata['admin_regcode'], 
		password.hashstring, keypair)
	assert not status.error(), f"test_reset_password(): regcode failed: {status.info()}"
	devid = status['devid']

	status = iscmds.login(conn, dbdata['admin_wid'], CryptoString(dbdata['oekey']))
	assert not status.error(), f"test_reset_password(): login phase failed: {status.info()}"

	status = iscmds.password(conn, dbdata['admin_wid'], password.hashstring)
	assert not status.error(), f"test_reset_password(): password phase failed: {status.info()}"

	status = iscmds.device(conn, devid, keypair)
	assert not status.error(), "test_reset_password(): device phase failed: " \
		f"{status.info()}"

	status = init_user(conn, dbdata)
	assert not status.error(), f"test_reset_password(): user init failed: {status.info()}"

	status = iscmds.reset_password(conn, dbdata['user_wid'])
	assert not status.error(), f"test_reset_password(): password reset failed: {status.info()}"
	resetdata = status

	status = iscmds.logout(conn)
	assert not status.error(), f"test_reset_password(): admin logout failed: {status.info()}"

	newpassword = Password('SomeOth3rPassw*rd')
	status = iscmds.passcode(conn, dbdata['user_wid'], resetdata['resetcode'],
		newpassword.hashstring)
	assert not status.error(), f"test_reset_password(): passcode failed: {status.info()}"


def test_set_password():
	'''Test the SETPASSWORD command'''
	dbconn = setup_test()
	dbdata = init_server(dbconn)

	conn = serverconn.ServerConnection()
	status = conn.connect('localhost', 2001)
	assert not status.error(), f"test_set_password(): failed to connect to server: {status.info()}"

	# Moved all the test code to integration_setup.init_admin(), because that kind of setup is 
	# needed for other tests.
	status = init_admin(conn, dbdata)
	assert not status.error(), f"test_set_password(): init_admin failed: {status.info()}"

	badpassword = Password('MyS3cretPassw*rd')
	newpassword = Password('Renovate-Baggy-Grunt-Override')
	status = iscmds.setpassword(conn, badpassword.hashstring, newpassword.hashstring)
	assert status.error() and status['Code'] == 402, \
		"test_set_password: failed to catch bad password"
	
	status = iscmds.setpassword(conn, dbdata['admin_password'].hashstring,
		newpassword.hashstring)
	assert not status.error(), "test_set_password: failed to update password"

	conn.disconnect()


def test_set_status():
	'''Test the SETSTATUS command'''
	dbconn = setup_test()
	dbdata = init_server(dbconn)

	conn = serverconn.ServerConnection()
	status = conn.connect('localhost', 2001)
	assert not status.error(), f"test_set_workstatus(): failed to connect to server: {status.info()}"

	status = init_admin(conn, dbdata)
	assert not status.error(), f"test_set_workstatus(): init_admin failed: {status.info()}"

	status = init_user(conn, dbdata)
	assert not status.error(), f"test_set_workstatus(): init_user failed: {status.info()}"

	status = iscmds.setstatus(conn, dbdata['user_wid'], 'disabled')
	assert not status.error(), f"test_set_workstatus(): set_workstatus failed: {status.info()}"

	conn.disconnect()


def test_unregister():
	'''Tests the unregister() command'''
	dbconn = setup_test()
	dbdata = init_server(dbconn)

	conn = serverconn.ServerConnection()
	status = conn.connect('localhost', 2001)
	assert not status.error(), f"test_unregister(): failed to connect to server: {status.info()}"

	status = init_admin(conn, dbdata)
	assert not status.error(), f"test_unregister(): init_admin failed: {status.info()}"

	status = init_user(conn, dbdata)
	assert not status.error(), f"test_unregister(): init_user failed: {status.info()}"
	
	status = iscmds.logout(conn)
	assert not status.error(), f"test_unregister(): logout failed: {status.info()}"

	status = iscmds.login(conn, dbdata['user_wid'], CryptoString(dbdata['oekey']))
	assert not status.error(), f"test_unregister(): user login phase failed: {status.info()}"

	status = iscmds.password(conn, dbdata['user_wid'], dbdata['user_password'].hashstring)
	assert not status.error(), f"test_unregister(): password phase failed: {status.info()}"

	status = iscmds.device(conn, dbdata['user_devid'], dbdata['user_devpair'])
	assert not status.error(), f"test_unregister(): device phase failed: {status.info()}"

	status = iscmds.unregister(conn, dbdata['user_password'].hashstring, '')
	assert not status.error(), f"test_unregister(): unregister failed: {status.info()}"

	conn.disconnect()


if __name__ == '__main__':
	# test_addentry()
	# test_connect()
	# test_devkey()
	# test_iscurrent()
	# test_login_regcode()
	# test_preregister_regcode()
	# test_register()
	# test_reset_password()
	# test_set_password()
	test_set_status()
	# test_unregister()
