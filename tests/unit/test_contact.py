import inspect

from retval import ErrBadData

from pymensago.contact import flatten, unflatten, unflatten_field, Name

def funcname() -> str: 
	frames = inspect.getouterframes(inspect.currentframe())
	return frames[1].function

def test_flatten_unflatten():
	'''Tests the flatten() function'''

	unflat_data = {
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
		'Annotations': {
			'Anniversary': '0714',
		}
	}

	flat_data = {
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
		'Mensago.0.Label': 'Home',
		'Mensago.0.UserID': 'cavs4life',
		'Mensago.0.Workspace': 'f9ccb1f5-85e4-487d-9861-51d371101917',
		'Mensago.0.Domain': 'example.com',
		'Mensago.1.Label': 'Work',
		'Mensago.1.UserID': 'rbrannan',
		'Mensago.1.Workspace': '9015c2ea-2d02-491b-aa1f-4d536cfc4878',
		'Mensago.1.Domain': 'contoso.com',
		'Annotations.Anniversary': '0714',
	}

	status = flatten(unflat_data)
	assert not status.error(), f"{funcname()}: subtest #1 returned an error: {status.info()}"
	assert 'value' in status and status['value'] == flat_data, \
		f"{funcname()}: subtest #1 returned incorrect data"
	
	status = unflatten(flat_data)
	assert not status.error(), f"{funcname()}: subtest #2 returned an error: {status.info()}"
	assert 'value' in status and status['value'] == unflat_data, \
		f"{funcname()}: subtest #2 returned incorrect data"


def test_unflatten_field():
	'''Tests the unflatten_field function'''

	unflat_data = {
		'Top' : [ {	'Fieldname' : 'Value' } ]
	}
	target = dict()
	status = unflatten_field(target, 'Top.0.Fieldname', 'Value')
	assert not status.error(), f"{funcname()}: subtest #1 returned an error: {status.info()}"
	assert target == unflat_data, f"{funcname()}: subtest #1 returned incorrect data"

	unflat_data = {
		'Top' : [ [ 'Value'] ]
	}
	target = dict()
	status = unflatten_field(target, 'Top.0.0', 'Value')
	assert not status.error(), f"{funcname()}: subtest #2 returned an error: {status.info()}"
	assert target == unflat_data, f"{funcname()}: subtest #2 returned incorrect data"

	unflat_data = {
		'Top' : { 'FieldName' : { 'SecondFieldName' : 'Value'} }
	}
	target = dict()
	status = unflatten_field(target, 'Top.FieldName.SecondFieldName', 'Value')
	assert not status.error(), f"{funcname()}: subtest #3 returned an error: {status.info()}"
	assert target == unflat_data, f"{funcname()}: subtest #3 returned incorrect data"

	unflat_data = {
		'Top' : { 'FieldName' : [ 'Value'] }
	}
	target = dict()
	status = unflatten_field(target, 'Top.FieldName.0', 'Value')
	assert not status.error(), f"{funcname()}: subtest #4 returned an error: {status.info()}"
	assert target == unflat_data, f"{funcname()}: subtest #4 returned incorrect data"


def test_name():
	'''Tests the Name class methods'''

	name = Name('Corbin', 'Simons', 'Dr.', 'MD', ['James', 'Alexander'])

	assert name.formatted == 'Dr. Corbin James Alexander Simons, MD', \
		f'test_name: full name formatting test failed: {name.formatted}'
	
	name.set('Fred', 'Kingsley', suffixes=['CCNA', 'MCSE'], family_first=True)
	assert name.formatted == 'Kingsley Fred, CCNA, MCSE', \
		f'test_name: family first formatting test failed: {name.formatted}'


if __name__ == '__main__':
	# test_flatten_unflatten()
	test_unflatten_field()
	# test_name()
