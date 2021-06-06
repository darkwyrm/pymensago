import os
import platform
import sys
import toml

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
