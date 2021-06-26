import os
import shutil
import time

from retval import ErrUnimplemented

from pymensago.client import MensagoClient
import pymensago.iscmds as iscmds
from pymensago.encryption import Password
import pymensago.utils as utils
from tests.integration.integration_setup import setup_admin_profile, setup_test, init_server, \
	load_server_config, init_admin, funcname, setup_profile_base


def test_connect():
	'''Tests basic client connectivity'''
	test_folder = setup_profile_base('test_client_connect')
	client = MensagoClient(test_folder)

	assert not client.is_connected(), f"{funcname()}(): Not connected, but says so"
	status = client.connect(utils.Domain('example.com'))
	assert not status.error(), f"{funcname()}(): Couldn't connect to server"

	client.disconnect()
	assert not client.is_connected(), f"{funcname()}(): Connected, but says not"


def test_login():
	load_server_config()
	test_folder = setup_profile_base('test_client_login')
	client = MensagoClient(test_folder)

	pgdb = setup_test()
	dbdata = init_server(pgdb)
	status = setup_admin_profile(test_folder, dbdata)
	assert not status.error(), f"{funcname()}(): Couldn't set up admin profile"

	status = client.connect(utils.Domain('example.com'))
	assert not status.error(), f"{funcname()}(): Couldn't connect to server"
	status = init_admin(client.conn, dbdata)
	assert not status.error(), f"{funcname()}(): Couldn't init admin"
	
	status = client.disconnect()
	status = client.connect(utils.Domain('example.com'))
	assert not client.is_logged_in(), f"{funcname()}(): Not logged in, but says so"
	status = client.login(utils.MAddress('admin/example.com'))
	assert not status.error(), f"{funcname()}(): Couldn't log admin in"
	assert client.is_logged_in(), f"{funcname()}(): Logged in, but says not"


# TODO: Finish debugging test_preregister
def test_preregister():
	test_folder = setup_profile_base('test_client_preregister')
	client = MensagoClient(test_folder)

	pgdb = setup_test()
	dbdata = init_server(pgdb)
	status = setup_admin_profile(test_folder, dbdata)

	status = client.connect(utils.Domain('example.com'))
	assert not status.error(), f"{funcname()}(): Couldn't connect to server"
	status = init_admin(client.conn, dbdata)
	assert not status.error(), f"{funcname()}(): Couldn't init admin"
	status = client.login(utils.MAddress('admin/example.com'))
	assert not status.error(), f"{funcname()}(): Couldn't log in as admin"

	emptyID = utils.UserID()
	exampledom = utils.Domain('example.com')
	
	# Subtest #1: No data supplied
	
	status = client.preregister_account(emptyID, exampledom)
	assert not status.error(), f"{funcname()}(): Subtest #1 (no data) preregistration failed"
	assert status['domain'].as_string() == 'example.com' and \
		'wid' in status and 'regcode' in status, \
		f"{funcname()}(): Subtest #1 returned bad data"

	# Subtest #2: Workspace ID supplied
	
	status = client.preregister_account(utils.UserID('33333333-3333-3333-3333-333333333333'),
		exampledom)
	assert not status.error(), f"{funcname()}(): Subtest #2 (wid) preregistration failed"
	assert status['domain'].as_string() == 'example.com' and \
		'wid' in status and \
		'regcode' in status and \
		status['wid'].as_string() == '33333333-3333-3333-3333-333333333333', \
		f"{funcname()}(): Subtest #2 returned bad data"

	# Subtest #3: User ID supplied

	status = client.preregister_account(utils.UserID('csimons'), exampledom)
	assert not status.error(), f"{funcname()}(): Subtest #2 (wid) preregistration failed"
	assert status['domain'].as_string() == 'example.com' and \
		'wid' in status and \
		'regcode' in status and \
		status['uid'].as_string() == 'csimons', \
		f"{funcname()}(): Subtest #3 returned bad data"

	client.disconnect()



def test_register():
	serverdbdata = load_server_config()
	if serverdbdata['global']['registration'] not in ['network', 'public']:
		return
	
	test_folder = setup_profile_base('test_client_register')
	client = MensagoClient(test_folder)

	pgdb = setup_test()
	dbdata = init_server(pgdb)

	status = client.register_account(utils.Domain('example.com'), 'MyS3cretPassw*rd', 
		utils.UserID('csimons'))
	assert not status.error(), \
		f"test_register_account: failed to register test account: {status.info()}"


def test_regcode():
	load_server_config()
	test_folder = setup_profile_base('test_client_regcode')
	client = MensagoClient(test_folder)

	pgdb = setup_test()
	dbdata = init_server(pgdb)
	status = setup_admin_profile(test_folder, dbdata)

	status = client.connect(utils.Domain('example.com'))
	assert not status.error(), f"{funcname()}(): Couldn't connect to server"
	status = init_admin(client.conn, dbdata)
	assert not status.error(), f"{funcname()}(): Couldn't init admin"

	userid = utils.UserID('33333333-3333-3333-3333-333333333333')
	status = iscmds.preregister(client.conn, userid, utils.UserID('csimons'),
		utils.Domain('example.com'))
	assert not status.error(), f"{funcname()}(): user preregistration failed"
	assert status['domain'].as_string() == 'example.com' and \
		'wid' in status and \
		'regcode' in status and	\
		status['uid'].as_string() == 'csimons', f"{funcname()}(): failed to return expected data"

	regdata = status
	address = utils.MAddress('csimons/example.com')
	status = client.redeem_regcode(address, regdata['regcode'], 'MyS3cretPassw*rd')

	client.disconnect()

if __name__ == '__main__':
	# test_connect()
	# test_login()
	test_preregister()
	# test_register()
	# test_regcode()
