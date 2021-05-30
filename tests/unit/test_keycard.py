'''This module tests the KeyCard class'''
import base64
import datetime
import os
import shutil
import time

import nacl.signing
from pycryptostring import CryptoString

# pylint: disable=import-error
import pymensago.keycard as keycard
from pymensago.keycard import Base85Encoder, SIGINFO_HASH, SIGINFO_SIGNATURE

# Keys used in the various tests
# THESE KEYS ARE STORED ON GITHUB! DO NOT USE THESE FOR ANYTHING EXCEPT UNIT TESTS!!

# User Signing Key: p;XXU0XF#UO^}vKbC-wS(#5W6=OEIFmR2z`rS1j+
# User Verification Key: 6|HBWrxMY6-?r&Sm)_^PLPerpqOj#b&x#N_#C3}p

# User Contact Request Signing Key: ip52{ps^jH)t$k-9bc_RzkegpIW?}FFe~BX&<V}9
# User Contact Request Verification Key: d0-oQb;{QxwnO{=!|^62+E=UYk2Y3mr2?XKScF4D

# User Contact Request Encryption Key: j(IBzX*F%OZF;g77O8jrVjM1a`Y<6-ehe{S;{gph
# User Contact Request Decryption Key: 55t6A0y%S?{7c47p(R@C*X#at9Y`q5(Rc#YBS;r}

# User Primary Encryption Key: nSRso=K(WF{P+4x5S*5?Da-rseY-^>S8VN#v+)IN
# User Primary Decryption Key: 4A!nTPZSVD#tm78d=-?1OIQ43{ipSpE;@il{lYkg

# Organization Primary Signing Key: msvXw(nII<Qm6oBHc+92xwRI3>VFF-RcZ=7DEu3|
# Organization Primary Verification Key: )8id(gE02^S<{3H>9B;X4{DuYcb`%wo^mC&1lN88

# Organization Encryption Key: @b?cjpeY;<&y+LSOA&yUQ&ZIrp(JGt{W$*V>ATLG
# Organization Decryption Key: nQxAR1Rh{F4gKR<KZz)*)7}5s_^!`!eb!sod0<aT


def setup_test(name: str) -> str:
	'''Creates a test folder hierarchy'''
	test_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)),'testfiles')
	if not os.path.exists(test_folder):
		os.mkdir(test_folder)

	test_folder = os.path.join(test_folder, name)
	while os.path.exists(test_folder):
		try:
			shutil.rmtree(test_folder)
		except:
			print("Waiting a second for test folder to unlock")
			time.sleep(1.0)
	os.mkdir(test_folder)
	return test_folder


def make_test_userentry() -> keycard.UserEntry:
	'''Generates a user entry for testing purposes'''

	# User signing key
	skey = nacl.signing.SigningKey(b'p;XXU0XF#UO^}vKbC-wS(#5W6=OEIFmR2z`rS1j+', Base85Encoder)

	# Organization signing key
	oskey = nacl.signing.SigningKey(b'msvXw(nII<Qm6oBHc+92xwRI3>VFF-RcZ=7DEu3|', Base85Encoder)

	# crskey = nacl.signing.SigningKey(b'ip52{ps^jH)t$k-9bc_RzkegpIW?}FFe~BX&<V}9', Base85Encoder)
	# crekey = nacl.public.PrivateKey(b'VyFX5PC~?eL5)>q|6W7ciRrOJw$etlej<tY$f+t_', Base85Encoder)
	# ekey = nacl.public.PrivateKey(b'Wsx6BC(HP~goS-C_`K=6Daqr97kapfc=vQUzi?KI', Base85Encoder)

	usercard = keycard.UserEntry()
	usercard.set_fields({
		'Name':'Corbin Simons',
		'Workspace-ID':'4418bf6c-000b-4bb3-8111-316e72030468',
		'User-ID':'csimons',
		'Domain':'example.com',
		'Contact-Request-Verification-Key':'ED25519:d0-oQb;{QxwnO{=!|^62+E=UYk2Y3mr2?XKScF4D',
		'Contact-Request-Encryption-Key':'CURVE25519:yBZ0{1fE9{2<b~#i^R+JT-yh-y5M(Wyw_)}_SZOn',
		'Public-Encryption-Key':'CURVE25519:_`UC|vltn_%P5}~vwV^)oY){#uvQSSy(dOD_l(yE'
	})

	# Organization sign and verify

	okeystring = CryptoString()
	okeystring.set('ED25519:' + base64.b85encode(oskey.encode()).decode())
	rv = usercard.sign(okeystring, 'Organization')
	assert not rv.error(), 'Unexpected RetVal error %s' % rv.error()
	assert usercard.signatures['Organization'], 'entry failed to user sign'

	ovkey = nacl.signing.VerifyKey(oskey.verify_key.encode())
	ovkeystring = CryptoString()
	ovkeystring.prefix = 'ED25519'
	ovkeystring.data = base64.b85encode(ovkey.encode()).decode()

	rv = usercard.verify_signature(ovkeystring, 'Organization')
	assert not rv.error(), 'entry failed to org verify'

	# Add the hash

	rv = usercard.generate_hash('BLAKE2B-256')
	assert not rv.error(), 'entry failed to hash'

	# User sign and verify

	keystring = CryptoString()
	keystring.set('ED25519:' + base64.b85encode(skey.encode()).decode())
	rv = usercard.sign(keystring, 'User')
	assert not rv.error(), 'Unexpected RetVal error %s / %s' % (rv.error(), rv.info())
	assert usercard.signatures['User'], 'entry failed to user sign'
	
	vkey = nacl.signing.VerifyKey(skey.verify_key.encode())
	vkeystring = CryptoString()
	vkeystring.prefix = 'ED25519'
	vkeystring.data = base64.b85encode(vkey.encode()).decode()

	rv = usercard.verify_signature(vkeystring, 'User')
	assert not rv.error(), 'entry failed to user verify'

	status = usercard.is_compliant()
	assert not status.error(), f"UserEntry wasn't compliant: {str(status)}"
	
	return usercard


