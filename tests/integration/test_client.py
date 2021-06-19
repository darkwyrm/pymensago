import os
from pymensago.client import MensagoClient
import shutil
import time

def setup_test(name):
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
	test_folder = setup_test('test_client_connect')
	client = MensagoClient(test_folder)
	
	status = client.connect('example.com')
	assert not status.error()

	client.disconnect()


if __name__ == '__main__':
	test_connect()

