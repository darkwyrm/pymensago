'''This module tests the Profile and ProfileManager classes'''
import inspect
import os
import shutil
import time

from pymensago.encryption import Password
from pymensago.userinfo import save_user_list_field
from pymensago.userprofile import Profile
import pymensago.utils as utils
from pymensago.workspace import Workspace

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


def test_save_user_list_field():
	'''Tests save_user_list_field()'''

	unit_test_folder = setup_test('save_user_list_field')
	profile = Profile(unit_test_folder)
	profile.name = 'Primary'
	profile.wid = utils.UUID('b5a9367e-680d-46c0-bb2c-73932a6d4007')
	profile.domain = utils.Domain('example.com')
	profile.activate()
	pw = Password()
	status = pw.set('CheeseCustomerSmugnessDelegatorGenericUnaudited')
	assert not status.error()

	w = Workspace(profile.db, unit_test_folder)
	status = w.generate(utils.UserID('testname'), profile.domain, profile.wid, pw)
	assert not status.error(), f"Failed to generate workspace: {status.info()}"

	nicknamelist = [ 'nickname1', 'nickname2', 'nickname3' ]
	save_user_list_field(profile.db, 'Nicknames', nicknamelist)

	cursor = profile.db.cursor()
	cursor.execute("""SELECT fieldname,fieldvalue FROM userinfo WHERE fieldname LIKE 'Nicknames.%' 
		ORDER BY fieldname""")
	results = cursor.fetchall()
	assert results and len(results) == 3, f"{funcname()}(): wrong number of records saved"
	assert results[0][0] == 'Nicknames.0' and results[1][0] == 'Nicknames.1' and \
		results[2][0] == 'Nicknames.2', f"{funcname()}(): field names incorrect"

if __name__ == '__main__':
	test_save_user_list_field()
