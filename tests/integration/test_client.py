import os
import shutil
import time

from integration_setup import setup_test, init_server, load_server_config
from pymensago.client import MensagoClient
from pymensago.encryption import EncryptionPair, Password
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
	
	test_folder = setup_profile('test_client_connect')
	client = MensagoClient(test_folder)

	dbconn = setup_test()
	dbdata = init_server(dbconn)

	status = client.register_account('example.com', 'MyS3cretPassw*rd', utils.UserID('csimons'))
	assert not status.error(), f"test_register_account: failed to register test account: {status.info()}"



if __name__ == '__main__':
	# test_connect()
	test_register()
