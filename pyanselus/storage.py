'''This module provides an API to interact with the filesystem'''
import os
import platform
# import sqlite3

# import auth
from userprofile import ProfileManager

class ClientStorage:
	'''Provides a storage API for the rest of the client.'''

	def __init__(self):
		osname = platform.system().casefold()
		if osname == 'windows':
			self.profile_folder = os.path.join(os.getenv('LOCALAPPDATA'), 'anselus')
		else:
			self.profile_folder = os.path.join(os.getenv('HOME'), '.config','anselus')
		
		if not os.path.exists(self.profile_folder):
			os.mkdir(self.profile_folder)
		
		self.pman = ProfileManager()
		self.db = None


	def get_db(self):
		'''Returns a handle to the storage handler's database connection'''
		return self.db

	def get_profile_manager(self):
		'''Returns an instance of the storage handler's profile manager '''
		return self.pman
