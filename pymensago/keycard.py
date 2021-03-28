'''This module contains the classes representing the entry blocks which are chained together in a 
keycard.'''

import base64
import calendar
import datetime
import hashlib
import os
import re
import time

# Temporarily disabled while building blake3 module on Windows is sorted out
# import blake3
import nacl.public
import nacl.signing

from pymensago.cryptostring import CryptoString
from pymensago.encryption import EncryptionPair, SigningPair, Base85Encoder
from pymensago.hash import blake2hash
from pymensago.retval import RetVal, BadData, BadParameterValue, ExceptionThrown, ResourceExists, \
		ResourceNotFound

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
			return RetVal(BadParameterValue, f"field {fieldname} does not exist")
		
		m = re.match(r'^[0-9]+$', self.fields[fieldname])
		if not m:
			return RetVal(BadData, 'bad field value')
		
		intValue = 0
		try:
			intValue = int(m[0])
		except:
			return RetVal(BadData, 'bad field value')
		
		if minVal != -1 and intValue < minVal:
			return RetVal(BadData, f"field {fieldname} less than minimum")

		if maxVal != -1 and intValue > maxVal:
			return RetVal(BadData, f"field {fieldname} greater than maximum")
		
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
				return RetVal(BadData, 'bad name value')

		# Required field: Time to Live
		outStatus = self.__validate_integer('Time-To-Live', 1, 30)
		if outStatus.error():
			return outStatus

		# is_timestamp_valid() validates both of the required fields Timestamp and Expires
		return self.is_timestamp_valid()

	def __validate_org_data(self) -> RetVal:
		'''Checks the validity of all data fields'''
		
		if self.type != 'Organization':
			return RetVal(BadData, 'invalid entry type %s' % self.type)
		
		outStatus = self.__validate_common_data()
		if outStatus.error():
			return outStatus

		# Required field: Admin address
		m = re.match(r'^[\da-fA-F]{8}-?[\da-fA-F]{4}-?[\da-fA-F]{4}-?[\da-fA-F]{4}'
			r'-?[\da-fA-F]{12}/([a-zA-Z0-9]+\.)+[a-zA-Z0-9]+$', self.fields['Contact-Admin'])
		if not m:
			return RetVal(BadData, 'bad admin contact address')

		# Required fields: Primary Verification Key, Encryption Key
		# We can't verify the actual key data, but we can at least ensure that it's formatted
		# correctly and we can b85decode the key itself
		for keyfield in ['Primary-Verification-Key', 'Encryption-Key']:
			if not CryptoString(self.fields[keyfield]).is_valid():
				return RetVal(BadData, f"bad key field {keyfield}")
		
		# Optional fields: Support and Abuse addresses
		for contactfield in ['Contact-Support','Contact-Abuse']:
			if contactfield in self.fields.keys():
				m = re.match(r'^[\da-fA-F]{8}-?[\da-fA-F]{4}-?[\da-fA-F]{4}-?[\da-fA-F]{4}'
					r'-?[\da-fA-F]{12}/([a-zA-Z0-9]+\.)+[a-zA-Z0-9]+$',
					self.fields[contactfield])
				if not m:
					return RetVal(BadData, f"bad contact address {contactfield}")
		
		# Optional field: Language
		if 'Language' in self.fields.keys():
			m = re.match(r'^[a-zA-Z]{2,3}(,[a-zA-Z]{2,3})*?$', self.fields['Language'])
			if not m:
				return RetVal(BadData, 'bad language list')

		# Optional field: Secondary Verification Key
		if 'Secondary-Verification-Key' in self.fields.keys():
			if not CryptoString(self.fields['Secondary-Verification-Key']).is_valid():
				return RetVal(BadData, 'bad secondary verification key')
		
		return RetVal()

	def __validate_user_data(self) -> RetVal:
		'''Checks the validity of all data fields'''
		if self.type != 'User':
			return RetVal(BadData, 'invalid entry type %s' % self.type)
		
		outStatus = self.__validate_common_data()
		if outStatus.error():
			return outStatus

		# Required field: Workspace ID
		m = re.match(r'^[\da-fA-F]{8}-?[\da-fA-F]{4}-?[\da-fA-F]{4}-?[\da-fA-F]{4}'
			r'-?[\da-fA-F]{12}$', self.fields['Workspace-ID'])
		if not m:
			return RetVal(BadData, 'bad workspace ID')

		# Required field: Domain
		# Although mostly freeform, the Name field has a couple requirements:
		m = re.match(r'([a-zA-Z0-9]+\.)+[a-zA-Z0-9]+', self.fields['Domain'])
		if not m or len(self.fields['Domain']) >= 64:
			return RetVal(BadData, 'bad domain value')

		# Required fields: Contact Request Verification Key, Contact Request Encryption Key,
		#	Public-Encryption-Key
		for keyfield in ['Contact-Request-Verification-Key',
						 'Contact-Request-Encryption-Key',
						 'Public-Encryption-Key']:
			if not CryptoString(self.fields[keyfield]).is_valid():
				return RetVal(BadData, f"bad key field {keyfield}")

		# Optional field: User ID
		if 'User-ID' in self.fields.keys():
			if re.findall(r'[\\\/\s"]', self.fields['User-ID']) or \
				len(self.fields['User-ID']) >= 64:
				return RetVal(BadData, 'bad user id value')
			
		if 'Alternate-Encryption-Key' in self.fields.keys():
			if not CryptoString(self.fields['Alternate-Encryption-Key']).is_valid():
				return RetVal(BadData, 'bad alternate encryption key')

		return RetVal()

	def get_hash(self, algorithm: str) -> RetVal:
		'''Generates a hash containing the expected signatures and the previous hash, if it exists. 
		The supported hash algorithms are 'BLAKE2-256', 'BLAKE3-256', 'SHA-256', and 'SHA3-256'.'''  
		# if algorithm not in ['BLAKE3-256','BLAKE2B-256','SHA-256','SHA3-256']:
		if algorithm not in ['BLAKE2B-256','SHA-256','SHA3-256']:
			return RetVal(UnsupportedHashType, f'{algorithm} not a supported hash algorithm')
		
		hash_string = CryptoString()
		hash_level = -1
		for sig in self.signature_info:
			if sig['type'] == SIGINFO_HASH:
				hash_level = sig['level']
				break
		assert hash_level > 0, "BUG: signature_info missing hash entry"
		
		# if algorithm == 'BLAKE3-256':
		# 	hasher = blake3.blake3() # pylint: disable=c-extension-no-member
		# 	hasher.update(self.make_bytestring(hash_level))
		# 	hash_string.data = base64.b85encode(hasher.digest()).decode()
		# else:
			# hasher = None
			# if algorithm == 'BLAKE2B-256':
			# 	hasher = hashlib.blake2b(digest_size=32)
			# elif algorithm == 'SHA-256':
			# 	hasher = hashlib.sha256()
			# else:
			# 	hasher = hashlib.sha3_256()
			# hasher.update(self.make_bytestring(hash_level))
			# hash_string.data = base64.b85encode(hasher.digest()).decode()
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
				return RetVal(BadData, f"leading/trailing whitespace in field {field}")
		
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
			return RetVal(BadData, 'bad expiration date')
		expire_time = datetime.datetime(int(m[1]), int(m[2]), int(m[3]),
			tzinfo=datetime.timezone(datetime.timedelta(hours=0)))

		m = re.match(r'^([0-9]{4})([0-9]{2})([0-9]{2})T([0-9]{2})([0-9]{2})([0-9]{2})Z$',
			self.fields['Timestamp'])
		if not m or not _is_valid_date(int(m[2]), int(m[3]), int(m[1]), 
			int(m[4]), int(m[5]), int(m[6])):
			return RetVal(BadData, 'bad timestamp')
		timestamp_time = datetime.datetime(int(m[1]), int(m[2]), int(m[3]),
			int(m[4]), int(m[5]), int(m[6]),
			tzinfo=datetime.timezone(datetime.timedelta(hours=0)))

		if timestamp_time > expire_time:
			return RetVal(BadData, 'bad timestamp')
		
		return RetVal()

	def is_expired(self) -> RetVal:
		'''Checks if the entry is expired'''
		if 'Expires' not in self.fields.keys():
			return RetVal(RequiredFieldMissing, 'Expires')
		
		m = re.match(r'^([0-9]{4})([0-9]{2})([0-9]{2})$', self.fields['Expires'])
		if not m or not _is_valid_date(int(m[2]), int(m[3]), int(m[1])):
			return RetVal(BadData, 'bad expiration date')
		expire_time = datetime.datetime(int(m[1]), int(m[2]), int(m[3]),
			tzinfo=datetime.timezone(datetime.timedelta(hours=0)))

		if datetime.datetime.now() > expire_time:
			return RetVal(BadData, 'entry is expired')

		return RetVal()

	def get_signature(self, sigtype: str) -> RetVal:
		'''Retrieves the requested signature and type'''
		if sigtype not in self.signatures:
			return RetVal(ResourceNotFound, sigtype)
		
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
		
		return RetVal(BadData, self.signatures[sigtype])
	
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
			return RetVal(BadParameterValue, 'path may not be empty')
		
		if os.path.exists(path) and not clobber:
			return RetVal(ResourceExists)
		
		try:
			with open(path, 'wb') as f:
				f.write(self.make_bytestring(-1))
		
		except Exception as e:
			return RetVal(ExceptionThrown, str(e))

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
					return RetVal(BadData, 'bad signature line %s' % sigparts[0])
				self.signatures[sigparts[0]] = v
			else:
				self.fields[k] = v
		
		return RetVal()
	
	def set(self, data: bytes) -> RetVal:
		'''Sets the object's information from a bytestring'''

		try:
			rawstring = data.decode()
		except Exception as e:
			return RetVal(ExceptionThrown, e)
		
		lines = rawstring.split('\r\n')
		for line in lines:
			if not line:
				continue

			stripped = line.strip()
			if not stripped:
				continue

			parts = stripped.split(':', 1)
			if len(parts) != 2:
				return RetVal(BadData, line)
			
			if parts[0] == 'Type':
				if parts[1] != self.type:
					return RetVal(BadData, "can't use %s data on a %s entry" % (parts[0], self.type))
			
			elif parts[0].endswith('Signature'):
				sigparts = parts[0].split('-', 1)
				if sigparts[0] not in [ 'Custody', 'User', 'Organization', 'Entry' ]:
					return RetVal(BadData, 'bad signature line %s' % sigparts[0])
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
			return RetVal(BadParameterValue, 'signing key')
		
		if signing_key.prefix != 'ED25519':
			return RetVal(UnsupportedEncryptionType, signing_key.prefix)
		
		sig_names = [x['name'] for x in self.signature_info]
		if sigtype not in sig_names:
			return RetVal(BadParameterValue, 'sigtype')
		
		key = nacl.signing.SigningKey(signing_key.raw_data())

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
			return RetVal(BadParameterValue, 'bad verify key')
		
		sig_names = [x['name'] for x in self.signature_info]
		if sigtype not in sig_names:
			return RetVal(BadParameterValue, 'bad signature type')
		
		if verify_key.prefix != 'ED25519':
			return RetVal(UnsupportedEncryptionType, verify_key.prefix)

		if sigtype in self.signatures and not self.signatures[sigtype]:
			return RetVal(NotCompliant, 'empty signature ' + sigtype)
		
		sig = CryptoString()
		status = sig.set(self.signatures[sigtype])
		if status.error():
			return status

		try:
			vkey = nacl.signing.VerifyKey(verify_key.raw_data())
		except Exception as e:
			return RetVal(ExceptionThrown, e)

		try:
			data = self.make_bytestring(sig_names.index(sigtype))
			vkey.verify(data, sig.raw_data())
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

		For organization entries, rotating optional keys works a little differently: the primary 
		signing key becomes the secondary signing key in the new entry. When rotation is False, 
		which is recommended only in instances of revocation, the secondary key is removed. Only 
		when rotate_optional is True is the field altsign.private returned.
		'''
		if key.prefix != 'ED25519':
			return RetVal(BadParameterValue, f'wrong key type {key.prefix}')
		
		status = self.is_compliant()
		if status.error():
			return status
		
		new_entry = OrgEntry()
		new_entry.fields = self.fields.copy()

		try:
			index = int(new_entry.fields['Index'])
			new_entry.fields['Index'] = str(index + 1)
		except Exception:
			return RetVal(BadData, 'invalid entry index')
		
		out = RetVal()

		skey = SigningPair()
		ekey = EncryptionPair()

		out['sign.public'] = skey.get_public_key()
		out['sign.pubhash'] = skey.get_public_hash()
		out['sign.private'] = skey.get_private_key()
		out['sign.privhash'] = skey.get_private_hash()
		out['encrypt.public'] = ekey.get_public_key()
		out['encrypt.pubhash'] = ekey.get_public_hash()
		out['encrypt.private'] = ekey.get_private_key()
		out['encrypt.privhash'] = ekey.get_private_hash()
		
		if rotate_optional:
			altskey = SigningPair()
			out['altsign.public'] = altskey.get_public_key()
			out['altsign.pubhash'] = altskey.get_public_hash()
			out['altsign.private'] = altskey.get_private_key()
			out['altsign.privhash'] = altskey.get_private_hash()
		else:
			out['altsign.public'] = self.fields['Primary-Verification-Key']
			out['altsign.pubhash'] = blake2hash(
				self.fields['Primary-Verification-Key'].as_string().encode())
			out['altsign.private'] = ''

		status = new_entry.sign(key, 'Custody')
		if status.error():
			return status

		out['entry'] = new_entry
		return out
	
	def verify_chain(self, previous: EntryBase) -> RetVal:
		'''Verifies the chain of custody between the provided previous entry and the current one.'''

		if previous.type != 'Organization':
			return RetVal(BadParameterValue, 'entry type mismatch')
		
		if 'Custody' not in self.signatures or not self.signatures['Custody']:
			return RetVal(ResourceNotFound, 'custody signature missing')
		
		if 'Primary-Verification-Key' not in previous.fields or \
				not previous.fields['Primary-Verification-Key']:
			return RetVal(ResourceNotFound, 'signing key missing')
		
		try:
			prev_index = int(previous['Index'])
		except:
			return RetVal(BadData, 'previous entry has a bad index')
		
		try:
			index = int(self['Index'])
		except:
			return RetVal(BadData, 'current entry has a bad index')
		
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
			'Public-Encryption-Key',
			'Alternate-Encryption-Key',
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
			'Public-Encryption-Key',
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
		sign.public / sign.private -- primary signing keypair
		crsign.public / crsign.private -- contact request signing keypair
		crencrypt.public / crencrypt.private -- contact request encryption keypair
		encrypt.public / encrypt.private -- general-purpose public encryption keypair
		altencrypt.public / altencrypt.private -- alternate public encryption keypair

		Note that the last two keys are not required to be updated during entry rotation so that 
		they can be rotated on a different schedule from the other keys. These fields are only 
		returned if there are no errors.
		'''

		if key.prefix != 'ED25519':
			return RetVal(BadParameterValue, f'wrong key type {key.prefix}')
		
		status = self.is_compliant()
		if status.error():
			return status
		
		new_entry = UserEntry()
		new_entry.fields = self.fields.copy()
		try:
			index = int(new_entry.fields['Index'])
			new_entry.fields['Index'] = str(index + 1)
		except Exception:
			return RetVal(BadData, 'invalid entry index')

		out = RetVal()

		skey = SigningPair()
		crskey = SigningPair()
		crekey = EncryptionPair()

		out['sign.public'] = skey.get_public_key()
		out['sign.private'] = skey.get_private_key()
		out['crsign.public'] = crskey.get_public_key()
		out['crsign.private'] = crskey.get_private_key()
		out['crencrypt.public'] = crekey.get_public_key()
		out['crencrypt.private'] = crekey.get_private_key()
		
		new_entry.fields['Contact-Request-Verification-Key'] = out['crsign.public']
		new_entry.fields['Contact-Request-Encryption-Key'] = out['crencrypt.public']

		if rotate_optional:
			ekey = EncryptionPair()
			out['encrypt.public'] = ekey.get_public_key()
			out['encrypt.private'] = ekey.get_private_key()

			aekey = EncryptionPair()
			out['altencrypt.public'] = aekey.get_public_key()
			out['altencrypt.private'] = aekey.get_private_key()
			
			new_entry.fields['Public-Encryption-Key'] = out['encrypt.public']
			new_entry.fields['Alternate-Encryption-Key'] = out['altencrypt.public']
		else:
			out['encrypt.public'] = ''
			out['encrypt.private'] = ''
			out['altencrypt.public'] = ''
			out['altencrypt.private'] = ''

		status = new_entry.sign(key, 'Custody')
		if status.error():
			return status

		out['entry'] = new_entry
		return out
		
	def verify_chain(self, previous: EntryBase) -> RetVal:
		'''Verifies the chain of custody between the provided previous entry and the current one.'''

		if previous.type != 'User':
			return RetVal(BadParameterValue, 'entry type mismatch')
		
		if 'Custody' not in self.signatures or not self.signatures['Custody']:
			return RetVal(ResourceNotFound, 'custody signature missing')
		
		if 'Contact-Request-Verification-Key' not in previous.fields or \
				not previous.fields['Contact-Request-Verification-Key']:
			return RetVal(ResourceNotFound, 'signing key missing')
		
		status = self.verify_signature(CryptoString(previous.fields['Contact-Request-Verification-Key']),
				'Custody')
		return status


