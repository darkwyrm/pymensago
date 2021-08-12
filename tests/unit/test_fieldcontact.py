import copy
import inspect

from pymensago.fieldcontact import FieldList, Field, FieldDict

def funcname() -> str: 
	frames = inspect.getouterframes(inspect.currentframe())
	return frames[1].function


def test_field():
	'''Test the various methods of a Field object'''
	f = Field('foo')
	f.value = 'bar'
	
	teststr = str(f)
	assert teststr == '"foo":"bar"', f"{funcname()}: JSON output didn't match"


def test_fieldlist():
	'''Tests the various methods of a FieldList object'''

	f = FieldList('TestList')
	f.values = [ 'a', 'b', 'c' ]

	teststr = str(f)
	assert teststr == '["a","b","c"]', f"{funcname()}: JSON output didn't match"
	

	testval = f+'d'
	assert testval.values == ['a','b','c','d'], f"{funcname()}: + operator +str subtest failed"
	testval = f+['d','e']
	assert testval.values == ['a','b','c','d','e'], f"{funcname()}: + operator +list subtest failed"
	testval = f+1
	assert testval.values == ['a','b','c',1], f"{funcname()}: + operator +int subtest failed"

	testval.values = [ 'a', 'b', 'c' ]
	assert testval == f, f"{funcname()}: == operator == subtest failed"
	testval = f+'d'
	assert testval != f, f"{funcname()}: == operator != subtest failed"
	assert testval.count() == 4, f"{funcname()}: count subtest failed"

	testval = FieldList('TestList')
	testval.merge(f)
	assert testval.values == ['a','b','c'], f"{funcname()}: merge FieldList subtest failed"
	testval = copy.deepcopy(f)
	testval.merge('d')
	assert testval.values == ['a','b','c','d'], f"{funcname()}: merge +str subtest failed"
	testval = copy.deepcopy(f)
	testval.merge(['d','e'])
	assert testval.values == ['a','b','c','d','e'], f"{funcname()}: merge +list subtest failed"
	testval = copy.deepcopy(f)
	testval.merge(1)
	assert testval.values == ['a','b','c',1], f"{funcname()}: merge +int subtest failed"

if __name__ == '__main__':
	test_field()
	test_fieldlist()
