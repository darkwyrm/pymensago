'''The userprofile module handles user profile management'''
import json
import os
import pathlib
import platform
import shutil
import sqlite3
import uuid

from retval import RetVal, ResourceExists, ExceptionThrown, BadParameterValue, ResourceNotFound
import utils

BadProfileList = 'BadProfileList'
InvalidProfile = 'InvalidProfile'

class Profile:
	'''Encapsulates data for user profiles'''
	def __init__(self, path: str):
		if not path:
			raise ValueError('path may not be empty')
		
		self.name = os.path.basename(path)
		self.path = path
		self.isdefault = False
		self.id = ''
		self.wid = ''
		self.domain = ''
		self.port = 2001
		self.db = None

	def __str__(self):
		return str(self.as_dict())

	def make_id(self):
		'''Generates a new profile ID for the object'''
		self.id = str(uuid.uuid4())

	def address(self) -> str:
		'''Returns the identity workspace address for the profile'''
		return '/'.join([self.wid, self.domain])
	
	def serverstring(self) -> str:
		'''Returns the identity workspace address for the profile including port'''
		return ':'.join([self.address(),self.port])
	
	def activate(self):
		'''Connects the profile to its associated database'''
		dbpath = os.path.join(self.path, 'storage.db')
		if os.path.exists(dbpath):
			self.db = sqlite3.connect(dbpath)
		else:
			self.reset_db()
	
	def deactivate(self):
		'''Disconnects the profile from its associated database'''
		if self.db:
			self.db.close()
			self.db = None
	
	def as_dict(self) -> dict:
		'''Returns the state of the profile as a dictionary'''
		return {
			'name' : self.name,
			'isdefault' : self.isdefault,
			'id' : self.id,
			'wid' : self.wid,
			'domain' : self.domain,
			'port' : self.port
		}
	
	def set_from_dict(self, data: dict):
		'''Assigns profile data from a dictionary'''
		
		for k,v in data.items():
			if k in [ 'name', 'isdefault', 'id', 'wid', 'domain', 'port' ]:
				setattr(self, k, v)
	
	def is_valid(self) -> bool:
		'''Returns true if data stored in the profile object is valid'''
		if self.name and utils.validate_uuid(self.id):
			return True
		
		return False

	def reset_db(self) -> sqlite3.Connection:
		'''This function reinitializes the database to empty, taking a path to the file used by the 
		SQLite database. Returns a handle to an open SQLite3 connection.
		'''
		if not os.path.exists(self.path):
			os.mkdir(self.path)
		
		dbpath = os.path.join(self.path, 'storage.db')
		if os.path.exists(dbpath):
			try:
				os.remove(dbpath)
			except Exception as e:
				print('Unable to delete old database %s: %s' % (dbpath, e))
		
		self.db = sqlite3.connect(dbpath)
		cursor = self.db.cursor()

		sqlcmds = [ '''
			CREATE TABLE workspaces (
				"wid" TEXT NOT NULL UNIQUE,
				"userid" TEXT,
				"domain" TEXT,
				"password" TEXT,
				"pwhashtype" TEXT,
				"type" TEXT
			);''', '''
			CREATE table "folders"(
				"fid" TEXT NOT NULL UNIQUE,
				"address" TEXT NOT NULL,
				"keyid" TEXT NOT NULL,
				"path" TEXT NOT NULL,
				"permissions" TEXT NOT NULL
			);''', '''
			CREATE table "sessions"(
				"address" TEXT NOT NULL,
				"devid" TEXT NOT NULL,
				"devname" TEXT,
				"enctype" TEXT NOT NULL,
				"public_key" TEXT NOT NULL,
				"private_key" TEXT NOT NULL
			);''', '''
			CREATE table "keys"(
				"keyid" TEXT NOT NULL UNIQUE,
				"address" TEXT NOT NULL,
				"type" TEXT NOT NULL,
				"category" TEXT NOT NULL,
				"private" TEXT NOT NULL,
				"public" TEXT,
				"algorithm" TEXT NOT NULL
			);''', '''
			CREATE table "keycards"(
				"fingerprint" TEXT NOT NULL UNIQUE,
				"fptype" TEXT NOT NULL,
				"cardtype" TEXT NOT NULL,
				"carddata" TEXT NOT NULL,
				"identity" TEXT NOT NULL,
				"expires" TEXT NOT NULL
			);''', '''
			CREATE table "messages"(
				"id" TEXT NOT NULL UNIQUE,
				"from"  TEXT NOT NULL,
				"address" TEXT NOT NULL,
				"cc"  TEXT,
				"bcc" TEXT,
				"date" TEXT NOT NULL,
				"thread_id" TEXT NOT NULL,
				"subject" TEXT,
				"body" TEXT,
				"attachments" TEXT
			);''', '''
			CREATE TABLE "contacts" (
				"id"	TEXT NOT NULL,
				"sensitivity"	TEXT NOT NULL,
				"source"	TEXT NOT NULL,
				"fieldname"	TEXT,
				"fieldvalue"	TEXT
			);''', '''
			CREATE TABLE "notes" (
				"id"	TEXT NOT NULL UNIQUE,
				"address" TEXT,
				"title"	TEXT,
				"body"	TEXT,
				"notebook"	TEXT,
				"tags"	TEXT,
				"created"	TEXT NOT NULL,
				"updated"	TEXT,
				"attachments"	TEXT
			);''', '''
			CREATE TABLE "files" (
				"id"	TEXT NOT NULL UNIQUE,
				"name"	TEXT NOT NULL,
				"type"	TEXT NOT NULL,
				"path"	TEXT NOT NULL
			);'''
		]

		for sqlcmd in sqlcmds:
			cursor = self.db.cursor()
			cursor.execute(sqlcmd)
		self.db.commit()
		return self.db

	def get_workspaces(self) -> list:
		'''Returns a list containing all subscribed workspaces in the profile'''
		# TODO: Implement
		return list()


