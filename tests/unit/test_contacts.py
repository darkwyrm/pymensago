import pymensago.contacts as contacts

def test_contact_import():
	'''Tests the ability to import a contact into another'''

	# Subtest #1: Merge import
	contact2 = {
		'Name': { 'Given':'Richard', 'Family':'Brannan'},
		'Gender': 'Male',
		'Phone': { 'Mobile':'555-555-1234' },
		'Mensago': { 'UserID':'cavs4life', 'Domain':'example.com' },
		'Website': 'https://www.example.com',
		'ID': '3a4a4f45-f6cb-4e43-8a07-98c949e5b20d'
	}
	
	contact1 = contacts.Contact()
	contact1.merge(contact2)
	assert contact1 == {
		'Version': '1.0',
		'Sensitivity': 'private',
		'EntityType': 'individual',
		'Source': 'owner',
		'Update': 'no',
		'ID': '3a4a4f45-f6cb-4e43-8a07-98c949e5b20d',
		'Name': { 'Given':'Richard', 'Family':'Brannan'},
		'Gender': 'Male',
		'Phone': { 'Mobile':'555-555-1234' },
		'Mensago': { 'UserID':'cavs4life', 'Domain':'example.com' },
		'Website': 'https://www.example.com',
	}, 'test_contact_import: merge test failed'
	contact1.merge({'website':'https://test.example.com'}, True)
	assert contact1['website'] == 'https://test.example.com', 'clobber test failed'


if __name__ == '__main__':
	test_contact_import()
