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
	status = contact1.set_user_field('Photo', os.path.join(imgfolder, 'toolarge.png'))
	assert status.error() == ErrBadData, 'contact_setphoto failed to handle a too-large photo'

	status = contact1.set_user_field('Photo', os.path.join(imgfolder, 'toconvert.gif'))
	assert not status.error(), 'contact_setphoto failed to handle a GIF'
	assert contact1['Photo']['Mime'] == 'image/webp', \
		'contact_setphoto failed to convert a GIF'

	status = contact1.set_user_field('Photo', os.path.join(imgfolder, 'testpic.jpg'))
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


def test_delete_user_field():
	'''Tests the method delete_user_field'''
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
	status = c.delete_user_field('Anniversary')
	assert not status.error(), f"{funcname()}: subtest #1 returned an error"
	assert 'Anniversary' not in c.fields, f"{funcname()}: subtest #1 failed to delete string field"

	# Subtest #2: Try to delete a nonexistent field
	status = c.delete_user_field('Anniversary')
	assert not status.error(), f"{funcname()}: subtest #2 returned an error"

	# Subtest #3: Delete an element of a list field
	status = c.delete_user_field('Nicknames.1')
	assert not status.error(), f"{funcname()}: subtest #3 returned an error"
	assert c.fields['Nicknames'] == ['Rick','Rich'], \
		f"{funcname()}: subtest #3 failed to delete a list field item"
	
	# Subtest #4: Delete an dictionary field element
	status = c.delete_user_field('Website.Mensago')
	assert not status.error(), f"{funcname()}: subtest #4 returned an error"
	assert len(c.fields['Website']) == 1 and 'Personal' in c.fields['Website'], \
		f"{funcname()}: subtest #4 failed to correctly delete a dictionary field item"

	# Subtest #5: Delete a field inside a dictionary list
	status = c.delete_user_field('Phone.0.Preferred')
	assert not status.error(), f"{funcname()}: subtest #5 returned an error"
	assert len(c.fields['Phone']) == 1 and 'Preferred' not in c.fields['Phone'][0], \
		f"{funcname()}: subtest #5 failed to correctly delete a field from a dictionary list item"



