'''Implements tests for the utils module'''

# pylint: disable=import-error
import pymensago.utils as utils

def test_validate_uuid():
	'''Tests utils.validate_uuid'''
	assert utils.validate_uuid('5a56260b-aa5c-4013-9217-a78f094432c3'), 'Failed to validate good ID'
	assert not utils.validate_uuid('5a56260b-c-4013-9217-a78f094432c3'), 'Failed to reject bad ID'


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
	for testid in [ "GoodID", "alsogoooood", "🐧", "ಅಎಇ", "11111111-1111-1111-1111-111111111111" ]:
		assert uid.set(testid) == testid.strip().casefold(), \
			f"test_userid_set failed good user ID '{testid}'"
		assert uid.is_valid(), f"test_userid_is_valid failed good user ID '{testid}'"

	for testid in [ "a bad id", "also/bad" ]:
		assert not uid.set(testid), f"test_userid_set passed bad user ID '{testid}'"
		assert not uid.is_valid(), f"test_userid_is_valid passed bad user ID '{testid}'"


def test_domain():
	'''Tests Domain.set() and is_valid()'''

	dom = utils.Domain()
	for testdom in [ "foo-bar.baz.com", "FOO.bar.com " ]:
		assert dom.set(testdom) == testdom.strip().casefold(), \
			f"test_domain_set failed good domain '{testdom}'"
		assert dom.is_valid(), f"test_domain_is_valid failed good domain '{testdom}'"

	for testdom in [ "a bad-id.com", "also_bad.org" ]:
		assert not dom.set(testdom), f"test_domain_set passed bad domain'{testdom}'"
		assert not dom.is_valid(), f"test_domain_is_valid passed bad domain '{testdom}'"


def test_uuid():
	'''Tests UUID.set() and is_valid()'''

	wid = utils.UUID()
	for testwid in [ "11111111-1111-1111-1111-111111111111", 
					" aaaaaaaa-BBBB-1111-1111-111111111111" ]:
		assert wid.set(testwid) == testwid.strip().casefold(), \
			f"test_uuid_set failed good workspace ID '{testwid}'"
		assert wid.is_valid(), f"test_uuid_set failed good workspace ID '{testwid}'"

	for testwid in [ "11111111111111111111111111111111", "also_bad" ]:
		assert not wid.set(testwid), f"test_uuid_is_valid passed bad workspace ID'{testwid}'"
		assert not wid.is_valid(), f"test_uuid_is_valid passed bad workspace ID '{testwid}'"


if __name__ == '__main__':
	test_maddress_set()
	test_userid()
	test_domain()
	test_uuid()
