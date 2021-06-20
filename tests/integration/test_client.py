import os
import shutil
import time

from integration_setup import setup_test, init_server, load_server_config, init_admin
from pymensago.client import MensagoClient
import pymensago.iscmds as iscmds
from pymensago.encryption import Password
import pymensago.utils as utils

def setup_profile(name):
	'''Creates a new profile folder hierarchy'''
	test_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)),'testfiles')
	if not os.path.exists(test_folder):
		os.mkdir(test_folder)

	profiletest_folder = os.path.join(test_folder, name)
	while os.path.exists(profiletest_folder):
		try:
			shutil.rmtree(profiletest_folder)
		except:
			print("Waiting a second for test folder to unlock")
			time.sleep(1.0)
	os.mkdir(profiletest_folder)
	return profiletest_folder


def test_connect():
	'''Tests basic client connectivity'''
	test_folder = setup_profile('test_client_connect')
	client = MensagoClient(test_folder)
	
	status = client.connect('example.com')
	assert not status.error()

	client.disconnect()


def test_register():
	serverdbdata = load_server_config()
	if serverdbdata['global']['registration'] not in ['network', 'public']:
		return
	
	test_folder = setup_profile('test_client_register')
	client = MensagoClient(test_folder)

	dbconn = setup_test()
	init_server(dbconn)

	status = client.register_account('example.com', 'MyS3cretPassw*rd', utils.UserID('csimons'))
	assert not status.error(), f"test_register_account: failed to register test account: {status.info()}"


def test_regcode():
	serverdbdata = load_server_config()
	test_folder = setup_profile('test_client_regcode')
	client = MensagoClient(test_folder)

	dbconn = setup_test()
	dbdata = init_server(dbconn)

	status = client.connect(utils.Domain('example.com'))
	status = init_admin(client.conn, dbdata)

	userid = utils.UserID('33333333-3333-3333-3333-333333333333')
	status = iscmds.preregister(client.conn, userid, utils.UserID('csimons'),
		utils.Domain('example.com'))
	assert not status.error(), "init_user(): uid preregistration failed"
	assert status['domain'].as_string() == 'example.com' and \
		'wid' in status and \
		'regcode' in status and	\
		status['uid'].as_string() == 'csimons', "init_user(): failed to return expected data"

	regdata = status
	address = utils.MAddress('csimons/example.com')
	status = client.redeem_regcode(address, regdata['regcode'], 'MyS3cretPassw*rd')

	client.disconnect()

if __name__ == '__main__':
	# test_connect()
	# test_register()
	test_regcode()
