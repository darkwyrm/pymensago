'''This module contains the classes representing the entry blocks which are chained together in a 
keycard.'''

import base64
import calendar
import datetime
import hashlib
import os
import re
import sqlite3
import time

import blake3
import nacl.public
import nacl.signing
from pycryptostring import CryptoString, is_cryptostring
from retval import ErrBadType, RetVal, ErrBadData, ErrBadValue, ErrExists, ErrNotFound

from pymensago.encryption import EncryptionPair, SigningPair, Base85Encoder
from pymensago.hash import blake2hash

FeatureNotAvailable = 'FeatureNotAvailable'
UnsupportedKeycardType = 'UnsupportedKeycardType'
UnsupportedHashType = 'UnsupportedHashType'
UnsupportedEncryptionType = 'UnsupportedEncryptionType'
InvalidKeycard = 'InvalidKeycard'
InvalidEntry = 'InvalidEntry'
InvalidHash = 'InvalidHash'
HashMismatch = 'HashMismatch'

# These three return codes are associated with a second field, 'field', which indicates which
# signature field is related to the error
NotCompliant = 'NotCompliant'
RequiredFieldMissing = 'RequiredFieldMissing'
SignatureMissing = 'SignatureMissing'

SIGINFO_HASH = 1
SIGINFO_SIGNATURE = 2

class ComplianceException(Exception):
	'''Custom exception for spec compliance failures'''

def _is_valid_date(m : int, d : int, y : int, hours=-1, minutes=-1, seconds=-1) -> bool:
	'''Returns false if the date is invalid for this context'''
	if y < 2020 or m < 1 or m > 12 or d < 1:
		return False

	if m == 2:
		if ((y%4 == 0 and y%100 != 0) and d > 29):
			return False
		if d > 28:
			return False
	elif m in [1, 3, 5, 7, 8, 10, 12]:
		if d > 31:
			return False
	elif d > 30:
		return False
	
	if hours > 23 or minutes > 59 or seconds > 59:
		return False

	return True