def make_test_orgentry() -> keycard.OrgEntry:
	'''Generates an organizational entry for testing purposes'''

	# Primary signing key
	pskey = nacl.signing.SigningKey(b'msvXw(nII<Qm6oBHc+92xwRI3>VFF-RcZ=7DEu3|', Base85Encoder)
	
	orgcard = keycard.OrgEntry()
	orgcard.set_fields({
		'Name':'Acme Widgets, Inc.',
		'Contact-Admin':'c590b44c-798d-4055-8d72-725a7942f3f6/acme.com',
		'Language':'en',
		'Domain':'acme.com',
		'Primary-Verification-Key':'ED25519:)8id(gE02^S<{3H>9B;X4{DuYcb`%wo^mC&1lN88',
		'Encryption-Key':'CURVE25519:@b?cjpeY;<&y+LSOA&yUQ&ZIrp(JGt{W$*V>ATLG'
	})

	# Organization sign, hash, and verify

	rv = orgcard.generate_hash('BLAKE2B-256')
	assert not rv.error(), 'entry failed to hash'

	pskeystring = CryptoString()
	pskeystring.set('ED25519:' + base64.b85encode(pskey.encode()).decode())
	rv = orgcard.sign(pskeystring, 'Organization')
	assert not rv.error(), 'Unexpected RetVal error %s' % rv.error()
	assert orgcard.signatures['Organization'], 'entry failed to user sign'

	ovkey = nacl.signing.VerifyKey(pskey.verify_key.encode())
	ovkeystring = CryptoString()
	ovkeystring.prefix = 'ED25519'
	ovkeystring.data = base64.b85encode(ovkey.encode()).decode()

	rv = orgcard.verify_signature(ovkeystring, 'Organization')
	assert not rv.error(), 'org entry failed to verify'

	status = orgcard.is_compliant()
	assert not status.error(), f"OrgEntry wasn't compliant: {str(status)}"

	return orgcard


def test_set_field():
	'''Tests setfield'''
	card = keycard.EntryBase()
	card.set_field('Name','Corbin Smith')
	assert card.fields['Name'] == 'Corbin Smith', "set_field() didn't work"


def test_set_fields():
	'''Tests setfields'''
	card = keycard.EntryBase()
	card.set_fields({
		'Name':'Example, Inc.',
		'Contact-Admin':'admin/example.com',
		'noncompliant-field':'foobar2000'
	})

	assert 'Name' in card.fields and 'Contact-Admin' in card.fields and \
			'noncompliant-field' in card.fields, "set_fields() didn't work right"


def test_set():
	'''Tests set()'''

	# Note that the Type field is not set so that set() doesn't reject the data because it doesn't
	# match the entry type
	indata = \
		b'Name:Acme, Inc.\r\n' \
		b'Contact-Admin:admin/acme.com\r\n' \
		b'Language:en\r\n' \
		b'Primary-Verification-Key:ED25519:&JEq)5Ktu@jfM+Sa@+1GU6E&Ct2*<2ZYXh#l0FxP\r\n' \
		b'Encryption-Key:CURVE25519:^fI7bdC(IEwC#(nG8Em-;nx98TcH<TnfvajjjDV@\r\n' \
		b'Time-To-Live:14\r\n' \
		b'Expires:730\r\n' \
		b'Organization-Signature:x3)dYq@S0rd1Rfbie*J7kF{fkxQ=J=A)OoO1WGx97o-utWtfbwyn-$(js'\
			b'_n^d6uTZY7p{gd60=rPZ|;m\r\n'

	basecard = keycard.EntryBase()
	status = basecard.set(indata)
	assert not status.error(), "EntryBase.set() failed"
	assert basecard.signatures['Organization'] == 'x3)dYq@S0rd1Rfbie*J7kF{fkxQ=J=A)OoO1WGx' \
			'97o-utWtfbwyn-$(js_n^d6uTZY7p{gd60=rPZ|;m', \
			"set() didn't handle the signature correctly"


