import inspect

import pymensago.dbfs as dbfs

def funcname() -> str: 
	frames = inspect.getouterframes(inspect.currentframe())
	return frames[1].function


def test_make_dblocal():
	'''Tests make_path_dblocal()'''

	for testpath in [ '/', '/foo', 'foo', '/foo/bar' ]:
		assert dbfs.validate_dbpath(testpath), f"{funcname()}: failed valid path {testpath}"

		path = dbfs.DBPath(testpath)
		assert path.path != '', f"{funcname()}: failed constructing valid dbpath {testpath}"
	
	for testpath in [ '', '/foo/', dbfs.DBPath('foo'), ' /foo ', '\\foo' ]:
		assert not dbfs.validate_dbpath(testpath), f"{funcname()}: passed invalid path {testpath}"

	assert dbfs.DBPath('/foo/').path != '/foo', \
		f"{funcname()}: DBPath constructor init adjustment failure: '/foo/'"
	assert dbfs.DBPath(' /foo/ ').path != '/foo', \
		f"{funcname()}: DBPath constructor init adjustment failure: '/foo/'"


if __name__ == '__main__':
	test_make_dblocal()