def test_set_user_field():
	'''Tests the method set_user_field'''
	c = contacts.Contact({
		'Header' : {
			'Version': '1.0',
			'EntityType': 'individual'
		},
		'GivenName': 'Bob',
		'Annotations': {}
	})

	# Subtest #1: Set a top-level string field
	status = c.set_user_field('GivenName', 'Richard')
	assert not status.error(), f"{funcname()}: subtest #1 returned an error"
	assert 'GivenName' in c.fields, f"{funcname()}: subtest #1 failed to set string field"
	assert c.fields['GivenName'] == 'Richard', f"{funcname()}: subtest #1 field has wrong value"

	# Subtest #2: Try to set a nonexistent field
	status = c.set_user_field('FamilyName', 'Brannan')
	assert not status.error(), f"{funcname()}: subtest #2 returned an error"
	assert 'FamilyName' in c.fields, f"{funcname()}: subtest #2 failed to add a string field"
	assert c.fields['FamilyName'] == 'Brannan', f"{funcname()}: subtest #1 field has wrong value"

	# Subtest #3: Create a list containing one string
	status = c.set_user_field('Categories.-1', 'Friends')
	assert not status.error(), f"{funcname()}: subtest #3 returned an error"
	assert 'Categories' in c.fields and len(c.fields['Categories']) == 1, \
		f"{funcname()}: subtest #3 failed to add a string list"
	assert c.fields['Categories'][0] == 'Friends', f"{funcname()}: subtest #3 field has wrong value"

	# Subtest #4: Append an item to a list
	status = c.set_user_field('Categories.-1', 'Chess')
	assert not status.error(), f"{funcname()}: subtest #4 returned an error"
	assert 'Categories' in c.fields and len(c.fields['Categories']) == 2, \
		f"{funcname()}: subtest #4 failed to append to a string list"
	assert c.fields['Categories'][1] == 'Chess', f"{funcname()}: subtest #4 field has wrong value"

	# Subtest #5: Create a dictionary containing one string
	status = c.set_user_field('Websites.Example', 'https://www.example.com/')
	assert not status.error(), f"{funcname()}: subtest #5 returned an error"
	assert 'Websites' in c.fields and len(c.fields['Websites']) == 1, \
		f"{funcname()}: subtest #5 failed to add a dictionary"
	assert 'Example' in c.fields['Websites'] \
		and c.fields['Websites']['Example'] == 'https://www.example.com/', \
		f"{funcname()}: subtest #5 field has wrong value"

	# Subtest #6: Add an item to a dictionary
	status = c.set_user_field('Websites.Example2', 'https://www.example.net/')
	assert not status.error(), f"{funcname()}: subtest #6 returned an error"
	assert 'Websites' in c.fields and len(c.fields['Websites']) == 2, \
		f"{funcname()}: subtest #5 failed to add to an existing dictionary"
	assert 'Example2' in c.fields['Websites'] \
		and c.fields['Websites']['Example2'] == 'https://www.example.net/', \
		f"{funcname()}: subtest #6 field has wrong value"
	
	# Subtest #7: Create a dictionary of strings inside a list
	status = c.set_user_field('MailingAddresses.0.Label', 'Home')
	assert not status.error(), f"{funcname()}: subtest #7 returned an error"
	assert 'MailingAddresses' in c.fields and len(c.fields['MailingAddresses']) == 1, \
		f"{funcname()}: subtest #7 failed to add a dictionary inside a list"
	assert isinstance(c.fields['MailingAddresses'][0], dict), \
		f"{funcname()}: subtest #7 added the wrong type to a list"
	assert 'Label' in c.fields['MailingAddresses'][0] \
		and c.fields['MailingAddresses'][0]['Label'] == 'Home', \
		f"{funcname()}: subtest #7 field has wrong value"
	
	# Subtest #8: Add a value to a dictionary of strings inside a list
	status = c.set_user_field('MailingAddresses.0.Country', 'United States')
	assert not status.error(), f"{funcname()}: subtest #9 returned an error"
	assert 'MailingAddresses' in c.fields and len(c.fields['MailingAddresses']) == 1, \
		f"{funcname()}: subtest #8 failed to find the dictionary inside a list"
	assert isinstance(c.fields['MailingAddresses'][0], dict), \
		f"{funcname()}: subtest #8 found a non-dictionary inside the list"
	assert 'Country' in c.fields['MailingAddresses'][0] \
		and c.fields['MailingAddresses'][0]['Country'] == 'United States', \
		f"{funcname()}: subtest #8 field has wrong value"

	# Subtest #9: Create a dictionary of strings inside a dictionary
	# This isn't part of the schema, but exists should the schema change to need this type
	status = c.set_user_field('Subtest9.Dict.Test', 'Value9')
	assert not status.error(), f"{funcname()}: subtest #9 returned an error"
	assert 'Subtest9' in c.fields and len(c.fields['Subtest9']) == 1, \
		f"{funcname()}: subtest #9 failed to add a dictionary inside a dictionary"
	assert isinstance(c.fields['Subtest9']['Dict'], dict), \
		f"{funcname()}: subtest #9 added the wrong type to a dictionary"
	assert 'Test' in c.fields['Subtest9']['Dict'] \
		and c.fields['Subtest9']['Dict']['Test'] == 'Value9', \
		f"{funcname()}: subtest #9 field has wrong value"
	
	# Subtest #10: Create a list of strings inside a list
	# This isn't part of the schema, but exists should the schema change to need this type
	status = c.set_user_field('Subtest10.-1.-1', 'Value10')
	assert not status.error(), f"{funcname()}: subtest #10 returned an error"
	assert 'Subtest10' in c.fields and len(c.fields['Subtest10']) == 1, \
		f"{funcname()}: subtest #10 failed to add a dictionary inside a dictionary"
	assert isinstance(c.fields['Subtest10'][0], list), \
		f"{funcname()}: subtest #10 added the wrong type to a list"
	assert len(c.fields['Subtest10'][0]) == 1 \
		and c.fields['Subtest10'][0][0] == 'Value10', \
		f"{funcname()}: subtest #10 field has wrong value"

	# Subtest #11: Create a list of strings inside a dictionary
	# This isn't part of the schema, but exists should the schema change to need this type
	status = c.set_user_field('Subtest11.Dict.-1', 'Value11')
	assert not status.error(), f"{funcname()}: subtest #11 returned an error"
	assert 'Subtest11' in c.fields and len(c.fields['Subtest11']) == 1, \
		f"{funcname()}: subtest #11 failed to add a list inside a dictionary"
	assert isinstance(c.fields['Subtest11']['Dict'], list), \
		f"{funcname()}: subtest #11 added the wrong type to a list"
	assert len(c.fields['Subtest11']['Dict']) == 1 \
		and c.fields['Subtest11']['Dict'][0] == 'Value11', \
		f"{funcname()}: subtest #11 field has wrong value"


def test_get_user_field():
	'''Tests get_user_field()'''
	# TODO: Implement get_user_field() tests


if __name__ == '__main__':
	# test_contact_import()
	# test_contact_setphoto()
	# test_contact_to_string()
	# test_delete_user_field()
	# test_set_user_field()
	test_get_user_field()