def test_make_bytestring():
	'''Tests make_bytestring()'''

	basecard = keycard.EntryBase()
	basecard.type = "Test"
	basecard.field_names = [ 'Name', 'User-ID', 'Workspace-ID', 'Domain', 'Time-To-Live', 'Expires']
	basecard.signature_info = [
		{ 'name' : 'Custody', 'level' : 1, 'optional' : True, 'type' : SIGINFO_SIGNATURE },
		{ 'name' : 'Organization', 'level' : 2, 'optional' : False, 'type' : SIGINFO_SIGNATURE },
		{ 'name' : 'Hashes', 'level' : 3, 'optional' : False, 'type' : SIGINFO_HASH },
		{ 'name' : 'User', 'level' : 4, 'optional' : False, 'type' : SIGINFO_SIGNATURE }
	]

	basecard.set_fields({
		'Name':'Corbin Smith',
		'User-ID':'csmith',
		'Workspace-ID':'4418bf6c-000b-4bb3-8111-316e72030468',
		'Domain':'example.com',
		'Time-To-Live':'7',
		'Expires':'20201002',
		'Custody-Signature':'0000000000',
		'Organization-Signature':'2222222222',
		'User-Signature':'1111111111',
	})

	expected_out = \
		b'Type:Test\r\n' \
		b'Name:Corbin Smith\r\n' \
		b'User-ID:csmith\r\n' \
		b'Workspace-ID:4418bf6c-000b-4bb3-8111-316e72030468\r\n' \
		b'Domain:example.com\r\n' \
		b'Time-To-Live:7\r\n' \
		b'Expires:20201002\r\n' \
		b'Custody-Signature:0000000000\r\n' \
		b'Organization-Signature:2222222222\r\n' \
		b'User-Signature:1111111111\r\n' \
	
	actual_out = basecard.make_bytestring(-1)
	assert actual_out == expected_out, "user byte string didn't match"



def test_set_expiration():
	'''Tests set_expiration()'''
	card = keycard.EntryBase()
	card.set_expiration(7)
	expiration = datetime.datetime.utcnow() + datetime.timedelta(7)
	assert card.fields['Expires'] == expiration.strftime("%Y%m%d"), "Expiration calculations failed"


def test_sign():
	'''Tests signing of a keycard entry'''
	skey = nacl.signing.SigningKey(b'p;XXU0XF#UO^}vKbC-wS(#5W6=OEIFmR2z`rS1j+', Base85Encoder)
	# crskey = nacl.signing.SigningKey(b'msvXw(nII<Qm6oBHc+92xwRI3>VFF-RcZ=7DEu3|', Base85Encoder)
	# crekey = nacl.public.PrivateKey(b'VyFX5PC~?eL5)>q|6W7ciRrOJw$etlej<tY$f+t_', Base85Encoder)
	# ekey = nacl.public.PrivateKey(b'Wsx6BC(HP~goS-C_`K=6Daqr97kapfc=vQUzi?KI', Base85Encoder)

	basecard = keycard.EntryBase()
	basecard.type = "Test"
	basecard.field_names = [ 'Name', 'Workspace-ID', 'Domain', 'Contact-Request-Verification-Key',
			'Contact-Request-Encryption-Key', 'Public-Encryption-Key', 'Expires']
	basecard.set_fields({
		'Name':'Corbin Simons',
		'Workspace-ID':'4418bf6c-000b-4bb3-8111-316e72030468',
		'Domain':'example.com',
		'Contact-Request-Verification-Key':'ED25519:7dfD==!Jmt4cDtQDBxYa7(dV|N$}8mYwe$=RZuW|',
		'Contact-Request-Encryption-Key':'CURVE25519:yBZ0{1fE9{2<b~#i^R+JT-yh-y5M(Wyw_)}_SZOn',
		'Public-Encryption-Key':'CURVE25519:_`UC|vltn_%P5}~vwV^)oY){#uvQSSy(dOD_l(yE',
		'Expires':'20201002',

		# These junk signatures will end up being cleared when sign('User') is called
		'User-Signature':'1111111111',
		'Organization-Signature':'2222222222',
		'Entry-Signature':'3333333333'
	})
	basecard.signature_info = [
		{ 'name' : 'Custody', 'level' : 1, 'optional' : True, 'type' : SIGINFO_SIGNATURE },
		{ 'name' : 'Organization', 'level' : 2, 'optional' : False, 'type' : SIGINFO_SIGNATURE },
		{ 'name' : 'Hashes', 'level' : 3, 'optional' : False, 'type' : SIGINFO_HASH },
		{ 'name' : 'User', 'level' : 4, 'optional' : False, 'type' : SIGINFO_SIGNATURE }
	]

	keystring = CryptoString()
	keystring.set('ED25519:' + base64.b85encode(skey.encode()).decode())
	rv = basecard.sign(keystring, 'Organization')
	assert not rv.error(), 'Unexpected RetVal error %s' % rv.error()
	assert basecard.signatures['Organization'], 'entry failed to org sign'

	rv = basecard.generate_hash('BLAKE2B-256')
	assert not rv.error(), 'Unexpected RetVal error %s' % rv.error()
	
	expected_sig = \
		'ED25519:N~nZ1#wE%i`sO?wZ%b4;zrEk4D-rd{!oY=C26w0GepfvnArTHlw*HeIZB|oHZke`T*eGbw>GvYD8YQR)'
	assert basecard.signatures['Organization'] == expected_sig, \
			"entry did not yield the expected signature"