class EntryBase:
	'''Base class for all code common to org and user cards'''
	def __init__(self):
		self.fields = dict()
		self.field_names = list()
		self.required_fields = list()
		self.type = ''
		self.signatures = dict()
		self.signature_info = list()
		self.prev_hash = ''
		self.hash = ''
	
	def __contains__(self, key):
		return key in self.fields

	def __delitem__(self, key):
		del self.fields[key]

	def __getitem__(self, key):
		return self.fields[key]
	
	def __iter__(self):
		return self.fields.__iter__()
	
	def __setitem__(self, key, value):
		self.fields[key] = value
	
	def __str__(self):
		return self.make_bytestring(-1).decode()
	
	def __validate_integer(self, fieldname : str, minVal=-1, maxVal=-1) -> RetVal:
		'''Validates a non-negative integer. Checks range of value if supplied.'''
		if fieldname not in self.fields.keys():
			return RetVal(ErrBadValue, f"field {fieldname} does not exist")
		
		m = re.match(r'^[0-9]+$', self.fields[fieldname])
		if not m:
			return RetVal(ErrBadData, 'bad field value')
		
		intValue = 0
		try:
			intValue = int(m[0])
		except:
			return RetVal(ErrBadData, 'bad field value')
		
		if minVal != -1 and intValue < minVal:
			return RetVal(ErrBadData, f"field {fieldname} less than minimum")

		if maxVal != -1 and intValue > maxVal:
			return RetVal(ErrBadData, f"field {fieldname} greater than maximum")
		
		return RetVal()

	def __validate_common_data(self) -> RetVal:
		'''Checks the validity of data fields common to orgs and users'''
		
		# Required field: Index
		outStatus = self.__validate_integer('Index', 1)
		if outStatus.error():
			return outStatus
		
		# Field: Name, required for orgs, optional for users
		# Although mostly freeform, the Name field has a couple requirements:
		# 1) at least 1 printable character
		# 2) No more than 64 code points
		if 'Name' in self.fields.keys():
			m = re.match(r'\w+', self.fields['Name'])
			if not m or len(self.fields['Name']) >= 64:
				return RetVal(ErrBadData, 'bad name value')

		# Required field: Time to Live
		outStatus = self.__validate_integer('Time-To-Live', 1, 30)
		if outStatus.error():
			return outStatus

		# is_timestamp_valid() validates both of the required fields Timestamp and Expires
		return self.is_timestamp_valid()

	def __validate_org_data(self) -> RetVal:
		'''Checks the validity of all data fields'''
		
		if self.type != 'Organization':
			return RetVal(ErrBadData, 'invalid entry type %s' % self.type)
		
		outStatus = self.__validate_common_data()
		if outStatus.error():
			return outStatus

		# Required field: Admin address
		m = re.match(r'^[\da-fA-F]{8}-?[\da-fA-F]{4}-?[\da-fA-F]{4}-?[\da-fA-F]{4}'
			r'-?[\da-fA-F]{12}/([a-zA-Z0-9]+\.)+[a-zA-Z0-9]+$', self.fields['Contact-Admin'])
		if not m:
			return RetVal(ErrBadData, 'bad admin contact address')

		# Required fields: Primary Verification Key, Encryption Key
		# We can't verify the actual key data, but we can at least ensure that it's formatted
		# correctly and we can b85decode the key itself
		for keyfield in ['Primary-Verification-Key', 'Encryption-Key']:
			if not is_cryptostring(self.fields[keyfield]):
				return RetVal(ErrBadData, f"bad key field {keyfield}")
		
		# Optional fields: Support and Abuse addresses
		for contactfield in ['Contact-Support','Contact-Abuse']:
			if contactfield in self.fields.keys():
				m = re.match(r'^[\da-fA-F]{8}-?[\da-fA-F]{4}-?[\da-fA-F]{4}-?[\da-fA-F]{4}'
					r'-?[\da-fA-F]{12}/([a-zA-Z0-9]+\.)+[a-zA-Z0-9]+$',
					self.fields[contactfield])
				if not m:
					return RetVal(ErrBadData, f"bad contact address {contactfield}")
		
		# Optional field: Language
		if 'Language' in self.fields.keys():
			m = re.match(r'^[a-zA-Z]{2,3}(,[a-zA-Z]{2,3})*?$', self.fields['Language'])
			if not m:
				return RetVal(ErrBadData, 'bad language list')

		# Optional field: Secondary Verification Key
		if 'Secondary-Verification-Key' in self.fields.keys():
			if not is_cryptostring(self.fields['Secondary-Verification-Key']):
				return RetVal(ErrBadData, 'bad secondary verification key')
		
		return RetVal()

	def __validate_user_data(self) -> RetVal:
		'''Checks the validity of all data fields'''
		if self.type != 'User':
			return RetVal(ErrBadData, 'invalid entry type %s' % self.type)
		
		outStatus = self.__validate_common_data()
		if outStatus.error():
			return outStatus

		# Required field: Workspace ID
		m = re.match(r'^[\da-fA-F]{8}-?[\da-fA-F]{4}-?[\da-fA-F]{4}-?[\da-fA-F]{4}'
			r'-?[\da-fA-F]{12}$', self.fields['Workspace-ID'])
		if not m:
			return RetVal(ErrBadData, 'bad workspace ID')

		# Required field: Domain
		# Although mostly freeform, the Name field has a couple requirements:
		m = re.match(r'([a-zA-Z0-9]+\.)+[a-zA-Z0-9]+', self.fields['Domain'])
		if not m or len(self.fields['Domain']) >= 64:
			return RetVal(ErrBadData, 'bad domain value')

		# Required fields: Contact Request Verification Key, Contact Request Encryption Key,
		#	Encryption-Key, Verification-Key
		for keyfield in ['Contact-Request-Verification-Key',
						 'Contact-Request-Encryption-Key',
						 'Encryption-Key',
						 'Verification-Key']:
			if not is_cryptostring(self.fields[keyfield]):
				return RetVal(ErrBadData, f"bad key field {keyfield}")

		# Optional field: User ID
		if 'User-ID' in self.fields.keys():
			if re.findall(r'[\\\/\s"]', self.fields['User-ID']) or \
				len(self.fields['User-ID']) >= 64:
				return RetVal(ErrBadData, 'bad user id value')
			
		return RetVal()

	def get_hash(self, algorithm: str) -> RetVal:
		'''Generates a hash containing the expected signatures and the previous hash, if it exists. 
		The supported hash algorithms are 'BLAKE2-256', 'BLAKE3-256', 'SHA-256', and 'SHA3-256'.'''  
		if algorithm not in ['BLAKE3-256','BLAKE2B-256','SHA-256','SHA3-256']:
			return RetVal(UnsupportedHashType, f'{algorithm} not a supported hash algorithm')
		
		hash_string = CryptoString()
		hash_level = -1
		for sig in self.signature_info:
			if sig['type'] == SIGINFO_HASH:
				hash_level = sig['level']
				break
		assert hash_level > 0, "BUG: signature_info missing hash entry"
		
		hasher = None
		if algorithm == 'BLAKE3-256':
			hasher = blake3.blake3() # pylint: disable=c-extension-no-member
			hasher.update(self.make_bytestring(hash_level))
			hash_string.data = base64.b85encode(hasher.digest()).decode()
		else:
			hasher = None
			if algorithm == 'BLAKE2B-256':
				hasher = hashlib.blake2b(digest_size=32)
			elif algorithm == 'SHA-256':
				hasher = hashlib.sha256()
			else:
				hasher = hashlib.sha3_256()
			hasher.update(self.make_bytestring(hash_level))
			hash_string.data = base64.b85encode(hasher.digest()).decode()
		
		hash_string.prefix = algorithm
		return RetVal().set_value('hash', str(hash_string))
	
	def is_data_compliant(self) -> RetVal:
		'''Performs basic compliancy checks for the data fields only'''

		if self.type not in [ 'User', 'Organization']:
			return RetVal(UnsupportedKeycardType, f"unsupported card type {self.type}")
		
		# Check for existence of required fields
		for field in self.required_fields:
			if field not in self.fields or not self.fields[field]:
				return RetVal(RequiredFieldMissing, f"missing field {field}")
		
			if field != field.strip():
				return RetVal(ErrBadData, f"leading/trailing whitespace in field {field}")
		
		if self.type == 'User':
			return self.__validate_user_data()
			
		return self.__validate_org_data()

	def is_compliant(self) -> RetVal:
		'''Checks the fields to ensure that it meets spec requirements. If a field causes it 
		to be noncompliant, the noncompliant field is also returned'''
		status = self.is_data_compliant()
		if status.error():
			return status

		# Ensure signature compliance
		for info in self.signature_info:
			if info['type'] == SIGINFO_HASH:
				if not self.hash:
					return RetVal(SignatureMissing, 'Hash')
				else:
					continue
			
			if info['optional']:
				# Optional signatures, if present, may not be empty
				if info['name'] in self.signatures and not self.signatures[info['name']]:
					return RetVal(SignatureMissing, '%s-Signature' % info['name'])
			else:
				if info['name'] not in self.signatures or not self.signatures[info['name']]:
					return RetVal(SignatureMissing, '%s-Signature' % info['name'])

		return RetVal()
	
	def is_timestamp_valid(self) -> RetVal:
		'''Checks the validity of the timestamp. As a side effect, it checks the validity of the 
		expiration date field, but it does not check if the entry is actually expired'''
		m = re.match(r'^([0-9]{4})([0-9]{2})([0-9]{2})$', self.fields['Expires'])
		if not m or not _is_valid_date(int(m[2]), int(m[3]), int(m[1])):
			return RetVal(ErrBadData, 'bad expiration date')
		expire_time = datetime.datetime(int(m[1]), int(m[2]), int(m[3]),
			tzinfo=datetime.timezone(datetime.timedelta(hours=0)))

		m = re.match(r'^([0-9]{4})([0-9]{2})([0-9]{2})T([0-9]{2})([0-9]{2})([0-9]{2})Z$',
			self.fields['Timestamp'])
		if not m or not _is_valid_date(int(m[2]), int(m[3]), int(m[1]), 
			int(m[4]), int(m[5]), int(m[6])):
			return RetVal(ErrBadData, 'bad timestamp')
		timestamp_time = datetime.datetime(int(m[1]), int(m[2]), int(m[3]),
			int(m[4]), int(m[5]), int(m[6]),
			tzinfo=datetime.timezone(datetime.timedelta(hours=0)))

		if timestamp_time > expire_time:
			return RetVal(ErrBadData, 'bad timestamp')
		
		return RetVal()

	def is_expired(self) -> RetVal:
		'''Checks if the entry is expired'''
		if 'Expires' not in self.fields.keys():
			return RetVal(RequiredFieldMissing, 'Expires')
		
		m = re.match(r'^([0-9]{4})([0-9]{2})([0-9]{2})$', self.fields['Expires'])
		if not m or not _is_valid_date(int(m[2]), int(m[3]), int(m[1])):
			return RetVal(ErrBadData, 'bad expiration date')
		expire_time = datetime.datetime(int(m[1]), int(m[2]), int(m[3]),
			tzinfo=datetime.timezone(datetime.timedelta(hours=0)))

		if datetime.datetime.now() > expire_time:
			return RetVal(ErrBadData, 'entry is expired')

		return RetVal()

	def get_signature(self, sigtype: str) -> RetVal:
		'''Retrieves the requested signature and type'''
		if sigtype not in self.signatures:
			return RetVal(ErrNotFound, sigtype)
		
		if len(self.signatures[sigtype]) < 1:
			return RetVal(SignatureMissing, sigtype)

		parts = self.signatures[sigtype].split(':')
		if len(parts) == 1:
			return RetVal().set_value(SIGINFO_SIGNATURE, parts[0])
		
		if len(parts) == 2:
			return RetVal().set_values({
				'algorithm' : parts[0],
				SIGINFO_SIGNATURE : parts[1]
			})
		
		return RetVal(ErrBadData, self.signatures[sigtype])
	
	def make_bytestring(self, signature_level : int) -> bytes:
		'''Creates a byte string from the fields in the keycard. Because this doesn't use join(), 
		it is not affected by Python's line ending handling, which is critical in ensuring that 
		signatures are not invalidated. The parameter, signature_level, specifies how many 
		signatures to include. Passing a negative number specifies all signatures.'''
		lines = list()
		if self.type:
			lines.append(b':'.join([b'Type', self.type.encode()]))

		for field in self.field_names:
			if field in self.fields and self.fields[field]:
				lines.append(b':'.join([field.encode(), self.fields[field].encode()]))
		
		if signature_level > len(self.signature_info) or signature_level < 0:
			signature_level = self.signature_info[-1]['level']
		
		sig_names = [x['name'] for x in self.signature_info]
		for i in range(signature_level):
			name = sig_names[i]
			if self.signature_info[i]['type'] == SIGINFO_HASH:
				if self.prev_hash:
					lines.append(b'Previous-Hash:%s' % self.prev_hash.encode())
				if self.hash:
					lines.append(b'Hash:%s' % self.hash.encode())
			elif name in self.signatures and self.signatures[name]:
				lines.append(b''.join([name.encode() + b'-Signature:',
								self.signatures[name].encode()]))

		lines.append(b'')
		return b'\r\n'.join(lines)
	
	def save(self, path : str, clobber = False) -> RetVal:
		'''Saves to the specified path, forcing CRLF line endings to prevent any weird behavior 
		caused by line endings invalidating signatures.'''

		if not path:
			return RetVal(ErrBadValue, 'path may not be empty')
		
		if os.path.exists(path) and not clobber:
			return RetVal(ErrExists)
		
		try:
			with open(path, 'wb') as f:
				f.write(self.make_bytestring(-1))
		
		except Exception as e:
			return RetVal.wrap_exception(e)

		return RetVal()
	
	def set_field(self, field_name: str, field_value: str):
		'''Takes a dictionary of fields to be assigned to the object. Any field which is not part 
		of the official spec is assigned but otherwise ignored.'''
		self.fields[field_name] = field_value
		
		# Any kind of editing invalidates the signatures and hash
		self.signatures = dict()
		self.hash = ''

	def set_fields(self, fields: dict) -> RetVal:
		'''Takes a dictionary of fields to be assigned to the object. Any field which is not part 
		of the official spec is assigned but otherwise ignored.'''
		self.signatures = dict()
		self.hash = ''

		for k,v in fields.items():
			if k.endswith('Signature'):
				sigparts = k.split('-', 1)
				if sigparts[0] not in [ 'Custody', 'User', 'Organization', 'Entry' ]:
					return RetVal(ErrBadData, 'bad signature line %s' % sigparts[0])
				self.signatures[sigparts[0]] = v
			else:
				self.fields[k] = v
		
		return RetVal()
	
	def set(self, data: bytes) -> RetVal:
		'''Sets the object's information from a bytestring'''

		try:
			rawstring = data.decode()
		except Exception as e:
			return RetVal.wrap_exception(e)
		
		lines = rawstring.split('\r\n')
		for line in lines:
			if not line:
				continue

			stripped = line.strip()
			if not stripped:
				continue

			parts = stripped.split(':', 1)
			if len(parts) != 2:
				return RetVal(ErrBadData, line)
			
			if parts[0] == 'Type':
				if parts[1] != self.type:
					return RetVal(ErrBadData, "can't use %s data on a %s entry" % (parts[0], self.type))
			
			elif parts[0].endswith('Signature'):
				sigparts = parts[0].split('-', 1)
				if sigparts[0] not in [ 'Custody', 'User', 'Organization', 'Entry' ]:
					return RetVal(ErrBadData, 'bad signature line %s' % sigparts[0])
				self.signatures[sigparts[0]] = parts[1]
			
			else:
				self.fields[parts[0]] = parts[1]
			
		return RetVal()

	def set_expiration(self, numdays=-1) -> RetVal:
		'''Sets the expiration field to the number of days specified after the current date'''
		if numdays < 0:
			if self.type == 'Organization':
				numdays = 365
			elif self.type == 'User':
				numdays = 90
			else:
				return RetVal(UnsupportedKeycardType)
		
		# An expiration date can be no longer than 3 years
		if numdays > 1095:
			numdays = 1095
		
		expiration = datetime.datetime.utcnow() + datetime.timedelta(numdays)
		self.fields['Expires'] = expiration.strftime("%Y%m%d")
		return RetVal()

	def sign(self, signing_key: CryptoString, sigtype: str) -> RetVal:
		'''Adds a signature to the  Note that for any change in the keycard fields, this 
		call must be made afterward. Note that successive signatures are deleted, such that 
		updating a User signature will delete the Organization signature which depends on it. The 
		sigtype must be Custody, User, or Organization, and the type is case-sensitive.'''
		if not signing_key.is_valid():
			return RetVal(ErrBadValue, 'signing key')
		
		if signing_key.prefix != 'ED25519':
			return RetVal(UnsupportedEncryptionType, signing_key.prefix)
		
		sig_names = [x['name'] for x in self.signature_info]
		if sigtype not in sig_names:
			return RetVal(ErrBadValue, 'sigtype')
		
		key = nacl.signing.SigningKey(signing_key.as_raw())

		# Clear all signatures which follow the current one. This expects that the signature_info
		# field lists the signatures in the order that they are required to appear.		
		clear_sig = False
		sigtype_index = 0

		# We really do need to use an index here instead of just an iterator. Sheesh.
		for i in range(len(sig_names)): # pylint: disable=consider-using-enumerate
			name = sig_names[i]
			if name == sigtype:
				clear_sig = True
				sigtype_index = i

			if clear_sig:
				self.signatures[name] = ''

		data = self.make_bytestring(sigtype_index + 1)
		signed = key.sign(data, Base85Encoder)
		self.signatures[sigtype] = 'ED25519:' + signed.signature.decode()
		return RetVal()

	def generate_hash(self, algorithm: str) -> RetVal:
		'''Populates the hash attribute based on the data in the entry. For supported algorithms,
		see EntryBase.get_hash()'''  
		status = self.get_hash(algorithm)
		if status.error():
			return status
		
		self.hash = status['hash']
		return status

	def verify_hash(self) -> RetVal:
		'''Checks that the entry's actual hash matches that in the hash field'''
		current_hash = CryptoString(self.hash)
		if not current_hash.is_valid():
			return RetVal(InvalidHash, f"{self.hash} is not a valid CryptoString")
		
		status = self.get_hash(current_hash.prefix)
		if status.error():
			return status
		
		return RetVal()

	def verify_signature(self, verify_key: CryptoString, sigtype: str) -> RetVal:
		'''Verifies a signature, given a verification key'''
	
		if not verify_key.is_valid():
			return RetVal(ErrBadValue, 'bad verify key')
		
		sig_names = [x['name'] for x in self.signature_info]
		if sigtype not in sig_names:
			return RetVal(ErrBadValue, 'bad signature type')
		
		if verify_key.prefix != 'ED25519':
			return RetVal(UnsupportedEncryptionType, verify_key.prefix)

		if sigtype in self.signatures and not self.signatures[sigtype]:
			return RetVal(NotCompliant, 'empty signature ' + sigtype)
		
		sig = CryptoString()
		if not sig.set(self.signatures[sigtype]):
			return RetVal(ErrBadData, 'entry signature is bad')

		try:
			vkey = nacl.signing.VerifyKey(verify_key.as_raw())
		except Exception as e:
			return RetVal.wrap_exception(e)

		try:
			data = self.make_bytestring(sig_names.index(sigtype))
			vkey.verify(data, sig.as_raw())
		except nacl.exceptions.BadSignatureError:
			return RetVal(InvalidKeycard)
		
		return RetVal()


