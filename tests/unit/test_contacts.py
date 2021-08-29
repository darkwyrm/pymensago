import inspect
import os

from retval import ErrBadData

import pymensago.contacts as contacts

def funcname() -> str: 
	frames = inspect.getouterframes(inspect.currentframe())
	return frames[1].function


def test_contact_import():
	'''Tests the ability to import a contact into another'''

	# Subtest #1: Merge import
	contact2 = contacts.Contact({
		'Header' : {
			'Version': '1.0',
			'EntityType': 'individual'
		},
		'GivenName': 'Richard',
		'FamilyName': 'Brannan',
		'Gender': 'Male',
		'Website': { 'Personal':'https://www.example.com' },
		'Phone': [	{	'Label':'Mobile',
						'Number':'555-555-1234' 
					}
				],
		'Mensago': [ 
			{	'Label':'Home',
				'UserID':'cavs4life',
				'Workspace':'f9ccb1f5-85e4-487d-9861-51d371101917',
				'Domain':'example.com'
			}
		]
	})
	
	contact1 = contacts.Contact()
	status = contact1.merge(contact2)
	assert not status.error(), f"{funcname()}: contact merge failed"
	assert contact1.fields == {
		'Header' : {
			'Version': '1.0',
			'EntityType': 'individual'
		},
		'GivenName': 'Richard',
		'FamilyName': 'Brannan',
		'Gender': 'Male',
		'Website': { 'Personal':'https://www.example.com' },
		'Phone': [	{	'Label':'Mobile',
						'Number':'555-555-1234' 
					}
				],
		'Mensago': [
			{	'Label':'Home',
				'UserID':'cavs4life',
				'Workspace':'f9ccb1f5-85e4-487d-9861-51d371101917',
				'Domain':'example.com'
			}
		],
		'Annotations': {}
	}, 'test_contact_import: merge test failed'
	
	status = contact1.merge({'Website':'https://test.example.com'}, True)
	assert not status.error(), f"{funcname()}: contact merge #2 failed"
	assert contact1['Website'] == 'https://test.example.com', 'clobber test failed'


def test_contact_setphoto():
	'''Tests the Contact class' photo setting capabilities'''
	imgfolder = os.path.join(os.path.dirname(os.path.realpath(__file__)),'images')
	
	contact1 = contacts.Contact()
	status = contact1.set_field('Photo', os.path.join(imgfolder, 'toolarge.png'))
	assert status.error() == ErrBadData, 'contact_setphoto failed to handle a too-large photo'

	status = contact1.set_field('Photo', os.path.join(imgfolder, 'toconvert.gif'))
	assert not status.error(), 'contact_setphoto failed to handle a GIF'
	assert contact1['Photo']['Mime'] == 'image/webp', \
		'contact_setphoto failed to convert a GIF'

	status = contact1.set_field('Photo', os.path.join(imgfolder, 'testpic.jpg'))
	assert not status.error(), 'contact_setphoto failed to handle a JPEG'
	assert contact1['Photo']['Mime'] == 'image/jpeg', \
		'contact_setphoto failed to set a JPEG'


def test_contact_to_string():
	'''Tests the pretty-printing of a Contact'''
	c = contacts.Contact({
		'Header' : {
			'Version': '1.0',
			'EntityType': 'individual'
		},
		'GivenName': 'Richard',
		'FamilyName': 'Brannan',
		'Gender': 'Male',
		'Website': { 'Personal':'https://www.example.com' },
		'Phone': [	{	'Label':'Mobile',
						'Number':'555-555-1234' 
					}
				],
		'Birthday': '19750415',
		'Anniversary': '0714',
		'Mensago': [
			{	'Label':'Home',
				'UserID':'cavs4life',
				'Workspace':'f9ccb1f5-85e4-487d-9861-51d371101917',
				'Domain':'example.com'
			}
		],
		'Annotations': {}
	})
	
	expected_string = '\n'.join(['Individual','Name: Richard Brannan','Gender: Male',
		'Phone (Mobile): 555-555-1234','Mensago (Home): cavs4life/example.com',
		'Anniversary: July 14','Birthday: April 15 1975',
		'Website (Personal): https://www.example.com'])
	out_string = c.to_string()
	assert out_string == expected_string, "to_string() output didn't match expected"


