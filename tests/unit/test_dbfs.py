import inspect

import pymensago.dbfs as dbfs

def funcname() -> str: 
	frames = inspect.getouterframes(inspect.currentframe())
	return frames[1].function


def test_make_dblocal():
	'''Tests make_path_dblocal()'''

	for testpath in [ '/', '/foo', 'foo', '/foo/bar' ]:
		assert dbfs.validate_dbpath(testpath), f"{funcname()}: failed valid path {testpath}"
	
	for testpath in [ '', '/foo/', dbfs.DBPath('foo'), ' /foo ' ]:
		assert not dbfs.validate_dbpath(testpath), f"{funcname()}: passed invalid path {testpath}"


if __name__ == '__main__':
	test_make_dblocal()

