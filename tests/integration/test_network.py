from pycryptostring import CryptoString

from tests.integration.integration_setup import setup_test, init_server, init_admin, init_user, \
	setup_admin_profile, setup_profile_base, funcname
from pymensago.config import load_server_config
from pymensago.encryption import EncryptionPair, Password
import pymensago.iscmds as iscmds
import pymensago.serverconn as serverconn
import pymensago.userprofile as userprofile
import pymensago.utils as utils

def test_addentry():
	'''Tests the addentry() command'''
	dbconn = setup_test()
	dbdata = init_server(dbconn)
	test_folder = setup_profile_base('test_addentry')
	status = setup_admin_profile(test_folder, dbdata)

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
	test_folder = setup_profile_base('test_devkey')
	status = setup_admin_profile(test_folder, dbdata)
	
	status = userprofile.profman.get_active_profile()
	assert not status.error(), f"{funcname()}: failed to get active profile"
	profile = status['profile']

	conn = serverconn.ServerConnection()
	status = conn.connect('localhost', 2001)
	assert not status.error(), f"{funcname()}(): failed to connect to server: {status.info()}"

	status = init_admin(conn, dbdata)
	assert not status.error(), f"{funcname()}(): init_admin failed: {status.info()}"

	newdevpair = EncryptionPair(
		CryptoString(r'CURVE25519:mO?WWA-k2B2O|Z%fA`~s3^$iiN{5R->#jxO@cy6{'),
		CryptoString(r'CURVE25519:2bLf2vMA?GA2?L~tv<PA9XOw6e}V~ObNi7C&qek>'	)
	)

	status = iscmds.devkey(conn, profile.devid, dbdata['admin_devpair'], newdevpair)
	assert not status.error(), f"{funcname()}(): error returned: {status.info()}"

	conn.disconnect()


def test_getwid():
	'''Tests iscmds.getwid(), which returns a WID for an Mensago address'''

	dbconn = setup_test()
	dbdata = init_server(dbconn)
	test_folder = setup_profile_base(funcname())
	status = setup_admin_profile(test_folder, dbdata)

	conn = serverconn.ServerConnection()
	status = conn.connect('localhost', 2001)
	assert not status.error(), f"test_getwid(): failed to connect to server: {status.info()}"

	status = init_admin(conn, dbdata)
	assert not status.error(), f"test_getwid(): init_admin failed: {status.info()}"

	status = iscmds.getwid(conn, utils.UserID('admin'), utils.Domain('example.com'))
	assert not status.error(), f"test_getwid(): getwid failed: {status.info()}"
	assert status['Workspace-ID'].value == dbdata['admin_wid'].value, \
		"test_getwid(): admin wid mismatch"

	conn.disconnect()


def test_iscurrent():
	'''Tests the iscurrent() command'''

	dbconn = setup_test()
	dbdata = init_server(dbconn)
	test_folder = setup_profile_base(funcname())
	status = setup_admin_profile(test_folder, dbdata)

	conn = serverconn.ServerConnection()
	status = conn.connect('localhost', 2001)
	assert not status.error(), f"{funcname()}(): failed to connect to server: {status.info()}"

	status = iscmds.iscurrent(conn, 1, utils.UUID())
	assert not status.error(), f"{funcname()}(): org failure check failed: {status.info()}"

	status = iscmds.iscurrent(conn, 2, utils.UUID())
	assert not status.error(), f"{funcname()}(): org success check failed: {status.info()}"


def test_orgcard():
	'''Tests the orgcard command'''

	dbconn = setup_test()
	dbdata = init_server(dbconn)
	test_folder = setup_profile_base(funcname())
	status = setup_admin_profile(test_folder, dbdata)

	conn = serverconn.ServerConnection()
	status = conn.connect('localhost', 2001)
	assert not status.error(), f"{funcname()}(): failed to connect to server: {status.info()}"

	status = iscmds.orgcard(conn, 1, -1)
	assert not status.error() and 'card' in status, ""

	card = status['card']
	assert card.type == 'Organization', f"{funcname()}(): subtest #1 wrong card type received"
	assert len(card.entries) == 2, f"{funcname()}(): subtest #1 card had wrong number of entries"

	status = iscmds.orgcard(conn, 0, -1)
	assert not status.error() and 'card' in status, ""

	card = status['card']
	assert card.type == 'Organization', f"{funcname()}(): subtest #2 wrong card type received"
	assert len(card.entries) == 1, f"{funcname()}(): subtest #2 card had wrong number of entries"
	
	conn.disconnect()