class ProfileManager:
	'''Handles user profile management'''
	
	def __init__(self, profile_path=''):
		if profile_path:
			self.profile_folder = profile_path
		else:
			osname = platform.system().casefold()
			if osname == 'windows':
				self.profile_folder = os.path.join(os.getenv('LOCALAPPDATA'), 'anselus')
			else:
				self.profile_folder = os.path.join(os.getenv('HOME'), '.config','anselus')
		
		if not os.path.exists(self.profile_folder):
			os.mkdir(self.profile_folder)
		
		self.profiles = list()
		self.default_profile = ''
		self.active_index = -1
		self.profile_id = ''
		
		# Activate the default profile. If one doesn't exist, create one
		self.error_state = self.load_profiles()
		
		if not self.get_profiles():
			self.error_state = self.create_profile('primary')
			if not self.error_state.error():
				self.set_default_profile('primary')
		
		if not self.error_state.error():
			self.error_state = self.activate_profile(self.get_default_profile())

	def save_profiles(self) -> RetVal:
		'''
		Saves the current list of profiles to the profile list file.

		Returns:
		"error" : error state - string
		'''
		if self.error_state.error():
			return self.error_state
		
		profile_list_path = os.path.join(self.profile_folder, 'profiles.json')
		
		if not os.path.exists(self.profile_folder):
			os.mkdir(self.profile_folder)

		try:
			with open(profile_list_path, 'w') as fhandle:
				profile_data = list()
				for profile in self.profiles:

					if not profile.is_valid():
						return RetVal(InvalidProfile, profile.name)
					
					profile_data.append(profile.as_dict())

					item_folder = os.path.join(self.profile_folder, profile.name)
					if not os.path.exists(item_folder):
						os.mkdir(item_folder)

				json.dump(profile_data, fhandle, ensure_ascii=False, indent=1)
			
		except Exception as e:
			return RetVal(ExceptionThrown, e.__str__())

		return RetVal()

	def load_profiles(self) -> RetVal:
		'''
		Loads profile information from the specified JSON file stored in the top level of the 
		profile folder.

		Returns:
		"error" : string
		"profiles" : list
		'''
		profile_list_path = os.path.join(self.profile_folder, 'profiles.json')
		
		if os.path.exists(profile_list_path):
			profile_data = list()
			try:
				with open(profile_list_path, 'r') as fhandle:
					profile_data = json.load(fhandle)
				
			except Exception:
				return RetVal(BadProfileList)

			profiles = list()
			for item in profile_data:
				profile = Profile(os.path.join(self.profile_folder, item['name']))
				profile.set_from_dict(item)
				profiles.append(profile)
				if profile.isdefault:
					self.default_profile = profile.name

			self.profiles = profiles
		return RetVal()
	
	def __index_for_profile(self, name: str) -> int:
		'''Returns the numeric index of the named profile. Returns -1 on error'''
		if not name:
			return -1
		
		name_squashed = name.casefold()
		for i in range(0, len(self.profiles)):
			if name_squashed == self.profiles[i].name:
				return i
		return -1

	def create_profile(self, name) -> RetVal:
		'''
		Creates a profile with the specified name. Profile names are not case-sensitive.

		Returns: 
		RetVal error state also contains a copy of the created profile as "profile"
		'''
		if not name:
			return RetVal(BadParameterValue, "BUG: name may not be empty")
		
		name_squashed = name.casefold()
		if self.__index_for_profile(name_squashed) >= 0:
			return RetVal(ResourceExists, name)

		profile = Profile(os.path.join(self.profile_folder, name_squashed))
		profile.make_id()
		self.profiles.append(profile)

		if len(self.profiles) == 1:
			profile.isdefault = True
			self.default_profile = name
		
		status = self.save_profiles()
		if status.error():
			return status
		
		status.set_value("profile", profile)
		return status

	def delete_profile(self, name) -> RetVal:
		'''
		Deletes the named profile and all files on disk contained in it.
		'''
		if name == 'default':
			return RetVal(BadParameterValue, "'default' is reserved")
		
		if not name:
			return RetVal(BadParameterValue, "BUG: name may not be empty")
		
		name_squashed = name.casefold()
		itemindex = self.__index_for_profile(name_squashed)
		if itemindex < 0:
			return RetVal(ResourceNotFound, "%s doesn't exist" % name)

		profile = self.profiles.pop(itemindex)
		if os.path.exists(profile.path):
			try:
				shutil.rmtree(profile.path)
			except Exception as e:
				return RetVal(ExceptionThrown, e.__str__())
		
		if profile.isdefault:
			if self.profiles:
				self.profiles[0].isdefault = True
		
		return self.save_profiles()

	def rename_profile(self, oldname, newname) -> RetVal:
		'''
		Renames a profile, leaving the profile ID unchanged.
		'''
		
		if not oldname or not newname:
			return RetVal(BadParameterValue, "BUG: name may not be empty")
		
		old_squashed = oldname.casefold()
		new_squashed = newname.casefold()

		if old_squashed == new_squashed:
			return RetVal()
		
		index = self.__index_for_profile(old_squashed)
		if index < 0:
			return RetVal(ResourceNotFound, "%s doesn't exist" % oldname)

		if self.__index_for_profile(new_squashed) >= 0:
			return RetVal(ResourceExists, "%s already exists" % newname)

		if index == self.active_index:
			self.profiles[index].deactivate()

		oldpath = pathlib.Path(self.profiles[index].path)
		newpath = oldpath.parent.joinpath(new_squashed)
		try:
			os.rename(oldpath, newpath)
		except Exception as e:
			if index == self.active_index:
				self.profiles[index].activate()
			return RetVal(ExceptionThrown, str(e))

		self.profiles[index].name = new_squashed
		self.profiles[index].path = newpath
		
		if index == self.active_index:
			self.profiles[index].activate()
		
		return self.save_profiles()
	
	def get_profiles(self) -> dict:
		'''Returns a list of loaded profiles'''
		return self.profiles
	
	def get_default_profile(self) -> str:
		'''
		Returns the name of the default profile. If one has not been set, it returns an empty string.
		'''
		for item in self.profiles:
			if item.isdefault:
				return item.name
		return ''

	def set_default_profile(self, name: str) -> RetVal:
		'''
		Sets the default profile. If there is only one profile -- or none at all -- this call has 
		no effect.
		'''
		if not name:
			return RetVal(BadParameterValue, "BUG: name may not be empty")
		
		if len(self.profiles) == 1:
			if self.profiles[0].isdefault:
				return RetVal()
			self.profiles[0].isdefault = True
			return self.save_profiles()
		
		oldindex = -1
		for i in range(0, len(self.profiles)):
			if self.profiles[i].isdefault:
				oldindex = i
		
		name_squashed = name.casefold()
		newindex = self.__index_for_profile(name_squashed)
		
		if newindex < 0:
			return RetVal(ResourceNotFound, "New profile %s not found" % name_squashed)
		
		if oldindex >= 0:
			if name_squashed == self.profiles[oldindex].name:
				return RetVal()
			self.profiles[oldindex].isdefault = False

		self.profiles[newindex].isdefault = True		
		return self.save_profiles()

	def activate_profile(self, name: str) -> RetVal:
		'''
		Activates the specified profile.

		Returns:
		"error" : string
		"wid" : string
		"host" : string
		"port" : integer
		'''
		if self.active_index >= 0:
			self.profiles[self.active_index].deactivate()
			self.active_index = -1
		
		if not name:
			return RetVal(BadParameterValue, "BUG: name may not be empty")
		
		name_squashed = name.casefold()
		active_index = self.__index_for_profile(name_squashed)
		if active_index < 0:
			return RetVal(ResourceNotFound, "%s doesn't exist" % name_squashed)
		
		self.profile_id = name_squashed

		self.active_index = active_index
		self.profiles[self.active_index].activate()
		
		out = RetVal()
		out.set_values({
			'wid' : self.profiles[active_index].wid,
			'host' : self.profiles[active_index].domain,
			'port' : self.profiles[active_index].port 
		})
		return out

	def get_active_profile(self) -> RetVal:
		'''Returns the active profile'''
		if self.active_index >= 0:
			return RetVal().set_value("profile", self.profiles[self.active_index])
		return RetVal(InvalidProfile,'No active profile')
