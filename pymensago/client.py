'''This module provides a simple interface to the handling storage and networking needs for a 
Mensago client'''
from pycryptostring import CryptoString
from pymensago.utils import Domain, MAddress, UUID, UserID, WAddress
import socket

from retval import ErrNotFound, ErrUnimplemented, RetVal, ErrInternalError, ErrBadValue, ErrExists

import pymensago.auth as auth
from pymensago.contactdb import load_field
import pymensago.iscmds as iscmds
import pymensago.keycard as keycard
import pymensago.kcresolver as kcresolver
import pymensago.serverconn as serverconn
import pymensago.userprofile as userprofile
import pymensago.utils as utils
from pymensago.encryption import Password, EncryptionPair
from pymensago.userinfo import save_name
from pymensago.workspace import Workspace

ErrNotLoggedIn = 'ErrNotLoggedIn'
ErrNotConnected = 'ErrNotConnected'
ErrNotAdmin = 'ErrNotAdmin'

class MensagoClient:
	'''
	This is the primary interface to the entire library from an application perspective.
	'''
	def __init__(self, profile_folder=''):
		self.active_profile = ''
		self.conn = serverconn.ServerConnection()
		self.pman = userprofile.profman
		self.pman.load_profiles(profile_folder)
		self.login_active = False
		self.is_admin = False
		
		# This unusual construct is because if the profile manager is given an empty profile folder
		# path, it defaults to a predetermined location
		self.kcr = kcresolver.KCResolver(self.pman.profile_folder)

	def connect(self, domain: Domain) -> RetVal:
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

	def login(self, address: MAddress) -> RetVal:
		'''Logs into a server. NOTE: not the same as connecting to one. At the same time, if no 
		connection is established, login() will also create the connection.'''
		if not self.conn.is_connected():
			self.connect(address.domain)
		
		record = kcresolver.get_mgmt_record(address.domain.as_string())
		if record.error():
			return record

		status = userprofile.profman.get_active_profile()
		if status.error():
			return status
		profile = status['profile']
		
		waddr = WAddress()
		if address.id_type == 1:
			waddr.id.set(address.id.as_string())
		else:
			status = profile.resolve_address(address)
			if status.error():
				return status
			
			waddr.id = status['wid']
		waddr.domain = address.domain
		
		if not waddr.is_valid():
			return RetVal(ErrBadValue, 'bad resolved workpace ID')

		status = iscmds.login(self.conn, waddr.id, CryptoString(record['ek']))
		if status.error():
			return status
		
		status = auth.get_credentials(profile.db, waddr)
		if status.error():
			return status
		
		status = iscmds.password(self.conn, status['password'].hashstring)
		if status.error():
			return status

		status = auth.get_session_keypair(profile.db, waddr)
		if status.error():
			return status
		devpair = status['keypair']

		status = iscmds.device(self.conn, profile.devid, devpair)

		if not status.error():
			self.login_active = True
			self.is_admin = status['isadmin']
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

	def preregister_account(self, id: UserID=None, domain: Domain=None) -> RetVal:
		'''Create a new account on the local server. This is a simple command because it is not 
		meant to create a local profile.'''

		if not self.is_logged_in() or not self.is_admin:
			return RetVal(ErrNotLoggedIn, 'must be logged in as admin')
		
		uid = UserID()
		wid = UUID()
		dom = Domain()
		
		if id and not id.is_empty():
			if not id.is_valid():
				return RetVal(ErrBadValue, 'Bad user ID')
			
			if id.is_wid():
				wid = id.as_wid()
			else:
				uid = id
		
		if domain and not domain.is_empty():
			if not domain.is_valid():
				return RetVal(ErrBadValue, 'Bad domain')
			dom = domain
		
		# This call works because preregister checks to make sure that the optional parameters
		# are both != None and aren't empty.
		regdata = iscmds.preregister(self.conn, wid, uid, dom)
		if regdata.error():
			return regdata

		if regdata.error():
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
		if not profile.domain.is_empty():
			return RetVal(ErrExists, 'an identity workspace already exists on this profile')

		# Password requirements aren't really set here, but we do have to draw the 
		# line *somewhere*.
		pw = Password()
		status = pw.set(userpass)
		if status.error():
			return status
		
		devpair = EncryptionPair()

		status = kcresolver.get_server_config(address.domain)
		if status.error():
			return status
		
		host = status['server']
		port = status['port']
		status = self.conn.connect(host, port)
		if status.error():
			return status
		
		regdata = iscmds.regcode(self.conn, address, regcode, pw.hashstring, profile.devid, devpair)
		self.conn.disconnect()
		if regdata.error():
			return regdata

		# Just a basic sanity check
		if 'wid' not in regdata or 'devid' not in regdata:
			return RetVal(ErrInternalError, 'BUG: bad data from serverconn.register()') \
					.set_value('status', 300)

		w = Workspace(profile.db, profile.path)
		status = w.generate(address.id, address.domain, regdata['wid'], pw)
		if status.error():
			return status

		status = profile.set_identity(w)
		if status.error():
			return status
		
		status = auth.add_device_session(profile.db, MAddress(f"{regdata['wid']}/{address.domain}"),
										regdata['devid'], devpair, socket.gethostname())
		if status.error():
			return status
		
		# TODO: create, cross-sign, and upload first keycard entry

		return regdata
	
	def register_account(self, domain: Domain, userpass: str, userid=None, 
		name: utils.Name=None) -> RetVal:
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
		# Generate new workspace data, which includes the associated crypto keys
		# Add the device ID and session to the profile and the server
		# Create, upload, and cross-sign the first keycard entry
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
		if not profile.domain.is_empty():
			return RetVal(ErrExists, 'a user workspace already exists')

		status = kcresolver.get_server_config(domain)
		if status.error():
			return status
		host = status['server']
		port = status['port']
		
		# Password requirements aren't really set here, but we do have to draw the 
		# line *somewhere*.
		pw = Password()
		status = pw.set(userpass)
		if status.error():
			return status
		
		# Add the device to the workspace
		devpair = EncryptionPair()

		status = self.conn.connect(host, port)
		if status.error():
			return status
		
		if userid:
			regdata = iscmds.register(self.conn, userid, pw.hashstring, profile.devid, 
				devpair.public)
		else:
			regdata = iscmds.register(self.conn, utils.UserID(utils.UUID().generate()), 
				pw.hashstring, profile.devid, devpair.public)

		# Just a basic sanity check
		if 'wid' not in regdata:
			self.conn.disconnect()
			return RetVal(ErrInternalError, 'BUG: bad data from serverconn.register()') \
					.set_value('status', 300)

		if name:
			regdata['name'] = name
		regdata['password'] = pw
		regdata['devpair'] = devpair
		regdata['devid'] = profile.devid

		status = self._setup_workspace(profile, regdata)
		self.conn.disconnect()
		if status.error():
			return status

		return regdata

	def update_keycard(self) -> RetVal:
		'''Creates a new entry in the user's keycard. New keys are created and added to the database'''
		
		status = self.pman.get_active_profile()
		if status.error():
			return status
		
		profile = status['profile']

		entry = keycard.UserEntry()
		entry.set_expiration()
		
		crepair = None
		crspair = None
		epair = None
		spair = None
		status = keycard.db_get_card(profile.db, profile.get_identity().as_string())
		if status.error():
			if status.error() != ErrNotFound:
				return status
			
			# Create the user's first keycard entry. It's not valid until it's been cross-signed by both
			# the client and the organization, though.

			# The keys in the database we
			status = auth.get_key_by_type(profile.db, 'crencrypt')
			if status.error():
				return status
			crepair = status['key']
			entry['Contact-Request-Encryption-Key'] = crepair.get_public_key()

			status = auth.get_key_by_type(profile.db, 'crsign')
			if status.error():
				return status
			crspair = status['key']
			entry['Contact-Request-Verification-Key'] = crspair.get_public_key()

			status = auth.get_key_by_type(profile.db, 'encrypt')
			if status.error():
				return status
			epair = status['key']
			entry['Encryption-Key'] = epair.get_public_key()

			status = auth.get_key_by_type(profile.db, 'sign')
			if status.error():
				return status
			spair = status['key']
			entry['Verification-Key'] = spair.get_public_key()

			entry['Workspace-ID'] = profile.wid.as_string()
			entry['Domain'] = profile.domain.as_string()
			if profile.userid.is_valid() and not profile.userid.is_wid():
				entry['UserID'] = profile.userid.as_string()
			
			status = load_field(profile.db, profile.wid, 'FormattedName')
			if status.error() and status.error() != ErrNotFound:
				return status
			
			if not status.error():
				entry['Name'] = status['value']
		
		else:
			card = status['card']
			status = card.verify()
			if status.error():
				return status
			
			status = auth.get_key_by_type('crsign')
			if status.error():
				return status
			crspair = status['key']

			status = card.chain(crspair.private, True)
			if status.error():
				return status
			
			entry = card.entries[-1]
			crspair = status['crsign']
			crepair = status['crencrypt']
			spair = status['sign']
			epair = status['encrypt']

		# Keycard entry setup complete. Now we log in and handle signing. Although we still have the
		# network connection to the server from registration, we are not logged in... yet.
		
		address = MAddress()
		address.set_from_wid(profile.wid, profile.domain)
		status = self.login(address)
		if status.error():
			return status

		status = kcresolver.get_mgmt_record(profile.domain)
		if status.error():
			return status

		ovkey = status['pvk']
		status = iscmds.addentry(self.conn, entry, ovkey, spair)

		return status

	def _setup_workspace(self, profile: userprofile.Profile, regdata: dict) -> RetVal:
		'''This finishes all the profile and workspace setup common to both standard registration 
		and registration via a code.'''
		
		w = Workspace(profile.db, profile.path)
		status = w.generate(regdata['uid'], regdata['domain'], regdata['wid'], regdata['password'])
		if status.error():
			return status
		
		status = profile.set_identity(w)
		if status.error():
			return status
		
		if regdata['name']:
			save_name(profile.db, regdata['name'])

		address = utils.WAddress()
		address.id = regdata['wid']
		address.domain = regdata['domain']
		
		status = auth.add_device_session(profile.db, address, regdata['devid'], regdata['devpair'],
			socket.gethostname())
		if status.error():
			return status
		
		return self.update_keycard()