def test_verify_signature():
	'''Tests the signing of a test keycard entry'''
	# This is an extensive test because while it doesn't utilize all the fields that a standard
	# entry would normally have, it tests signing and verification of user, org, and entry
	# signatures. This test is also only intended to confirm success states of the method.

	# User signing key
	skey = nacl.signing.SigningKey(b'p;XXU0XF#UO^}vKbC-wS(#5W6=OEIFmR2z`rS1j+', Base85Encoder)

	# Organization signing key
	oskey = nacl.signing.SigningKey(b'msvXw(nII<Qm6oBHc+92xwRI3>VFF-RcZ=7DEu3|', Base85Encoder)

	# crekey = nacl.public.PrivateKey(b'VyFX5PC~?eL5)>q|6W7ciRrOJw$etlej<tY$f+t_', Base85Encoder)
	# ekey = nacl.public.PrivateKey(b'Wsx6BC(HP~goS-C_`K=6Daqr97kapfc=vQUzi?KI', Base85Encoder)

	basecard = keycard.EntryBase()
	basecard.type = "Test"
	basecard.field_names = [ 'Name', 'Workspace-ID', 'Domain', 'Contact-Request-Verification-Key',
			'Contact-Request-Encryption-Key', 'Public-Encryption-Key', 'Expires']
	basecard.set_fields({
		'Name':'Corbin Simons',
		'Workspace-ID':'4418bf6c-000b-4bb3-8111-316e72030468',
		'Domain':'example.com',
		'Contact-Request-Verification-Key':'ED25519:d0-oQb;{QxwnO{=!|^62+E=UYk2Y3mr2?XKScF4D',
		'Contact-Request-Encryption-Key':'CURVE25519:yBZ0{1fE9{2<b~#i^R+JT-yh-y5M(Wyw_)}_SZOn',
		'Public-Encryption-Key':'CURVE25519:_`UC|vltn_%P5}~vwV^)oY){#uvQSSy(dOD_l(yE',
		'Expires':'20201002',

		# These junk signatures will end up being cleared when sign('User') is called
		'User-Signature':'1111111111',
		'Organization-Signature':'2222222222',
		'Entry-Signature':'3333333333'
	})
	basecard.signature_info = [
		{ 'name' : 'Custody', 'level' : 1, 'optional' : True, 'type' : SIGINFO_SIGNATURE },
		{ 'name' : 'Organization', 'level' : 2, 'optional' : False, 'type' : SIGINFO_SIGNATURE },
		{ 'name' : 'Hashes', 'level' : 3, 'optional' : False, 'type' : SIGINFO_HASH },
		{ 'name' : 'User', 'level' : 4, 'optional' : False, 'type' : SIGINFO_SIGNATURE }
	]

	# Organization sign and verify

	okeystring = CryptoString()
	okeystring.set('ED25519:' + base64.b85encode(oskey.encode()).decode())
	rv = basecard.sign(okeystring, 'Organization')
	assert not rv.error(), 'Unexpected RetVal error %s' % rv.error()
	assert basecard.signatures['Organization'], 'entry failed to user sign'

	expected_sig = \
		'ED25519:>>6(c|MBt?66%ywF=2yw4k}%;-8J)218?T=4XtV**m9S4Wzo@%E0Xme7@op7Vky?>VnCb?h(%WGO9(g!'
	assert basecard.signatures['Organization'] == expected_sig, \
			"entry did not yield the expected org signature"
	

	ovkey = nacl.signing.VerifyKey(oskey.verify_key.encode())
	ovkeystring = CryptoString()
	ovkeystring.prefix = 'ED25519'
	ovkeystring.data = base64.b85encode(ovkey.encode()).decode()

	rv = basecard.verify_signature(ovkeystring, 'Organization')
	assert not rv.error(), 'entry failed to org verify'

	# Set up the hashes
	basecard.prev_hash = '1234567890'
	rv = basecard.generate_hash('BLAKE2B-256')
	assert not rv.error(), 'entry failed to BLAKE3 hash'

	expected_hash = r'BLAKE2B-256:kBO4*3!t3M2PONHy>*Ew)Hw8!v)rZcvpo;azDJvx'
	assert basecard.hash == expected_hash, "entry did not yield the expected hash"
	
	# User sign and verify

	keystring = CryptoString()
	keystring.set('ED25519:' + base64.b85encode(skey.encode()).decode())
	rv = basecard.sign(keystring, 'User')
	assert not rv.error(), 'Unexpected RetVal error %s' % rv.error()
	assert basecard.signatures['User'], 'entry failed to user sign'
	
	expected_sig = \
		'ED25519:@R53O{bS93YmZq5qs2`f0Uj)Ks^_cl{3Tl;lce#{hF-LsexWsbWqH_5erOQ+VY^pBkADo)@zxG)YZVU#'
	assert basecard.signatures['User'] == expected_sig, \
			"entry did not yield the expected user signature"

	vkey = nacl.signing.VerifyKey(skey.verify_key.encode())
	vkeystring = CryptoString()
	vkeystring.prefix = 'ED25519'
	vkeystring.data = base64.b85encode(vkey.encode()).decode()

	rv = basecard.verify_signature(vkeystring, 'User')
	assert not rv.error(), 'entry failed to user verify'


