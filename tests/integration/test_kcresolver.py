
from tests.integration.integration_setup import setup_test, init_server, funcname
from pymensago.kcresolver import get_mgmt_record

def test_get_mgmt_record():
	'''Tests get_mgmt_record()'''
	dbconn = setup_test()
	init_server(dbconn)

	status = get_mgmt_record('example.com')
	assert not status.error(), f"{funcname()}(): error returned for example.com"
	
	fields = status.fields()
	assert 'pvk' in fields, f"{funcname()}(): pvk missing for example.com"
	assert 'ek' in fields, f"{funcname()}(): ek missing for example.com"
	assert 'svk' in fields, f"{funcname()}(): svk missing for example.com"

if __name__ == '__main__':
	test_get_mgmt_record()
