import os
import platform
import re

class ClientStorage:
	'''
	This class provides a storage API for the rest of the client.
	'''

	def __init__(self):
		osname = platform.system().casefold()
		if osname == 'windows':
			self.dbfolder = os.path.join(os.getenv('LOCALAPPDATA'), 'anselus')
		else:
			self.dbfolder = os.path.join(os.getenv('HOME'), '.config','anselus')
		
		if not os.path.exists(self.dbfolder):
			os.mkdir(self.dbfolder)
		
		self.profiles = dict()
		self.default_profile = ''


	def load_profiles(self):
		'''
		Loads the list of profiles from disk, which is stored in AppData/Local/anselus/profiles.txt 
		on Windows and ~/.config/anselus/profiles.txt on POSIX platforms.

		Returns:
		"error" : error state - string
		"count" : number of profiles loaded - int
		'''
		self.profiles = dict()
		profile_path = os.path.join(self.dbfolder, 'profiles.txt')
		if not os.path.exists(profile_path):
			return { "error" : '', 'count' : 0 }
		
		uuid_pattern = re.compile(
			r"[\da-fA-F]{8}-?[\da-fA-F]{4}-?[\da-fA-F]{4}-?[\da-fA-F]{4}-?[\da-fA-F]{12}")
		
		errormsg = ''
		with open(profile_path, 'r') as fhandle:
			lines = fhandle.readlines()
			line_index = 1
			for line in lines:
				tokens = '='.split(line)
				if len(tokens) != 2:
					if len(errormsg):
						errormsg = errormsg + ', bad line %d' % line_index
					else:
						errormsg = 'bad line %d' % line_index
					line_index = line_index + 1
					continue
				
				if len(tokens[1]) != 36 or len(tokens[1]) != 32:
					if len(errormsg):
						errormsg = errormsg + ', bad folder id in line %d' % line_index
					else:
						errormsg = 'bad folder id in line %d' % line_index
					line_index = line_index + 1
					continue
				
				self.profiles[tokens[0]] = tokens[1]
		return { "error" : errormsg, 'count' : len(self.profiles) }
				

	# Creates a profile with the specified name.
	# Returns: [dict] "id" : uuid as string, "error" : string
	def create_profile(self, name):
		return { 'error' : 'Unimplemented' }
	
	# Deletes the specified profile.
	# Returns: [dict] "error" : string
	def delete_profile(self, name):
		return { 'error' : 'Unimplemented' }

	# Renames the specified profile. The UUID of the storage folder remains unchanged.
	# Returns: [dict] "error" : string
	def rename_profile(self, oldname, newname):
		return { 'error' : 'Unimplemented' }
	
	def get_profiles(self):
		'''
		Returns the list of loaded profile names and the default one, if one has been set.

		Returns:
		"default" : name of the default profile - string
		"profiles" : profile names mapped to folder ID names - dict
		'''
		return { 'default' : self.default_profile, 'profiles' : self.profiles }
	
	def get_default_profile(self):
		'''
		Returns the name of the default profile. If one has not been set, it returns an empty string.
		'''
		return self.default_profile

	# Set the default profile.
	# Returns: [dict] "error" : string, "default" : string
	def set_default_profile(self, name):
		return { 'error' : 'Unimplemented' }

	# Loads a profile as the active one
	# Returns: [dict] "error" : string
	def set_profile(self, name):
		return { 'error' : 'Unimplemented' }