'''This module implements a Mensago keycard resolver with caching'''

import os

from retval import ErrOK, RetVal, ErrBadValue, ErrNotFound, ErrUnimplemented

from pymensago.config import load_server_config
import pymensago.iscmds as iscmds
import pymensago.keycard as keycard
from pymensago.serverconn import ServerConnection
from pymensago.utils import Domain, validate_domain, MAddress

class KCResolver:
	'''A caching keycard resolver class'''

	def __init__(self, profile_path: str) -> None:
		if not profile_path:
			raise ValueError('profile path may not be empty')
		
		self.path = profile_path
		if not os.path.exists(self.path):
			os.mkdir(self.path)
		
		self.db = None

	def get_card(self, owner: str) -> RetVal:
		'''returns a Keycard object in the 'keycard' field if successful'''
		
		return self._resolve_card(owner)

	def _resolve_card(self, owner: str) -> RetVal:
		'''internal method which does all the actual resolving if the card isn't in the db'''
		# TODO: implement KCResolver._resolve_card()

		# First, determine if this is an org card or a user card. It's a user card unless we are
		# just given a domain, in which case it's an org card that we need.
		orgcard = False
		if len(owner.split('/')) == 1 and validate_domain(owner):
			orgcard = True
		else:
			addr = MAddress()
			status = addr.set(owner)
			if status.error():
				return status
		
		status = self._get_card_from_db(owner, orgcard)
		if status.error() != ErrNotFound:
			return status

		# The card has been returned, so we have *something*. It might, however, need updates.
		# TODO: _resolve_card(): check to see if the card's TTL has expired and get updates if it has.
		# If updates are needed, we'll need to add them to the database and then return the card


		# If we've gotten this far, the card isn't in the database cache, so perform the resolution,
		# add it to the database, and return it to the caller
		ip = ''
		if addr.domain == 'test.example.com':
			ip = '127.0.0.1'
		else:
			# TODO: Implement Mensago server lookup in _resolve_card()
			# This requires getting the management record from DNS and finding out the IP of the server
			# from that record.
			return RetVal(ErrUnimplemented)
		
		# Step 2: Connect and get card
		conn = ServerConnection()
		status = conn.connect(ip, 2001)
		if status.error():
			return status

		# Validation of the card data is done inside these calls
		card = None
		if orgcard:
			out = iscmds.orgcard(conn, 1, -1)
		else:
			out = iscmds.usercard(conn, str(owner), 1, -1)
		
		conn.disconnect()
		if out.error():
			return out
		
		status = self._add_card_to_db(owner, orgcard, out['keycard'])
		if status.error():
			return status

		return out

	def resolve_address(self, addr: MAddress) -> RetVal:
		'''obtains the workspace ID for a Mensago address'''

		if not addr.is_valid():
			return RetVal(ErrBadValue)
		
		if addr.id_type == 1:
			return RetVal().set_value('Workspace-ID', addr.id)

		# TODO: POSTDEMO: Add caching to kcresolver.resolve_address

		# Step 1: Get the server to connect to

		# We have to have a domain for testing. Anything in the example.com domain is considered to 
		# always resolve to localhost
		serverconfig = get_server_config(addr.domain)
		if serverconfig.error():
			return serverconfig
		
		# Step 2: Connect and request the address
		conn = ServerConnection()
		status = conn.connect(serverconfig['server'], serverconfig['port'])
		if status.error():
			return status
		
		status = iscmds.getwid(conn, addr.id, addr.domain)
		conn.disconnect()
		return status

	def _get_card_from_db(self, owner: str, isorg: bool) -> RetVal:
		'''gets a keycard from the db cache if it exists'''
		
		# TODO: Implement keycard Time-To-Live handling

		out = RetVal()
		card = keycard.Keycard()

		# This is an internal call and owner has already been validated once, so we don't have to
		# do it again. Likewise, we validate everything ruthlessly when data is brought in, so
		# because that's already been done once, we don't need to do it again here -- just create
		# entries from each row and add them to the card.
		cursor = self.db.cursor()
		cursor.execute("SELECT entry FROM keycards WHERE owner=? ORDER BY 'index'", (owner,))
		row = cursor.fetchone()
		while row:
			entry = None
			if isorg:
				entry = keycard.OrgEntry()
			else:
				entry = keycard.UserEntry()
			status = entry.set(row[0].encode())
			if status.error():
				return status
			card.entries.append(card)
			row = cursor.fetchone()
		
		if len(card.entries) > 0:
			out.set_value('keycard',card)
		
		return out
	
	def _add_card_to_db(self, owner: str, isorg: bool, card: keycard.Keycard) -> RetVal:
		'''adds a keycard to the database cache after removing any stale entries'''

		# TODO: Implement keycard Time-To-Live handling

		cursor = self.db.cursor()
		cursor.execute("DELETE FROM keycards WHERE owner=?", (owner,))
		for entry in card.entries:
			cursor.execute('''INSERT INTO keycards(owner,index,entry,fingerprint,expires)
				VALUES(?,?,?,?,?)''',
				(owner, entry['Index'], str(entry), entry.hash, entry['Expires']))
		self.db.commit()

		return RetVal()

	def _update_card_in_db(self, owner: str, isorg: bool, card: keycard.Keycard) -> RetVal:
		'''updates a keycard in the database cache'''

		# TODO: Implement keycard Time-To-Live handling

		# Because keycards are append-only, we just have to find out what the last index stored
		# in the database is and then add any remaining entries to the database
		index = -1

		cursor = self.db.cursor()
		cursor.execute("SELECT index FROM keycards WHERE owner=? ORDER BY 'index' DESC LIMIT 1")
		row = cursor.fetchone()
		if row:
			try:
				index = int(row[0])
			except:
				pass
		
		if index < 0:
			self._add_card_to_db(owner, isorg, card)
			return RetVal()
		
		if index < len(card.entries):
			for entry in card.entries[index:]:
				cursor.execute('''INSERT INTO keycards(owner,index,entry,fingerprint,expires)
					VALUES(?,?,?,?,?)''',
					(owner, entry['Index'], str(entry), entry.hash, entry['Expires']))
			self.db.commit()

		return RetVal()


