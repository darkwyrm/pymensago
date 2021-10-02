from glob import glob
import inspect
import os.path
from re import L
import shutil
import sys
import time

import psycopg2
from pycryptostring import CryptoString
from retval import RetVal

# pylint: disable=import-error
import pymensago.auth as auth
from pymensago.client import MensagoClient
from pymensago.config import load_server_config
from pymensago.contact import Name
from pymensago.encryption import Password, EncryptionPair, SigningPair, SecretKey
from pymensago.fmap import FolderMapping
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

admin_profile_data = {
	'name': 'Administrator',
	'uid': utils.UserID('admin'),

	# These fields are set by init_server()
	'wid': utils.UUID(),
	'domain': utils.Domain(),
	'address': utils.MAddress(),
	'waddress': utils.WAddress(),

	'password': Password('Linguini2Pegboard*Album'),
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
	'folder': SecretKey(CryptoString(r'XSALSA20:H)3FOR}+C8(4Jm#$d+fcOXzK=Z7W+ZVX11jI7qh*')),

	'device': EncryptionPair(
		CryptoString(r'CURVE25519:mO?WWA-k2B2O|Z%fA`~s3^$iiN{5R->#jxO@cy6{'),
		CryptoString(r'CURVE25519:2bLf2vMA?GA2?L~tv<PA9XOw6e}V~ObNi7C&qek>'	)),
}

# Test User Information

user1_profile_data = {
	'name': 'Corbin Simons',
	'uid': utils.UserID('csimons'),

	'wid': utils.UUID('4418bf6c-000b-4bb3-8111-316e72030468'),
	'domain': utils.Domain('example.com'),
	'address': utils.MAddress('csimons/example.com'),
	'waddress': utils.WAddress('4418bf6c-000b-4bb3-8111-316e72030468/example.com'),

	'password': Password('MyS3cretPassw*rd'),
	'crencryption': EncryptionPair(
		CryptoString(r'CURVE25519:j(IBzX*F%OZF;g77O8jrVjM1a`Y<6-ehe{S;{gph'),
		CryptoString(r'CURVE25519:55t6A0y%S?{7c47p(R@C*X#at9Y`q5(Rc#YBS;r}')),
	
	'crsigning': SigningPair(
		CryptoString(r'ED25519:d0-oQb;{QxwnO{=!|^62+E=UYk2Y3mr2?XKScF4D'),
		CryptoString(r'ED25519:ip52{ps^jH)t$k-9bc_RzkegpIW?}FFe~BX&<V}9')),
	
	'encryption': EncryptionPair(
		CryptoString(r'CURVE25519:nSRso=K(WF{P+4x5S*5?Da-rseY-^>S8VN#v+)IN'),
		CryptoString(r'CURVE25519:4A!nTPZSVD#tm78d=-?1OIQ43{ipSpE;@il{lYkg')),
	
	'signing': SigningPair(
		CryptoString(r'ED25519:k^GNIJbl3p@N=j8diO-wkNLuLcNF6#JF=@|a}wFE'),
		CryptoString(r'ED25519:;NEoR>t9n3v%RbLJC#*%n4g%oxqzs)&~k+fH4uqi')),
	
	'storage': SecretKey(CryptoString(r'XSALSA20:(bk%y@WBo3&}(UeXeHeHQ|1B}!rqYF20DiDG+9^Q')),
	'folder': SecretKey(CryptoString(r'XSALSA20:-DfH*_9^tVtb(z9j3Lu@_(=ow7q~8pq^<;;f%2_B')),

	'device': EncryptionPair(
		CryptoString(r'CURVE25519:94|@e{Kpsu_Qe{L@_U;QnOHz!eJ5zz?V@>+K)6F}'),
		CryptoString(r'CURVE25519:!x2~_pSSCx1M$n7{QBQ5e*%~ytBzKL_C(bCviqYh')),
}

def funcname() -> str: 
	frames = inspect.getouterframes(inspect.currentframe())
	return frames[1].function

