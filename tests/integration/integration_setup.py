import base64
import os.path
import re
import socket
import sys

import nacl.secret
import psycopg2
import toml

def load_db_config(config_file_path: str) -> dict:
	'''Loads the Anselus server configuration from the config file'''
	
	if os.path.exists(config_file_path):
		try:
			serverconfig = toml.load(config_file_path)
		except Exception as e:
			print("Unable to load server config %s: %s" % (config_file_path, e))
			sys.exit(1)
	else:
		serverconfig = {}

	serverconfig.setdefault('database', dict())
	serverconfig['database'].setdefault('engine','postgresql')
	serverconfig['database'].setdefault('ip','127.0.0.1')
	serverconfig['database'].setdefault('port','5432')
	serverconfig['database'].setdefault('name','anselus')
	serverconfig['database'].setdefault('user','anselus')
	serverconfig['database'].setdefault('password','CHANGEME')

	serverconfig.setdefault('network', dict())
	serverconfig['network'].setdefault('listen_ip','127.0.0.1')
	serverconfig['network'].setdefault('port','2001')

	serverconfig.setdefault('global', dict())
	serverconfig['global'].setdefault('workspace_dir','/var/anselus')
	serverconfig['global'].setdefault('registration','private')
	serverconfig['global'].setdefault('default_quota',0)

	serverconfig.setdefault('security', dict())
	serverconfig['security'].setdefault('failure_delay_sec',3)
	serverconfig['security'].setdefault('max_failures',5)
	serverconfig['security'].setdefault('lockout_delay_min',15)
	serverconfig['security'].setdefault('registration_delay_min',15)

	if serverconfig['database']['engine'].lower() != 'postgresql':
		print("This script exepects a server config using PostgreSQL. Exiting")
		sys.exit()
	
	return serverconfig


def db_setup(serverconfig: dict, schema_path: str):
	'''Reset the test database to defaults'''
	try:
		conn = psycopg2.connect(host=serverconfig['database']['ip'],
								port=serverconfig['database']['port'],
								database="anselus",
								user=serverconfig['database']['user'],
								password=serverconfig['database']['password'])
	except Exception as e:
		print("Couldn't connect to database: %s" % e)
		sys.exit(1)

	sqlcmds = ''
	with open(schema_path, 'r') as f:
		sqlcmds = f.read()
	
	cur = conn.cursor()
	cur.execute(sqlcmds)
	cur.close()
	conn.commit()

	return conn


def setup_test():
	'''Resets the Postgres test database to be ready for an integration test'''
	config = load_db_config('/etc/anselusd/serverconfig.toml')

	schema_path = os.path.abspath(__file__ + '/../')
	schema_path = os.path.join(schema_path, 'psql_schema.sql')
	conn = db_setup(config, schema_path)
	return conn


def add_workspace(account: dict, dbconn):
	'''Creates a workspace using the supplied information in the parameter `account`'''
	
	cursor = dbconn.cursor()
	cmdparts = ["INSERT INTO iwkspc_main(wid,friendly_address,password,status) VALUES('",
				account['wid'],
				"',"]
	if account['uid']:
		cmdparts.extend(["'",account['uid'],"',"])
	else:
		cmdparts.append("'',")
	
	cmdparts.extend(["'", account['serverpwhash'],"','", account['status'], "');"])
	cmd = ''.join(cmdparts)
	cursor.execute(cmd)
	
	box = nacl.secret.SecretBox(account['keys'][4]['key'])
	for folder_name,fid in account['folder_map'].items():
		cmd = ("INSERT INTO iwkspc_folders(wid, fid, enc_name, enc_key) "
					"VALUES('%s','%s','%s',$$%s$$);" % 
					( account['wid'], fid,
					base64.b85encode(box.encrypt(bytes(folder_name, 'utf8'))).decode('utf8'),
					account['keys'][4]['id']))
		cursor.execute(cmd)

	i = 0
	while i < len(account['devices']):
		cmd =	(	"INSERT INTO iwkspc_devices(wid, devid, keytype, devkey, status) "
					"VALUES('%s','%s','%s','%s','active');" % (
						account['wid'], account['devices'][i]['id'], 
						account['devices'][i]['keytype'],
						account['devices'][i]['public_b85']
					)
				)
		cursor.execute(cmd)
		i = i + 1
	
	cursor.close()
	dbconn.commit()


def connect():
	'''Creates a connection to the server.'''
	try:
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		# Set a short timeout in case the server doesn't respond immediately,
		# which is the expectation as soon as a client connects.
		sock.settimeout(10.0)
	except:
		return None
	
	try:
		sock.connect(('127.0.0.1', 2001))
		
		# absorb the hello string
		_ = sock.recv(8192)

	except Exception as e:
		print("Connection failed: %s" % e)
		sock.close()
		return None

	# Set a timeout of 30 minutes
	sock.settimeout(1800.0)
	return sock


def validate_uuid(indata):
	'''Validates a UUID's basic format. Does not check version information.'''

	# With dashes, should be 36 characters or 32 without
	if (len(indata) != 36 and len(indata) != 32) or len(indata) == 0:
		return False
	
	uuid_pattern = re.compile(
			r"[\da-fA-F]{8}-?[\da-fA-F]{4}-?[\da-fA-F]{4}-?[\da-fA-F]{4}-?[\da-fA-F]{12}")
	
	if not uuid_pattern.match(indata):
		return False
	
	return True
