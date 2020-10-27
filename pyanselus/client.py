'''This module provides a simple interface to the handling storage and networking needs for an 
Anselus client'''
import socket

import auth
import serverconn
from encryption import Password, KeyPair
from retval import RetVal, InternalError, BadParameterValue, ResourceExists
from storage import ClientStorage
from userprofile import Profile
from workspace import Workspace

class AnselusClient:
	'''
	The role of this class is to provide an interface to the client as a whole, not just the 
	storage aspects. It does duplicate the ClientStorage interface,	but it also handles network 
	interaction where needed. In short, the user's commands map pretty much one-to-one to this class.
	'''
	def __init__(self):
		self.fs = ClientStorage()
		self.active_profile = ''
		self.socket = None

	def activate_profile(self, name) -> RetVal:
		'''Activates the specified profile'''

		status = self.fs.pman.activate_profile(name)
		if status.error():
			return status
		
		if self.socket:
			serverconn.disconnect(self.socket)
		self.socket = None
		
		status = serverconn.connect(status['host'],status['port'])
		return status
	
	def get_active_profile(self) -> Profile:
		'''Returns a copy of the active profile'''
		return self.fs.pman.get_active_profile()

	def get_profiles(self) -> list:
		'''Gets the list of available profiles'''
		return self.fs.pman.get_profiles()

	def create_profile(self, name: str) -> Profile:
		'''Creates a new profile'''
		return self.fs.pman.create_profile(name)

	def delete_profile(self, name: str) -> RetVal:
		'''Deletes the specified profile'''
		return self.fs.pman.delete_profile(name)
	
	def rename_profile(self, oldname: str, newname: str) -> RetVal:
		'''Renames the specified profile'''
		status = self.fs.pman.rename_profile(oldname, newname)
		if status.error() != '':
			return status
		
		if self.active_profile == oldname:
			self.active_profile = newname
		return RetVal()
	
	def get_default_profile(self) -> str:
		'''Gets the default profile'''
		return self.fs.pman.get_default_profile()
		
	def set_default_profile(self, name: str) -> RetVal:
		'''Sets the profile loaded on startup'''
		return self.fs.pman.set_default_profile(name)

	def preregister_account(self, port_str: str, uid: str) -> RetVal:
		'''Create a new account on the local server. This is a simple command because it is not 
		meant to create a local profile.'''
		
		if port_str:
			try:
				port = int(port_str)
			except:
				return RetVal(BadParameterValue, 'Bad port number')
		else:
			port = 2001
		
		if port < 0 or port > 65535:
			return RetVal(BadParameterValue, 'Bad port number')

		if '"' in uid or '/' in uid:
			return RetVal(BadParameterValue, "User ID can't contain \" or /")

		conndata = serverconn.connect('127.0.0.1', port)
		if conndata.error():
			return conndata
		
		regdata = serverconn.preregister(conndata['socket'], uid)
		if regdata.error():
			return regdata
		serverconn.disconnect(conndata['socket'])

		if regdata['status'] != 200:
			return regdata
		
		if 'wid' not in regdata or 'regcode' not in regdata:
			return RetVal(InternalError, 'BUG: bad data from serverconn.preregister()') \
					.set_value('status', 300)

		return regdata

	def register_account(self, server: str, userpass: str) -> RetVal:
		'''Create a new account on the specified server.'''
		
		# Process for registration of a new account:
		# 
		# Check to see if we already have a workspace allocated on this profile. Because we don't
		# 	yet support shared workspaces, it means that there are only individual ones. Each 
		#	profile can have only one individual workspace.
		#
		# Check active profile for an existing workspace entry
		# Get the password from the user
		# Check active workspace for device entries. Because we are registering, existing device
		#	entries should be removed.
		# Add a device entry to the workspace. This includes both an encryption keypair and 
		#	a UUID for the device
		# Connect to requested server
		# Send registration request to server, which requires a hash of the user's supplied
		#	password
		# Close the connection to the server
		# If the server returns an error, such as 304 REGISTRATION CLOSED, then return an error.
		# If the server has returned anything else, including a 101 PENDING, begin the 
		#	client-side workspace information to generate.
		# Call storage.generate_profile_data()
		# Add the device ID and session string to the profile
		# Create the necessary client-side folders
		# Generate the folder mappings

		# If the server returned 201 REGISTERED, we can proceed with the server-side setup
		#
		# Create the server-side folders based on the mappings on the client side
		# Save all encryption keys into an encrypted 7-zip archive which uses the hash of the 
		# user's password has the archive encryption password and upload the archive to the server.
		
		if self.fs.pman.get_active_profile().domain:
			return RetVal(ResourceExists, 'a user workspace already exists')

		# Parse server string. Should be in the form of (ip/domain):portnum
		if ':' in server:
			addressparts = server.split(':')
			host = addressparts[0]
			try:
				port = int(addressparts[1])
			except ValueError:
				return RetVal(BadParameterValue, 'bad server string')
			serverstring = server
		else:
			host = server
			port = 2001
			serverstring = host + ':2001'
		
		# Password requirements aren't really set here, but we do have to draw the 
		# line *somewhere*.
		pw = Password()
		status = pw.Set(userpass)
		if status.error():
			return status
		
		# Add the device to the workspace
		devkey = KeyPair()

		conndata = serverconn.connect(host, port)
		if conndata.error():
			return conndata
		
		regdata = serverconn.register(conndata['socket'], pw.hashstring, devkey.enc_type,
				devkey.public85)
		if regdata.error():
			return regdata
		serverconn.disconnect(conndata['socket'])

		# Possible status codes from register()
		# 304 - Registration closed
		# 406 - Payment required
		# 101 - Pending
		# 201 - Registered
		# 300 - Internal server error
		# 408 - Resource exists
		if regdata['status'] in [304, 406, 300, 408]:
			return regdata
		
		# Just a basic sanity check
		if 'wid' not in regdata:
			return RetVal(InternalError, 'BUG: bad data from serverconn.register()') \
					.set_value('status', 300)

		w = Workspace(self.fs.pman.get_active_profile().db, self.fs.pman.get_active_profile().path)
		status = w.generate(self.fs.pman.get_active_profile(), server, regdata['wid'], pw)
		if status.error():
			return status
		
		address = '/'.join([regdata['wid'], serverstring])
		status = auth.add_device_session(self.fs.pman.get_active_profile().db, address, 
				regdata['devid'], devkey.enc_type, devkey.public85, devkey.private85,
				socket.gethostname())
		if status.error():
			return status

		return regdata
