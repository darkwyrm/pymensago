import inspect

import pymensago.mdate as mdate

def funcname() -> str: 
	frames = inspect.getouterframes(inspect.currentframe())
	return frames[1].function


def test_mdate():
	'''Tests the MDate class'''
	
	date = mdate.MDate()
	
	# This is not the right way io interact with these members. set() is preferred because it also
	# sets the format type in addition to validating the numbers
	date.year = 9999
	date.month = 12
	date.day = 32
	assert not date.is_valid(), f"{funcname}: is_valid() failure"

	assert date.set(2000, 5, 4), f"{funcname}: legitimate set() failed"
	assert date.format == mdate.MDATE_YYYYMMDD
	assert date.year == 2000 and date.day == 5 and date.day == 4, \
		f"{funcname}: value failure in assignment"
	
	assert not date.set(-1, 5, 4), f"{funcname}: year validation failure"
	assert not date.set(2000, 13, 4), f"{funcname}: month validation failure"
	assert not date.set(2000, 4, 31), f"{funcname}: day validation failure"

	# Because we don't change the object state unless given a valid value, it should still be set
	# to 20000504.
	assert date.year == 2000 and date.day == 5 and date.day == 4, \
		f"{funcname}: value failure in assignment"
	
	assert date.as_string() == '20000504', f"{funcname}: as_string formatting failure"

	# test format handling
	assert date.set(year=2000, month=5) and date.format == mdate.MDATE_YYYYMM, \
		f"{funcname}: set format YYYYMM failed"
	assert date.set(month=5, day=4) and date.format == mdate.MDATE_MMDD, \
		f"{funcname}: set format MMDD failed"
	assert date.set(2000) and date.format == mdate.MDATE_YYYY, f"{funcname}: set format YYYY failed"

	# test from_string() format handling
	assert date.from_string('20000504') and date.format == mdate.MDATE_YYYYMMDD, \
		f"{funcname}: from_string(YYYYMMDD) failed"
	assert date.from_string('200005') and date.format == mdate.MDATE_YYYYMM, \
		f"{funcname}: from_string(YYYYDD) failed"
	assert date.from_string('0504') and date.format == mdate.MDATE_MMDD, \
		f"{funcname}: from_string(MMDD) failed"
	assert date.from_string('2000') and date.format == mdate.MDATE_YYYY, \
		f"{funcname}: from_string(YYYY) failed"


def test_mdatetime():
	'''Tests the MDateTime class'''
	pass