def test_base_is_compliant():
	'''Tests compliance testing for the base class'''
	basecard = keycard.EntryBase()
	status = basecard.is_compliant()
	assert status.error(), "EntryBase met compliance and shouldn't"


def test_is_data_compliant_user():
	'''Tests data compliance checking for org entries'''
	entry = make_test_userentry()

	entry.set_fields({
		"Name":								"Corbin Simons",
		"Workspace-ID":						"4418bf6c-000b-4bb3-8111-316e72030468",
		"Domain":							"example.com",
		"Contact-Request-Verification-Key":	"ED25519:d0-oQb;{QxwnO{=!|^62+E=UYk2Y3mr2?XKScF4D",
		"Contact-Request-Encryption-Key":	"CURVE25519:j(IBzX*F%OZF;g77O8jrVjM1a`Y<6-ehe{S;{gph",
		"Public-Encryption-Key":			"CURVE25519:nSRso=K(WF{P+4x5S*5?Da-rseY-^>S8VN#v+)IN",
		"Time-To-Live":						"30",
		"Expires":							"20201002",
		"Timestamp":						"20200901T121212Z"
	})

	assert not entry.is_data_compliant().error(), \
		"is_data_compliant_user: failed to pass a compliant entry."

	entry.set_field('Index', '-1')
	assert entry.is_data_compliant().error(), \
		'is_data_compliant_user: passed an entry with a bad index'
	entry.set_field('Index', '1')

	entry.set_field('Name', '')
	assert entry.is_data_compliant().error(), \
		'is_data_compliant_user: passed an entry with an empty name'
	entry.set_field('Name', '\t \t')
	assert entry.is_data_compliant().error(), \
		'is_data_compliant_user: passed an entry with a whitespace name'
	entry.set_field('Name', 'Corbin Simons')

	entry.set_field('Workspace-ID', '4418bf6c-000b-4bb3-8111-316e72030468/example.com')
	assert entry.is_data_compliant().error(), \
		'is_data_compliant_user: passed an entry with a workspace address for a workspace ID'
	entry.set_field('Workspace-ID', '4418bf6c-000b-4bb3-8111-316e72030468')

	entry.set_field('Domain', '')
	assert entry.is_data_compliant().error(), \
		'is_data_compliant_user: passed an entry with an empty domain'
	entry.set_field('Domain', '\t \t')
	assert entry.is_data_compliant().error(), \
		'is_data_compliant_user: passed an entry with a whitespace domain'
	entry.set_field('Domain', 'example.com')

	for keyfield in ['Contact-Request-Verification-Key',
						'Contact-Request-Encryption-Key',
						'Public-Encryption-Key',
						'Alternate-Encryption-Key']:
		entry.set_field(keyfield, 'd0-oQb;{QxwnO{=!|^62+E=UYk2Y3mr2?XKScF4D')
		assert entry.is_data_compliant().error(), \
			f"is_data_compliant_user: passed an entry with bad field {keyfield}"
		entry.set_field(keyfield, 'ED25519:123456789:123456789')
		assert entry.is_data_compliant().error(), \
			f"is_data_compliant_user: passed an entry with bad field {keyfield}"
		entry.set_field(keyfield, 'ED25519:)8id(gE02^S<{3H>9B;X4{DuYcb`%wo^mC&1lN88')

	entry.set_field('Time-To-Live', '0')
	assert entry.is_data_compliant().error(), \
		'is_data_compliant_user: passed an entry with a bad time to live'
	entry.set_field('Time-To-Live', '60')
	assert entry.is_data_compliant().error(), \
		'is_data_compliant_user: passed an entry with a bad time to live'
	entry.set_field('Time-To-Live', "sdf'pomwerASDFOAQEtmlde123,l.")
	assert entry.is_data_compliant().error(), \
		'is_data_compliant_user: passed an entry with a bad time to live'
	entry.set_field('Time-To-Live', '7')

	tempstr = entry.fields['Expires']
	entry.set_field('Expires', '12345678')
	assert entry.is_data_compliant().error(), \
		'is_data_compliant_user: passed an entry with a bad expiration date'
	entry.set_field('Expires', '99999999')
	assert entry.is_data_compliant().error(), \
		'is_data_compliant_user: passed an entry with a bad expiration date'
	entry.fields['Expires'] = tempstr

	entry.set_field('Timestamp', '12345678 121212')
	assert entry.is_data_compliant().error(), \
		'is_data_compliant_user: passed an entry with a bad timestamp'
	entry.set_field('Timestamp', '12345678T121212Z')
	assert entry.is_data_compliant().error(), \
		'is_data_compliant_user: passed an entry with a bad timestamp'
	entry.set_field('Timestamp', '20200901T131313Z')

	entry.set_field('User-ID', 'Corbin Simons')
	assert entry.is_data_compliant().error(), \
		'is_data_compliant_user: passed an entry with a user ID containing whitespace'
	entry.set_field('User-ID', 'TEST\\csimons')
	assert entry.is_data_compliant().error(), \
		'is_data_compliant_user: passed an entry with a user ID containing illegal characters'
	entry.set_field('User-ID', 'csimons_is-teh.bestest:PERSON>>>>EVARRRR<<<<<LOL😁')
	assert not entry.is_data_compliant().error(), \
		'is_data_compliant_user: failed an entry with a valid user ID'


