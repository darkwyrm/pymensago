'''This module implements a Mensago keycard resolver with caching'''

import socket
import sqlite3

from pymensago.iscmds import getwid
from pymensago.retval import BadParameterValue, ExceptionThrown, RetVal, Unimplemented
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
		card_type = 'user'
		if len(owner.split('/')) == 1 and validate_domain(owner):
			card_type = 'org'
		else:
			addr = MAddress()
			status = addr.set(owner)
			if status.error():
				return status
		
		return RetVal(Unimplemented)

	def _get_card_from_db(self, owner: str) -> RetVal:
		'''gets a keycard from the db cache if it exists'''
		# TODO: implement KCResolver._get_card_from_db()
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
	
	return getwid(conn, addr.id, addr.domain)

