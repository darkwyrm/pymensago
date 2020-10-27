'''Tests the RetVal class'''

from retval import RetVal, OK, BadParameterValue

def test_setvalue():
	'''Tests setvalue()'''
	r = RetVal().set_value('foo','bar')
	assert r['foo'] == 'bar', 'Failed to get RetVal value'

def test_set_values():
	'''Tests set_values'''
	r = RetVal().set_values({
		'foo' : 'bar',
		'spam' : 'eggs'
	})
	
	assert r['foo'] == 'bar' and r['spam'] == 'eggs', 'Failed to get RetVal values'

def test_hasvalue():
	'''Tests hasvalue()'''
	r = RetVal()
	
	assert r.set_value('foo','bar'), 'Failed to set RetVal value'
	assert r.has_value('foo'), 'Failed to find existing RetVal value'

def test_error():
	'''Tests set_error() and error()'''
	r = RetVal()
	assert r.error() == OK, '''RetVal not initialized to OK state'''
	r.set_error(BadParameterValue)
	assert r.error() == BadParameterValue, '''RetVal not set to correct error state'''

def test_count():
	'''Tests count()'''
	r = RetVal()
	assert r.count() == 0, '''Unused RetVal is not empty'''
	r['foo'] = 'bar'
	assert r.count() == 1, '''Incorrect item count in RetVal'''
	r.empty()
	assert r.count() == 0, '''Emptied RetVal is not empty'''