class OrgEntry(EntryBase):
	'''Class for managing organization keycard entries'''
	
	def __init__(self):
		super().__init__()
		self.type = 'Organization'
		self.field_names = [
			'Index',
			'Name',
			'Contact-Admin',
			'Contact-Abuse',
			'Contact-Support',
			'Language',
			'Primary-Verification-Key',
			'Secondary-Verification-Key',
			'Encryption-Key',
			'Time-To-Live',
			'Expires',
			'Timestamp'
		]
		self.required_fields = [
			'Index',
			'Name',
			'Contact-Admin',
			'Primary-Verification-Key',
			'Encryption-Key',
			'Time-To-Live',
			'Expires',
			'Timestamp'
		]
		self.signature_info = [ 
			{ 'name' : 'Custody', 'level' : 1, 'optional' : True, 'type' : SIGINFO_SIGNATURE },
			{ 'name' : 'Hashes', 'level' : 3, 'optional' : False, 'type' : SIGINFO_HASH },
			{ 'name' : 'Organization', 'level' : 2, 'optional' : False, 'type' : SIGINFO_SIGNATURE }
		]
		
		self.fields['Index'] = '1'
		self.fields['Time-To-Live'] = '30'
		self.fields['Timestamp'] = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
		self.set_expiration()

	def chain(self, key: CryptoString, rotate_optional: bool) -> RetVal:
		'''Creates a new OrgEntry object with new keys and a custody signature. The keys are 
		returned in CryptoString format using the following fields:
		entry
		sign.public / sign.private -- primary signing keypair
		sign.pubhash / sign.privhash -- hashes of the corresponding keys
		altsign.public / altsign.private -- contact request signing keypair
		altsign.pubhash / altsign.privhash -- hashes of the corresponding keys
		encrypt.public / encrypt.private -- general-purpose public encryption keypair
		encrypt.pubhash / encrypt.privhash -- hashes of the corresponding keys

		Full SigningPair / EncryptionPair objects can be found in
		sign
		encrypt

		Because the alternate signing private key is not available, a full Pair field is not
		available, either.

		For organization entries, rotating optional keys works a little differently: the primary 
		signing key becomes the secondary signing key in the new entry. When rotation is False, 
		which is recommended only in instances of revocation, the secondary key is removed. Only 
		when rotate_optional is True is the field altsign.private returned.
		'''
		if key.prefix != 'ED25519':
			return RetVal(ErrBadValue, f'wrong key type {key.prefix}')
		
		status = self.is_compliant()
		if status.error():
			return status
		
		new_entry = OrgEntry()
		new_entry.fields = self.fields.copy()

		try:
			index = int(new_entry.fields['Index'])
			new_entry.fields['Index'] = str(index + 1)
		except Exception:
			return RetVal(ErrBadData, 'invalid entry index')
		
		out = RetVal()

		skey = SigningPair()
		ekey = EncryptionPair()

		out['sign'] = skey
		out['sign.public'] = skey.get_public_key()
		out['sign.pubhash'] = skey.get_public_hash()
		out['sign.private'] = skey.get_private_key()
		out['sign.privhash'] = skey.get_private_hash()
		out['encrypt'] = ekey
		out['encrypt.public'] = ekey.get_public_key()
		out['encrypt.pubhash'] = ekey.get_public_hash()
		out['encrypt.private'] = ekey.get_private_key()
		out['encrypt.privhash'] = ekey.get_private_hash()
		

		new_entry.fields['Primary-Verification-Key'] = skey.get_public_key()
		new_entry.fields['Encryption-Key'] = ekey.get_public_key()

		if rotate_optional:
			altskey = SigningPair()
			out['altsign.public'] = altskey.get_public_key()
			out['altsign.pubhash'] = altskey.get_public_hash()
			out['altsign.private'] = altskey.get_private_key()
			out['altsign.privhash'] = altskey.get_private_hash()
			new_entry.fields['Secondary-Verification-Key'] = altskey.get_public_key()
		else:
			out['altsign.public'] = self.fields['Primary-Verification-Key']
			out['altsign.pubhash'] = blake2hash(self.fields['Primary-Verification-Key'].encode())
			out['altsign.private'] = ''
			new_entry.fields['Secondary-Verification-Key'] = self.fields['Primary-Verification-Key']

		status = new_entry.sign(key, 'Custody')
		if status.error():
			return status

		out['entry'] = new_entry
		return out
	
	def verify_chain(self, previous: EntryBase) -> RetVal:
		'''Verifies the chain of custody between the provided previous entry and the current one.'''

		if previous.type != 'Organization':
			return RetVal(ErrBadValue, 'entry type mismatch')
		
		if 'Custody' not in self.signatures or not self.signatures['Custody']:
			return RetVal(ErrNotFound, 'custody signature missing')
		
		if 'Primary-Verification-Key' not in previous.fields or \
				not previous.fields['Primary-Verification-Key']:
			return RetVal(ErrNotFound, 'signing key missing')
		
		try:
			prev_index = int(previous['Index'])
		except:
			return RetVal(ErrBadData, 'previous entry has a bad index')
		
		try:
			index = int(self['Index'])
		except:
			return RetVal(ErrBadData, 'current entry has a bad index')
		
		if index != prev_index + 1:
			return RetVal(InvalidKeycard, 'entry index compliance failure')

		status = self.verify_signature(CryptoString(previous.fields['Primary-Verification-Key']),
				'Custody')
		return status


