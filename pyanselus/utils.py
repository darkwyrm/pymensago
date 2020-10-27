'''Houses just some different utility functions'''

import re

from retval import RetVal, BadParameterValue

# This function is needed because the Anselus admin ID is purposely nonconformant -- a user can
# *never* accidentally get assigned the value, and for the purposes of the platform, version 
# information doesn't matter.
def validate_uuid(indata):
	'''Validates a UUID's basic format. Does not check version information.'''

	# With dashes, should be 36 characters or 32 without
	if (len(indata) != 36 and len(indata) != 32) or len(indata) == 0:
		return False
	
	uuid_pattern = re.compile(
			r"[\da-fA-F]{8}-?[\da-fA-F]{4}-?[\da-fA-F]{4}-?[\da-fA-F]{4}-?[\da-fA-F]{12}")
	
	if not uuid_pattern.match(indata):
		return False
	
	return True


def split_address(address):
	'''Splits an Anselus numeric address into its two parts.'''
	parts = address.split('/')
	if len(parts) != 2 or \
		not parts[0] or \
		not parts[1] or \
		not validate_uuid(parts[0]):
		return RetVal(BadParameterValue, 'Bad workspace address')
	out = RetVal()
	out.set_value('wid', parts[0])
	out.set_value('domain', parts[1])
	return out
