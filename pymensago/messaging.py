'''Messaging-related code, mostly for message construction'''

import json
import jsonschema
import time

import pymensago.cryptostring as cs
from pymensago.encryption import PublicKey, SecretKey
from pymensago.retval import BadData, BadParameterValue, ExceptionThrown, InternalError, RetVal
from pymensago.utils import MAddress

RequiredDataMissing = 'required data missing'

class Envelope:
	'''The main message container class.'''
	def __init__(self) -> None:
		self.fields = {
			'Version': '1.0',
			'Date': time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()),
			'KeyHash': '',
			'PayloadKey': ''
		}
		self.payload = dict()
		self.msgkey = cs.CryptoString
	
	def __str__(self) -> str:
		'''Converts the object to the task-specific text format for Mensago data files. If there 
		is a problem, an empty string is returned. Internally, this calls marshall(), which is the 
		recommended way of flattening an Envelope instance.'''
		status = self.marshall()
		if status.error():
			return ''
		else:
			return status['envelope']

	def marshall(self) -> RetVal:
		'''Converts the object to the task-specific text format for Mensago data files'''
		
		# We have a lot of validation to do before we can actually generate the string
		if not self.msgkey.is_valid():
			return RetVal(RequiredDataMissing, 'message key missing')
		
		status = cs.validate(self.fields['KeyHash'])
		if status.error():
			return RetVal(InternalError, 'BUG: bad msg key hash')
		
		status = cs.validate(self.fields['PayloadKey'])
		if status.error():
			return RetVal(InternalError, 'BUG: bad payload key')
		
		if self.fields['Version'] != '1.0':
			return RetVal(BadData, 'bad version value')
		
		# Marshall and encrypt the payload. Because the internal structure of the payload varies,
		# we have to assume that the payload is valid. Minimal validation is possible, but largely
		# pointless
		try:
			envstr = json.dumps(self.fields)
		except Exception as e:
			return RetVal(ExceptionThrown, e)
		
		secretkey = SecretKey(self.msgkey)
		paystr = secretkey.encrypt(json.dumps(self.fields).encode())

		return RetVal().set_value('envelope',
					'\n'.join[ 'MENSAGO', envstr, '----------', self.msgkey.prefix, paystr ])
		

	def set_msg_key(self, recipientkey: cs.CryptoString) -> RetVal:
		'''Generates a message-specific key and attaches it to the message in encrypted form'''
		
		if not recipientkey.is_valid():
			return RetVal(BadParameterValue)
		
		pubkey = PublicKey(recipientkey)
		self.msgkey = SecretKey()
		status = pubkey.encrypt(str(self.msgkey).encode())
		if status.error():
			return status
		
		self.fields['PayloadKey'] = status['data']
		self.fields['KeyHash'] = pubkey.pubhash

		return RetVal()


	def set_sender(self, sender: MAddress, recipient: MAddress, orgkey: cs.CryptoString) -> RetVal:
		'''Sets the encrypted sender tag'''
		
		if not (sender.is_valid() and recipient.is_valid() and orgkey.is_valid()):
			return RetVal(BadParameterValue)
		
		try:
			tag = json.dumps({ 'From': sender.as_string(), 'RecipientDomain': recipient.domain })
		except Exception as e:
			return RetVal(BadData, 'JSON marshalling error')

		pubkey = PublicKey(orgkey)
		status = pubkey.encrypt(tag.encode())
		if status.error():
			return status
		
		self.fields['Sender'] = status['data']
		return RetVal()
		

	def set_receiver(self, sender: MAddress, recipient: MAddress, orgkey: cs.CryptoString) -> RetVal:
		'''Sets the encrypted reciver tag'''

		if not (sender.is_valid() and recipient.is_valid() and orgkey.is_valid()):
			return RetVal(BadParameterValue)
		
		try:
			tag = json.dumps({ 'To': recipient.as_string(), 'SenderDomain': sender.domain })
		except Exception as e:
			return RetVal(BadData, 'JSON marshalling error')

		pubkey = PublicKey(orgkey)
		status = pubkey.encrypt(tag.encode())
		if status.error():
			return status
		
		self.fields['Receiver'] = status['data']
		return RetVal()


__DataFileSchema = {
	'title': 'Mensago Data File',
	'description': 'The generic JSON container for all Mensago data files',
	'type': 'object',
	'properties': {
		'Version': { 'type': 'string' },
		'Date': { 'type': 'string' },
		'KeyHash': { 'type': 'string' },
		'PayloadKey': { 'type': 'string' },
		'Receiver': { 'type': 'string' },
		'Sender': { 'type': 'string' },
	},
	'required': [ 'Version', 'Date', 'KeyHash', 'PayloadKey' ],
}

__UserMsgSchema = {
	'title': 'User Message Payload',
	'description': 'The structure of a Mensago user message',
	'type': 'object',
	'properties': {
		'Type': { 'type': 'string' },
		'Version': { 'type': 'string' },
		'From': { 'type': 'string' },
		'To': { 'type': 'string' },
		'Date': { 'type': 'string' },
		'ThreadID': { 'type': 'string' },
		'Subject': { 'type': 'string' },
		'Body': { 'type': 'string' },
		'Images': {
			'type': 'array',
			'items': {
				'type': 'object',
				'properties': {
					'Name': { 'type': 'string' },
					'Type': { 'type': 'string' },
					'Data': { 'type': 'string' },
				},
				'required': [ 'Name', 'Type', 'Data' ]
			}
		},
		'Attachments': {
			'type': 'array',
			'items': {
				'type': 'object',
				'properties': {
					'Name': { 'type': 'string' },
					'Type': { 'type': 'string' },
					'Data': { 'type': 'string' },
				},
				'required': [ 'Name', 'Type', 'Data' ]
			}
		},
	},
	'required': [ 'Type', 'Version', 'From', 'To', 'Date', 'ThreadID', 'Subject', 'Body' ],
}

