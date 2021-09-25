import inspect
import os
import shutil
import time

import pymensago.config as config

def funcname() -> str: 
	frames = inspect.getouterframes(inspect.currentframe())
	return frames[1].function


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


def test_set_get_int():
	'''Tests getting and setting an integer field'''
	test_folder = setup_test('config_setget_int')
	dbpath = os.path.join(test_folder, 'storage.db')
	status = config.load(dbpath)
	assert not status.error(), f"{funcname()}: failed to load/init db"

	assert config.set_int('testint', 10), f"{funcname()}: failed to set integer field testint"
	assert config.get_int('testint') == 10, f"{funcname()}: failed to get integer field testint"


if __name__ == '__main__':
	test_set_get_int()