def test_is_compliant_user():
	'''Tests compliance testing for the UserEntry class'''

	# The original code for this test made a great setup for other UserEntry-based tests
	make_test_userentry()


def test_is_data_compliant_org():
	'''Tests data compliance checking for org entries'''
	entry = make_test_orgentry()

	entry.set_fields({
		"Name":						"Acme, Inc.",
		"Contact-Admin":			"54025843-bacc-40cc-a0e4-df48a099c2f3/acme.com",
		"Language":					"en",
		"Primary-Verification-Key":	"ED25519:)8id(gE02^S<{3H>9B;X4{DuYcb`%wo^mC&1lN88",
		"Encryption-Key":			"CURVE25519:@b?cjpeY;<&y+LSOA&yUQ&ZIrp(JGt{W$*V>ATLG",
		"Time-To-Live":				"14",
		"Expires":					"20201002",
		"Timestamp":				"20200901T131313Z"
	})

	assert not entry.is_data_compliant().error(), \
		"is_data_compliant_org: failed to pass a compliant entry."
	
	# Now to test failures of each field. The extent of this testing wouldn't normally be
	# necessary, but this function validates data from outside. We *have* to be extra sure that
	# this data is good... especially when it will be permanently added to the database if it is
	# accepted.

	entry.set_field('Index', '-1')
	assert entry.is_data_compliant().error(), \
		'is_data_compliant_org: passed an entry with a bad index'
	entry.set_field('Index', '1')

	entry.set_field('Name', '')
	assert entry.is_data_compliant().error(), \
		'is_data_compliant_org: passed an entry with an empty name'
	entry.set_field('Name', '\t \t')
	assert entry.is_data_compliant().error(), \
		'is_data_compliant_org: passed an entry with a whitespace name'
	entry.set_field('Name', 'Acme, Inc.')

	entry.set_field('Contact-Admin', 'admin/example.com')
	assert entry.is_data_compliant().error(), \
		'is_data_compliant_org: passed an entry with an Mensago address for Contact-Admin'
	entry.set_field('Contact-Admin', '54025843-bacc-40cc-a0e4-df48a099c2f3/example.com')

	entry.set_field('Contact-Abuse', 'abuse/example.com')
	assert entry.is_data_compliant().error(), \
		'is_data_compliant_org: passed an entry with an Mensago address for Contact-abuse'
	entry.set_field('Contact-Abuse', '54025843-bacc-40cc-a0e4-df48a099c2f3/example.com')

	entry.set_field('Contact-Support', 'support/example.com')
	assert entry.is_data_compliant().error(), \
		'is_data_compliant_org: passed an entry with an Mensago address for Contact-Support'
	entry.set_field('Contact-Support', '54025843-bacc-40cc-a0e4-df48a099c2f3/example.com')

	entry.set_field('Language', 'en-us')
	assert entry.is_data_compliant().error(), \
		'is_data_compliant_org: passed an entry with a bad language list'
	entry.set_field('Language', 'de,es,FR')
	assert not entry.is_data_compliant().error(), \
		'is_data_compliant_org: failed an entry with an compliant language list'

	entry.set_field('Primary-Verification-Key', 'd0-oQb;{QxwnO{=!|^62+E=UYk2Y3mr2?XKScF4D')
	assert entry.is_data_compliant().error(), \
		'is_data_compliant_org: passed an entry with a bad primary verification key'
	entry.set_field('Primary-Verification-Key', 'ED25519:123456789:123456789')
	assert entry.is_data_compliant().error(), \
		'is_data_compliant_org: passed an entry with a bad primary verification key'
	entry.set_field('Primary-Verification-Key', 'ED25519:)8id(gE02^S<{3H>9B;X4{DuYcb`%wo^mC&1lN88')

	entry.set_field('Secondary-Verification-Key', 'd0-oQb;{QxwnO{=!|^62+E=UYk2Y3mr2?XKScF4D')
	assert entry.is_data_compliant().error(), \
		'is_data_compliant_org: passed an entry with a bad secondary verification key'
	entry.set_field('Secondary-Verification-Key', 'ED25519:123456789:123456789')
	assert entry.is_data_compliant().error(), \
		'is_data_compliant_org: passed an entry with a bad secondary verification key'
	entry.set_field('Secondary-Verification-Key', 'ED25519:)8id(gE02^S<{3H>9B;X4{DuYcb`%wo^mC&1lN88')

	entry.set_field('Encryption-Key', 'd0-oQb;{QxwnO{=!|^62+E=UYk2Y3mr2?XKScF4D')
	assert entry.is_data_compliant().error(), \
		'is_data_compliant_org: passed an entry with a bad encryption key'
	entry.set_field('Encryption-Key', 'ED25519:123456789:123456789')
	assert entry.is_data_compliant().error(), \
		'is_data_compliant_org: passed an entry with a bad encryption key'
	entry.set_field('Encryption-Key', 'ED25519:)8id(gE02^S<{3H>9B;X4{DuYcb`%wo^mC&1lN88')

	entry.set_field('Time-To-Live', '0')
	assert entry.is_data_compliant().error(), \
		'is_data_compliant_org: passed an entry with a bad time to live'
	entry.set_field('Time-To-Live', '60')
	assert entry.is_data_compliant().error(), \
		'is_data_compliant_org: passed an entry with a bad time to live'
	entry.set_field('Time-To-Live', "sdf'pomwerASDFOAQEtmlde123,l.")
	assert entry.is_data_compliant().error(), \
		'is_data_compliant_org: passed an entry with a bad time to live'
	entry.set_field('Time-To-Live', '7')

	tempstr = entry.fields['Expires']
	entry.set_field('Expires', '12345678')
	assert entry.is_data_compliant().error(), \
		'is_data_compliant_org: passed an entry with a bad expiration date'
	entry.set_field('Expires', '99999999')
	assert entry.is_data_compliant().error(), \
		'is_data_compliant_org: passed an entry with a bad expiration date'
	entry.fields['Expires'] = tempstr

	entry.set_field('Timestamp', '12345678 121212')
	assert entry.is_data_compliant().error(), \
		'is_data_compliant_org: passed an entry with a bad timestamp'
	entry.set_field('Timestamp', '12345678T121212Z')
	assert entry.is_data_compliant().error(), \
		'is_data_compliant_org: passed an entry with a bad timestamp'
	entry.set_field('Timestamp', '20200901T131313Z')


