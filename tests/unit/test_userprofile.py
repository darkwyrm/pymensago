'''This module tests the Profile and ProfileManager classes'''
import inspect
import os
import shutil
import time

# pylint: disable=import-error
from pymensago.userprofile import Profile, ProfileManager

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


def test_profile_dbinit():
	'''Test the Profile class database initializer'''

	profile_test_folder = setup_test('profile_dbinit')
	profile = Profile(profile_test_folder)
	profile.name = 'primary'
	profile.wid = 'b5a9367e-680d-46c0-bb2c-73932a6d4007'
	profile.domain = 'example.com'

	assert profile.reset_db()


def test_pman_init():
	'''Tests initialization of ProfileManager objects. Oddly enough, this 
	tests a lot of parts of the class'''

	# Because so much is done in the constructor, this unit performs basic tests on the following:
	# load_profiles()
	# _index_for_profile()
	# create_profile()
	# get_default_profile()
	# set_default_profile()
	# activate_profile()
	# reset_db()

	profile_test_folder = setup_test('pman_init')
	pman = ProfileManager()
	status = pman.load_profiles(profile_test_folder)
	assert not status.error(), "test_pman_init: load_profiles failed"
	
	# Nothing has been done, so there should be 1 profile called 'primary'.
	assert len(pman.profiles) == 1, "Profile folder bootstrap didn't have a profile"
	assert pman.active_index == 0, 'Active profile index not 0'
	assert pman.default_profile == 'primary', 'Init profile not primary'


def test_pman_create():
	'''Tests ProfileManager's create() method'''
	profile_test_folder = setup_test('pman_create')
	pman = ProfileManager()
	status = pman.load_profiles(profile_test_folder)
	assert not status.error(), "test_pman_create: load_profiles failed"

	# Creation tests: empty name (fail), existing profile, new profile
	status = pman.create_profile(None)
	assert status.error(), "create_profile: failed to handle empty name"

	status = pman.create_profile('primary')
	assert status.error(), "create_profile: failed to handle existing profile"

	status = pman.create_profile('secondary')
	assert 'profile' in status and status['profile'], "Failed to get new profile"


def test_pman_delete():
	'''Tests ProfileManager's delete() method'''
	profile_test_folder = setup_test('pman_delete')
	pman = ProfileManager()
	status = pman.load_profiles(profile_test_folder)
	assert not status.error(), "test_pman_delete: load_profiles failed"

	# Deletion tests: empty name (fail), existing profile, nonexistent profile
	status = pman.create_profile('secondary')
	assert not status.error(), "delete_profile: failed to create regular profile"

	status = pman.delete_profile(None)
	assert status.error(), "delete_profile: failed to handle empty name"

	status = pman.delete_profile('secondary')
	assert not status.error(), "delete_profile: failed to delete existing profile"

	status = pman.delete_profile('secondary')
	assert status.error(), "delete_profile: failed to handle nonexistent profile"


def test_pman_rename():
	'''Tests ProfileManager's rename() method'''
	profile_test_folder = setup_test('pman_rename')
	pman = ProfileManager()
	status = pman.load_profiles(profile_test_folder)
	assert not status.error(), "test_pman_rename: load_profiles failed"

	# Rename tests: empty old name (fail), empty new name (fail), old name == new name, missing old
	# name profile, existing new name profile, successful rename
	status = pman.rename_profile(None, 'foo')
	assert status.error(), "rename_profile: failed to handle empty old name"

	status = pman.rename_profile('foo', None)
	assert status.error(), "rename_profile: failed to handle empty new name"
	
	status = pman.rename_profile('secondary', 'secondary')
	assert not status.error(), "rename_profile: failed to handle rename to self"

	status = pman.create_profile('foo')
	assert not status.error(), "rename_profile: failed to create test profile"

	status = pman.rename_profile('primary', 'foo')
	assert status.error(), "rename_profile: failed to handle existing new profile name"

	status = pman.rename_profile('foo', 'secondary')
	assert not status.error(), "rename_profile: failed to rename profile"


def test_pman_activate():
	'''Tests ProfileManager's activate() method'''
	profile_test_folder = setup_test('pman_activate')
	pman = ProfileManager()
	status = pman.load_profiles(profile_test_folder)
	assert not status.error(), "test_pman_activate: load_profiles failed"

	# Activate tests: empty name (fail), nonexistent name, successful call 
	status = pman.create_profile('secondary')
	assert not status.error(), "activate_profile: failed to create test profile"

	status = pman.activate_profile(None)
	assert status.error(), "activate_profile: failed to handle empty profile name"

	status = pman.activate_profile('foo')
	assert status.error(), "activate_profile: failed to handle nonexistent profile"
	
	status = pman.activate_profile('secondary')
	assert not status.error(), "activate_profile: failed to activate profile"


def test_pman_multitest():
	'''Performs multiple interactions with profiles to test similar to day-to-day usage'''

	profile_test_folder = setup_test(f"{funcname()}")
	pman = ProfileManager()
	status = pman.load_profiles(profile_test_folder)
	assert not status.error(), f"{funcname()}: load_profiles failed"

	status = pman.create_profile('secondary')
	assert not status.error(), f"{funcname()}: failed to create secondary profile"
	status = pman.activate_profile('secondary')
	assert not status.error(), f"{funcname()}: failed to activate secondary profile"
	status = pman.set_default_profile('secondary')
	assert not status.error(), f"{funcname()}: failed to set secondary profile as default"
	status = pman.rename_profile('primary', 'trash')
	assert not status.error(), f"{funcname()}: failed to rename primary profile to trash"
	status = pman.delete_profile('trash')
	assert not status.error(), f"{funcname()}: failed to delete trash profile"


if __name__ == '__main__':
	test_profile_dbinit()
	test_pman_init()
	test_pman_create()
	test_pman_delete()
	test_pman_rename()
	test_pman_activate()
	test_pman_multitest()

