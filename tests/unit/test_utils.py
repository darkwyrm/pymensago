'''Implements tests for the utils module'''

# pylint: disable=import-error
import pymensago.utils as utils

def test_validate_uuid():
	'''Tests utils.validate_uuid'''
	assert utils.validate_uuid('5a56260b-aa5c-4013-9217-a78f094432c3'), 'Failed to validate good ID'
	assert not utils.validate_uuid('5a56260b-c-4013-9217-a78f094432c3'), 'Failed to reject bad ID'


def test_split_address():
	'''Tests utils.split_address'''
	
	out = utils.split_address('5a56260b-aa5c-4013-9217-a78f094432c3/example.com')
	assert not out.error(), "split_address error on good address"
	assert out['wid'] == '5a56260b-aa5c-4013-9217-a78f094432c3', 'split_address returned bad wid'
	assert out['domain'] == 'example.com', 'split_address returned bad domain'

	assert utils.split_address('5a56260b-aa5c-4013-9217-a78f094432c3'), \
			'Failed to error on bad address #1'
	
	assert utils.split_address('example.com'), 'Failed to error on bad address #2'

def test_maddress_set():
	'''Tests MAddress.Set'''
	addr = utils.MAddress()
	assert not addr.set('🐈🐈🐈4life/example.com').error(), \
		'MAddress.Set() failed to pass a valid Mensago address'
	assert not addr.set('5a56260b-aa5c-4013-9217-a78f094432c3/example.com').error(), \
		'MAddress.Set() failed to pass a valid workspace address'
	assert addr.set('has spaces/example.com').error(), \
		'MAddress.Set() passed a Mensago address with spaces'
	assert addr.set('has_a_"/example.com').error(), \
		'MAddress.Set() passed a Mensago address with double quotes'
	assert addr.set('\\not_allowed/example.com').error(), \
		'MAddress.Set() passed a Mensago address with a backslash'
	assert addr.set('/example.com').error(), \
		'MAddress.Set() passed a Mensago address without an ID'
	assert addr.set('5a56260b-aa5c-4013-9217-a78f094432c3'
							'/example.com/example.com').error(), \
		'MAddress.Set() passed an invalid workspace address'
	assert addr.set('5a56260b-aa5c-4013-9217-a78f094432c3').error(), \
		'MAddress.Set() passed an invalid workspace address'
	assert addr.set(('a'*65) + '/example.com').error(), \
		'MAddress.Set() passed an address that was too long'

if __name__ == '__main__':
	test_maddress_set()
