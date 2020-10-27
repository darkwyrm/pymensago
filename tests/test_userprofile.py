'''This module tests the Profile and ProfileManager classes'''
import os
import shutil
import time

from userprofile import Profile, ProfileManager

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


def test_profile_class():
	'''Test the Profile class. It's not big or complicated, so several 
	tests are grouped together into one'''

	profile_test_folder = setup_test('profile_class')
	profile = Profile(profile_test_folder)
	profile.name = 'Primary'
	profile.id = 'ca7149eb-e533-4de6-90b1-3b0181d6fa16'
	profile.wid = 'b5a9367e-680d-46c0-bb2c-73932a6d4007'
	profile.domain = 'example.com'

	# Most of the class is so simple that it doesn't really need test
	# coverage, but set_from_dict and as_dict are a bit more than that.
	test_dict = {
		'name' : 'Primary',
		'isdefault' : False,
		'id' : 'ca7149eb-e533-4de6-90b1-3b0181d6fa16',
		'wid' : 'b5a9367e-680d-46c0-bb2c-73932a6d4007',
		'domain' : 'example.com',
		'port' : 2001
	}
	assert profile.as_dict() == test_dict, "Output did not match test data"

	profile = Profile(profile_test_folder)
	profile.set_from_dict(test_dict)
	assert 	profile.name == 'Primary' and \
			profile.isdefault is False and \
			profile.id == 'ca7149eb-e533-4de6-90b1-3b0181d6fa16' and \
			profile.wid == 'b5a9367e-680d-46c0-bb2c-73932a6d4007' and \
			profile.domain == 'example.com' and \
			profile.port == 2001, "set_dict() assignments did not match test data."


def test_profile_dbinit():
	'''Test the Profile class database initializer'''

	profile_test_folder = setup_test('profile_dbinit')
	profile = Profile(profile_test_folder)
	profile.name = 'Primary'
	profile.id = 'ca7149eb-e533-4de6-90b1-3b0181d6fa16'
	profile.wid = 'b5a9367e-680d-46c0-bb2c-73932a6d4007'
	profile.domain = 'example.com'

	assert profile.reset_db()


def test_pman_init():
	'''Tests initialization of ProfileManager objects. Oddly enough, this 
	tests a lot of parts of the class'''

	# Because so much is done in the constructor, this unit performs basic tests on the following:
	# save_profiles()
	# load_profiles()
	# __index_for_profile()
	# create_profile()
	# get_default_profile()
	# set_default_profile()
	# activate_profile()
	# reset_db()

	profile_test_folder = setup_test('pman_init')
	pman = ProfileManager(profile_test_folder)
	
	# Nothing has been done, so there should be 1 profile called 'primary'.
	assert not pman.error_state.error(), "ProfileManager didn't init: %s" % pman.error_state.error()
	assert len(pman.profiles) == 1, "Profile folder bootstrap didn't have a profile"
	assert pman.active_index == 0, 'Active profile index not 0'
	assert pman.default_profile == 'primary', 'Init profile not primary'


def test_pman_create():
	'''Tests ProfileManager's create() method'''
	profile_test_folder = setup_test('pman_create')
	pman = ProfileManager(profile_test_folder)

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
	pman = ProfileManager(profile_test_folder)

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
	pman = ProfileManager(profile_test_folder)

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
	pman = ProfileManager(profile_test_folder)

	# Activate tests: empty name (fail), nonexistent name, successful call 
	status = pman.create_profile('secondary')
	assert not status.error(), "activate_profile: failed to create test profile"

	status = pman.activate_profile(None)
	assert status.error(), "activate_profile: failed to handle empty profile name"

	status = pman.activate_profile('foo')
	assert status.error(), "activate_profile: failed to handle nonexistent profile"
	
	status = pman.activate_profile('secondary')
	assert not status.error(), "activate_profile: failed to activate profile"
