'''Messaging-related code, mostly for message construction'''

import json
import time

import pymensago.cryptostring as cs
from pymensago.encryption import PublicKey, SecretKey
from pymensago.retval import BadData, BadParameterValue, RetVal
from pymensago.utils import MAddress

RequiredFieldMissing = 'required field missing'

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
		pass

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
