'''This module tests the KeyCard class'''
import base64
import datetime
import os
import shutil
import time

import nacl.signing

import keycard
from keycard import AlgoString, Base85Encoder, SIGINFO_HASH, SIGINFO_SIGNATURE

# Keys used in the various tests

# User Signing Key: p;XXU0XF#UO^}vKbC-wS(#5W6=OEIFmR2z`rS1j+
# User Verification Key: 6|HBWrxMY6-?r&Sm)_^PLPerpqOj#b&x#N_#C3}p

# User Contact Request Signing Key: ip52{ps^jH)t$k-9bc_RzkegpIW?}FFe~BX&<V}9
# User Contact Request Verification Key: d0-oQb;{QxwnO{=!|^62+E=UYk2Y3mr2?XKScF4D

# Organization Primary Signing Key: msvXw(nII<Qm6oBHc+92xwRI3>VFF-RcZ=7DEu3|
# Organization Primary Verification Key: )8id(gE02^S<{3H>9B;X4{DuYcb`%wo^mC&1lN88

# Organization Encryption Key: @b?cjpeY;<&y+LSOA&yUQ&ZIrp(JGt{W$*V>ATLG
# Organization Decryption Key: nQxAR1Rh{F4gKR<KZz)*)7}5s_^!`!eb!sod0<aT


