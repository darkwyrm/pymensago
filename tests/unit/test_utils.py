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


def test_userid():
	'''Tests UserID.set() and is_valid()'''

	uid = utils.UserID()
	for testid in [ "GoodID", "alsogoooood", "🐧", "ಅಎಇ" ]:
		assert uid.set(testid) == testid.strip().casefold(), \
			f"test_userid_set failed good user ID '{testid}'"
		assert uid.is_valid(), f"test_userid_is_valid failed good user ID '{testid}'"

	for testid in [ "a bad id", "also/bad" ]:
		assert not uid.set(testid), f"test_userid_set passed bad user ID '{testid}'"
		assert not uid.is_valid(), f"test_userid_is_valid passed bad user ID '{testid}'"


def test_domain():
	'''Tests Domain.set() and is_valid()'''

	uid = utils.Domain()
	for testdom in [ "foo-bar.baz.com", "FOO.bar.com " ]:
		assert uid.set(testdom) == testdom.strip().casefold(), \
			f"test_domain_set failed good domain '{testdom}'"
		assert uid.is_valid(), f"test_domain_is_valid failed good domain '{testdom}'"

	for testdom in [ "a bad-id.com", "also_bad.org" ]:
		assert not uid.set(testdom), f"test_domain_set passed bad domain'{testdom}'"
		assert not uid.is_valid(), f"test_domain_is_valid passed bad domain '{testdom}'"


if __name__ == '__main__':
	test_maddress_set()
	test_userid()
	test_domain()