def test_preregister_regcode():
	'''Test the preregister and regcode commands'''
	dbconn = setup_test()
	dbdata = init_server(dbconn)
	test_folder = setup_profile_base(funcname())
	status = setup_admin_profile(test_folder, dbdata)

	conn = serverconn.ServerConnection()
	status = conn.connect('localhost', 2001)
	assert not status.error(), f"{funcname()}(): failed to connect to server: {status.info()}"

	status = userprofile.profman.get_active_profile()
	profile = None
	assert not status.error(), f"{funcname()}: failed to obtain active profile"
	profile = status['profile']

	password = Password('Linguini2Pegboard*Album')
	keypair = EncryptionPair(
		CryptoString(r'CURVE25519:mO?WWA-k2B2O|Z%fA`~s3^$iiN{5R->#jxO@cy6{'),
		CryptoString(r'CURVE25519:2bLf2vMA?GA2?L~tv<PA9XOw6e}V~ObNi7C&qek>'	)
	)
	status = iscmds.regcode(conn, utils.MAddress('admin/example.com'), dbdata['admin_regcode'],
		password.hashstring, profile.devid, keypair)
	assert not status.error(), f"{funcname()}: regcode failed: {status.info()}"

	status = iscmds.login(conn, dbdata['admin_wid'], CryptoString(dbdata['oekey']))
	assert not status.error(), f"{funcname()}: login phase failed: {status.info()}"

	status = iscmds.password(conn, password.hashstring)
	assert not status.error(), f"{funcname()}: password phase failed: {status.info()}"

	status = iscmds.device(conn, profile.devid, keypair)
	assert not status.error(), f"{funcname()}: device phase failed: " \
		f"{status.info()}"

	status = iscmds.preregister(conn, utils.UUID(), utils.UserID('csimons'), 
		utils.Domain('example.com'))
	assert not status.error(), f"{funcname()}: uid preregistration failed"
	assert status['domain'].as_string() == 'example.com' and 'wid' in status and 'regcode' in status, \
		f"{funcname()}: failed to return expected data"

	regdata = status
	password = Password('MyS3cretPassw*rd')
	devpair = EncryptionPair()
	devid = utils.UUID()
	devid.generate()
	status = iscmds.regcode(conn, utils.MAddress('csimons/example.com'), regdata['regcode'], 
		password.hashstring, devid, devpair)
	assert not status.error(), f"{funcname()}: uid regcode failed"

	conn.disconnect()


def test_register():
	'''Test worskpace registration'''
	
	# Registration testing only works when the server uses either network or public mode
	serverdbdata = load_server_config()
	if serverdbdata['global']['registration'] not in ['network', 'public']:
		return

	dbconn = setup_test()
	dbdata = init_server(dbconn)
	test_folder = setup_profile_base('test_register')
	status = setup_admin_profile(test_folder, dbdata)
	
	status = userprofile.profman.get_active_profile()
	assert not status.error(), f"{funcname()}: failed to get active profile"
	profile = status['profile']

	conn = serverconn.ServerConnection()
	status = conn.connect('localhost', 2001)
	assert not status.error(), f"test_login(): failed to connect to server: {status.info()}"
	
	password = Password('MyS3cretPassw*rd')
	devpair = EncryptionPair()
	status = iscmds.register(conn, utils.UserID('csimons'), password.hashstring, profile.devid, 
		devpair.public)
	assert not status.error(), f"test_register: failed to register test account: {status.info()}"

	conn.disconnect()


