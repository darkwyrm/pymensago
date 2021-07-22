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
		'Website': 'https://www.example.com',
		'Phone': { 'Mobile':'555-555-1234' },
		'Mensago': { 
			"Home": {
				'UserID':'cavs4life',
				'Workspace':'f9ccb1f5-85e4-487d-9861-51d371101917',
				'Domain':'example.com'
			}
		}
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
		'Website': 'https://www.example.com',
		'Phone': { 'Mobile':'555-555-1234' },
		'Mensago': { 
			"Home": {
				'UserID':'cavs4life',
				'Workspace':'f9ccb1f5-85e4-487d-9861-51d371101917',
				'Domain':'example.com'
			}
		},
		'Annotations': {}
	}, 'test_contact_import: merge test failed'
	
	status = contact1.merge({'Website':'https://test.example.com'}, True)
	assert not status.error(), f"{funcname()}: contact merge #2 failed"
	assert contact1['Website'] == 'https://test.example.com', 'clobber test failed'


def test_contact_setphoto():
	'''Tests the Contact class' setphoto capabilities'''
	imgfolder = os.path.join(os.path.dirname(os.path.realpath(__file__)),'images')
	
	contact1 = contacts.Contact()
	status = contact1.setphoto(os.path.join(imgfolder, 'toolarge.png'))
	assert status.error() == ErrBadData, 'contact_setphoto failed to handle a too-large photo'

	status = contact1.setphoto(os.path.join(imgfolder, 'toconvert.gif'))
	assert not status.error(), 'contact_setphoto failed to handle a GIF'
	assert contact1['Photo']['Mime'] == 'image/webp', \
		'contact_setphoto failed to convert a GIF'

	status = contact1.setphoto(os.path.join(imgfolder, 'testpic.jpg'))
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
		'Website': 'https://www.example.com',
		'Phone': { 'Mobile':'555-555-1234' },
		'Birthday': '19750415',
		'Anniversary': '0714',
		'Mensago': { 
			"Home": {
				'UserID':'cavs4life',
				'Workspace':'f9ccb1f5-85e4-487d-9861-51d371101917',
				'Domain':'example.com'
			}
		},
		'Annotations': {}
	})
	
	expected_string = '\n'.join(['Individual','Name: Richard Brannan','Gender: Male',
		'Phone (Mobile): 555-555-1234','Mensago (Home): cavs4life/example.com',
		'Anniversary: July 14','Birthday: April 15 1975','Website: https://www.example.com'])
	out_string = c.to_string()
	assert out_string == expected_string, "to_string() output didn't match expected"


if __name__ == '__main__':
	test_contact_import()
	test_contact_setphoto()
	test_contact_to_string()
