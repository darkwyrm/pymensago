
from pymensago.kcresolver import get_mgmt_record

def test_get_mgmt_record():
	'''Tests get_mgmt_record()'''

	status = get_mgmt_record('example.com')
	assert not status.error(), 'test_get_mgmt_record(): error returned for example.com'
	assert 'pvk' in status.fields(), 'test_get_mgmt_record(): pvk missing for example.com'

if __name__ == '__main__':
	test_get_mgmt_record()