def get_server_config(domain: Domain) -> RetVal:
	'''Given a domain, obtains the configuration information for the Mensago server for that 
	domain. The server's FQDN will be in the `server` field and the port in `port`.'''

	# TODO: POSTDEMO: Implement get_server_config for non-localhost domains

	if domain.value.endswith('example.com'):
		config = load_server_config()

		return RetVal().set_values({
			'server': 'localhost',
			'port': config['network']['port']
		})
	
	return RetVal(ErrUnimplemented, 'external lookup for non-local domains unimplemented')


def get_mgmt_record(domain: str) -> RetVal:
	'''Obtains the DNS management record for a domain and returns the following fields:

	pvk - a CryptoString object containing the organization's Primary Verification Key

	svk - a CryptoString object containing the organization's Secondary Verification Key. This field 
	will not exist if the management record has no secondary key.

	hash - a CryptoString hash of the server's TLS certificate public key 
	'''
	out = RetVal(ErrUnimplemented, 'get_mgmt_record unimplemented')

	if domain.endswith('example.com'):
		# Example domains are pointed to localhost, so we will query the local server to get the
		# necessary information.
		config = load_server_config()
		conn = ServerConnection()
		status = conn.connect('localhost', config['network']['port'])
		if status.error():
			return status
		
		# We just need the current keys, so just get the current org card entry
		status = iscmds.orgcard(conn, 0, -1)
		if status.error():
			return status
		conn.disconnect()
		card = status['card']

		out['pvk'] = card.entries[0].fields['Primary-Verification-Key']
		out['ek'] = card.entries[0].fields['Encryption-Key']
		if 'Secondary-Verification-Key' in card.entries[0].fields:
			out['svk'] = card.entries[0].fields['Secondary-Verification-Key']
		
		# Because TLS isn't implemented yet, we won't worry about the TLS cert key hash
		# TODO: POSTDEMO: get hash field for localhost TLS cert in get_mgmt_record()
		out.set_error(ErrOK)
		out.set_info('')
		
	# TODO: POSTDEMO: Finish implementing get_mgmt_record()
	
	return out