class UserEntry(EntryBase):
	'''Represents a user keycard entry'''
	def __init__(self):
		super().__init__()
		self.type = 'User'
		self.field_names = [
			'Index',
			'Name',
			'Workspace-ID',
			'User-ID',
			'Domain',
			'Contact-Request-Verification-Key',
			'Contact-Request-Encryption-Key',
			'Encryption-Key',
			'Verification-Key',
			'Time-To-Live',
			'Expires',
			'Timestamp'
		]
		self.required_fields = [
			'Index',
			'Workspace-ID',
			'Domain',
			'Contact-Request-Verification-Key',
			'Contact-Request-Encryption-Key',
			'Encryption-Key',
			'Verification-Key',
			'Time-To-Live',
			'Expires',
			'Timestamp'
		]
		self.signature_info = [ 
			{ 'name' : 'Custody', 'level' : 1, 'optional' : True, 'type' : SIGINFO_SIGNATURE },
			{ 'name' : 'Organization', 'level' : 2, 'optional' : False, 'type' : SIGINFO_SIGNATURE },
			{ 'name' : 'Hashes', 'level' : 3, 'optional' : False, 'type' : SIGINFO_HASH },
			{ 'name' : 'User', 'level' : 4, 'optional' : False, 'type' : SIGINFO_SIGNATURE }
		]
		
		self.fields['Index'] = '1'
		self.fields['Time-To-Live'] = '7'

		# Introduce a 5-minute delay to ensure that any minor clock differences between the client
		# and the server aren't going to cause trouble.
		timestamp = time.gmtime(calendar.timegm(time.gmtime()) - 300)
		self.fields['Timestamp'] = time.strftime('%Y%m%dT%H%M%SZ', timestamp)
		self.set_expiration()
	
	def chain(self, key: CryptoString, rotate_optional: bool) -> RetVal:
		'''Creates a new UserEntry object with new keys and a custody signature. It requires the 
		previous contact request signing key passed as an CryptoString. The new keys are returned in 
		CryptoString format using the following fields:
		entry
		crsign.public / crsign.private -- contact request signing keypair
		crencrypt.public / crencrypt.private -- contact request encryption keypair
		encrypt.public / encrypt.private -- general-purpose public encryption keypair
		sign.public / sign.private -- general-purpose primary signing keypair

		Full SigningPair / EncryptionPair objects can be found in
		crsign
		crencrypt
		sign
		encrypt
		'''

		if key.prefix != 'ED25519':
			return RetVal(ErrBadValue, f'wrong key type {key.prefix}')
		
		status = self.is_compliant()
		if status.error():
			return status
		
		new_entry = UserEntry()
		new_entry.fields = self.fields.copy()
		try:
			index = int(new_entry.fields['Index'])
			new_entry.fields['Index'] = str(index + 1)
		except Exception:
			return RetVal(ErrBadData, 'invalid entry index')

		out = RetVal()

		crskey = SigningPair()
		crekey = EncryptionPair()
		ekey = EncryptionPair()
		skey = SigningPair()

		out['crsign'] = crskey
		out['crsign.public'] = crskey.get_public_key()
		out['crsign.private'] = crskey.get_private_key()
		out['crencrypt'] = crekey
		out['crencrypt.public'] = crekey.get_public_key()
		out['crencrypt.private'] = crekey.get_private_key()
		out['encrypt'] = ekey
		out['encrypt.public'] = ekey.get_public_key()
		out['encrypt.private'] = ekey.get_private_key()
		out['sign'] = skey
		out['sign.public'] = skey.get_public_key()
		out['sign.private'] = skey.get_private_key()
		
		new_entry.fields['Contact-Request-Verification-Key'] = out['crsign.public']
		new_entry.fields['Contact-Request-Encryption-Key'] = out['crencrypt.public']
		new_entry.fields['Encryption-Key'] = out['encrypt.public']
		new_entry.fields['Verification-Key'] = out['sign.public']

		status = new_entry.sign(key, 'Custody')
		if status.error():
			return status

		out['entry'] = new_entry
		return out
		
	def verify_chain(self, previous: EntryBase) -> RetVal:
		'''Verifies the chain of custody between the provided previous entry and the current one.'''

		if previous.type != 'User':
			return RetVal(ErrBadValue, 'entry type mismatch')
		
		if 'Custody' not in self.signatures or not self.signatures['Custody']:
			return RetVal(ErrNotFound, 'custody signature missing')
		
		if 'Contact-Request-Verification-Key' not in previous.fields or \
				not previous.fields['Contact-Request-Verification-Key']:
			return RetVal(ErrNotFound, 'signing key missing')
		
		status = self.verify_signature(CryptoString(previous.fields['Contact-Request-Verification-Key']),
				'Custody')
		return status