def setup_test():
	'''Empties and resets the server's database to start from a clean slate'''
	
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
	'''Adds basic data to the database as if setupconfig had been run. It also rotates the org 
	keycard so that there are two entries. Returns data needed for tests, such as the keys'''
	
	# Start off by generating the org's root keycard entry and add to the database

	cur = dbconn.cursor()
	card = keycard.Keycard('Organization')
	
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

	# Chain a new entry to the root

	status = card.chain(initial_oskey, False)
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

	admin_profile_data['wid'] = utils.UUID(admin_wid)
	admin_profile_data['domain'] = utils.Domain('example.com')
	admin_profile_data['address'] = utils.MAddress('admin/example.com')
	admin_profile_data['waddress'] = utils.WAddress(admin_wid.as_string() + 'example.com')

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
		'abuse_wid' : utils.UUID(abuse_wid),
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
	'''Creates a new profile folder hierarchy on the client side in the specified test folder'''

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


# Profile_data fields
# Note that the field names are carefully chosen -- for code efficiency they are the exact same
# field names as those used in the database to identify the key types
#
# 'name' - (str) the user's name
# 'uid' - (UserID) user ID of the user
# 'wid' - (UUID) workspace ID of the user
# 'domain' - (Domain) domain of the user
# 'address' - (MAddress) full address of the user -- exists just for convenience
# 'password' - (Password) password object of the user's password
# 'device' - (EncryptionPair) first device encryption pair
# 'crencryption' - (EncryptionPair) contact request encryption pair
# 'crsigning' - (SigningPair) contact request signing pair
# 'encryption' - (EncryptionPair) general encryption pair
# 'signing' - (SigningPair) general signing pair
# 'folder' - (SecretKey) secret key for server-side folder name storage
# 'storage' - (SecretKey) secret key for server-side file storage
def setup_profile(profile_folder: str, config: dict, profile_data: dict) -> RetVal:
	'''Creates the client-side profile for an account. This call does not merely call the 
	corresponding client-level functions so that crypto keys are the same from one test 
	to the next.'''

	config['profile_folder'] = profile_folder

	profman = userprofile.profman
	status = profman.load_profiles(profile_folder)
	assert not status.error(), f"{funcname()}(): Failed to init profile folder {profile_folder}"

	status = profman.get_active_profile()
	assert not status.error(), f"{funcname()}(): Failed to get default profile"
	profile = status['profile']

	# The profile folder is assumed to be empty for the purposes of these tests. 'primary' is
	# assigned to the admin. Test users are assigned 'user1' and 'user2' for clarity.
	
	
	# In order to have consistent keys for debugging and testing purposes, we are going to more
	# or less reimplement Workspace.generate() here.'
	w = Workspace(profile.db, profile_folder)

	w.uid = profile_data['uid']
	w.wid = profile_data['wid']
	w.domain = profile_data['domain']
	w.pw = profile_data['password']

	address = w.wid.as_string() + '/' + w.domain.as_string()

	for key in [ 'crencryption', 'crsigning', 'encryption', 'signing', 'folder', 'storage' ]:
		status = auth.add_key(profile.db, profile_data[key], address, key)
		assert not status.error(), f"{funcname()}(): Failed to add {key} key to db"
	
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
		foldermap.Set(address, profile_data['folder'].pubhash, folder, 'root')
		w.add_folder(foldermap)

	# Create the folders themselves

	w.path.mkdir(parents=True, exist_ok=True)
	w.path.joinpath(profile.name, 'files').mkdir(exist_ok=True)
	w.path.joinpath(profile.name, 'files','attachments').mkdir(exist_ok=True)

	status = profman.get_active_profile()
	
	profile = None
	if not status.error():
		profile = status['profile']
	
	status = profile.set_identity(w)
	assert not status.error(), f"{funcname()}(): failure to set identity workspace"

	return RetVal()


