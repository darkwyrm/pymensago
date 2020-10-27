'''This module tests the workspace module'''
import os
import shutil
import time

from encryption import Password
from userprofile import Profile
from workspace import Workspace

def setup_test(name):
	'''Creates a new test folder hierarchy'''
	test_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)),'testfiles')
	if not os.path.exists(test_folder):
		os.mkdir(test_folder)

	unittest_folder = os.path.join(test_folder, name)
	while os.path.exists(unittest_folder):
		try:
			shutil.rmtree(unittest_folder)
		except:
			print("Waiting a second for test folder to unlock")
			time.sleep(1.0)
	os.mkdir(unittest_folder)
	return unittest_folder


def test_workspace_generate():
	'''Tests creating a workspace from scratch'''

	# Set up the test
	# 1) Create folder for unit test
	# 2) Create profile in unit test folder, including workspace database
	# 3) Connect to workspace database
	unit_test_folder = setup_test('workspace_generate')
	profile = Profile(unit_test_folder)
	profile.name = 'Primary'
	profile.id = 'ca7149eb-e533-4de6-90b1-3b0181d6fa16'
	profile.wid = 'b5a9367e-680d-46c0-bb2c-73932a6d4007'
	profile.domain = 'example.com'
	profile.activate()
	pw = Password()
	status = pw.Set('CheeseCustomerSmugnessDelegatorGenericUnaudited')
	assert not status.error()

	w = Workspace(profile.db, unit_test_folder)
	status = w.generate('testname', profile.domain, profile.wid, pw)
	assert not status.error(), "Failed to generate workspace"
