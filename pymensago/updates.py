from retval import ErrUnimplemented, RetVal
from pymensago.serverconn import ServerConnection

def download_updates(conn: ServerConnection) -> RetVal:
	'''Checks for updates on the server and downloads them into the local database.'''

	# First, check the update table for existing ones. 

	# TODO: Finish download_updates() once app config module is written
	
	return RetVal(ErrUnimplemented, "download_updates() unimplemented")