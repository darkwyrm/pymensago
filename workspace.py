'''This module encapsulates workspace-specific methods'''

import pathlib

import encryption
from retval import RetVal, ResourceExists, ResourceNotFound, ExceptionThrown

class Workspace:
	'''Workspace provides high-level operations for managing workspace data.'''
	def __init__(self, db, path):
		self.db = db
		p = pathlib.Path(path)
		self.path = p.absolute()

	def generate(self, name, server, wid, pw):
		'''Creates full all the data needed for an individual workspace account'''
		
		# Add workspace
		status = self.add_to_db(wid, server, pw)
		if status.error():
			return status
		
		address = '/'.join([wid,server])

		# Generate user's encryption keys
		keys = {
			'identity' : encryption.KeyPair('identity'),
			'conrequest' : encryption.KeyPair('conrequest'),
			'broadcast' : encryption.SecretKey('broadcast'),
			'folder' : encryption.SecretKey('folder')
		}
		
		# Add encryption keys
		for key in keys.items():
			out = self.db.add_key(key, address)
			if out['error']:
				status = self.db.remove_from_db_entry(wid, server)
				if status.error():
					return status
		
		# Add folder mappings
		foldermap = encryption.FolderMapping()

		folderlist = [
			'messages',
			'contacts',
			'events',
			'tasks',
			'notes'
			'files',
			'files attachments'
		]

		for folder in folderlist:
			foldermap.MakeID()
			foldermap.Set(address, keys['folder'].get_id(), folder, 'root')
			self.db.add_folder(foldermap)

		# Create the folders themselves
		try:
			self.path.mkdir(parents=True, exist_ok=True)
		except Exception as e:
			self.remove_from_db(wid, server)
			return RetVal(ExceptionThrown, e.__str__())
		
		self.path.joinpath('files').mkdir(exist_ok=True)
		self.path.joinpath('files','attachments').mkdir(exist_ok=True)
		return RetVal()

	def add_to_db(self, wid, domain, pw):
		'''Adds a workspace to the storage database'''

		cursor = self.db.cursor()
		cursor.execute("SELECT wid FROM workspaces WHERE wid=?", (wid,))
		results = cursor.fetchone()
		if results:
			return RetVal(ResourceExists, wid)
		
		cursor.execute('''INSERT INTO workspaces(wid,domain,password,pwhashtype,type)
			VALUES(?,?,?,?,?)''', (wid, domain, pw.hashstring, pw.hashtype, "single"))
		self.db.commit()
		return RetVal()

	def remove_from_db(self, wid, domain):
		'''
		Removes ALL DATA associated with a workspace. Don't call this unless you mean to erase
		all evidence that a particular workspace ever existed.
		'''
		cursor = self.db.cursor()
		cursor.execute("SELECT wid FROM workspaces WHERE wid=? AND domain=?", (wid,domain))
		results = cursor.fetchone()
		if not results or not results[0]:
			return RetVal(ResourceNotFound, "%s/%s" % (wid, domain))
		
		address = '/'.join([wid,domain])
		cursor.execute("DELETE FROM workspaces WHERE wid=? AND domain=?", (wid,domain))
		cursor.execute("DELETE FROM folders WHERE address=?", (address,))
		cursor.execute("DELETE FROM sessions WHERE address=?", (address,))
		cursor.execute("DELETE FROM keys WHERE address=?", (address,))
		cursor.execute("DELETE FROM messages WHERE address=?", (address,))
		cursor.execute("DELETE FROM notes WHERE address=?", (address,))
		self.db.commit()
		return RetVal()
	
	def add_folder(self, folder):
		'''
		Adds a mapping of a folder ID to a specific path in the workspace.
		Parameters:
		folder : FolderMapping object
		'''
		cursor = self.db.cursor()
		cursor.execute("SELECT fid FROM folders WHERE fid=?", (folder.fid,))
		results = cursor.fetchone()
		if results:
			return RetVal(ResourceExists, folder.fid)
		
		cursor.execute('''INSERT INTO folders(fid,address,keyid,path,permissions)
			VALUES(?,?,?,?,?)''', (folder.fid, folder.address, folder.keyid, folder.path,
				folder.permissions))
		self.db.commit()
		return RetVal()

	def remove_folder(self, fid):
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
			return RetVal(ResourceNotFound, fid)

		cursor.execute("DELETE FROM folders WHERE fid=?", (fid,))
		self.db.commit()
		return RetVal()
	
	def get_folder(self, fid):
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
			return RetVal(ResourceNotFound, fid)
		
		folder = encryption.FolderMapping()
		folder.fid = fid
		folder.Set(results[0], results[1], results[2], results[3])
		
		out = RetVal()
		out.set_value('folder', folder)
		return out
