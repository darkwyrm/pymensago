from retval import RetVal, ErrBadType, ErrBadValue

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



foo = {
	'Header' : {
		'Version': '1.0',
		'EntityType': 'individual'
	},
	'GivenName': 'Richard',
	'FamilyName': 'Brannan',
	'Nicknames' : [ 'Rick', 'Ricky', 'Rich'],
	'Gender': 'Male',
	'Website': { 'Personal':'https://www.example.com',
				'Mensago':'https://mensago.org' },
	'Phone': [	{	'Label':'Mobile',
					'Number':'555-555-1234',
					'Preferred':'yes'
				}
			],
	'Birthday': '19750415',
	'Anniversary': '0714',
	'Mensago': [
		{	'Label':'Home',
			'UserID':'cavs4life',
			'Workspace':'f9ccb1f5-85e4-487d-9861-51d371101917',
			'Domain':'example.com'
		},
		{	'Label':'Work',
			'UserID':'rbrannan',
			'Workspace':'9015c2ea-2d02-491b-aa1f-4d536cfc4878',
			'Domain':'contoso.com'
		}
	],
	'Annotations': {}
}

status = flatten(foo)
if not status.error():
	print(status['value'])

