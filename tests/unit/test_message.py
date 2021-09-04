import inspect

from pymensago.mdate import MDateTime
from pymensago.messages import Message
import pymensago.utils as utils

def funcname() -> str: 
	frames = inspect.getouterframes(inspect.currentframe())
	return frames[1].function

def test_message_tostring():
	'''Tests the Message.to_string() method'''

	msg = Message()
	msg.id.generate()
	msg.sender = utils.WAddress('22222222-2222-2222-2222-222222222222/example.com')
	msg.recipient = utils.WAddress('33333333-3333-3333-3333-333333333333/example.com')
	msg.time = MDateTime().now()
	msg.thread_id.generate()
	msg.subject = 'Re: This is a Test'
	msg.body = "This is just a test message.\n\nYAY"

	# We're going to skip images in the message, but we will exercise the attachment code
	msg.attachments = [{
		'Name' : 'testattachment.txt',
		'Type' : 'text/plain',
		'Data' : 'This is a test attachment. Nothing special, really.\n\n'
	}]

	msgstr = msg.to_string()
	print(msgstr)


if __name__ == '__main__':
	test_message_tostring()