# Pylint doesn't detect the use of this import:
from retval import RetVal # pylint: disable=unused-import

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
		'Contact-Request-Signing-Key':'ED25519:d0-oQb;{QxwnO{=!|^62+E=UYk2Y3mr2?XKScF4D',
		'Contact-Request-Encryption-Key':'CURVE25519:yBZ0{1fE9{2<b~#i^R+JT-yh-y5M(Wyw_)}_SZOn',
		'Public-Encryption-Key':'CURVE25519:_`UC|vltn_%P5}~vwV^)oY){#uvQSSy(dOD_l(yE'
	})

	# Organization sign and verify

	okeystring = AlgoString()
	okeystring.set('ED25519:' + base64.b85encode(oskey.encode()).decode())
	rv = usercard.sign(okeystring, 'Organization')
	assert not rv.error(), 'Unexpected RetVal error %s' % rv.error()
	assert usercard.signatures['Organization'], 'entry failed to user sign'

	ovkey = nacl.signing.VerifyKey(oskey.verify_key.encode())
	ovkeystring = AlgoString()
	ovkeystring.prefix = 'ED25519'
	ovkeystring.data = base64.b85encode(ovkey.encode()).decode()

	rv = usercard.verify_signature(ovkeystring, 'Organization')
	assert not rv.error(), 'entry failed to org verify'

	# Add the hash

	rv = usercard.generate_hash('BLAKE3-512')
	assert not rv.error(), 'entry failed to hash'

	# User sign and verify

	keystring = AlgoString()
	keystring.set('ED25519:' + base64.b85encode(skey.encode()).decode())
	rv = usercard.sign(keystring, 'User')
	assert not rv.error(), 'Unexpected RetVal error %s / %s' % (rv.error(), rv.info())
	assert usercard.signatures['User'], 'entry failed to user sign'
	
	vkey = nacl.signing.VerifyKey(skey.verify_key.encode())
	vkeystring = AlgoString()
	vkeystring.prefix = 'ED25519'
	vkeystring.data = base64.b85encode(vkey.encode()).decode()

	rv = usercard.verify_signature(vkeystring, 'User')
	assert not rv.error(), 'entry failed to user verify'

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
		'Primary-Signing-Key':'ED25519:)8id(gE02^S<{3H>9B;X4{DuYcb`%wo^mC&1lN88',
		'Encryption-Key':'CURVE25519:@b?cjpeY;<&y+LSOA&yUQ&ZIrp(JGt{W$*V>ATLG'
	})

	# Organization sign, hash, and verify

	pskeystring = AlgoString()
	pskeystring.set('ED25519:' + base64.b85encode(pskey.encode()).decode())
	rv = orgcard.sign(pskeystring, 'Organization')
	assert not rv.error(), 'Unexpected RetVal error %s' % rv.error()
	assert orgcard.signatures['Organization'], 'entry failed to user sign'

	ovkey = nacl.signing.VerifyKey(pskey.verify_key.encode())
	ovkeystring = AlgoString()
	ovkeystring.prefix = 'ED25519'
	ovkeystring.data = base64.b85encode(ovkey.encode()).decode()

	rv = orgcard.generate_hash('BLAKE3-512')
	assert not rv.error(), 'entry failed to hash'

	rv = orgcard.verify_signature(ovkeystring, 'Organization')
	assert not rv.error(), 'org entry failed to verify'

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
		b'Primary-Signing-Key:ED25519:&JEq)5Ktu@jfM+Sa@+1GU6E&Ct2*<2ZYXh#l0FxP\r\n' \
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
	basecard.field_names = [ 'Name', 'Workspace-ID', 'Domain', 'Contact-Request-Signing-Key',
			'Contact-Request-Encryption-Key', 'Public-Encryption-Key', 'Expires']
	basecard.set_fields({
		'Name':'Corbin Simons',
		'Workspace-ID':'4418bf6c-000b-4bb3-8111-316e72030468',
		'Domain':'example.com',
		'Contact-Request-Signing-Key':'ED25519:7dfD==!Jmt4cDtQDBxYa7(dV|N$}8mYwe$=RZuW|',
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

	keystring = AlgoString()
	keystring.set('ED25519:' + base64.b85encode(skey.encode()).decode())
	rv = basecard.sign(keystring, 'Organization')
	assert not rv.error(), 'Unexpected RetVal error %s' % rv.error()
	assert basecard.signatures['Organization'], 'entry failed to org sign'

	rv = basecard.generate_hash('BLAKE3-512')
	assert not rv.error(), 'Unexpected RetVal error %s' % rv.error()
	
	expected_sig = \
		'ED25519:Ied3Gcl&O6DeK7zk<l;brbZ$BCFwB4?mh1GJI=&Cc`nGV?owKG#tupX`igeH%~pfV)a*Kd9IJ5m0c9=<'
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
	basecard.field_names = [ 'Name', 'Workspace-ID', 'Domain', 'Contact-Request-Signing-Key',
			'Contact-Request-Encryption-Key', 'Public-Encryption-Key', 'Expires']
	basecard.set_fields({
		'Name':'Corbin Simons',
		'Workspace-ID':'4418bf6c-000b-4bb3-8111-316e72030468',
		'Domain':'example.com',
		'Contact-Request-Signing-Key':'ED25519:d0-oQb;{QxwnO{=!|^62+E=UYk2Y3mr2?XKScF4D',
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

	okeystring = AlgoString()
	okeystring.set('ED25519:' + base64.b85encode(oskey.encode()).decode())
	rv = basecard.sign(okeystring, 'Organization')
	assert not rv.error(), 'Unexpected RetVal error %s' % rv.error()
	assert basecard.signatures['Organization'], 'entry failed to user sign'

	expected_sig = \
		'ED25519:+k1r8iJ`;ol+sIJ*Yc*9Q*%SExR=vE0C99zRUC3JXOYWzS;HW?(idJ89Oal7y*iAQjZC!Wsdx+EQs2P?'
	assert basecard.signatures['Organization'] == expected_sig, \
			"entry did not yield the expected org signature"
	

	ovkey = nacl.signing.VerifyKey(oskey.verify_key.encode())
	ovkeystring = AlgoString()
	ovkeystring.prefix = 'ED25519'
	ovkeystring.data = base64.b85encode(ovkey.encode()).decode()

	rv = basecard.verify_signature(ovkeystring, 'Organization')
	assert not rv.error(), 'entry failed to org verify'

	# Set up the hashes
	basecard.prev_hash = '1234567890'
	rv = basecard.generate_hash('BLAKE3-512')
	assert not rv.error(), 'entry failed to BLAKE3 hash'

	expected_hash = \
		r'BLAKE3-512:1qTf`Hq*rSrlHM=x7E_r%}n8R#hpd3l(26c%A6p@djSv$c2+wU29J?&hs$~LbyOWaKM>Xk<LsA{J' \
		r'A(><Dw*k!BCD*6mAe6uJjYOG>u^j3_C>epRftL0LNs)g8JBw*0c#l_bF^fgr`U%saoQ)Eu$PFM5KsB+#ltJnCoP' \
		r'F5#Xr3J5`@;vl#}ffw?@6s=E4dVxY8{jr0S7&T16qZ#EbW^k~R~SkG6IdA#{uq#`4AmIj0MMIKZ&7!{vv;*JK@V' \
		r'p1;e^1f1d;_<z?H^3?StbaetVp4e!T5UKOn2BW31Xc$=e*gjksd5WT{3%ME)EZv7&h8qIN$2px(0g*s^zd*Kwo3' \
		r'Fz@{yP){@lLltp(JAt$|oPg&3bXOU?K*Lgzy3=?J_kW5f;6@rb^C*4>Y}0iDr&JASU_4#`l$iTH&Sc@?f$8J<JI' \
		r'np0v&6RpY1m)FeKN&dIq=(Gsu&tsFs^M@N<mbdb;I8rYP+7e5++!D<L%mK1s5JB4R@XFAcCC!p`k7DiN!nkrh`t' \
		r'hqyhBXu}wwL*r*ie{r0UDXttGe3$N?;)p**>BeZ(YN13&>OUUp0zoMF6p1gXoeyO`dHs4&&(aH%5SIq(t7GH5yl' \
		r'!5S&rrU-me?pr&}sg1<o1epP*V#z(nS9S!aW|oGS?O'
	assert basecard.hash == expected_hash, "entry did not yield the expected hash"
	
	# User sign and verify

	keystring = AlgoString()
	keystring.set('ED25519:' + base64.b85encode(skey.encode()).decode())
	rv = basecard.sign(keystring, 'User')
	assert not rv.error(), 'Unexpected RetVal error %s' % rv.error()
	assert basecard.signatures['User'], 'entry failed to user sign'
	
	expected_sig = \
		'ED25519:MFGN>u=oswij--OD6xpQ47K*9a^1O2_&c3eUO-IrG?EZD<N47iP3P{`)oi3VCG>P#B^`*RM9v0#j-M<6'
	assert basecard.signatures['User'] == expected_sig, \
			"entry did not yield the expected user signature"

	vkey = nacl.signing.VerifyKey(skey.verify_key.encode())
	vkeystring = AlgoString()
	vkeystring.prefix = 'ED25519'
	vkeystring.data = base64.b85encode(vkey.encode()).decode()

	rv = basecard.verify_signature(vkeystring, 'User')
	assert not rv.error(), 'entry failed to user verify'


def test_base_is_compliant():
	'''Tests compliance testing for the base class'''
	basecard = keycard.EntryBase()
	status = basecard.is_compliant()
	assert status.error(), "EntryBase met compliance and shouldn't"


def test_is_compliant_user():
	'''Tests compliance testing for the UserEntry class'''

	# The original code for this test made a great setup for other UserEntry-based tests
	make_test_userentry()


def test_is_compliant_org():
	'''Tests compliance testing for the OrgEntry class'''

	# Organization signing key
	oskey = nacl.signing.SigningKey(b'msvXw(nII<Qm6oBHc+92xwRI3>VFF-RcZ=7DEu3|', Base85Encoder)

	orgcard = keycard.OrgEntry()
	orgcard.set_fields({
		'Name':'Acme Widgets, Inc',
		'Contact-Admin':'admin/example.com',
		'Contact-Abuse':'abuse/example.com',
		'Language':'en',
		'Primary-Signing-Key':'ED25519:7dfD==!Jmt4cDtQDBxYa7(dV|N$}8mYwe$=RZuW|',
		'Encryption-Key':'CURVE25519:_`UC|vltn_%P5}~vwV^)oY){#uvQSSy(dOD_l(yE'
	})

	# sign and verify

	okeystring = AlgoString()
	okeystring.set('ED25519:' + base64.b85encode(oskey.encode()).decode())
	rv = orgcard.sign(okeystring, 'Organization')
	assert not rv.error(), 'Unexpected RetVal error %s' % rv.error()
	assert orgcard.signatures['Organization'], 'entry failed to user sign'

	ovkey = nacl.signing.VerifyKey(oskey.verify_key.encode())
	ovkeystring = AlgoString()
	ovkeystring.prefix = 'ED25519'
	ovkeystring.data = base64.b85encode(ovkey.encode()).decode()

	rv = orgcard.verify_signature(ovkeystring, 'Organization')
	assert not rv.error(), 'entry failed to org verify'

	rv = orgcard.generate_hash('BLAKE3-512')
	assert not rv.error(), 'entry failed to hash'

	status = orgcard.is_compliant()
	assert not status.error(), f"OrgEntry wasn't compliant: {str(status)}"


def test_org_chaining():
	'''Tests chaining of organization entries and verification thereof'''
	orgentry = make_test_orgentry()

	# Organization signing key
	pskeystring = AlgoString('ED25519:msvXw(nII<Qm6oBHc+92xwRI3>VFF-RcZ=7DEu3|')
	
	chaindata = orgentry.chain(pskeystring, True)
	assert not chaindata.error(), f'orgentry.chain returned an error: {chaindata.error()}'

	new_entry = chaindata['entry']

	# Now that we have a new entry, it only has a valid custody signature. Add all the other 
	# signatures needed to be compliant and then verify the whole thing.

	# The signing key is replaced during chain()
	new_pskeystring = AlgoString()
	status = new_pskeystring.set(chaindata['sign.private'])
	assert not status.error(), 'test_org_chain: new signing key has bad format'
	
	status = new_entry.sign(new_pskeystring, 'Organization')
	assert not status.error(), f'new entry failed to org sign: {status}'
	
	new_entry.prev_hash = orgentry.hash
	status = new_entry.generate_hash('BLAKE3-512')
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
	crskeystring = AlgoString('ED25519:ip52{ps^jH)t$k-9bc_RzkegpIW?}FFe~BX&<V}9') 

	# Organization signing key
	oskeystring = AlgoString('ED25519:msvXw(nII<Qm6oBHc+92xwRI3>VFF-RcZ=7DEu3|')
	
	chaindata = userentry.chain(crskeystring, True)
	assert not chaindata.error(), f'userentry.chain returned an error: {chaindata.error()}'

	new_entry = chaindata['entry']

	# Now that we have a new entry, it only has a valid custody signature. Add all the other 
	# signatures needed to be compliant and then verify the whole thing.

	# The signing key is replaced during chain()
	new_crskeystring = AlgoString()
	status = new_crskeystring.set(chaindata['crsign.private'])
	assert not status.error(), 'test_user_chain: new signing key has bad format'
	
	status = new_entry.sign(oskeystring, 'Organization')
	assert not status.error(), f'new entry failed to org sign: {status}'

	new_entry.prev_hash = userentry.hash
	status = new_entry.generate_hash('BLAKE3-512')
	assert not status.error(), f'new entry failed to hash: {status}'

	status = new_entry.sign(new_crskeystring, 'User')
	assert not status.error(), f'new entry failed to user sign: {status}'

	status = new_entry.is_compliant()
	assert not status.error(), f'new entry failed compliance check: {status}'

	# Testing of chain() is complete. Now test verify_chain()
	status = new_entry.verify_chain(userentry)
	assert not status.error(), f'chain of custody verification failed: {status}'


def test_keycard_chain_verify_load_save():
	'''Tests entry rotation of a keycard'''
	userentry = make_test_userentry()

	# User contact request signing and verification keys
	crskeystring = AlgoString('ED25519:ip52{ps^jH)t$k-9bc_RzkegpIW?}FFe~BX&<V}9') 
	
	card = keycard.Keycard()
	card.entries.append(userentry)

	chaindata = card.chain(crskeystring, True)
	assert not chaindata.error(), f'keycard chain failed: {chaindata}'

	new_entry = chaindata['entry']
	oskeystring = AlgoString('ED25519:msvXw(nII<Qm6oBHc+92xwRI3>VFF-RcZ=7DEu3|')

	status = new_entry.sign(oskeystring, 'Organization')
	assert not status.error(), f'chained entry failed to org sign: {status}'

	new_entry.prev_hash = userentry.hash
	new_entry.generate_hash('BLAKE3-512')
	assert not status.error(), f'chained entry failed to hash: {status}'

	skeystring = AlgoString(chaindata['sign.private'])
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

if __name__ == '__main__':
	test_keycard_chain_verify_load_save()
