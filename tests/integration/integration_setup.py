from glob import glob
import inspect
import os.path
import shutil
import sqlite3
import sys
import time

import psycopg2
from pycryptostring import CryptoString
from retval import RetVal

# pylint: disable=import-error
import pymensago.auth as auth
from pymensago.client import MensagoClient
from pymensago.config import load_server_config
from pymensago.encryption import Password, EncryptionPair, SigningPair, FolderMapping, SecretKey
import pymensago.keycard as keycard
import pymensago.iscmds as iscmds
import pymensago.serverconn as serverconn
import pymensago.userprofile as userprofile
import pymensago.utils as utils
from pymensago.workspace import Workspace

# Keys used in the various tests. 
# THESE KEYS ARE STORED ON GITHUB! DO NOT USE THESE FOR ANYTHING EXCEPT UNIT TESTS!!

# Test Organization Information

# Name: Example.com
# Contact-Admin: ae406c5e-2673-4d3e-af20-91325d9623ca/acme.com
# Support and Abuse accounts are forwarded to Admin
# Language: en

# Initial Organization Primary Signing Key: {UNQmjYhz<(-ikOBYoEQpXPt<irxUF*nq25PoW=_
# Initial Organization Primary Verification Key: r#r*RiXIN-0n)BzP3bv`LA&t4LFEQNF0Q@$N~RF*
# Initial Organization Primary Verification Key Hash: 
# 	BLAKE2B-256:ag29av@TUvh-V5KaB2l}H=m?|w`}dvkS1S1&{cMo

# Initial Organization Encryption Key: SNhj2K`hgBd8>G>lW$!pXiM7S-B!Fbd9jT2&{{Az
# Initial Organization Encryption Key Hash: BLAKE2B-256:-Zz4O7J;m#-rB)2llQ*xTHjtblwm&kruUVa_v(&W
# Initial Organization Decryption Key: WSHgOhi+bg=<bO^4UoJGF-z9`+TBN{ds?7RZ;w3o


# Test Admin Information

# Initial Admin CR Encryption Key: CURVE25519:mO?WWA-k2B2O|Z%fA`~s3^$iiN{5R->#jxO@cy6{
# Initial Admin CR Decryption Key: CURVE25519:2bLf2vMA?GA2?L~tv<PA9XOw6e}V~ObNi7C&qek>

# Initial Admin CR Verification Key: ED25519:E?_z~5@+tkQz!iXK?oV<Zx(ec;=27C8Pjm((kRc|
# Initial Admin CR Signing Key: ED25519:u4#h6LEwM6Aa+f<++?lma4Iy63^}V$JOP~ejYkB;

# Initial Admin Encryption Key: CURVE25519:Umbw0Y<^cf1DN|>X38HCZO@Je(zSe6crC6X_C_0F
# Initial Admin Decryption Key: CURVE25519:Bw`F@ITv#sE)2NnngXWm7RQkxg{TYhZQbebcF5b$

# Initial Admin Verification Key: 6|HBWrxMY6-?r&Sm)_^PLPerpqOj#b&x#N_#C3}p
# Initial Admin Signing Key: p;XXU0XF#UO^}vKbC-wS(#5W6=OEIFmR2z`rS1j+


# Test User Information

# Name: Corbin Simons
# Workspace-ID: 4418bf6c-000b-4bb3-8111-316e72030468
# Domain: example.com

# Initial User Contact Request Verification Key: d0-oQb;{QxwnO{=!|^62+E=UYk2Y3mr2?XKScF4D
# Initial User Contact Request Signing Key: ip52{ps^jH)t$k-9bc_RzkegpIW?}FFe~BX&<V}9

# Initial User Contact Request Encryption Key: j(IBzX*F%OZF;g77O8jrVjM1a`Y<6-ehe{S;{gph
# Initial User Contact Request Decryption Key: 55t6A0y%S?{7c47p(R@C*X#at9Y`q5(Rc#YBS;r}

# Initial User Encryption Key: nSRso=K(WF{P+4x5S*5?Da-rseY-^>S8VN#v+)IN
# Initial User Decryption Key: 4A!nTPZSVD#tm78d=-?1OIQ43{ipSpE;@il{lYkg

# Initial User Verification Key: ED25519:k^GNIJbl3p@N=j8diO-wkNLuLcNF6#JF=@|a}wFE
# Initial User Signing Key: ED25519:;NEoR>t9n3v%RbLJC#*%n4g%oxqzs)&~k+fH4uqi