def regcode_user(conn: serverconn.ServerConnection, config: dict, profile_data: dict, 
	regcode: str) -> RetVal:
	'''Finishes setting up the admin account by registering it, logging in, and uploading a 
	root keycard entry'''
	
	status = userprofile.profman.get_active_profile()
	profile = None
	if not status.error():
		profile = status['profile']
	
	status = iscmds.regcode(conn, profile_data['address'], regcode, 
		profile_data['password'].hashstring, profile.devid, profile_data['device'])
	assert not status.error(), f"{funcname()}: regcode failed: {status.info()}"

	waddr = utils.WAddress()
	waddr.id = profile_data['wid']
	waddr.domain = profile_data['domain']
	auth.add_device_session(profile.db, waddr, profile.devid, profile_data['device'])

	status = iscmds.login(conn, profile_data['wid'], CryptoString(config['oekey']))
	assert not status.error(), f"{funcname()}: login phase failed: {status.info()}"

	status = iscmds.password(conn, profile_data['password'].hashstring)
	assert not status.error(), f"{funcname()}: password phase failed: {status.info()}"

	status = iscmds.device(conn, profile.devid, profile_data['device'])
	assert not status.error(), f"{funcname()}: device phase failed: {status.info()}"

	entry = keycard.UserEntry()
	entry.set_fields({
		'Name':profile_data['name'],
		'Workspace-ID':profile_data['wid'].as_string(),
		'User-ID':profile_data['uid'].as_string(),
		'Domain':profile_data['domain'].as_string(),
		'Contact-Request-Verification-Key':profile_data['crsigning'].get_public_key(),
		'Contact-Request-Encryption-Key':profile_data['crencryption'].get_public_key(),
		'Encryption-Key':profile_data['encryption'].get_public_key(),
		'Verification-Key':profile_data['signing'].get_public_key()
	})

	status = iscmds.addentry(conn, entry, CryptoString(config['ovkey']), profile_data['crsigning'])
	assert not status.error(), f"{funcname()}: failed to add entry: {status.info()}"

	status = iscmds.iscurrent(conn, 1, profile_data['wid'])
	assert not status.error(), f"{funcname()}: user iscurrent() success check failed: " \
		f"{status.info()}"

	status = iscmds.iscurrent(conn, 2, profile_data['wid'])
	assert not status.error(), f"{funcname()}: user iscurrent() failure check failed: " \
		f"{status.info()}"
	
	return RetVal()


def setup_two_profiles(test_name: str)->RetVal:
	'''This test setup function fully sets up two profiles, 'primary' for the administrator and 
	'user1' for test user Corbin Simons. After the call, the profile is set to the admin, but
	no login session is created.
	Returns:
		'dbconn': connection object to the server's PostgreSQL database
		'dbdata': setupconfig configuration data returned from init_server()
		'test_folder': path to the test folder
		'client': Mensago client instance
	'''

	dbconn = setup_test()
	dbdata = init_server(dbconn)
	test_folder = setup_profile_base(test_name)
	status = setup_profile(test_folder, dbdata, admin_profile_data)

	conn = serverconn.ServerConnection()
	status = conn.connect('localhost', 2001)
	assert not status.error(), f"test_set_workstatus(): failed to connect to server: {status.info()}"

	status = regcode_user(conn, dbdata, admin_profile_data, dbdata['admin_regcode'])
	assert not status.error(), f"test_set_workstatus(): regcode_user failed: {status.info()}"

	# Preregister the regular user
	regdata = iscmds.preregister(conn, user1_profile_data['wid'], user1_profile_data['uid'],
				user1_profile_data['domain'])
	assert not regdata.error(), f"{funcname()}: uid preregistration failed"
	assert regdata['domain'].as_string() == 'example.com' and 'wid' in regdata \
		and 'regcode' in regdata and regdata['uid'].as_string() == 'csimons', \
		f"{funcname()}: user prereg failed to return expected data"
	conn.disconnect()

	# Log in as the user and set up the profile
	client = MensagoClient(test_folder)
	status = client.pman.create_profile('user1')
	assert not status.error(), f"{funcname()}: client failed to create test user profile"
	status = client.pman.activate_profile('user1')
	assert not status.error(), f"{funcname()}: client failed to switch to test user profile"

	status = client.connect(utils.Domain('example.com'))
	assert not status.error(), f"{funcname()}: client failed to connect to server"
	status = client.redeem_regcode(user1_profile_data['address'], regdata['regcode'], 'Some*1Pass',
								Name('Corbin', 'Simons'))
	assert not status.error(), f"{funcname()}: client failed to regcode test user"
	client.logout()

	# Log out as the user and switch to the admin
	status = client.pman.activate_profile('primary')
	assert not status.error(), f"{funcname()}: client failed to switch to back to admin profile"

	return RetVal().set_values({
		'dbconn': dbconn,
		'dbdata': dbdata,
		'test_folder': test_folder,
		'client': client
	})
