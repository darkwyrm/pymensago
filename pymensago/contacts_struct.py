from typing import Union

from retval import ErrOutOfRange, RetVal, ErrBadType, ErrBadValue

# Dot-notation turns a nested dictionary into a flat one. This makes database interactions MUCH
# easier. For example:
# {
# 	Foo: [	
# 		{ "Bar":"Baz" }
# 	]
# }
# flattens to { "Foo.0.Bar": "Baz" }
def flatten(d: dict) -> RetVal:
	'''Flattens a dictionary in Contact format into a single-level dot-notated dictionary. All 
	fields are expected to be dictionaries, lists, or strings. The flattened result is returned 
	in the 'value' field unless there is an error.'''
	if not len(d):
		return RetVal().set_value('value', dict())
	
	if not isinstance(d, dict):
		return RetVal(ErrBadType)
	
	flattened = dict()
	for k,v in d.items():
		status = RetVal()
		if isinstance(v, str):
			flattened[k] = v
		elif isinstance(v, dict):
			status = _flatten_dict(flattened, [k], v)
		elif isinstance(v, list):
			status = _flatten_list(flattened, [k], v)
		else:
			return RetVal(ErrBadValue, f"field {k} is not dictionary, list, or string")
		
		if status.error():
			return status

	return RetVal().set_value('value', flattened)


def _flatten_dict(target: dict, levels: list, d: dict) -> RetVal:
	for k,v in d.items():
		status = RetVal()
		if isinstance(v, str):
			flatkey = f"{'.'.join(levels)}.{k}"
			target[flatkey] = v
		elif isinstance(v, dict):
			status = _flatten_dict(target, [k], v)
		elif isinstance(v, list):
			status = _flatten_list(target, [k], v)
		else:
			return RetVal(ErrBadValue, f"field {k} is not dictionary, list, or string")
		
		if status.error():
			return status

	return RetVal()

def _flatten_list(target: dict, levels: list, l: list) -> RetVal:
	for i in range(len(l)):
		status = RetVal()
		if isinstance(l[i], str):
			flatkey = f"{'.'.join(levels)}.{str(i)}"
			target[flatkey] = l[i]
		elif isinstance(l[i], dict):
			status = _flatten_dict(target, levels + [str(i)], l[i])
		elif isinstance(l[i], list):
			status = _flatten_list(target, levels + [str(i)], l[i])
	
		if status.error():
			return status

	return RetVal()



# foo = {
# 	'Header' : {
# 		'Version': '1.0',
# 		'EntityType': 'individual'
# 	},
# 	'GivenName': 'Richard',
# 	'FamilyName': 'Brannan',
# 	'Nicknames' : [ 'Rick', 'Ricky', 'Rich'],
# 	'Gender': 'Male',
# 	'Website': { 'Personal':'https://www.example.com',
# 				'Mensago':'https://mensago.org' },
# 	'Phone': [	{	'Label':'Mobile',
# 					'Number':'555-555-1234',
# 					'Preferred':'yes'
# 				}
# 			],
# 	'Birthday': '19750415',
# 	'Anniversary': '0714',
# 	'Mensago': [
# 		{	'Label':'Home',
# 			'UserID':'cavs4life',
# 			'Workspace':'f9ccb1f5-85e4-487d-9861-51d371101917',
# 			'Domain':'example.com'
# 		},
# 		{	'Label':'Work',
# 			'UserID':'rbrannan',
# 			'Workspace':'9015c2ea-2d02-491b-aa1f-4d536cfc4878',
# 			'Domain':'contoso.com'
# 		}
# 	],
# 	'Annotations': {}
# }

# status = flatten(foo)
# if not status.error():
# 	print(status['value'])

