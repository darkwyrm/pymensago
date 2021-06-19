'''This module encapsulates workspace-specific methods'''

import pathlib

import sqlite3
from retval import RetVal, ErrExists, ErrNotFound, ErrBadValue

import pymensago.auth as auth
import pymensago.encryption as encryption
from pymensago.utils import UserID, UUID, Domain

class Workspace:
	'''Workspace provides high-level operations for managing workspace data.'''
	def __init__(self, db: sqlite3.Connection, path: str):
		self.db = db
		self.path = pathlib.Path(path).absolute()
		self.uid = UserID()
		self.wid = UUID()
		self.domain = Domain()
		self.type = 'identity'
		self.pw = encryption.Password()

	def generate(self, userid: UserID, server: Domain, wid: UUID, pw: encryption.Password) -> RetVal:
		'''Creates all the data needed for an individual workspace account'''

		if not userid.is_valid() and userid:
			return RetVal(ErrBadValue, 'userid not valid')
		if not server.is_valid():
			return RetVal(ErrBadValue, 'domain not valid')
		if not wid.is_valid():
			return RetVal(ErrBadValue, 'workspace id not valid')
		if not pw.is_valid():
			return RetVal(ErrBadValue, 'password not valid')

		self.uid = userid
		self.wid = wid
		self.domain = server
		self.pw = pw

		# Add workspace
		status = self.add_to_db(pw)
		if status.error():
			return status
		
		address = wid.as_string() + '/' + server.as_string()

		# Generate user's encryption keys
		keys = {
			'crencryption' : encryption.EncryptionPair(),
			'crsigning' : encryption.SigningPair(),
			'encryption' : encryption.EncryptionPair(),
			'signing' : encryption.SigningPair(),
			'storage' : encryption.SecretKey(),
			'folder' : encryption.SecretKey()
		}
		
		# Add encryption keys
		for key in keys.values():
			out = auth.add_key(self.db, key, address)
			if out.error():
				status = self.remove_workspace_entry(wid, server)
				if status.error():
					return status
		
		# Add folder mappings
		foldermap = encryption.FolderMapping()

		folderlist = [
			'messages',
			'contacts',
			'events',
			'tasks',
			'notes',
			'files',
			'files attachments'
		]

		for folder in folderlist:
			foldermap.MakeID()
			foldermap.Set(address, keys['folder'].pubhash, folder, 'root')
			self.add_folder(foldermap)

		# Create the folders themselves
		try:
			self.path.mkdir(parents=True, exist_ok=True)
		except Exception as e:
			self.remove_from_db()
			return RetVal.wrap_exception(e)
		
		self.path.joinpath('files').mkdir(exist_ok=True)
		self.path.joinpath('files','attachments').mkdir(exist_ok=True)

		self.set_userid(userid)
		return RetVal()

	def add_to_db(self, pw: encryption.Password) -> RetVal:
		'''Adds a workspace to the storage database'''

		cursor = self.db.cursor()
		cursor.execute("SELECT wid FROM workspaces WHERE wid=? OR type = 'identity'", 
			(self.wid.as_string(),))
		results = cursor.fetchone()
		if results:
			return RetVal(ErrExists, self.wid.as_string())
		
		cursor.execute('''INSERT INTO workspaces(wid,domain,password,pwhashtype,type)
			VALUES(?,?,?,?,?)''', 
			(self.wid.as_string(), self.domain.as_string(), pw.hashstring, pw.hashtype, self.type))
		self.db.commit()
		return RetVal()

	def remove_from_db(self) -> RetVal:
		'''
		Removes ALL DATA associated with a workspace. Don't call this unless you mean to erase
		all evidence that a particular workspace ever existed.
		'''
		cursor = self.db.cursor()
		cursor.execute("SELECT wid FROM workspaces WHERE wid=? AND domain=?", (self.wid,self.domain))
		results = cursor.fetchone()
		if not results or not results[0]:
			return RetVal(ErrNotFound, "%s/%s" % (self.wid, self.domain))
		
		address = '/'.join([self.wid,self.domain])
		cursor.execute("DELETE FROM workspaces WHERE wid=? AND domain=?", (self.wid,self.domain))
		cursor.execute("DELETE FROM folders WHERE address=?", (address,))
		cursor.execute("DELETE FROM sessions WHERE address=?", (address,))
		cursor.execute("DELETE FROM keys WHERE address=?", (address,))
		cursor.execute("DELETE FROM messages WHERE address=?", (address,))
		cursor.execute("DELETE FROM notes WHERE address=?", (address,))
		self.db.commit()
		return RetVal()
	
	def remove_workspace_entry(self, wid: UUID, domain: Domain) -> RetVal:
		'''
		Removes a workspace from the storage database.
		NOTE: this only removes the workspace entry itself. It does not remove keys, sessions,
		or other associated data.
		'''
		cursor = self.db.cursor()
		cursor.execute("SELECT wid FROM workspaces WHERE wid=? AND domain=?", 
			(wid.as_string(),domain.as_string()))
		results = cursor.fetchone()
		if not results or not results[0]:
			return RetVal(ErrNotFound, "%s/%s not found" % (wid.as_string(),domain.as_string()))
		
		cursor.execute("DELETE FROM workspaces WHERE wid=? AND domain=?", 
			(wid.as_string(),domain.as_string()))
		self.db.commit()
		return RetVal()
		
	def add_folder(self, folder: encryption.FolderMapping) -> RetVal:
		'''
		Adds a mapping of a folder ID to a specific path in the workspace.
		Parameters:
		folder : FolderMapping object
		'''
		cursor = self.db.cursor()
		cursor.execute("SELECT fid FROM folders WHERE fid=?", (folder.fid,))
		results = cursor.fetchone()
		if results:
			return RetVal(ErrExists, folder.fid)
		
		cursor.execute('''INSERT INTO folders(fid,address,keyid,path,permissions)
			VALUES(?,?,?,?,?)''', (folder.fid, folder.address, folder.keyid, folder.path,
				folder.permissions))
		self.db.commit()
		return RetVal()

	def remove_folder(self, fid: encryption.FolderMapping) -> RetVal:
		'''Deletes a folder mapping.
		Parameters:
		fid : uuid

		Returns:
		error : string
		'''
		cursor = self.db.cursor()
		cursor.execute("SELECT fid FROM folders WHERE fid=?", (fid,))
		results = cursor.fetchone()
		if not results or not results[0]:
			return RetVal(ErrNotFound, fid)

		cursor.execute("DELETE FROM folders WHERE fid=?", (fid,))
		self.db.commit()
		return RetVal()
	
	def get_folder(self, fid: encryption.FolderMapping) -> RetVal:
		'''Gets the specified folder.
		Parameters:
		fid : uuid

		Returns:
		'error' : string
		'folder' : FolderMapping object
		'''

		cursor = self.db.cursor()
		cursor.execute('''
			SELECT address,keyid,path,permissions FROM folders WHERE fid=?''', (fid,))
		results = cursor.fetchone()
		if not results or not results[0]:
			return RetVal(ErrNotFound, fid)
		
		folder = encryption.FolderMapping()
		folder.fid = fid
		folder.Set(results[0], results[1], results[2], results[3])
		
		return RetVal().set_value('folder', folder)

	def set_userid(self, userid: UserID) -> RetVal:
		'''set_userid() sets the human-friendly name for the workspace'''
		
		if ' ' or '"' in userid:
			return RetVal(ErrBadValue, '" and space not permitted')
		
		cursor = self.db.cursor()
		sqlcmd='''
		UPDATE workspaces
		SET userid=?
		WHERE wid=? and domain=?
		'''
		cursor.execute(sqlcmd, (userid.as_string(), self.wid.as_string(), self.domain.as_string()))
		self.db.commit()
		self.uid = userid

		return RetVal()

	def get_userid(self) -> RetVal:
		'''get_userid() gets the human-friendly name for the workspace'''
		return RetVal().set_value('userid', self.uid)
