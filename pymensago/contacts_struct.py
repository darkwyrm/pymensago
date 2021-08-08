from retval import ErrBadType, RetVal

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
	for k,v in d:
		status = RetVal()
		if isinstance(v, str):
			flattened[k] = v
		elif isinstance(v, dict):
			status = _flatten_dict(flattened, [k], v)
		elif isinstance(v, list):
			status = _flatten_list(flattened, [k], v)
		
		if status.error():
			return status

	return RetVal().set_values(flattened)


def _flatten_dict(target: dict, levels: list, d: dict) -> RetVal:
	pass

def _flatten_list(target: dict, levels: list, l: list) -> RetVal:
	pass