def test_is_compliant_org():
	'''Tests compliance testing for the OrgEntry class'''

	# Organization signing key
	oskey = nacl.signing.SigningKey(b'msvXw(nII<Qm6oBHc+92xwRI3>VFF-RcZ=7DEu3|', Base85Encoder)

	orgcard = keycard.OrgEntry()
	orgcard.set_fields({
		'Name':'Acme Widgets, Inc',
		'Contact-Admin':'54025843-bacc-40cc-a0e4-df48a099c2f3/example.com',
		'Contact-Abuse':'54025843-bacc-40cc-a0e4-df48a099c2f3/example.com',
		'Language':'en',
		'Primary-Verification-Key':'ED25519:7dfD==!Jmt4cDtQDBxYa7(dV|N$}8mYwe$=RZuW|',
		'Encryption-Key':'CURVE25519:_`UC|vltn_%P5}~vwV^)oY){#uvQSSy(dOD_l(yE'
	})

	# sign and verify

	okeystring = CryptoString()
	okeystring.set('ED25519:' + base64.b85encode(oskey.encode()).decode())
	rv = orgcard.sign(okeystring, 'Organization')
	assert not rv.error(), 'Unexpected RetVal error %s' % rv.error()
	assert orgcard.signatures['Organization'], 'entry failed to user sign'

	ovkey = nacl.signing.VerifyKey(oskey.verify_key.encode())
	ovkeystring = CryptoString()
	ovkeystring.prefix = 'ED25519'
	ovkeystring.data = base64.b85encode(ovkey.encode()).decode()

	rv = orgcard.verify_signature(ovkeystring, 'Organization')
	assert not rv.error(), 'entry failed to org verify'

	rv = orgcard.generate_hash('BLAKE2B-256')
	assert not rv.error(), 'entry failed to hash'

	status = orgcard.is_compliant()
	assert not status.error(), f"OrgEntry wasn't compliant: {str(status)}"


def test_org_chaining():
	'''Tests chaining of organization entries and verification thereof'''
	orgentry = make_test_orgentry()

	# Organization signing key
	pskeystring = CryptoString('ED25519:msvXw(nII<Qm6oBHc+92xwRI3>VFF-RcZ=7DEu3|')
	
	chaindata = orgentry.chain(pskeystring, True)
	assert not chaindata.error(), f'orgentry.chain returned an error: {chaindata.error()}'

	new_entry = chaindata['entry']

	# Now that we have a new entry, it only has a valid custody signature. Add all the other 
	# signatures needed to be compliant and then verify the whole thing.

	# The signing key is replaced during chain()
	new_pskeystring = CryptoString()
	
	assert new_pskeystring.set(chaindata['sign.private']), \
		'test_org_chain: new signing key has bad format'
	
	status = new_entry.sign(new_pskeystring, 'Organization')
	assert not status.error(), f'new entry failed to org sign: {status}'
	
	new_entry.prev_hash = orgentry.hash
	status = new_entry.generate_hash('BLAKE2B-256')
	assert not status.error(), f'new entry failed to hash: {status}'
	
	status = new_entry.is_compliant()
	assert not status.error(), f'new entry failed compliance check: {status}'

	# Testing of chain() is complete. Now test verify_chain()
	status = new_entry.verify_chain(orgentry)
	assert not status.error(), f'chain of custody verification failed: {status}'


