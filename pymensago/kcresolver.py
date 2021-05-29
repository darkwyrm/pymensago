'''This module implements a Mensago keycard resolver with caching'''

import socket
import sqlite3

from retval import RetVal, ErrBadValue, ErrNotFound, ErrUnimplemented

import pymensago.iscmds as iscmds
import pymensago.keycard as keycard
from pymensago.serverconn import ServerConnection
from pymensago.utils import validate_domain, MAddress

class KCResolver:
	'''A caching keycard resolver class'''

	def __init__(self, conn: sqlite3.Connection) -> None:
		self.db = conn

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


def resolve_address(addr: MAddress) -> RetVal:
	'''obtains the workspace ID for a Mensago address'''
	if not addr.is_valid():
		return RetVal(ErrBadValue)
	
	if addr.id_type == 1:
		return RetVal().set_value('Workspace-ID', addr.id)
	
	# Step 1: Get the server to connect to

	# We have to have a domain for testing. test.example.com is considered to always resolve to
	# localhost
	ip = ''
	if addr.domain == 'test.example.com':
		ip = '127.0.0.1'
	else:
		# TODO: Implement Mensago server lookup in resolve_address()
		# This requires getting the management record from DNS and finding out the IP of the server
		# from that record.
		return RetVal(ErrUnimplemented)
	
	# Step 2: Connect and request the address
	conn = ServerConnection()
	status = conn.connect(ip, 2001)
	if status.error():
		return status
	
	status = iscmds.getwid(conn, addr.id, addr.domain)
	conn.disconnect()
	return status