class Keycard:
	'''Encapsulates a chain of keycard entries and higher-level management methods'''
	def __init__(self, cardtype = ''):
		self.type = cardtype
		self.entries = list()
	
	def chain(self, key: CryptoString, rotate_optional: bool) -> RetVal:
		'''Appends a new entry to the chain. This method requires that the root entry already 
		exist. Note that user cards will not have all the required signatures when the call returns'''
		if len(self.entries) < 1:
			return RetVal(ErrNotFound, 'missing root entry')

		# Just in case we get some squirrelly non-Org, non-User card type
		chain_method = getattr(self.entries[-1], "chain", None)
		if not chain_method or not callable(chain_method):
			return RetVal(FeatureNotAvailable, "entry doesn't support chaining")
		
		chaindata = self.entries[-1].chain(key, rotate_optional)
		if chaindata.error():
			return chaindata
		
		new_entry = chaindata['entry']

		skeystring = CryptoString()
		if not skeystring.set(chaindata['sign.private']):
			return RetVal(ErrBadData, 'bad signing key')
		
		if new_entry.type == 'User':
			status = new_entry.sign(skeystring, 'User')
		else:
			status = new_entry.sign(skeystring, 'Organization')
		if status.error():
			return status
		
		chaindata['entry'] = new_entry
		self.entries.append(new_entry)
		return chaindata
	
	def load(self, path: str) -> RetVal:
		'''Loads a keycard from a file'''
		if not path:
			return RetVal(ErrBadValue, 'path may not be empty')
		
		if not os.path.exists(path):
			return RetVal(ErrNotFound)
		
		# Although we care very much about saving keycards with the Windows-style line endings,
		# we actually want the line endings to get stripped on load because the fields aren't
		# stored with line endings
		try:
			with open(path, 'r') as f:
				card_type = ''
				accumulator = list()
				line_index = 1
				entry_index = 1
				rawline = f.readline()

				while rawline:
					line = rawline.strip()
					if not line:
						line_index = line_index + 1
						continue
					
					if line == '----- BEGIN ENTRY -----':
						accumulator.clear()
					elif line == '----- END ENTRY -----':
						
						entry = None
						if card_type == 'User':
							entry = UserEntry()
						elif card_type == 'Organization':
							entry = OrgEntry()
						else:
							return RetVal(UnsupportedKeycardType,
									f'entry {entry_index} has invalid type')

						status = entry.set(b'\r\n'.join(accumulator))
						if status.error():
							status.info = f'keycard entry {entry_index}: {status.info}'
							return status
						self.entries.append(entry)
						entry_index = entry_index + 1
					else:
						parts = line.split(':', 1)
						if len(parts) != 2:
							return RetVal(ErrBadData, f'invalid line {line_index}')
						
						if parts[0] == 'Type':
							if card_type:
								if card_type != parts[1]:
									return RetVal(ErrBadData, 'entry type does not match keycard')
							else:
								card_type = parts[1]

						accumulator.append(line.encode())
					
					line_index = line_index + 1
					rawline = f.readline()

		
		except Exception as e:
			return RetVal.wrap_exception(e)




		return RetVal()

	def save(self, path: str, clobber: bool) -> RetVal:
		'''Saves a keycard to a file'''
		if not path:
			return RetVal(ErrBadValue, 'path may not be empty')
		
		if os.path.exists(path) and not clobber:
			return RetVal(ErrExists)
			
		try:
			with open(path, 'wb') as f:
				for entry in self.entries:
					f.write(b'----- BEGIN ENTRY -----\r\n')
					f.write(entry.make_bytestring(-1))
					f.write(b'----- END ENTRY -----\r\n')
			
		except Exception as e:
			return RetVal.wrap_exception(e)

		return RetVal()
	
	def verify(self) -> RetVal:
		'''Verifies the card's entire chain of entries'''
		
		if len(self.entries) == 0:
			return RetVal(ErrNotFound, 'keycard contains no entries')
		
		if len(self.entries) == 1:
			return RetVal()
		
		for i in range(len(self.entries) - 1):
			status = self.entries[i + 1].verify_chain(self.entries[i])
			if status.error():
				return status

		return RetVal()


