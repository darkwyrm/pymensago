'''This module tests the various classes and functions in the encryption module'''
import base64
import json
import os
import shutil
import time

import encryption
# Pylint doesn't detect the use of this import:
from retval import RetVal # pylint: disable=unused-import

def setup_test(name):
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


def test_keypair_base():
	'''Tests base initialization of the KeyPair class'''
	kp = encryption.KeyPair()
	assert base64.b85decode(kp.public85.encode()) == kp.public, \
			"public85 does not match public key"
	assert base64.b85decode(kp.private85.encode()) == kp.private, \
			"private85 does not match private key"


def test_keypair_save():
	'''Tests the save code of the KeyPair class'''
	test_folder = setup_test('encryption_keypair_save')

	public85 = "(B2XX5|<+lOSR>_0mQ=KX4o<aOvXe6M`Z5ldINd`"
	private85 = "(Rj5)mmd1|YqlLCUP0vE;YZ#o;tJxtlAIzmPD7b&"
	public_key = base64.b85decode(public85.encode())
	private_key = base64.b85decode(private85.encode())
	kp = encryption.KeyPair('', public_key, private_key, 'curve25519')

	keypair_path = os.path.join(test_folder, 'testpair.json')
	status = kp.save(keypair_path)
	assert not status.error(), "Failed to create saved encryption pair file"

	fhandle = open(keypair_path)
	filedata = json.load(fhandle)
	fhandle.close()

	assert filedata['type'] == 'encryptionpair', "Saved data does not match input data"
	assert filedata['encryption'] == 'curve25519', "Saved data does not match input data"
	assert filedata['publickey'] == public85, "Saved data does not match input data"
	assert filedata['privatekey'] == private85, "Saved data does not match input data"


def test_keypair_load():
	'''Tests the load code of the KeyPair class'''
	test_folder = setup_test('encryption_keypair_load')

	public85 = "(B2XX5|<+lOSR>_0mQ=KX4o<aOvXe6M`Z5ldINd`"
	private85 = "(Rj5)mmd1|YqlLCUP0vE;YZ#o;tJxtlAIzmPD7b&"
	public_key = base64.b85decode(public85.encode())
	private_key = base64.b85decode(private85.encode())
	kp = encryption.KeyPair('', public_key, private_key, 'curve25519')

	keypair_path = os.path.join(test_folder, 'testpair.json')
	status = kp.save(keypair_path)
	assert not status.error(), "Failed to create saved encryption pair file"

	status = encryption.load_encryptionpair(keypair_path)
	assert not status.error(), "Failed to load saved pair file"

	testpair = status['keypair']

	assert testpair.type == kp.type, "Loaded data does not match input data"
	assert testpair.enc_type == kp.enc_type, "Loaded data does not match input data"
	assert testpair.get_public_key85() == public85, "Loaded data does not match input data"
	assert testpair.get_private_key85() == private85, "Loaded data does not match input data"
	

def test_signpair_base():
	'''Tests base initialization of the SigningPair class'''
	sp = encryption.SigningPair()
	assert base64.b85decode(sp.public85.encode()) == sp.public, \
			"public85 does not match public key"
	assert base64.b85decode(sp.private85.encode()) == sp.private, \
			"private85 does not match private key"


def test_signpair_save():
	'''Tests the save code of the SigningPair class'''
	test_folder = setup_test('encryption_signpair_save')

	public85 = "PnY~pK2|;AYO#1Z;B%T$2}E$^kIpL=>>VzfMKsDx"
	private85 = "{^A@`5N*T%5ybCU%be892x6%*Rb2rnYd=SGeO4jF"
	public_key = base64.b85decode(public85.encode())
	private_key = base64.b85decode(private85.encode())
	sp = encryption.SigningPair('', public_key, private_key, 'ed25519')

	keypair_path = os.path.join(test_folder, 'testpair.json')
	status = sp.save(keypair_path)
	assert not status.error(), "Failed to create saved signing pair file"

	fhandle = open(keypair_path)
	filedata = json.load(fhandle)
	fhandle.close()

	assert filedata['type'] == 'signingpair', "Saved data does not match input data"
	assert filedata['encryption'] == 'ed25519', "Saved data does not match input data"
	assert filedata['publickey'] == public85, "Saved data does not match input data"
	assert filedata['privatekey'] == private85, "Saved data does not match input data"


def test_signpair_load():
	'''Tests the load code of the SigningPair class'''
	test_folder = setup_test('encryption_signpair_load')

	public85 = "PnY~pK2|;AYO#1Z;B%T$2}E$^kIpL=>>VzfMKsDx"
	private85 = "{^A@`5N*T%5ybCU%be892x6%*Rb2rnYd=SGeO4jF"
	public_key = base64.b85decode(public85.encode())
	private_key = base64.b85decode(private85.encode())
	kp = encryption.SigningPair('', public_key, private_key, 'ed25519')

	keypair_path = os.path.join(test_folder, 'testpair.json')
	status = kp.save(keypair_path)
	assert not status.error(), "Failed to create saved signing pair file"

	status = encryption.load_signingpair(keypair_path)
	assert not status.error(), "Failed to load saved pair file"

	testpair = status['keypair']

	assert testpair.type == kp.type, "Loaded data does not match input data"
	assert testpair.enc_type == kp.enc_type, "Loaded data does not match input data"
	assert testpair.get_public_key85() == public85, "Loaded data does not match input data"
	assert testpair.get_private_key85() == private85, "Loaded data does not match input data"


def test_secretkey_base():
	'''Tests base initialization of the SecretKey class'''
	sk = encryption.SecretKey()
	assert base64.b85decode(sk.key85.encode()) == sk.key, "key85 does not match key"


def test_secretkey_save():
	'''Tests the save code of the SecretKey class'''
	test_folder = setup_test('encryption_secretkey_save')

	key85 = "J~T^ko3HCFb$1Z7NudpcJA-dzDpF52IF1Oysh+CY"
	key = base64.b85decode(key85.encode())
	sk = encryption.SecretKey('', key, 'salsa20')

	key_path = os.path.join(test_folder, 'testkey.json')
	status = sk.save(key_path)
	assert not status.error(), "Failed to create saved encryption pair file"

	fhandle = open(key_path)
	filedata = json.load(fhandle)
	fhandle.close()

	assert filedata['type'] == 'secretkey', "Saved data does not match input data"
	assert filedata['encryption'] == 'salsa20', "Saved data does not match input data"
	assert filedata['key'] == key85, "Saved data does not match input data"


def test_secretkey_load():
	'''Tests the load code of the SecretKey class'''
	test_folder = setup_test('encryption_secretkey_load')

	key85 = "J~T^ko3HCFb$1Z7NudpcJA-dzDpF52IF1Oysh+CY"
	key = base64.b85decode(key85.encode())
	sk = encryption.SecretKey('', key, 'salsa20')

	key_path = os.path.join(test_folder, 'testkey.json')
	status = sk.save(key_path)
	assert not status.error(), "Failed to create saved encryption pair file"

	status = encryption.load_secretkey(key_path)
	assert not status.error(), "Failed to load secret key file"

	testpair = status['key']

	assert testpair.type == sk.type, "Loaded data does not match input data"
	assert testpair.enc_type == sk.enc_type, "Loaded data does not match input data"
	assert testpair.get_key85() == key85, "Loaded data does not match input data"