def test_delete_field():
	'''Tests the method delete_field'''
	c = contacts.Contact({
		'Header' : {
			'Version': '1.0',
			'EntityType': 'individual'
		},
		'GivenName': 'Richard',
		'FamilyName': 'Brannan',
		'Nicknames' : [ 'Rick', 'Ricky', 'Rich'],
		'Gender': 'Male',
		'Website': { 'Personal':'https://www.example.com',
					'Mensago':'https://mensago.org' },
		'Phone': [	{	'Label':'Mobile',
						'Number':'555-555-1234',
						'Preferred':'yes'
					}
				],
		'Birthday': '19750415',
		'Anniversary': '0714',
		'Mensago': [
			{	'Label':'Home',
				'UserID':'cavs4life',
				'Workspace':'f9ccb1f5-85e4-487d-9861-51d371101917',
				'Domain':'example.com'
			},
			{	'Label':'Work',
				'UserID':'rbrannan',
				'Workspace':'9015c2ea-2d02-491b-aa1f-4d536cfc4878',
				'Domain':'contoso.com'
			}
		],
		'Annotations': {}
	})

	# Subtest #1: Delete a top-level string field
	status = c.delete_field('Anniversary')
	assert not status.error(), f"{funcname()}: subtest #1 returned an error"
	assert 'Anniversary' not in c.fields, f"{funcname()}: subtest #1 failed to delete string field"

	# Subtest #2: Try to delete a nonexistent field
	status = c.delete_field('Anniversary')
	assert not status.error(), f"{funcname()}: subtest #2 returned an error"

	# Subtest #3: Delete an element of a list field
	status = c.delete_field('Nicknames.1')
	assert not status.error(), f"{funcname()}: subtest #3 returned an error"
	assert c.fields['Nicknames'] == ['Rick','Rich'], \
		f"{funcname()}: subtest #3 failed to delete a list field item"
	
	# Subtest #4: Delete a dictionary field element
	status = c.delete_field('Website.Mensago')
	assert not status.error(), f"{funcname()}: subtest #4 returned an error"
	assert len(c.fields['Website']) == 1 and 'Personal' in c.fields['Website'], \
		f"{funcname()}: subtest #4 failed to correctly delete a dictionary field item"

	# Subtest #5: Delete a field inside a dictionary list
	status = c.delete_field('Phone.0.Preferred')
	assert not status.error(), f"{funcname()}: subtest #5 returned an error"
	assert len(c.fields['Phone']) == 1 and 'Preferred' not in c.fields['Phone'][0], \
		f"{funcname()}: subtest #5 failed to correctly delete a field from a dictionary list item"


def test_get_field():
	'''Tests get_field()'''
	c = contacts.Contact({
		'Header' : {
			'Version': '1.0',
			'EntityType': 'individual'
		},
		'GivenName': 'Richard',
		'FamilyName': 'Brannan',
		'Nicknames' : [ 'Rick', 'Ricky', 'Rich'],
		'Gender': 'Male',
		'Website': { 'Personal':'https://www.example.com',
					'Mensago':'https://mensago.org' },
		'Phone': [	{	'Label':'Mobile',
						'Number':'555-555-1234',
						'Preferred':'yes'
					}
				],
		'Birthday': '19750415',
		'Anniversary': '0714',
		'Mensago': [
			{	'Label':'Home',
				'UserID':'cavs4life',
				'Workspace':'f9ccb1f5-85e4-487d-9861-51d371101917',
				'Domain':'example.com'
			},
			{	'Label':'Work',
				'UserID':'rbrannan',
				'Workspace':'9015c2ea-2d02-491b-aa1f-4d536cfc4878',
				'Domain':'contoso.com'
			}
		],
		'Annotations': {}
	})

	# Subtest #1: get a top-level string field
	status = c.get_field('Anniversary')
	assert not status.error(), f"{funcname()}: subtest #1 returned an error"
	assert status['value'] == '0714', f"{funcname()}: subtest #1 failed to get string field"

	# Subtest #2: try to get a nonexistent field
	status = c.get_field('ThisFieldDoesntExist')
	assert status.error(), f"{funcname()}: subtest #2 status OK for a nonexistent field"

	# Subtest #3: get an element of a list field
	status = c.get_field('Nicknames.1')
	assert not status.error(), f"{funcname()}: subtest #3 returned an error"
	assert status['value'] == 'Ricky', f"{funcname()}: subtest #3 failed to get list element"
	
	# Subtest #4: get a dictionary field element
	status = c.get_field('Website.Mensago')
	assert not status.error(), f"{funcname()}: subtest #4 returned an error"
	assert status['value'] == 'https://mensago.org', \
		f"{funcname()}: subtest #4 failed to get dictionary element"

	# Subtest #5: get a field inside a dictionary list
	status = c.get_field('Phone.0.Preferred')
	assert not status.error(), f"{funcname()}: subtest #5 returned an error"
	assert status['value'] == 'yes', f"{funcname()}: subtest #5 failed to get dictionary element"
		


if __name__ == '__main__':
	# test_contact_import()
	test_contact_setphoto()
	# test_contact_to_string()
	# test_delete_field()
	# test_get_field()