class Keycard:
	'''Encapsulates a chain of keycard entries and higher-level management methods'''
	def __init__(self, cardtype = ''):
		self.type = cardtype
		self.entries = list()
	
	def chain(self, key: CryptoString, rotate_optional: bool) -> RetVal:
		'''Appends a new entry to the chain, optionally rotating keys which aren't required to be 
		changed. This method requires that the root entry already exist. Note that user cards will 
		not have all the required signatures when the call returns'''
		if len(self.entries) < 1:
			return RetVal(ResourceNotFound, 'missing root entry')

		# Just in case we get some squirrelly non-Org, non-User card type
		chain_method = getattr(self.entries[-1], "chain", None)
		if not chain_method or not callable(chain_method):
			return RetVal(FeatureNotAvailable, "entry doesn't support chaining")
		
		chaindata = self.entries[-1].chain(key, rotate_optional)
		if chaindata.error():
			return chaindata
		
		new_entry = chaindata['entry']

		skeystring = CryptoString()
		status = skeystring.set(chaindata['sign.private'])
		if status.error():
			return status
		
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
			return RetVal(BadParameterValue, 'path may not be empty')
		
		if not os.path.exists(path):
			return RetVal(ResourceNotFound)
		
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
							return RetVal(BadData, f'invalid line {line_index}')
						
						if parts[0] == 'Type':
							if card_type:
								if card_type != parts[1]:
									return RetVal(BadData, 'entry type does not match keycard')
							else:
								card_type = parts[1]

						accumulator.append(line.encode())
					
					line_index = line_index + 1
					rawline = f.readline()

		
		except Exception as e:
			return RetVal(ExceptionThrown, str(e))




		return RetVal()

	def save(self, path: str, clobber: bool) -> RetVal:
		'''Saves a keycard to a file'''
		if not path:
			return RetVal(BadParameterValue, 'path may not be empty')
		
		if os.path.exists(path) and not clobber:
			return RetVal(ResourceExists)
			
		try:
			with open(path, 'wb') as f:
				for entry in self.entries:
					f.write(b'----- BEGIN ENTRY -----\r\n')
					f.write(entry.make_bytestring(-1))
					f.write(b'----- END ENTRY -----\r\n')
			
		except Exception as e:
			return RetVal(ExceptionThrown, str(e))

		return RetVal()
	
	def verify(self) -> RetVal:
		'''Verifies the card's entire chain of entries'''
		
		if len(self.entries) == 0:
			return RetVal(ResourceNotFound, 'keycard contains no entries')
		
		if len(self.entries) == 1:
			return RetVal()
		
		for i in range(len(self.entries) - 1):
			status = self.entries[i + 1].verify_chain(self.entries[i])
			if status.error():
				return status

		return RetVal()
