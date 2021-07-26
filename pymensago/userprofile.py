'''The userprofile module handles user profile management'''
import json
import os
import pathlib
import platform
from pymensago.workspace import Workspace
import shutil
import sqlite3

from retval import ErrBusy, RetVal, ErrEmptyData, ErrUnimplemented, ErrExists, ErrBadValue, ErrNotFound
import pymensago.utils as utils


BadProfileList = 'BadProfileList'
InvalidProfile = 'InvalidProfile'

_db_setup_cmds = [ '''
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
		"devname" TEXT NOT NULL,
		"public_key" TEXT NOT NULL,
		"private_key" TEXT NOT NULL,
		"os" TEXT NOT NULL
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
		"rowid" INTEGER PRIMARY KEY AUTOINCREMENT,
		"owner" TEXT NOT NULL,
		"index" INTEGER,
		"entry" TEXT NOT NULL,
		"fingerprint" TEXT NOT NULL,
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
	CREATE TABLE "contactinfo" (
		"id" TEXT NOT NULL,
		"fieldname" TEXT NOT NULL,
		"fieldvalue" TEXT,
		"group" TEXT
	);''', '''
	CREATE TABLE "annotations" (
		"id" TEXT NOT NULL,
		"fieldname" TEXT NOT NULL,
		"fieldvalue" TEXT,
		"group" TEXT
	);''', '''
	CREATE TABLE "photos" (
		"id" TEXT NOT NULL,
		"source" TEXT NOT NULL,
		"type" TEXT NOT NULL,
		"photodata" BLOB,
		"group" TEXT
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


class Profile:
	'''Encapsulates data for user profiles'''
	def __init__(self, path: str):
		if not path:
			raise ValueError('path may not be empty')
		
		self.name = os.path.basename(path)
		self.path = path
		self.default = False
		self.userid = utils.UserID()
		self.wid = utils.UUID()
		self.domain = utils.Domain()
		self.db = None
		self.devid = utils.UUID()

		if os.path.exists(os.path.join(self.path, 'default.txt')):
			self.default = True
		
		status = self.load_config()
		if not self.devid.is_valid():
			self.devid.generate()
		
		if status.error():
			self.save_config()

	def activate(self) -> RetVal:
		'''Connects the profile to its associated database'''

		if not os.path.exists(self.path):
			try:
				os.mkdir(self.path)
			except Exception as e:
				return RetVal().wrap_exception(e)
		
		dbpath = os.path.join(self.path, 'storage.db')
		if os.path.exists(dbpath):
			self.db = sqlite3.connect(dbpath)
			return RetVal().set_value('connection', self.db)
		
		return self.reset_db()

	def load_config(self) -> RetVal:
		'''Loads the config file for the profile'''

		config_path = os.path.join(self.path, 'config.json')
		if os.path.exists(config_path):
			filedata = dict()
			with open(config_path, 'r') as fhandle:
				try:
					filedata = json.load(fhandle)
				except Exception as e:
					return RetVal().wrap_exception(e)
			status = self.devid.set(filedata['Device-ID'])
			if not status:
				self.devid.generate()
		else:
			return RetVal(ErrNotFound, 'profile config file missing')
		
		return RetVal()
	
	def save_config(self) -> RetVal:
		'''Saves the profile-specific configuration information to a file'''
		
		if self.devid.is_empty():
			return RetVal()
		
		config_path = os.path.join(self.path, 'config.json')
		if os.path.exists(config_path):
			try:
				os.unlink(config_path)
			except Exception as e:
				return RetVal().wrap_exception(e)
		
		filedata = { 'Device-ID': self.devid.as_string() }
		with open(config_path, 'w') as fhandle:
			try:
				filedata = json.dump(filedata, fhandle)
			except Exception as e:
				return RetVal().wrap_exception(e)
		
		return RetVal()
	
	def deactivate(self):
		'''Disconnects the profile from its associated database'''
		if self.db:
			self.db.close()
			self.db = None

	def set_default(self, is_default: bool) -> RetVal:
		'''Makes a profile the default'''

		filepath = os.path.join(self.path, 'default.txt')
		if is_default:
			if not os.path.exists(filepath):
				try:
					handle = open(filepath, 'w')
					handle.close()
				except Exception as e:
					return RetVal.wrap_exception()
				
		else:
			if os.path.exists(filepath):
				try:
					os.unlink(filepath)
				except Exception as e:
					return RetVal().wrap_exception(e)
		
		self.default = is_default
		return RetVal()

	def is_default(self) -> bool:
		''''Returns true if the profile is the default one'''
		return self.default
		
	def get_identity(self) -> utils.MAddress:
		'''Returns the identity workspace address for the profile'''
		
		out = utils.MAddress()
		if self.userid.is_valid() and self.domain.is_valid():
			out.set_from_userid(self.userid, self.domain)
			return out
		
		if self.wid.is_valid() and self.domain.is_valid():
			out.set_from_wid(self.wid, self.domain)
			return out
		
		# We got this far, which means we need to get the info from the profile database
		
		cursor = self.db.cursor()
		cursor.execute("SELECT wid,domain,userid FROM workspaces WHERE type = 'identity'")
		results = cursor.fetchone()
		if not results or not results[0]:
			return RetVal(ErrNotFound)

		if self.wid.is_empty():
			self.wid.set(results[0])
		if self.domain.is_empty():
			self.domain.set(results[1])
		if self.userid.is_empty():
			self.userid.set(results[2])

		if self.userid.is_valid() and self.domain.is_valid():
			out.set_from_userid(self.userid, self.domain)
			return out
		
		if self.wid.is_valid() and self.domain.is_valid():
			out.set_from_wid(self.wid, self.domain)
			return out
	
	def set_identity(self, w: Workspace) -> RetVal:
		'''Assigns an identity workspace to the profile. Because so much is tied to an identity 
		workspace, once this is set, it cannot be changed.'''

		if w.db and w.db != self.db:
			return RetVal(ErrBusy, f"Workspace {w.wid} already belongs to another profile")
		
		saved_db = w.db
		w.db = self.db
		status = w.add_to_db(w.pw)
		if status.error():
			w.db = saved_db
		
		self.wid = w.wid
		self.userid = w.uid
		self.domain = w.domain

		return status

	def reset_db(self) -> RetVal:
		'''This function reinitializes the database to empty, taking a path to the file used by the 
		SQLite database. The status includes the field 'connection' which contains a 
		sqlite3.Connection object.'''
		
		dbpath = os.path.join(self.path, 'storage.db')
		if os.path.exists(dbpath):
			try:
				os.remove(dbpath)
			except Exception as e:
				RetVal().wrap_exception(e)
		
		self.db = sqlite3.connect(dbpath)
		cursor = self.db.cursor()

		global _db_setup_cmds
		for sqlcmd in _db_setup_cmds:
			cursor = self.db.cursor()
			cursor.execute(sqlcmd)
		self.db.commit()
		return RetVal().set_value('connection', self.db)
	
	def resolve_address(self, address: utils.MAddress) -> RetVal:
		'''Resolves a Mensago address and returns a workspace ID in the field 'wid'''

		if address.id_type == 1:
			return RetVal().set_value('wid', address.id.as_string())
		
		cursor = self.db.cursor()
		cursor.execute("SELECT wid FROM workspaces WHERE userid=? AND domain=?", 
			(address.id.as_string(), address.domain.as_string()))
		results = cursor.fetchone()
		if not results or not results[0]:
			return RetVal(ErrNotFound)

		return RetVal().set_value('wid', utils.UUID(results[0]))


class ProfileManager:
	'''Handles user profile management'''
	
	def __init__(self):
		self.profiles = list()
		self.default_profile = ''
		self.active_index = -1
		self.error_state = RetVal()

	def load_profiles(self, profile_path='') -> RetVal:
		'''Loads profile information from the specified JSON file stored in the top level of the 
		profile folder.'''

		self.active_index = -1
		
		if profile_path:
			self.profile_folder = profile_path
		else:
			osname = platform.system().casefold()
			if osname == 'windows':
				self.profile_folder = os.path.join(os.getenv('LOCALAPPDATA'), 'mensago')
			else:
				self.profile_folder = os.path.join(os.getenv('HOME'), '.config','mensago')
		
		if not os.path.exists(self.profile_folder):
			os.mkdir(self.profile_folder)
		
		items = os.listdir(self.profile_folder)

		self.profiles = list()
		self.default_profile = ''
		for item in items:
			itempath = os.path.join(self.profile_folder, item)
			if not os.path.isdir(itempath):
				continue
			
			profile = Profile(itempath)
			self.profiles.append(profile)
			if profile.is_default():
				if self.default_profile:
					# If we have more than profile marked as default, the first one encountered
					# retains that status
					profile.set_default(False)
				else:
					self.default_profile = profile.name

		if not self.get_profiles():
			self.error_state = self.create_profile('primary')
			if not self.error_state.error():
				self.set_default_profile('primary')
		
		if not self.error_state.error():
			self.error_state = self.activate_profile(self.get_default_profile())

		return RetVal()
	
	def _index_for_profile(self, name: str) -> int:
		'''Returns the numeric index of the named profile. Returns -1 on error'''
		if not name:
			return -1
		
		name_squashed = name.casefold()
		for i in range(0, len(self.profiles)):
			if name_squashed == self.profiles[i].name:
				return i
		return -1

	def create_profile(self, name: str) -> RetVal:
		'''Creates a profile with the specified name. Profile names are expected to be all.

		Attached Values: 
		'profile': a copy of the created profile as "profile"'''

		if not name:
			return RetVal(ErrEmptyData, "BUG: name may not be empty")
		
		name_squashed = name.casefold()
		if self._index_for_profile(name_squashed) >= 0:
			return RetVal(ErrExists, f"profile {name} already exists")

		new_profile_path = os.path.join(self.profile_folder, name_squashed)
		try:
			os.mkdir(new_profile_path)
		except Exception as e:
			return RetVal().wrap_exception(e)

		profile = Profile(new_profile_path)
		self.profiles.append(profile)

		if len(self.profiles) == 1:
			profile.set_default(True)
			self.default_profile = name
		
		return RetVal().set_value("profile", profile)

	def delete_profile(self, name: str) -> RetVal:
		'''Deletes the named profile and all files on disk contained in it.'''

		if name == 'default':
			return RetVal(ErrBadValue, "'default' is reserved")
		
		if not name:
			return RetVal(ErrEmptyData, "BUG: profile name may not be empty")
		
		name_squashed = name.casefold()
		itemindex = self._index_for_profile(name_squashed)
		if itemindex < 0:
			return RetVal(ErrNotFound, "%s doesn't exist" % name)

		profile = self.profiles.pop(itemindex)
		if os.path.exists(profile.path):
			try:
				shutil.rmtree(profile.path)
			except Exception as e:
				return RetVal.wrap_exception(e)
		
		if profile.is_default() and self.profiles:
			self.profiles[0].set_default(True)
		
		return RetVal()

	def rename_profile(self, oldname, newname) -> RetVal:
		'''Renames a profile, leaving the profile ID unchanged.'''
		
		if not oldname or not newname:
			return RetVal(ErrEmptyData, "BUG: profile names may not be empty")
		
		old_squashed = oldname.casefold()
		new_squashed = newname.casefold()

		if old_squashed == new_squashed:
			return RetVal()
		
		index = self._index_for_profile(old_squashed)
		if index < 0:
			return RetVal(ErrNotFound, f"{oldname} doesn't exist")

		if self._index_for_profile(new_squashed) >= 0:
			return RetVal(ErrExists, f"{newname} already exists")

		if index == self.active_index:
			self.profiles[index].deactivate()

		oldpath = pathlib.Path(self.profiles[index].path)
		newpath = oldpath.parent.joinpath(new_squashed)
		try:
			os.rename(oldpath, newpath)
		except Exception as e:
			if index == self.active_index:
				self.profiles[index].activate()
			return RetVal.wrap_exception(e)

		self.profiles[index].name = new_squashed
		self.profiles[index].path = newpath
		
		if index == self.active_index:
			self.profiles[index].activate()
		
		return RetVal()
	
	def get_profiles(self) -> list:
		'''Returns a list of loaded profiles'''
		return self.profiles
	
	def get_default_profile(self) -> str:
		'''
		Returns the name of the default profile. If one has not been set, it returns an empty string.
		'''
		for item in self.profiles:
			if item.is_default():
				return item.name
		return ''

	def set_default_profile(self, name: str) -> RetVal:
		'''
		Sets the default profile. If there is only one profile -- or none at all -- this call has 
		no effect.
		'''
		if not name:
			return RetVal(ErrEmptyData, "BUG: name may not be empty")
		
		if len(self.profiles) == 1:
			if self.profiles[0].is_default():
				return RetVal()
			self.profiles[0].set_default(True)
			return RetVal()
		
		oldindex = -1
		for i in range(0, len(self.profiles)):
			if self.profiles[i].is_default():
				oldindex = i
		
		name_squashed = name.casefold()
		newindex = self._index_for_profile(name_squashed)
		
		if newindex < 0:
			return RetVal(ErrNotFound, f"New profile {name_squashed} not found")
		
		if oldindex >= 0:
			if name_squashed == self.profiles[oldindex].name:
				return RetVal()
			self.profiles[oldindex].set_default(False)

		self.profiles[newindex].set_default(True)
		return RetVal()

	def activate_profile(self, name: str) -> RetVal:
		'''Activates the specified profile.

		Returns:
		"error" : string
		"wid" : string
		"host" : string
		"port" : integer
		'''
		if not name:
			return RetVal(ErrEmptyData, "BUG: name may not be empty")
		
		name_squashed = name.casefold()
		active_index = self._index_for_profile(name_squashed)
		if active_index < 0:
			return RetVal(ErrNotFound, f"{name_squashed} doesn't exist")
		
		if self.active_index >= 0:
			self.profiles[self.active_index].deactivate()
			self.active_index = -1
		
		self.profile_id = name_squashed

		self.active_index = active_index
		self.profiles[self.active_index].activate()

		# Force loading of basic identity info if it hasn't already been done
		self.profiles[self.active_index].get_identity()
		
		return RetVal().set_values({
			'wid' : self.profiles[active_index].wid,
			'host' : self.profiles[active_index].domain
		})

	def get_active_profile(self) -> RetVal:
		'''Returns the active profile'''

		if self.active_index >= 0:
			return RetVal().set_value("profile", self.profiles[self.active_index])
		return RetVal(InvalidProfile,'No active profile')


profman = ProfileManager()