def funcname() -> str: 
	frame = inspect.currentframe()
	return inspect.getframeinfo(frame).function

def setup_test():
	'''Resets the Postgres test database to be ready for an integration test'''
	
	serverconfig = load_server_config()

	# Reset the test database to defaults
	try:
		conn = psycopg2.connect(host=serverconfig['database']['ip'],
								port=serverconfig['database']['port'],
								database=serverconfig['database']['name'],
								user=serverconfig['database']['user'],
								password=serverconfig['database']['password'])
	except Exception as e:
		print("Couldn't connect to database: %s" % e)
		sys.exit(1)

	schema_path = os.path.abspath(__file__ + '/../')
	schema_path = os.path.join(schema_path, 'psql_schema.sql')

	sqlcmds = ''
	with open(schema_path, 'r') as f:
		sqlcmds = f.read()
	
	cur = conn.cursor()
	cur.execute(sqlcmds)
	cur.close()
	conn.commit()

	return conn


def init_server(dbconn) -> dict:
	'''Adds basic data to the database as if setupconfig had been run. Returns data needed for 
	tests, such as the keys'''
	
	# Start off by generating the org's root keycard entry and add to the database

	cur = dbconn.cursor()
	card = keycard.Keycard()
	
	root_entry = keycard.OrgEntry()
	root_entry.set_fields({
		'Name':'Example, Inc.',
		'Contact-Admin':'c590b44c-798d-4055-8d72-725a7942f3f6/acme.com',
		'Language':'en',
		'Domain':'example.com',
		'Primary-Verification-Key':'ED25519:r#r*RiXIN-0n)BzP3bv`LA&t4LFEQNF0Q@$N~RF*',
		'Encryption-Key':'CURVE25519:SNhj2K`hgBd8>G>lW$!pXiM7S-B!Fbd9jT2&{{Az'
	})

	initial_ovkey = CryptoString(r'ED25519:r#r*RiXIN-0n)BzP3bv`LA&t4LFEQNF0Q@$N~RF*')
	initial_oskey = CryptoString(r'ED25519:{UNQmjYhz<(-ikOBYoEQpXPt<irxUF*nq25PoW=_')
	initial_ovhash = CryptoString(r'BLAKE2B-256:ag29av@TUvh-V5KaB2l}H=m?|w`}dvkS1S1&{cMo')

	initial_epubkey = CryptoString(r'CURVE25519:SNhj2K`hgBd8>G>lW$!pXiM7S-B!Fbd9jT2&{{Az')
	initial_eprivkey = CryptoString(r'CURVE25519:WSHgOhi+bg=<bO^4UoJGF-z9`+TBN{ds?7RZ;w3o')
	initial_epubhash = CryptoString(r'BLAKE2B-256:-Zz4O7J;m#-rB)2llQ*xTHjtblwm&kruUVa_v(&W')
	
	# Organization hash, sign, and verify

	rv = root_entry.generate_hash('BLAKE2B-256')
	assert not rv.error(), 'entry failed to hash'

	rv = root_entry.sign(initial_oskey, 'Organization')
	assert not rv.error(), 'Unexpected RetVal error %s' % rv.error()
	assert root_entry.signatures['Organization'], 'entry failed to org sign'

	rv = root_entry.verify_signature(initial_ovkey, 'Organization')
	assert not rv.error(), 'org entry failed to verify'

	status = root_entry.is_compliant()
	assert not status.error(), f"OrgEntry wasn't compliant: {str(status)}"

	card.entries.append(root_entry)
	cur.execute("INSERT INTO keycards(owner,creationtime,index,entry,fingerprint) " \
		"VALUES('organization',%s,%s,%s,%s);",
		(root_entry.fields['Timestamp'],root_entry.fields['Index'],
			root_entry.make_bytestring(-1).decode(), root_entry.hash))

	cur.execute("INSERT INTO orgkeys(creationtime, pubkey, privkey, purpose, fingerprint) "
				"VALUES(%s,%s,%s,'encrypt',%s);",
				(root_entry.fields['Timestamp'], initial_epubkey.as_string(),
				initial_eprivkey.as_string(), initial_epubhash.as_string()))

	cur.execute("INSERT INTO orgkeys(creationtime, pubkey, privkey, purpose, fingerprint) "
				"VALUES(%s,%s,%s,'sign',%s);",
				(root_entry.fields['Timestamp'], initial_ovkey.as_string(),
				initial_oskey.as_string(), initial_ovhash.as_string()))

	cur.close()
	dbconn.commit()	
	cur = dbconn.cursor()

	# Sleep for 1 second in order for the new entry's timestamp to be useful
	time.sleep(1)

	# Chain a new entry to the root

	status = card.chain(initial_oskey, True)
	assert not status.error(), f'keycard chain failed: {status}'

	# Save the keys to a separate RetVal so we can keep using status for return codes
	keys = status
	
	new_entry = status['entry']
	new_entry.prev_hash = root_entry.hash
	new_entry.generate_hash('BLAKE2B-256')
	assert not status.error(), f'chained entry failed to hash: {status}'
	
	status = card.verify()
	assert not status.error(), f'keycard failed to verify: {status}'

	cur.execute("INSERT INTO keycards(owner,creationtime,index,entry,fingerprint) " \
		"VALUES('organization',%s,%s,%s,%s);",
		(new_entry.fields['Timestamp'],new_entry.fields['Index'],
			new_entry.make_bytestring(-1).decode(), new_entry.hash))

	cur.execute("INSERT INTO orgkeys(creationtime, pubkey, privkey, purpose, fingerprint) "
				"VALUES(%s,%s,%s,'sign',%s);",
				(new_entry.fields['Timestamp'], keys['sign.public'],
				keys['sign.private'], keys['sign.pubhash']))

	cur.execute("INSERT INTO orgkeys(creationtime, pubkey, privkey, purpose, fingerprint) "
				"VALUES(%s,%s,%s,'encrypt',%s);",
				(new_entry.fields['Timestamp'], keys['encrypt.public'],
				keys['encrypt.private'], keys['encrypt.pubhash']))
	
	if keys.has_value('altsign.public'):
		cur.execute("INSERT INTO orgkeys(creationtime, pubkey, privkey, purpose, fingerprint) "
					"VALUES(%s,%s,%s,'altsign',%s);",
					(new_entry.fields['Timestamp'], keys['altsign.public'],
					keys['altsign.private'], keys['altsign.pubhash']))


	# Prereg the admin account
	admin_wid = utils.UUID('ae406c5e-2673-4d3e-af20-91325d9623ca')
	regcode = 'Undamaged Shining Amaretto Improve Scuttle Uptake'
	cur.execute(f"INSERT INTO prereg(wid, uid, domain, regcode) VALUES('{admin_wid}', 'admin', "
		f"'example.com', '{regcode}');")
	
	# Set up abuse/support forwarding to admin
	abuse_wid = 'f8cfdbdf-62fe-4275-b490-736f5fdc82e3'
	cur.execute("INSERT INTO workspaces(wid, uid, domain, password, status, wtype) "
		f"VALUES('{abuse_wid}', 'abuse', 'example.com', '-', 'active', 'alias');")
	cur.execute(f"INSERT INTO aliases(wid, alias) VALUES('{abuse_wid}', "
		f"'{'/'.join([admin_wid.as_string(), 'example.com'])}');")

	support_wid = 'f0309ef1-a155-4655-836f-55173cc1bc3b'
	cur.execute(f"INSERT INTO workspaces(wid, uid, domain, password, status, wtype) "
		f"VALUES('{support_wid}', 'support', 'example.com', '-', 'active', 'alias');")
	cur.execute(f"INSERT INTO aliases(wid, alias) VALUES('{support_wid}', "
		f"'{'/'.join([admin_wid.as_string(), 'example.com'])}');")
	
	cur.close()
	dbconn.commit()	

	return {
		'configfile' : load_server_config(),
		'ovkey' : keys['sign.public'],
		'oskey' : keys['sign.private'],
		'oekey' : keys['encrypt.public'],
		'odkey' : keys['encrypt.private'],
		'admin_wid' : utils.UUID(admin_wid),
		'admin_regcode' : regcode,
		'root_org_entry' : root_entry,
		'second_org_entry' : new_entry,
		'support_wid' : utils.UUID(support_wid),
		'abuse_wid' : utils.UUID(abuse_wid)
	}


