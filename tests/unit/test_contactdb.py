import inspect
import os

from retval import ErrBadData

import pymensago.contact as contact

def funcname() -> str: 
	frames = inspect.getouterframes(inspect.currentframe())
	return frames[1].function


def test_contact_setphoto():
	'''Tests the Contact class' photo setting capabilities'''
	imgfolder = os.path.join(os.path.dirname(os.path.realpath(__file__)),'images')
	
	contact1 = dict()
	status = contact.setphoto(contact1, os.path.join(imgfolder, 'toolarge.png'))
	assert status.error() == ErrBadData, 'contact_setphoto failed to handle a too-large photo'

	status = contact.setphoto(contact1, os.path.join(imgfolder, 'toconvert.gif'))
	assert not status.error(), 'contact_setphoto failed to handle a GIF'
	assert contact1['Photo']['Mime'] == 'image/webp', \
		'contact_setphoto failed to convert a GIF'

	status = contact.setphoto(contact1, os.path.join(imgfolder, 'testpic.jpg'))
	assert not status.error(), 'contact_setphoto failed to handle a JPEG'
	assert contact1['Photo']['Mime'] == 'image/jpeg', \
		'contact_setphoto failed to set a JPEG'


if __name__ == '__main__':
	test_contact_setphoto()

