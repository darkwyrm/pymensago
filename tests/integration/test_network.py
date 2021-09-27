from tests.integration.integration_setup import user1_profile_data, funcname, setup_two_profiles, \
	admin_profile_data

from pycryptostring import CryptoString
from pymensago.envelope import Envelope
import pymensago.iscmds as iscmds
import pymensago.messages as messages
import pymensago.updates as updates
import pymensago.utils as utils

def test_local_delivery():
	'''Tests the SEND command for the sender and then GETUPDATES on the recipient side'''

	status = setup_two_profiles('test_local_delivery')
	assert not status.error(), f"{funcname()}: profile setup failure: {status.error()}"
	setupdata = status
	client = setupdata['client']

	status = client.login(utils.MAddress('admin/example.com'))
	assert not status.error(), f"{funcname()}: admin login failure: {status.error()}"

	# Construct a test contact request, which is the only kind of message allowed to be sent
	# to a person not in your address book
	cr = messages.ContactRequest(messages.CONTACT_REQUEST_INITIATE)
	cr.contact_info = {
		'Header': { 'Version':'1.0', 'EntityType':'Individual' },
		'GivenName': 'Example.com',
		'FamilyName': 'Admin',
		'FormattedName': 'Example.com Admin',
		'Mensago': [
			{	'Label': 'Primary',
				'UserID': admin_profile_data['uid'].as_string(),
				'Domain': admin_profile_data['domain'].as_string(),
				'WorkspaceID': admin_profile_data['wid'].as_string()
			}
		]
	}
	cr.message = 'I would like to connect with you in case you need help.\n\n--Admin'

	# Assemble the envelope and save to disk so that it can be sent
	
	env = Envelope()
	env.payload = cr

	# Proper clients will do a keycard lookup for the organization and get the key from there. This
	# is an integration test under very controlled conditions, so we can skip that part and only
	# test the code we really want to test.
	status = env.set_sender(admin_profile_data['waddress'], user1_profile_data['waddress'],
		CryptoString(setupdata['dbdata']['oekey']))
	assert not status.error(), f"{funcname()}: Failed to encrypt sender information"

	# This is exactly the same call only because the sender and receiver are on the same server.
	# If they weren't, the key here would be the receiving organization's encryption key
	status = env.set_receiver(admin_profile_data['waddress'], user1_profile_data['waddress'],
		CryptoString(setupdata['dbdata']['oekey']))
	assert not status.error(), f"{funcname()}: Failed to encrypt receiver information"

	# set_msg_key() sets up the message encryption and takes the CryptoString public key of the 
	# recipient
	status = env.set_msg_key(user1_profile_data['crencryption'].public)
	assert not status.error(), f"{funcname()}: Failed to set message key"

	status = client.send(env, user1_profile_data['domain'])
	assert not status.error(), f"{funcname()}: Failed to send message"

	# Now switch to the recipient and check for updates
	client.logout()
	status = client.pman.activate_profile('user1')
	assert not status.error(), f"{funcname()}: failed to switch to user profile: {status.error()}"
	
	status = client.login(utils.MAddress('csimons/example.com'))
	assert not status.error(), f"{funcname}: user login failure: {status.error()}"

	status = client.pman.get_active_profile()
	assert not status.error(), f"{funcname()}: failed to get active profile: {status.error()}"
	profile = status['profile']

	status = updates.download_updates(client.conn, profile.db)
	assert not status.error(), \
		f"{funcname()}: failed to get recipient workspace updates: {status.error()}"

	# TODO: Finish implementing test_local_delivery()

	client.disconnect()	


def test_set_status():
	'''Test the SETSTATUS command'''
	
	status = setup_two_profiles('test_local_delivery')
	assert not status.error(), f"{funcname}: profile setup failure: {status.error()}"
	client = status['client']
	
	status = client.login(utils.MAddress('admin/example.com'))
	assert not status.error(), f"{funcname()}: client failed to log back in as admin"

	status = iscmds.setstatus(client.conn, user1_profile_data['wid'], 'disabled')
	assert not status.error(), f"test_set_workstatus(): set_workstatus failed: {status.info()}"

	client.disconnect()



if __name__ == '__main__':
	# test_set_status()
	test_local_delivery()