def reset_workspace_dir(config: dict):
	'''Resets the system workspace storage directory to an empty skeleton'''

	glob_list = glob(os.path.join(config['configfile']['global']['workspace_dir'],'*'))
	if not glob_list:
		return
	
	for glob_item in glob_list:
		if os.path.isfile(glob_item):
			try:
				os.remove(glob_item)
			except:
				assert False, f"Unable to delete file {glob_item}"
		else:
			try:
				shutil.rmtree(glob_item)
			except:
				assert False, f"Unable to delete file {glob_item}"
	
	os.mkdir(os.path.join(config['configfile']['global']['workspace_dir'],'tmp'))


# Setup functions for tests and commands

def setup_profile_base(name):
	'''Creates a new profile folder hierarchy'''
	test_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)),'testfiles')
	if not os.path.exists(test_folder):
		os.mkdir(test_folder)

	profiletest_folder = os.path.join(test_folder, name)
	while os.path.exists(profiletest_folder):
		try:
			shutil.rmtree(profiletest_folder)
		except:
			print("Waiting a second for test folder to unlock")
			time.sleep(1.0)
	os.mkdir(profiletest_folder)
	return profiletest_folder


def setup_admin_profile(profile_folder: str, config: dict) -> RetVal:
	'''Creates the client-side profile for the administrator account'''

	config['profile_folder'] = profile_folder

	profman = userprofile.profman
	status = profman.load_profiles(profile_folder)
	assert not status.error(), f"{funcname()}(): Failed to init profile folder {profile_folder}"

	status = profman.get_active_profile()
	assert not status.error(), f"{funcname()}(): Failed to get default profile"
	profile = status['profile']

	# The profile folder is assumed to be empty for the purposes of these tests. Thus, we will
	# also assume that the primary profile for the integration tests is for the admin. The
	# profile will not have any workspaces assigned to it, so we will create a workspace for the
	# admin and add it to the primary profile.
	
	password = Password('Linguini2Pegboard*Album')
	config['admin_password'] = password

	# In order to have consistent keys for debugging and testing purposes, we are going to more
	# or less reimplement Workspace.generate() here.'

	w = Workspace(profile.db, profile_folder)

	w.uid = utils.UserID('admin')
	w.wid = config['admin_wid']
	w.domain = utils.Domain('example.com')
	w.pw = password

	address = w.wid.as_string() + '/' + w.domain.as_string()

	# Generate and add user's crypto keys

	keys = {
		'crencryption': EncryptionPair(
			CryptoString(r'CURVE25519:mO?WWA-k2B2O|Z%fA`~s3^$iiN{5R->#jxO@cy6{'),
			CryptoString(r'CURVE25519:2bLf2vMA?GA2?L~tv<PA9XOw6e}V~ObNi7C&qek>'	)),
		
		'crsigning': SigningPair(
			CryptoString(r'ED25519:E?_z~5@+tkQz!iXK?oV<Zx(ec;=27C8Pjm((kRc|'),
			CryptoString(r'ED25519:u4#h6LEwM6Aa+f<++?lma4Iy63^}V$JOP~ejYkB;')),
		
		'encryption': EncryptionPair(
			CryptoString(r'CURVE25519:Umbw0Y<^cf1DN|>X38HCZO@Je(zSe6crC6X_C_0F'),
			CryptoString(r'CURVE25519:Bw`F@ITv#sE)2NnngXWm7RQkxg{TYhZQbebcF5b$')),
		
		'signing': SigningPair(
			CryptoString(r'ED25519:6|HBWrxMY6-?r&Sm)_^PLPerpqOj#b&x#N_#C3}p'),
			CryptoString(r'ED25519:p;XXU0XF#UO^}vKbC-wS(#5W6=OEIFmR2z`rS1j+')),
		
		'storage': SecretKey(CryptoString(r'XSALSA20:M^z-E(u3QFiM<QikL|7|vC|aUdrWI6VhN+jt>GH}')),
		'folder': SecretKey(CryptoString(r'XSALSA20:H)3FOR}+C8(4Jm#$d+fcOXzK=Z7W+ZVX11jI7qh*'))
	}

	config['admin_crepair'] = keys['crencryption']
	config['admin_crspair'] = keys['crsigning']
	config['admin_epair'] = keys['encryption']
	config['admin_spair'] = keys['signing']
	config['admin_storage'] = keys['storage']
	config['admin_folder'] = keys['folder']

	for k,v in keys.items():
		status = auth.add_key(profile.db, v, address, k)
		assert not status.error(), f"{funcname()}(): Failed to add {k} key to db"
	
	# Add folder mappings
	foldermap = FolderMapping()

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
		w.add_folder(foldermap)

	# Create the folders themselves

	w.path.mkdir(parents=True, exist_ok=True)
	w.path.joinpath('files').mkdir(exist_ok=True)
	w.path.joinpath('files','attachments').mkdir(exist_ok=True)


	status = profman.get_active_profile()
	
	profile = None
	if not status.error():
		profile = status['profile']
	
	status = profile.set_identity(w)
	assert not status.error(), f"{funcname()}(): failure to set identity workspace"

	return RetVal()
	

