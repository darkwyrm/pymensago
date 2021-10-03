import inspect
import os
import shutil
import time

import pymensago.dbfs as dbfs
from pymensago.encryption import Password
import pymensago.userprofile as userprofile
import pymensago.utils as utils
from pymensago.workspace import Workspace

def funcname() -> str: 
	frames = inspect.getouterframes(inspect.currentframe())
	return frames[1].function


def setup_test_profile(name):
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


def test_dbpath():
	'''Tests make_path_dblocal()'''

	for testpath in [ '/', '/foo', 'foo', '/foo/bar' ]:
		assert dbfs.validate_dbpath(testpath), f"{funcname()}: failed valid path {testpath}"

		path = dbfs.DBPath(testpath)
		assert path.path != '', f"{funcname()}: failed constructing valid dbpath {testpath}"
	
	for testpath in [ '', '/foo/', dbfs.DBPath('foo'), ' /foo ', '\\foo' ]:
		assert not dbfs.validate_dbpath(testpath), f"{funcname()}: passed invalid path {testpath}"

	assert dbfs.DBPath('/foo/').path != '/foo', \
		f"{funcname()}: DBPath constructor init adjustment failure: '/foo/'"
	assert dbfs.DBPath(' /foo/ ').path != '/foo', \
		f"{funcname()}: DBPath constructor init adjustment failure: '/foo/'"
	
	assert dbfs.DBPath('/foo/bar/baz').basename() == 'baz', \
		f"{funcname()}: DBPath.basename() failure: '/foo/bar/baz'"
	assert dbfs.DBPath('/foo/bar/1234.5678.11111111').basename() == '1234.5678.11111111', \
		f"{funcname()}: DBPath.basename() failure: '/foo/bar/1234.5678.11111111'"


def test_make_dblocal():
	'''Tests make_path_dblocal()'''
	
	profile_test_folder = setup_test_profile('make_dblocal')
	pman = userprofile.profman
	pman.load_profiles(profile_test_folder)
	profile = pman.get_active_profile()['profile']
	w = Workspace(profile.db, 'primary')
	status = w.generate(utils.UserID('admin'), utils.Domain('example.com'), 
		utils.UUID('89aa5480-36c6-42d1-b0fe-d06803e0ae15'), Password('MyS3cretPassw*rd'))
	assert not status.error(), f"{funcname()}: failed to generate workspace: " + status.error()
	status = profile.set_identity(w)
	assert not status.error(), f"{funcname()}: failed to set workspace identity: " + status.error()
	
	status = dbfs.load_folder_maps(profile.db)
	assert not status.error(), f"{funcname()}: failed to load folder maps: " + status.error()
	map = status['maps']
	invmap = dict()
	for k,v in map.items():
		invmap[v] = k
	
	testpath = f"/ wsp 89aa5480-36c6-42d1-b0fe-d06803e0ae15 " + \
		f"{invmap['/messages']} 12345.1234.11111111-1111-1111-111111111111"
	status = userprofile.make_path_dblocal(profile, testpath)
	assert not status.error(), f"{funcname()}: subtest #1 error: " + status.error()
	assert status['path'] == '/messages/12345.1234.11111111-1111-1111-111111111111', \
		 f"{funcname()}: subtest #1 returned incorrect value: " + status['path']
	

if __name__ == '__main__':
	test_dbpath()
	test_make_dblocal()