def test_user_chaining():
	'''Tests chaining of user entries and verification thereof'''
	userentry = make_test_userentry()

	# User contact request signing key
	crskeystring = CryptoString('ED25519:ip52{ps^jH)t$k-9bc_RzkegpIW?}FFe~BX&<V}9') 

	# Organization signing key
	oskeystring = CryptoString('ED25519:msvXw(nII<Qm6oBHc+92xwRI3>VFF-RcZ=7DEu3|')
	
	chaindata = userentry.chain(crskeystring, True)
	assert not chaindata.error(), f'userentry.chain returned an error: {chaindata.error()}'

	new_entry = chaindata['entry']

	# Now that we have a new entry, it only has a valid custody signature. Add all the other 
	# signatures needed to be compliant and then verify the whole thing.

	# The signing key is replaced during chain()
	new_crskeystring = CryptoString()
	assert new_crskeystring.set(chaindata['crsign.private']), \
		'test_user_chain: new signing key has bad format'
	
	status = new_entry.sign(oskeystring, 'Organization')
	assert not status.error(), f'new entry failed to org sign: {status}'

	new_entry.prev_hash = userentry.hash
	status = new_entry.generate_hash('BLAKE2B-256')
	assert not status.error(), f'new entry failed to hash: {status}'

	status = new_entry.sign(new_crskeystring, 'User')
	assert not status.error(), f'new entry failed to user sign: {status}'

	status = new_entry.is_compliant()
	assert not status.error(), f'new entry failed compliance check: {status}'

	# Testing of chain() is complete. Now test verify_chain()
	status = new_entry.verify_chain(userentry)
	assert not status.error(), f'chain of custody verification failed: {status}'


def test_hashing():
	'''Confirms that all supported algorithms work as expected'''
	userentry = make_test_userentry()

	algolist = [ 'BLAKE2B-256', 'BLAKE2B-256', 'SHA-256', 'SHA3-256' ]
	for algorithm in algolist:
		status = userentry.generate_hash(algorithm)
		assert not status.error(), f'hash test for {algorithm} failed'


def test_keycard_chain_verify_load_save():
	'''Tests entry rotation of a keycard'''
	userentry = make_test_userentry()

	# User contact request signing and verification keys
	crskeystring = CryptoString('ED25519:ip52{ps^jH)t$k-9bc_RzkegpIW?}FFe~BX&<V}9') 
	
	card = keycard.Keycard()
	card.entries.append(userentry)

	chaindata = card.chain(crskeystring, True)
	assert not chaindata.error(), f'keycard chain failed: {chaindata}'

	new_entry = chaindata['entry']
	oskeystring = CryptoString('ED25519:msvXw(nII<Qm6oBHc+92xwRI3>VFF-RcZ=7DEu3|')

	status = new_entry.sign(oskeystring, 'Organization')
	assert not status.error(), f'chained entry failed to org sign: {status}'

	new_entry.prev_hash = userentry.hash
	new_entry.generate_hash('BLAKE2B-256')
	assert not status.error(), f'chained entry failed to hash: {status}'

	skeystring = CryptoString(chaindata['sign.private'])
	status = new_entry.sign(skeystring, 'User')
	assert not status.error(), f'chained entry failed to user sign: {status}'

	card.entries[-1] = new_entry
	status = card.verify()
	assert not status.error(), f'keycard failed to verify: {status}'

	# Although it doesn't make a lot of initial sense to group saving and loading tests with 
	# code that handles chaining and verification, it saves on a lot of duplicate test code
	test_folder = setup_test('keycard_save')
	status = card.save(os.path.join(test_folder,'user_save_test_keycard.kc'), True)
	assert not status.error(), f'keycard failed to save: {status}'

	newcard = keycard.Keycard()
	status = newcard.load(os.path.join(test_folder,'user_save_test_keycard.kc'))
	assert not status.error(), f'keycard failed to load: {status}'


def bench_hashers():
	'''Quick benchmark for the different hash algorithms'''
	entry = make_test_userentry()

	# Clear the User signature to avoid skewing the results
	entry.generate_hash('BLAKE2-256')

	iterations = 25000
	print(f'Times for {iterations} iterations of each hash algorithm:')
	for hasher in ['BLAKE2-256', 'BLAKE2B-256', 'SHA-256', 'SHA3-256']:
		start = time.time()
		for _ in range(iterations):
			entry.generate_hash(hasher)
		stop = time.time()
		print(f'{hasher}:\t{stop-start}')

if __name__ == '__main__':
	# test_sign()
	# test_verify_signature()
	# test_keycard_chain_verify_load_save()
	# bench_hashers()
	test_is_data_compliant_user()
