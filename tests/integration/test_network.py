from pymensago.contact import Name
from pycryptostring import CryptoString

from tests.integration.integration_setup import setup_test, init_server, user1_profile_data, \
	setup_profile, setup_profile_base, funcname, admin_profile_data, regcode_user
from pymensago.client import MensagoClient
from pymensago.config import load_server_config
from pymensago.encryption import EncryptionPair, Password
import pymensago.iscmds as iscmds
import pymensago.serverconn as serverconn
import pymensago.userprofile as userprofile
import pymensago.utils as utils

def test_send():
	'''Tests the SEND command'''
	# TODO: Implement test_send()


def test_set_status():
	'''Test the SETSTATUS command'''
	dbconn = setup_test()
	dbdata = init_server(dbconn)
	test_folder = setup_profile_base('test_setstatus')
	status = setup_profile(test_folder, dbdata, admin_profile_data)

	conn = serverconn.ServerConnection()
	status = conn.connect('localhost', 2001)
	assert not status.error(), f"test_set_workstatus(): failed to connect to server: {status.info()}"

	status = regcode_user(conn, dbdata, admin_profile_data, dbdata['admin_regcode'])
	assert not status.error(), f"test_set_workstatus(): regcode_user failed: {status.info()}"

	# Preregister the regular user
	regdata = iscmds.preregister(conn, user1_profile_data['wid'], user1_profile_data['uid'],
				user1_profile_data['domain'])
	assert not regdata.error(), f"{funcname()}: uid preregistration failed"
	assert regdata['domain'].as_string() == 'example.com' and 'wid' in regdata \
		and 'regcode' in regdata and regdata['uid'].as_string() == 'csimons', \
		f"{funcname()}: user prereg failed to return expected data"
	conn.disconnect()

	# Log in as the user and set up the profile
	client = MensagoClient(test_folder)
	status = client.pman.create_profile('user1')
	assert not status.error(), f"{funcname()}: client failed to create test user profile"
	status = client.pman.activate_profile('user1')
	assert not status.error(), f"{funcname()}: client failed to switch to test user profile"

	status = client.connect(utils.Domain('example.com'))
	assert not status.error(), f"{funcname()}: client failed to connect to server"
	status = client.redeem_regcode(user1_profile_data['address'], regdata['regcode'], 'Some*1Pass',
								Name('Corbin', 'Simons'))
	assert not status.error(), f"{funcname()}: client failed to regcode test user"
	client.logout()

	# Log out as the user, switch to the admin, and perform the reset
	status = client.pman.activate_profile('primary')
	assert not status.error(), f"{funcname()}: client failed to switch to back to admin profile"
	status = client.login(utils.MAddress('admin/example.com'))
	assert not status.error(), f"{funcname()}: client failed to log back in as admin"

	status = iscmds.setstatus(client.conn, user1_profile_data['wid'], 'disabled')
	assert not status.error(), f"test_set_workstatus(): set_workstatus failed: {status.info()}"

	conn.disconnect()


if __name__ == '__main__':
	# test_set_status()
	test_send()
