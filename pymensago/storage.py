'''This module provides an API to interact with the filesystem'''
import os
import platform

from pymensago.userprofile import ProfileManager

class ClientStorage:
	'''Provides a storage API for the rest of the client.'''

	def __init__(self, profile_folder=''):
		self.pman = ProfileManager()
		self.db = None

	def get_db(self):
		'''Returns a handle to the storage handler's database connection'''
		return self.db

	def get_profile_manager(self):
		'''Returns an instance of the storage handler's profile manager '''
		return self.pman
