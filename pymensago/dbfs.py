'''The dbfs module implements filesystem-like operations on top of the SQLite3 database'''
import sqlite3
import typing
import uuid

from retval import RetVal, ErrNotFound, ErrUnimplemented

# This module implements basic filesystem operations inside the SQLite3 database. This is because
# the files themselves are stored in the database for (a) data protection and (b) easy search.
# Only attachments are stored outside the database, and this is for bloat protection. The files'
# names are the same as those on the server to make tracking them easier. Folder names, OTOH,
# are stored in the database using the user-facing names (inbox, notes, etc.)

def validate_dbpath(path: str) -> bool:
	'''Returns true if the path supplied is valid'''

	if not isinstance(path, str):
		return False
	
	if path == '/':
		return True
	
	if not path or '//' in path or '\\' in path or path[-1] == '/' or path.strip() != path:
		return False
	
	return True


class DBPath:
	'''Represents an internal DBFS path.
	
	Notes:
		The only printable characters not permitted in these paths are forward slashes and
		backslashes. Paths are also expected to not have trailing slashes, which will be stripped.
		Leading and trailing whitespace is also stripped to avoid problems.
	'''
	
	def __init__(self, src):
		if isinstance(src, str):
			self.path = src.strip()
		elif isinstance(src, DBPath):
			self.path = src.path.strip()
		else:
			self.path = ''
		
		if not self.is_valid():
			self.path = ''

	def is_valid(self) -> bool:
		'''Returns True if the instance contains a valid path'''
		return validate_dbpath(self.path)

	def basename(self) -> str:
		'''Returns the name of the entry represented by the path.'''
		if self.path == '/':
			return '/'
		
		return self.path.split('/')[-1]

	def append(self, path) -> None:
		'''Appends the path to the object.

		Parameters:
		  * path: the path to append to the current instance

		Notes:
			If the path parameter is invalid, the instance's value is not changed.
		'''
		temp = ''
		if isinstance(path, str):
			temp = path.strip()
		elif isinstance(path, DBPath):
			temp = path.path.strip()
		
		if not temp or not validate_dbpath(temp):
			return self
		
		if temp[-1] == '/':
			temp = temp[:-1]
		
		self.path = self.path + '/' + temp


def delete(db: sqlite3.Connection, path: DBPath) -> RetVal:
	'''Deletes a file the database virtual filesytem.
	
	Parameters:
	  * path: the DBPath of the directory to remove
	
	Returns:
	  * no additional fields
	'''
	
	# TODO: implement dbfs.delete()
	return RetVal(ErrUnimplemented)


def mkdir(db: sqlite3.Connection, path: DBPath) -> RetVal:
	'''Creates a new directory in the database virtual filesytem.

	Parameters:
	  * path: the full DBPath of the directory to create
	
	Returns:
	  * id: (UUID) the unique identifier for that directory
	
	Notes:
		This function will create parent directories if they don't already exist.
	'''
	
	# TODO: implement dbfs.mkdir()
	return RetVal(ErrUnimplemented)


def move(db: sqlite3.Connection, filepath: DBPath, destination: DBPath) -> RetVal:
	'''Moves a file to another directory.

	Parameters:
	  * filepath: the full DBPath of the file to move
	  * destination: the directory to move the file to
	
	Notes:
		This function may not be used to rename files, only move them.
	'''
	
	# TODO: implement dbfs.move()
	return RetVal(ErrUnimplemented)


def read(db: sqlite3.Connection, path: DBPath) -> RetVal:
	'''Reads a file from the database virtual filesytem.
	
	Parameters:
	  * path: full DBPath of the file to read
	
	Returns:
	  * data: (str) The JSON data of the file payload
	'''
	
	# TODO: implement dbfs.read()
	return RetVal(ErrUnimplemented)


def rmdir(db: sqlite3.Connection, path: DBPath) -> RetVal:
	'''Removes a directory from the database virtual filesytem.
	
	Parameters:
	  * path: the DBPath of the directory to remove
	
	Returns:
	  * no additional fields
	
	Notes:
		This function will return an error if the directory is not empty.
	'''
	
	# TODO: implement dbfs.rmdir()
	return RetVal(ErrUnimplemented)


def write(db: sqlite3.Connection, path: DBPath, data: str) -> RetVal:
	'''Writes a file to the database virtual filesytem.
	
	Parameters:
	  * path: full DBPath of the file to write
	  * data: (str) The JSON data of the file payload
	
	Returns:
	  * no additional fields
	'''
	
	# TODO: implement dbfs.write()
	return RetVal(ErrUnimplemented)


class FolderMap:
	'''Represents the mapping of a server-side path to a local one'''
	def __init__(self):
		self.fid = ''
		self.address = ''
		self.keyid = ''
		self.path = DBPath('')
		self.permissions = ''
	
	def MakeID(self) -> None:
		'''Generates a FID for the object'''
		self.fid = str(uuid.uuid4())

	def Set(self, address, keyid, path, permissions) -> None:
		'''Sets the values of the object'''
		self.address = address
		self.keyid = keyid
		self.path = DBPath(path)
		self.permissions = permissions


def load_folder_maps(db: sqlite3.Connection) -> RetVal():
	'''Loads from the database all folder maps.

	Parameters:
		db: connection to the SQLite3 database
	
	Returns:
		maps: (dict) dictionary of UUID string keys to workspace-relative paths
	
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