def unflatten(d: dict):
	'''Unflattens a dictionary from the format described for flatten()'''
	if not len(d):
		return RetVal().set_value('value', dict())
	
	if not isinstance(d, dict):
		return RetVal(ErrBadType)
	
	unflattened = dict()
	for k,v in d.items():
		if not isinstance(k, str):
			return RetVal(ErrBadType, 'keys must be strings')
		
		if not len(k):
			return RetVal(ErrBadValue, 'string keys may not be empty')
		
		if not isinstance(v, str):
			return RetVal(ErrBadType, 'values must be strings')
		
		parts = k.split('.')
		if len(parts) == 1:
			unflattened[parts[0]] = v
		else:
			# The top-level item is a container. We need to find out the type of the container's
			# index. From there, we ensure that the container exists and then call the appropriate
			# unflatten call to unpack the container's values
			index_is_int = True
			try:
				index = int(parts[1])
			except:
				index = parts[1]
				index_is_int = False
			
			if index_is_int:
				# Index is an integer. Container must be a list
				if parts[0] not in unflattened:
					unflattened[parts[0]] = list()
				
				if not isinstance(unflattened[parts[0]], list):
					return RetVal(ErrBadType, f"Type mismatch: {parts[0]}")


			else:
				# Index is a string. Container must be a dictionary
				if parts[0] not in unflattened:
					unflattened[parts[0]] = dict()
				
				if not isinstance(unflattened[parts[0]], dict):
					return RetVal(ErrBadType, f"Type mismatch: {parts[0]}")

			_unflatten_recurse(unflattened[parts[0]], parts, 1, v)
			

	return RetVal().set_value('value', unflattened)


def _unflatten_recurse(target: Union[dict,list], levels: list, levelindex: int, value: str) -> RetVal:
	'''This method continues to unpack a dot-notated string field. It is only called by itself or 
	unflatten(), so we will assume that parameter values are correct.'''

	if isinstance(target, list):
		target_is_list = True
		targetindex = int(levels[levelindex])
	else:
		target_is_list = False
		targetindex = levels[levelindex]

	if len(levels[levelindex:]) == 1:
		if target_is_list:
			target[levels[-1]] = value
		else:
			value_index = int(levels[-1])
			
			if value_index == len(target):
				target.append(value)
			elif value_index < 0:
				return RetVal(ErrBadValue, f"negative list index for f{'.'.join(levels)}")
			elif value_index < len(target):
				target[value_index] = value
			elif value_index > len(target):
				return RetVal(ErrOutOfRange, f"list index for f{'.'.join(levels)} out of bounds")
	else:
		index_is_int = True
		try:
			index = int(levels[levelindex+1])
		except:
			index = levels[levelindex+1]
			index_is_int = False

		if index_is_int:
			# Index is an integer. Container must be a list
			if index not in target:
				if isinstance(target, list):
					target.append(list())
				else:
					target[index] = list()
			
			if not isinstance(target[index], list):
				return RetVal(ErrBadType, f"Type mismatch: {index}")

		else:
			# Index is a string. Container must be a dictionary
			if index not in target:
				if isinstance(target, list):
					target.append(dict())
				else:
					target[index] = dict()
			elseL			
			if not isinstance(target[index], dict):
				return RetVal(ErrBadType, f"Type mismatch: {index}")

			_unflatten_recurse(target[index], levels, levelindex+1, value)


bar = {
	'Header.Version': '1.0',
	'Header.EntityType': 'individual',
	'GivenName': 'Richard',
	'FamilyName': 'Brannan',
	'Nicknames.0': 'Rick',
	'Nicknames.1': 'Ricky',
	'Nicknames.2': 'Rich',
	'Gender': 'Male',
	'Website.Personal': 'https://www.example.com',
	'Website.Mensago': 'https://mensago.org',
	'Phone.0.Label': 'Mobile',
	'Phone.0.Number': '555-555-1234',
	'Phone.0.Preferred': 'yes',
	'Birthday': '19750415',
	'Anniversary': '0714',
	'Mensago.0.Label': 'Home',
	'Mensago.0.UserID': 'cavs4life',
	'Mensago.0.Workspace': 'f9ccb1f5-85e4-487d-9861-51d371101917',
	'Mensago.0.Domain': 'example.com',
	'Mensago.1.Label': 'Work',
	'Mensago.1.UserID': 'rbrannan',
	'Mensago.1.Workspace': '9015c2ea-2d02-491b-aa1f-4d536cfc4878',
	'Mensago.1.Domain': 'contoso.com'
}

status = unflatten(bar)
if not status.error():
	print(status['value'])
