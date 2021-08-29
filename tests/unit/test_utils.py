'''Implements tests for the utils module'''

import pymensago.utils as utils

def test_maddress_set():
	'''Tests MAddress.Set'''

	test_addresses = [
		'🐈🐈🐈4life/example.com',
		'5a56260b-aa5c-4013-9217-a78f094432c3/example.com',
	]
	addr = utils.MAddress()
	for testaddr in test_addresses:
		assert not addr.set(testaddr).error(), \
			f"MAddress.Set() failed to pass valid Mensago address {testaddr}"

	bad_addresses = [
		'has spaces/example.com',
		'has_a_"/example.com',
		'\\not_allowed/example.com',
		'/example.com',
		'5a56260b-aa5c-4013-9217-a78f094432c3/example.com/example.com',
		'5a56260b-aa5c-4013-9217-a78f094432c3',
		('a'*65) + '/example.com',
	]
	for testaddr in bad_addresses:
		assert addr.set(testaddr).error(), \
			f"MAddress.Set() passed invalid Mensago address {testaddr}"


def test_waddress_set():
	'''Tests WAddress.Set'''

	addr = utils.WAddress()
	assert not addr.set('5a56260b-aa5c-4013-9217-a78f094432c3/example.com').error(), \
		f"WAddress.Set() failed to pass valid workspace address"

	bad_addresses = [
		'/example.com',
		'5a56260b-aa5c-4013-9217-a78f094432c3/example.com/example.com',
		'5a56260b-aa5c-4013-9217-a78f094432c3',
	]
	for testaddr in bad_addresses:
		assert addr.set(testaddr).error(), \
			f"WAddress.Set() passed invalid Mensago address {testaddr}"


def test_userid():
	'''Tests UserID.set() and is_valid()'''

	uid = utils.UserID()
	assert uid.is_empty(), 'test_userid - unset userid is not empty'
	for testid in [ "GoodID", "alsogoooood", "🐧", "ಅಎಇ", "11111111-1111-1111-1111-111111111111" ]:
		
		assert uid.set(testid) == testid.strip().casefold(), \
			f"test_userid - set failed good user ID '{testid}'"
		assert uid.is_valid(), f"test_userid failed good user ID '{testid}'"
		
		if testid == "11111111-1111-1111-1111-111111111111":
			assert uid.is_wid(), f"test_userid - is_wid test failed for {testid}"
		else:
			assert not uid.is_wid(), f"test_userid - is_wid test failed for {testid}"
		
		assert uid.as_string() == testid.strip().casefold(), \
			f"test_userid - as_string failed'{testid}'"

	for testid in [ "a bad id", "also/bad" ]:
		assert not uid.set(testid), f"test_userid - set passed bad user ID '{testid}'"
		assert not uid.is_valid(), f"test_userid - is_valid passed bad user ID '{testid}'"


def test_domain():
	'''Tests Domain.set() and is_valid()'''

	dom = utils.Domain()
	assert dom.is_empty(), 'test_domain - unset domain is not empty'
	for testdom in [ "foo-bar.baz.com", "FOO.bar.com " ]:
		assert dom.set(testdom) == testdom.strip().casefold(), \
			f"test_domain_set failed good domain '{testdom}'"
		
		assert dom.is_valid(), f"test_domain failed good domain '{testdom}'"
		
		assert dom.as_string() == testdom.strip().casefold(), \
			f"test_domain - as_string failed '{testdom}'"

	for testdom in [ "a bad-id.com", "also_bad.org" ]:
		assert not dom.set(testdom), f"test_domain_set passed bad domain'{testdom}'"
		assert not dom.is_valid(), f"test_domain passed bad domain '{testdom}'"


def test_uuid():
	'''Tests UUID.set() and is_valid()'''

	wid = utils.UUID()
	for testwid in [ "11111111-1111-1111-1111-111111111111", 
					" aaaaaaaa-BBBB-1111-1111-111111111111" ]:
		assert wid.set(testwid) == testwid.strip().casefold(), \
			f"test_uuid - set failed good workspace ID '{testwid}'"

		assert wid.is_valid(), f"test_uuid - is_valid failed good workspace ID '{testwid}'"
		
		assert wid.as_string() == testwid.strip().casefold(), \
			f"test_uuid - as_string failed '{testwid}'"

	for testwid in [ "11111111111111111111111111111111", "also_bad" ]:
		assert not wid.set(testwid), f"test_uuid - set passed bad workspace ID'{testwid}'"
		assert not wid.is_valid(), f"test_uuid  - is_valid passed bad workspace ID '{testwid}'"


def test_name():
	'''Tests the Name class methods'''

	name = utils.Name('Corbin', 'Simons', 'Dr.', 'MD', ['James', 'Alexander'])

	assert name.formatted == 'Dr. Corbin James Alexander Simons, MD', \
		f'test_name: full name formatting test failed: {name.formatted}'



if __name__ == '__main__':
	test_maddress_set()
	test_userid()
	test_domain()
	test_uuid()
	test_name()

