'''This module implements a Mensago keycard resolver with caching'''

import sqlite3

from pymensago.retval import RetVal, Unimplemented

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
		return RetVal(Unimplemented)

	def _get_card_from_db(self, owner: str) -> RetVal:
		'''gets a keycard from the db cache if it exists'''
		# TODO: implement KCResolver._get_card_from_db()
		return RetVal(Unimplemented)
