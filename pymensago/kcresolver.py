'''This module implements a Mensago keycard resolver with caching'''

import socket
import sqlite3

import pymensago.iscmds as iscmds
import pymensago.keycard as keycard
from pymensago.retval import BadParameterValue, ExceptionThrown, ResourceNotFound, RetVal, Unimplemented
from pymensago.serverconn import ServerConnection
from pymensago.utils import validate_domain, MAddress

class KCResolver:
	'''A caching keycard resolver class'''

	def __init__(self, conn: sqlite3.Connection) -> None:
		self.db = conn

	def get_card(self, owner: str) -> RetVal:
		'''returns a Keycard object in the 'keycard' field if successful'''
		# TODO: implement KCResolver.get_card()
		return RetVal(Unimplemented)

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
		
		status = self._get_card_from_db(owner)
		if status.error() != ResourceNotFound:
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
			return RetVal(Unimplemented)
		
		# Step 2: Connect and get card
		conn = ServerConnection()
		status = conn.connect(ip, 2001)
		if status.error():
			return status

		card = None
		if orgcard:
			out = iscmds.orgcard(conn, 1, -1)
		else:
			out = iscmds.usercard(conn, str(owner), 1, -1)
		
		conn.disconnect()
		if out.error():
			return out
		
		status = self._update_card_in_db(out['keycard'])
		if status.error():
			return status

		return out

	def _get_card_from_db(self, owner: str) -> RetVal:
		'''gets a keycard from the db cache if it exists'''
		
		# TODO: implement KCResolver._get_card_from_db()
		return RetVal(Unimplemented)
	
	def _add_card_to_db(self, card: keycard.Keycard) -> RetVal:
		'''adds a keycard to the database cache'''

		# TODO: implement KCResolver._add_card_to_db()
		return RetVal(Unimplemented)

	def _update_card_in_db(self, card: keycard.Keycard) -> RetVal:
		'''updates a keycard in the database cache'''

		# TODO: implement KCResolver._update_card_in_db()
		return RetVal(Unimplemented)


def resolve_address(addr: MAddress) -> RetVal:
	'''obtains the workspace ID for a Mensago address'''
	if not addr.is_valid():
		return RetVal(BadParameterValue)
	
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
		return RetVal(Unimplemented)
	
	# Step 2: Connect and request the address
	conn = ServerConnection()
	status = conn.connect(ip, 2001)
	if status.error():
		return status
	
	status = iscmds.getwid(conn, addr.id, addr.domain)
	conn.disconnect()
	return status

