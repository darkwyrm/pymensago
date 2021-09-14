from tests.integration.integration_setup import user1_profile_data, funcname, setup_two_profiles
import pymensago.iscmds as iscmds
import pymensago.utils as utils

def test_local_delivery():
	'''Tests the SEND command for the sender and then GETUPDATES on the recipient side'''
	# TODO: Finish implementing test_local_delivery()

	status = setup_two_profiles('test_local_delivery')
	assert not status.error(), f"{funcname}: profile setup failure: {status.error()}"
	client = status['client']

	status = client.login(utils.MAddress('admin/example.com'))
	assert not status.error(), f"{funcname}: admin login failure: {status.error()}"

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
	test_set_status()
	test_local_delivery()
