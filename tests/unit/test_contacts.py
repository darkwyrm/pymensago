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
		'Public': {
			'Name': { 'Given':'Richard', 'Family':'Brannan'},
			'Gender': 'Male',
		'Website': 'https://www.example.com',
		'Mensago': { 'UserID':'cavs4life', 'Domain':'example.com' },
		},
		'Private': {
			'Phone': { 'Mobile':'555-555-1234' },
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
		'Public': {
			'Name': { 'Given':'Richard', 'Family':'Brannan'},
			'Gender': 'Male',
			'Website': 'https://www.example.com',
			'Mensago': { 'UserID':'cavs4life', 'Domain':'example.com' },
		},
		'Private': {
			'Phone': { 'Mobile':'555-555-1234' },
		},
		'Secret': {},
		'Annotations': {}
	}, 'test_contact_import: merge test failed'
	
	status = contact1.merge({'Public':{'Website':'https://test.example.com'}}, True)
	assert not status.error(), f"{funcname()}: contact merge #2 failed"
	assert contact1['Public']['Website'] == 'https://test.example.com', 'clobber test failed'


def test_contact_setphoto():
	'''Tests the Contact class' setphoto capabilities'''
	imgfolder = os.path.join(os.path.dirname(os.path.realpath(__file__)),'images')
	
	contact1 = contacts.Contact()
	status = contact1.setphoto(os.path.join(imgfolder, 'toolarge.png'), 'Public')
	assert status.error() == ErrBadData, 'contact_setphoto failed to handle a too-large photo'

	status = contact1.setphoto(os.path.join(imgfolder, 'toconvert.gif'), 'Public')
	assert not status.error(), 'contact_setphoto failed to handle a GIF'
	assert contact1['Public']['Photo']['Mime'] == 'image/webp', \
		'contact_setphoto failed to convert a GIF'

	status = contact1.setphoto(os.path.join(imgfolder, 'testpic.jpg'), 'Public')
	assert not status.error(), 'contact_setphoto failed to handle a JPEG'
	assert contact1['Public']['Photo']['Mime'] == 'image/jpeg', \
		'contact_setphoto failed to set a JPEG'


def test_contact_to_string():
	'''Tests the pretty-printing of a Contact'''
	c = contacts.Contact({
		'Header' : {
			'Version': '1.0',
			'EntityType': 'individual'
		},
		'Public': {
			'Name': { 'Given':'Richard', 'Family':'Brannan'},
			'Gender': 'Male',
			'Website': 'https://www.example.com',
			'Mensago': { 'UserID':'cavs4life', 'Domain':'example.com' },
		},
		'Private': {
			'Phone': { 'Mobile':'555-555-1234' },
		},
		'Secret': {},
		'Annotations': {}
	})
	
	print(c.to_string('Private'))

if __name__ == '__main__':
	test_contact_import()
	test_contact_setphoto()
	test_contact_to_string()
