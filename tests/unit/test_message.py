import inspect

import pymensago.mdate as mdate
from pymensago.messages import Message
import pymensago.utils as utils

def funcname() -> str: 
	frames = inspect.getouterframes(inspect.currentframe())
	return frames[1].function


def test_message_asstring():
	'''Tests the Message.as_string() method'''

	current_time = mdate.now()
	
	msg = Message()
	msg.id = utils.UUID('11111111-1111-1111-1111-111111111111')
	msg.sender = utils.WAddress('22222222-2222-2222-2222-222222222222/example.com')
	msg.recipient = utils.WAddress('33333333-3333-3333-3333-333333333333/example.com')
	msg.time = current_time
	msg.thread_id = utils.UUID('44444444-4444-4444-4444-444444444444')
	msg.subject = 'Re: This is a Test'
	msg.body = "This is just a test message.\n\nYAY"

	# We're going to skip images in the message, but we will exercise the attachment code
	msg.attachments = [{
		'Name' : 'testattachment.txt',
		'Type' : 'text/plain',

		# The message 'This is a test attachment. Nothing special, really.\n\n'. Attachments are
		# expected to be base85 encoded. It seems silly to encode plain text, but this requirement
		# prevents the need for escaping to ensure that the text doesn't break the JSON format
		'Data' : r'RA^~)AZc?TVIXv6b95kKbaY{3Xl-R~bS@xHZ**vBZf78KaAjj@VQefQa%Ev`Y<VsU3I'
		
	}]

	msgstr = msg.as_string()
	expected_string = "Message ID: 11111111-1111-1111-1111-111111111111\n" \
		"Sender: 22222222-2222-2222-2222-222222222222/example.com\n" \
		"Recipient: 33333333-3333-3333-3333-333333333333/example.com\n" \
		f"Date: {current_time.as_string()}\n" \
		"Thread ID: 44444444-4444-4444-4444-444444444444\n" \
		"Subject: Re: This is a Test\n" \
		"Body:\n" \
		"This is just a test message.\n\nYAY\n\n" \
		"Attachments:\n" \
		"  testattachment.txt, ~53 bytes"
	assert msgstr == expected_string, f"{expected_string}\n\n{msgstr}\n\n" + \
		f"{funcname()}: String generated did not match expected"