def db_add_entry(self, db: sqlite3.Connection, entry: EntryBase):
	'''Adds an entry to the database, ensuring no duplicates'''
	cursor = db.cursor()

	if entry.type == 'User':
		owner = f"{entry['Workspace-ID']}/{entry['Domain']}"
	else:
		owner = entry['Domain']
	cursor.execute("DELETE FROM keycards WHERE owner=? AND index=?", (owner,entry['Index']))

	entry_bytes = entry.make_bytestring(-1)
	cursor.execute('''
		INSERT INTO keycards(owner,index,type,entry,textentry,hash,expires,timestamp)
		VALUES(?,?,?,?,?,?,?,?)''',
		(owner, entry['Index'], entry.type, entry_bytes, str(entry_bytes), entry['Hash'], 
			entry['Expires'], entry['Timestamp']))
	db.commit()


def db_get_last_entry(self, db: sqlite3.Connection, owner: str) -> RetVal:
	'''Gets the most recent entry from the database'''
	
	cursor = db.cursor()
	cursor.execute("SELECT type,entry FROM keycards WHERE owner=? ORDER BY 'index' DESC LIMIT 1",
		(owner,))
	results = cursor.fetchone()
	if not results or not results[0] or not results[1]:
		return RetVal(ErrNotFound)

	if results[0].casefold() == 'organization':
		entry = OrgEntry()
	elif results[0].casefold() == 'user':
		entry = UserEntry()
	else:
		return RetVal(ErrBadType, f"bad entry type '{results[0]}' found in database")

	status = entry.set(results[1])
	if status.error():
		return status
	return RetVal().set_value('entry', entry)


def db_get_card(db: sqlite3.Connection, owner: str) -> RetVal:
	'''Obtains the entire keycard for the requested owner from the database'''
	cursor = db.cursor()
	cursor.execute("SELECT type,entry FROM keycards WHERE owner=? ORDER BY 'index'",
		(owner,))
	results = cursor.fetchone()
	if not results or not results[0] or not results[1]:
		return RetVal(ErrNotFound)
	
	if results[0].casefold() == 'organization':
		entry = OrgEntry()
	elif results[0].casefold() == 'user':
		entry = UserEntry()
	else:
		return RetVal(ErrBadType, f"bad entry type '{results[0]}' found in database")

	card = Keycard(entry.type)
	while results:
		status = entry.set(results[1])
		if status.error():
			return status
		card.entries.append(entry)
		results = cursor.fetchone()

	return RetVal().set_value('card', card)