def init_admin(conn: serverconn.ServerConnection, config: dict) -> RetVal:
	'''Finishes setting up the admin account by registering it, logging in, and uploading a 
	root keycard entry'''
	
	devpair = EncryptionPair(
		CryptoString(r'CURVE25519:mO?WWA-k2B2O|Z%fA`~s3^$iiN{5R->#jxO@cy6{'),
		CryptoString(r'CURVE25519:2bLf2vMA?GA2?L~tv<PA9XOw6e}V~ObNi7C&qek>'	)
	)
	config['admin_devpair'] = devpair

	status = iscmds.regcode(conn, utils.MAddress('admin/example.com'), config['admin_regcode'], 
		config['admin_password'].hashstring, devpair)
	assert not status.error(), f"init_admin(): regcode failed: {status.info()}"
	devid = utils.UUID(status['devid'])
	config['admin_devid'] = devid

	status = iscmds.login(conn, config['admin_wid'], CryptoString(config['oekey']))
	assert not status.error(), f"init_admin(): login phase failed: {status.info()}"

	status = iscmds.password(conn, config['admin_password'].hashstring)
	assert not status.error(), f"init_admin(): password phase failed: {status.info()}"

	status = iscmds.device(conn, devid, devpair)
	assert not status.error(), "init_admin(): device phase failed: " \
		f"{status.info()}"

	entry = keycard.UserEntry()
	entry.set_fields({
		'Name':'Administrator',
		'Workspace-ID':config['admin_wid'].as_string(),
		'User-ID':'admin',
		'Domain':'example.com',
		'Contact-Request-Verification-Key':config['admin_crspair'].get_public_key(),
		'Contact-Request-Encryption-Key':config['admin_crepair'].get_public_key(),
		'Encryption-Key':config['admin_epair'].get_public_key(),
		'Verification-Key':config['admin_spair'].get_public_key()
	})

	status = iscmds.addentry(conn, entry, CryptoString(config['ovkey']), config['admin_crspair'])
	assert not status.error(), f"init_admin: failed to add entry: {status.info()}"

	status = iscmds.iscurrent(conn, 1, config['admin_wid'])
	assert not status.error(), "init_admin(): admin iscurrent() success check failed: " \
		f"{status.info()}"

	status = iscmds.iscurrent(conn, 2, config['admin_wid'])
	assert not status.error(), "init_admin(): admin iscurrent() failure check failed: " \
		f"{status.info()}"
	
	return RetVal()


def init_user(conn: serverconn.ServerConnection, config: dict) -> RetVal:
	'''Creates a test user for command testing'''
	
	userid = utils.UserID('33333333-3333-3333-3333-333333333333')
	status = iscmds.preregister(conn, userid, utils.UserID('csimons'), utils.Domain('example.com'))
	assert not status.error(), "init_user(): uid preregistration failed"
	assert status['domain'].as_string() == 'example.com' and \
		'wid' in status and \
		'regcode' in status and	\
		status['uid'].as_string() == 'csimons', "init_user(): failed to return expected data"

	regdata = status
	password = Password('MyS3cretPassw*rd')
	devpair = EncryptionPair()
	status = iscmds.regcode(conn, utils.MAddress('csimons/example.com'), regdata['regcode'], 
		password.hashstring, devpair)
	assert not status.error(), "init_user(): uid regcode failed"
	devid = utils.UUID(status['devid'])

	config['user_wid'] = userid
	config['user_uid'] = utils.UserID(regdata['uid'])
	config['user_domain'] = utils.Domain(regdata['domain'])
	config['user_devid'] = devid
	config['user_devpair'] = devpair
	config['user_password'] = password

	return RetVal()
