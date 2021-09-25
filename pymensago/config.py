import os
import platform
import sqlite3
import sys
import toml

from retval import  RetVal, ErrEmptyData

# Although load_server_config() exists here for historical reasons, this module is for interacting
# with application configuration information. It is stored as a table of strings in the profile's
# database. This is so that a person can have a regular everyday profile and a super-secret
# Paranoid Mode profile for whatever reason and they can coexist peacefully.

_modstate = {
	'path': '',
	'dbconn': None
}

def load(path: str) -> RetVal:
	'''Attempts to load settings from the specified database.'''
	if not path:
		return RetVal(ErrEmptyData)
	
	global _modstate 

	try:
		conn = sqlite3.connect(path)
	except Exception as e:
		return RetVal().wrap_exception(e)

	_modstate['path'] = path
	_modstate['dbconn'] = conn
	
	# Ensure that the configuration table exists
	cur = conn.cursor()
	cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='appconfig';")
	exists = cur.fetchone()
	
	if not exists:
		cur.execute('''CREATE TABLE "appconfig" (
			"fname" TEXT NOT NULL UNIQUE,
			"ftype" TEXT NOT NULL,
			"fvalue" TEXT);''')
		conn.commit()

	return RetVal()


def get_int(name: str) -> int:
	'''Gets an integer field. Returns None if it doesn't exist.'''
	global _modstate
	if not name or not _modstate['path']:
		return None
	
	conn = _modstate['dbconn']

	cur = conn.cursor()
	cur.execute("SELECT fvalue FROM appconfig WHERE fname=? AND ftype='int';", (name,))
	row = cur.fetchone()
	if not row or len(row) == 0:
		return None
	
	try:
		out = int(row[0])
	except:
		return None

	return out


def set_int(name: str, value: int) -> bool:
	'''Creates/sets an integer field'''
	global _modstate
	if not name or not value or not _modstate['path'] or not isinstance(value, int):
		return False
	
	conn = _modstate['dbconn']

	val = get_int(name)

	cur = conn.cursor()
	if val is not None:
		cur.execute("UPDATE appconfig SET fvalue=? WHERE fname=? and ftype='int';", (value, name))
	else:
		cur.execute("INSERT INTO appconfig (fname,ftype,fvalue) VALUES(?,'int',?);", (name, value))
	conn.commit()
	return True


def get_str(name: str) -> str:
	'''Gets a string field. Returns None if it doesn't exist.'''
	global _modstate
	if not name or not _modstate['path']:
		return None
	
	conn = _modstate['dbconn']

	cur = conn.cursor()
	cur.execute("SELECT fvalue FROM appconfig WHERE fname=? AND ftype='str';", (name,))
	row = cur.fetchone()
	if not row or len(row) == 0:
		return None

	return row[0]


def set_str(name: str, value: int) -> bool:
	'''Creates/sets a string field'''
	global _modstate
	if not name or not value or not _modstate['path'] or not isinstance(value, str):
		return False
	
	conn = _modstate['dbconn']

	val = get_str(name)

	cur = conn.cursor()
	if val is not None:
		cur.execute("UPDATE appconfig SET fvalue=? WHERE fname=? and ftype='str';", (value, name))
	else:
		cur.execute("INSERT INTO appconfig (fname,ftype,fvalue) VALUES(?,'str',?);", (name, value))
	conn.commit()
	return True


def load_server_config() -> dict:
	'''Loads the Mensago server configuration from the config file'''
	
	config_file_path = '/etc/mensagod/serverconfig.toml'
	if platform.system() == 'Windows':
		config_file_path = 'C:\\ProgramData\\mensagod\\serverconfig.toml'

	if os.path.exists(config_file_path):
		try:
			serverconfig = toml.load(config_file_path)
		except Exception as e:
			print("Unable to load server config %s: %s" % (config_file_path, e))
			sys.exit(1)
	else:
		serverconfig = {}
	
	serverconfig.setdefault('network', dict())
	serverconfig['network'].setdefault('listen_ip','127.0.0.1')
	serverconfig['network'].setdefault('port', 2001)

	serverconfig.setdefault('database', dict())
	serverconfig['database'].setdefault('engine','postgresql')
	serverconfig['database'].setdefault('ip','127.0.0.1')
	serverconfig['database'].setdefault('port','5432')
	serverconfig['database'].setdefault('name','mensago')
	serverconfig['database'].setdefault('user','mensago')
	serverconfig['database'].setdefault('password','CHANGEME')

	serverconfig.setdefault('global', dict())

	if platform.system() == 'Windows':
		serverconfig['global'].setdefault('top_dir','C:\\ProgramData\\mensago')
		serverconfig['global'].setdefault('workspace_dir','C:\\ProgramData\\mensago\\wsp')
	else:
		serverconfig['global'].setdefault('top_dir','/var/mensago')
		serverconfig['global'].setdefault('workspace_dir','/var/mensago/wsp')
	serverconfig['global'].setdefault('registration','private')
	serverconfig['global'].setdefault('registration_subnet',
		'192.168.0.0/16, 172.16.0.0/12, 10.0.0.0/8, 127.0.0.1/8')
	serverconfig['global'].setdefault('registration_subnet6','fe80::/10')
	serverconfig['global'].setdefault('default_quota',0)
	
	serverconfig.setdefault('performance', dict())
	serverconfig['performance'].setdefault('max_file_size', 50)
	serverconfig['performance'].setdefault('max_message_size', 50)
	serverconfig['performance'].setdefault('max_sync_age', 7)
	serverconfig['performance'].setdefault('max_delivery_threads', 100)
	serverconfig['performance'].setdefault('max_client_threads', 10_000)
	serverconfig['performance'].setdefault('keycard_cache_size', 5_000)

	serverconfig.setdefault('security', dict())
	serverconfig['security'].setdefault('diceware_wordlist', 'eff_short_prefix')
	serverconfig['security'].setdefault('diceware_wordcount', 6)
	serverconfig['security'].setdefault('failure_delay_sec',3)
	serverconfig['security'].setdefault('max_failures',5)
	serverconfig['security'].setdefault('lockout_delay_min',15)
	serverconfig['security'].setdefault('registration_delay_min',15)
	serverconfig['security'].setdefault('password_reset_min', 60)
	serverconfig['security'].setdefault('password_security', 'normal')

	if serverconfig['database']['engine'].lower() != 'postgresql':
		print("This script exepects a server config using PostgreSQL. Exiting")
		sys.exit()
	
	return serverconfig