def test_reset_password():
	'''Tests password reset code'''
	dbconn = setup_test()
	dbdata = init_server(dbconn)
	test_folder = setup_profile_base('test_reset_password')
	status = setup_admin_profile(test_folder, dbdata)

	conn = serverconn.ServerConnection()
	status = conn.connect('localhost', 2001)
	assert not status.error(), f"test_login(): failed to connect to server: {status.info()}"

	status = userprofile.profman.get_active_profile()
	profile = None
	assert not status.error(), f"{funcname()}: failed to obtain active profile"
	profile = status['profile']

	password = Password('Linguini2Pegboard*Album')
	keypair = EncryptionPair(
		CryptoString(r'CURVE25519:mO?WWA-k2B2O|Z%fA`~s3^$iiN{5R->#jxO@cy6{'),
		CryptoString(r'CURVE25519:2bLf2vMA?GA2?L~tv<PA9XOw6e}V~ObNi7C&qek>'	)
	)
	status = iscmds.regcode(conn, utils.MAddress('admin/example.com'), dbdata['admin_regcode'], 
		password.hashstring, profile.devid, keypair)
	assert not status.error(), f"test_reset_password(): regcode failed: {status.info()}"

	status = iscmds.login(conn, dbdata['admin_wid'], CryptoString(dbdata['oekey']))
	assert not status.error(), f"test_reset_password(): login phase failed: {status.info()}"

	status = iscmds.password(conn, password.hashstring)
	assert not status.error(), f"test_reset_password(): password phase failed: {status.info()}"

	status = iscmds.device(conn, profile.devid, keypair)
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
	test_folder = setup_profile_base('test_set_password')
	status = setup_admin_profile(test_folder, dbdata)

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
	test_folder = setup_profile_base('test_setstatus')
	status = setup_admin_profile(test_folder, dbdata)

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
	test_folder = setup_profile_base('test_unregister')
	status = setup_admin_profile(test_folder, dbdata)

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

	status = iscmds.password(conn, dbdata['user_password'].hashstring)
	assert not status.error(), f"test_unregister(): password phase failed: {status.info()}"

	status = iscmds.device(conn, dbdata['user_devid'], dbdata['user_devpair'])
	assert not status.error(), f"test_unregister(): device phase failed: {status.info()}"

	status = iscmds.unregister(conn, dbdata['user_password'].hashstring, utils.UUID())
	assert not status.error(), f"test_unregister(): unregister failed: {status.info()}"

	conn.disconnect()


def test_usercard():
	'''Tests the usercard command'''

	dbconn = setup_test()
	dbdata = init_server(dbconn)
	test_folder = setup_profile_base(funcname())
	status = setup_admin_profile(test_folder, dbdata)

	# TODO: Finish test_usercard()
	# A call to set up a test user here is needed

	conn = serverconn.ServerConnection()
	status = conn.connect('localhost', 2001)
	assert not status.error(), f"{funcname()}(): failed to connect to server: {status.info()}"

	status = iscmds.usercard(conn, utils.MAddress('csimons/example.com'), 1, -1)
	assert not status.error(), \
		f"{funcname()}: subtest #1 usercard error {status.error()}: {status.info()}"

	card = status['card']
	assert card.type == 'User', f"{funcname()}(): subtest #1 wrong card type received"
	assert len(card.entries) == 2, f"{funcname()}(): subtest #1 card had wrong number of entries"

	status = iscmds.orgcard(conn, 0, -1)
	assert not status.error() and 'card' in status, ""

	card = status['card']
	assert card.type == 'User', f"{funcname()}(): subtest #2 wrong card type received"
	assert len(card.entries) == 1, f"{funcname()}(): subtest #2 card had wrong number of entries"
	
	conn.disconnect()


if __name__ == '__main__':
	# test_addentry()
	# test_connect()
	# test_devkey()
	# test_iscurrent()
	# test_orgcard()
	# test_preregister_regcode()
	# test_register()
	# test_reset_password()
	# test_set_password()
	# test_set_status()
	# test_unregister()
	test_usercard()
