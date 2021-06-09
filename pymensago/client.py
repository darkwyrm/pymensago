'''This module provides a simple interface to the handling storage and networking needs for a 
Mensago client'''
from pymensago.utils import MAddress
import socket
import uuid

from retval import ErrUnimplemented, RetVal, ErrInternalError, ErrBadValue, ErrExists

import pymensago.auth as auth
import pymensago.iscmds as iscmds
import pymensago.kcresolver as kcresolver
import pymensago.serverconn as serverconn
from pymensago.encryption import Password, EncryptionPair
from pymensago.userprofile import Profile, ProfileManager
from pymensago.workspace import Workspace

class MensagoClient:
	'''
	This is the primary interface to the entire library from an application perspective.
	'''
	def __init__(self, profile_folder=''):
		self.active_profile = ''
		self.conn = serverconn.ServerConnection()
		self.pman = ProfileManager(profile_folder)
		self.kcr = kcresolver.KCResolver(self.pman.profile_folder)
		self.login_active = False

	def activate_profile(self, name) -> RetVal:
		'''Activates the specified profile'''

		status = self.pman.activate_profile(name)
		if status.error():
			return status
		
		self.conn.disconnect()
		
		status = self.conn.connect(status['host'],status['port'])
		return status
	
	def connect(self, domain: str) -> RetVal:
		'''Establishes a network connection to a Mensago server. No logging in is performed.'''
		serverconfig = kcresolver.get_server_config(domain)
		if serverconfig.error():
			return serverconfig
		return self.conn.connect(serverconfig['server'], serverconfig['port'])
	
	def is_connected(self) -> bool:
		'''Returns true if the client has an active connection with a server. Note that this does 
		not imply that the client has an active login session on that connection.'''
		return self.conn.is_connected()

	def disconnect(self):
		'''Ends a network session with a Mensago server.'''
		self.login_active = False
		self.conn.disconnect()

	def get_profile_manager(self) -> ProfileManager:
		return self.pman
	
	def login(self, address: MAddress) -> RetVal:
		'''Logs into a server. NOTE: not the same as connecting to one. At the same time, if no 
		connection is established, login() will also create the connection.'''
		if not self.conn.is_connected():
			self.connect(address.domain)
		
		record = kcresolver.get_mgmt_record(address.domain)
		if record.error():
			return record

		status = iscmds.login(self.conn, address.id, record['pvk'])
		if not status.error():
			self.login_active = True
		return status

	def is_logged_in(self) -> bool:
		'''Returns true if an active login session has been completed'''
		if self.conn.is_connected():
			return self.login_active
		self.login_active = False
		return False

	def logout(self) -> RetVal:
		'''Logs out of a server'''
		self.login_active = False
		return iscmds.logout(self.conn)

	def preregister_account(self, port_str: str, uid: str) -> RetVal:
		'''Create a new account on the local server. This is a simple command because it is not 
		meant to create a local profile.'''
		
		if port_str:
			try:
				port = int(port_str)
			except:
				return RetVal(ErrBadValue, 'Bad port number')
		else:
			port = 2001
		
		if port < 0 or port > 65535:
			return RetVal(ErrBadValue, 'Bad port number')

		if '"' in uid or '/' in uid:
			return RetVal(ErrBadValue, "User ID can't contain \" or /")

		status = self.conn.connect('127.0.0.1', port)
		if status.error():
			return status
		
		regdata = serverconn.preregister(self.conn, '', uid, '')
		if regdata.error():
			return regdata
		self.conn.disconnect()

		if regdata['status'] != 200:
			return regdata
		
		if 'wid' not in regdata or 'regcode' not in regdata:
			return RetVal(ErrInternalError, 'BUG: bad data from serverconn.preregister()') \
					.set_value('status', 300)

		return regdata

	def redeem_regcode(self, address: MAddress, regcode: str, userpass: str) -> RetVal:
		'''Completes setup of a preregistered account'''
		
		status = self.pman.get_active_profile()
		if status.error():
			return status
		
		profile = status['profile']
		if profile.domain:
			return RetVal(ErrExists, 'a user workspace already exists')

		# Password requirements aren't really set here, but we do have to draw the 
		# line *somewhere*.
		pw = Password()
		status = pw.Set(userpass)
		if status.error():
			return status
		
		devpair = EncryptionPair()

		# For now, we will just use the default port (2001) and convert example.com to localhost
		if address.domain in ['localhost', 'example.com']:
			host = 'localhost'
		else:
			# TODO: Eventually look up the IP/port from the DNS management record.
			return RetVal(ErrUnimplemented, 'DNS support not yet implemented. Sorry!')
		
		status = self.conn.connect(host, 2001)
		if status.error():
			return status
		
		regdata = iscmds.regcode(self.conn, str(address), regcode, pw.hashstring, )
		self.conn.disconnect()
		if regdata.error():
			return regdata

		# Just a basic sanity check
		if 'wid' not in regdata or 'devid' not in regdata:
			return RetVal(ErrInternalError, 'BUG: bad data from serverconn.register()') \
					.set_value('status', 300)

		w = Workspace(profile.db, profile.path)
		status = w.generate(profile, address.domain, regdata['wid'], pw)
		if status.error():
			return status
		

		
		status = auth.add_device_session(profile.db, MAddress(f"{regdata['wid']}/{host}"),
										regdata['devid'], devpair, socket.gethostname())
		if status.error():
			return status

		regdata['password'] = pw
		return regdata
	
	def register_account(self, server: str, userpass: str, userid='') -> RetVal:
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
		
		status = self.pman.get_active_profile()
		if status.error():
			return status
		
		profile = status['profile']
		if profile.domain:
			return RetVal(ErrExists, 'a user workspace already exists')

		# Parse server string. Should be in the form of (ip/domain):portnum
		host = ''
		port = -1
		if ':' in server:
			addressparts = server.split(':')
			host = addressparts[0]
			try:
				port = int(addressparts[1])
			except ValueError:
				return RetVal(ErrBadValue, 'bad server string')
			serverstring = server
		else:
			host = server
			port = 2001
		
		# Password requirements aren't really set here, but we do have to draw the 
		# line *somewhere*.
		pw = Password()
		status = pw.Set(userpass)
		if status.error():
			return status
		
		# Add the device to the workspace
		devpair = EncryptionPair()

		status = self.conn.connect(host, port)
		if status.error():
			return status
		
		regdata = iscmds.register(self.conn, userid, pw.hashstring, devpair.public)
		self.conn.disconnect()
		if regdata.error():
			return regdata

		# Just a basic sanity check
		if 'wid' not in regdata:
			return RetVal(ErrInternalError, 'BUG: bad data from serverconn.register()') \
					.set_value('status', 300)

		w = Workspace(profile.db, profile.path)
		status = w.generate(profile, server, regdata['wid'], pw)
		if status.error():
			return status
		
		
		status = auth.add_device_session(profile.db, MAddress(f"{regdata['wid']}/{host}"),
				regdata['devid'], devpair, socket.gethostname())
		if status.error():
			return status

		return regdata
