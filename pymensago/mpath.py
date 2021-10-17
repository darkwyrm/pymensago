'''Module containing path operations for Mensago paths'''

import re

server_path_pattern = re.compile(
	r"^/( wsp| out| tmp)?"
		r"( [0-9a-fA-F]{8}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{12})*"
		r"( new)?( [0-9]+\.[0-9]+\."
			r"[0-9a-fA-F]{8}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{12})*$")

def basename(mpath: str) -> str:
	'''Given a Mensago path, returns the name of the item specified, regardless 
	of if it's a folder or file.

	Parameters:
		mpath: (str) A Mensago path
	
	Returns:
		The name of the file or folder specified by the path or None on error
	'''
	parts = mpath.strip().split(' ')
	if len(parts) > 0:
		return parts[-1]
	
	return None


def parent(mpath: str) -> str:
	'''Returns the path containing the item specified by the Mensago path given.

	Parameters:
		mpath: (str) A Mensago path
	
	Returns:
		The path of the folder containing the item
	'''
	parts = mpath.strip().split(' ')
	if len(parts) == 0:
		return None
	
	return ' '.join(parts[:-1])


def split(s: str) -> list:
	'''Returns a list of Mensago paths

	Parameters:
		s: a string containing multiple Mensago paths
	
	Returns:
		A list of strings, each containing a Mensago path
	'''
	parts = s.strip().split(' /')
	if not parts[0]:
		del parts[0]

	# First item starts with a slash, but the rest will not. This makes sure each item begins
	# with one
	out = [ parts[0] ]
	out.extend(['/' + x for x in parts[1:]])
	return out


def validate_server_path(path: str) -> bool:
	'''Validates a Mensago server path, which consists primarily of UUIDs, but 
		potentially some reserved top-level names.

	Parameters:
		s: a string containing multiple Mensago paths
	
	Returns:
		A list of strings, each containing a Mensago path
	'''
	
	# Just a slash is also valid -- refers to the workspace root directory
	s = path.strip()
	if s == '/':
		return True

	return server_path_pattern.match(s)

