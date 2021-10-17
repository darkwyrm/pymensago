import pymensago.mpath as mpath

def test_basename():
	'''Tests mpath.basename()'''
	assert mpath.basename('/ foo bar baz') == 'baz', 'basename test failed'


def test_parent():
	'''Tests mpath.parent()'''
	assert mpath.parent('/ foo bar baz') == '/ foo bar', 'parent test failed'


def test_split():
	'''Tests mpath.split()'''
	testdata = '/ foo bar baz / spam eggs / 123 456 789'
	expected_data = ['/ foo bar baz', '/ spam eggs', '/ 123 456 789']
	assert mpath.split(testdata) == expected_data, 'split test failed'


def test_validate_server_path():
	'''Tests mpath.validate_server_path()'''
	testpaths = [
		'/',
		'/ tmp 11111111-1111-1111-1111-111111111111 1234.1234.22222222-2222-2222-2222-222222222222',
		'/ out 11111111-1111-1111-1111-111111111111 33333333-3333-3333-3333-333333333333',
		'/ wsp 11111111-1111-1111-1111-111111111111 33333333-3333-3333-3333-333333333333 new '
			'1234.1234.22222222-2222-2222-2222-222222222222',
	]
	for testpath in testpaths:
		assert mpath.validate_server_path(testpath), 'validate_server_path test failed: ' + testpath


if __name__ == '__main__':
	test_basename()
	test_parent()
	test_split()
	test_validate_server_path()

