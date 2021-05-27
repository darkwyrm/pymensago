import os

import pymensago.contacts as contacts
from pymensago.retval import BadData

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


def test_contact_setphoto():
	'''Tests the Contact class' setphoto capabilities'''
	imgfolder = os.path.join(os.path.dirname(os.path.realpath(__file__)),'images')
	
	contact1 = contacts.Contact()
	status = contact1.setphoto(os.path.join(imgfolder, 'toolarge.png'))
	assert status.error() == BadData, 'contact_setphoto failed to handle a too-large photo'

	status = contact1.setphoto(os.path.join(imgfolder, 'toconvert.gif'))
	assert not status.error(), 'contact_setphoto failed to handle a GIF'
	assert contact1['Photo']['Mime'] == 'image/webp', 'contact_setphoto failed to convert a GIF'

	status = contact1.setphoto(os.path.join(imgfolder, 'testpic.jpg'))
	assert not status.error(), 'contact_setphoto failed to handle a JPEG'
	assert contact1['Photo']['Mime'] == 'image/jpeg', 'contact_setphoto failed to set a JPEG'

if __name__ == '__main__':
	test_contact_import()
	test_contact_setphoto()
