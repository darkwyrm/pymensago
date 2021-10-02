import sqlite3
import uuid

from retval import ErrNotFound, RetVal

class FolderMap:
	'''Represents the mapping of a server-side path to a local one'''
	def __init__(self):
		self.fid = ''
		self.address = ''
		self.keyid = ''
		self.path = ''
		self.permissions = ''
	
	def MakeID(self) -> None:
		'''Generates a FID for the object'''
		self.fid = str(uuid.uuid4())

	def Set(self, address, keyid, path, permissions) -> None:
		'''Sets the values of the object'''
		self.address = address
		self.keyid = keyid
		self.path = path
		self.permissions = permissions


def load_folder_maps(db: sqlite3.Connection) -> RetVal():
	'''Loads from the database all folder maps.

	Parameters:
		db: connection to the SQLite3 database
	
	Returns:
		maps: (dict) dictionary of UUID keys to workspace-relative paths
	
	Notes:
		Because folders can have the same name due to being in different locations,
		the full path is used. For example 'files attachments' for the attachments
		folder for the workspace.
	'''

	maps = dict()

	cur = db.cursor()
	cur.execute("SELECT fid,path FROM folders")
	for row in cur.fetchall():
		maps[row[0]] = row[1]
	
	if len(maps) == 0:
		return RetVal(ErrNotFound)
	
	return RetVal().set_value('maps', maps)

