import datetime as dt
import re
import time

from retval import ErrOutOfRange, ErrUnimplemented, RetVal, ErrBadValue, ErrBadType

# This module greatly simplifies working with dates and times within the Mensago codebase because
# only concerns itself with one date format and one time format in UTC only. It also is restricted
# to one of four groups of components: year, year-month, year-month-day, or month-day. All date
# components are required to be padded by zeroes to ensure that the string is of the proper size.

# Date formats
MDATE_YYYYMMDD = 1
MDATE_YYYYMM = 2
MDATE_MMDD = 3
MDATE_YYYY = 4
MDATE_INVALID = -1

def _validate_date(y: int, m: int, d: int) -> RetVal:
	if y < 0 or m < 0 or d < 0:
		return RetVal(ErrOutOfRange, 'date components may not be negative')
	
	if m > 12:
		return RetVal(ErrOutOfRange, 'month component out of range')
	
	if m in [ 1,3,5,7,8,10,12 ]:
		if d > 31:
			return RetVal(ErrOutOfRange, 'day component out of range')
	elif m in [ 4,6,9,11 ]:
		if d > 31:
			return RetVal(ErrOutOfRange, 'day component out of range')
	elif m == 2:
		# It's annoying to handle leap year :/
		febmax = 28
		if m % 4 == 0 and m % 100 != 0:
			febmax = 29

		if d > febmax:
			return RetVal(ErrOutOfRange, 'day component out of range')


def _get_format_type(year: int, month: int, day: int) -> int:
	if year:
		if month:
			if day:
				return MDATE_YYYYMMDD
			else:
				return MDATE_YYYYMM
		else:
			if day:
				return MDATE_INVALID
			else:
				return MDATE_YYYY
	else:
		if month:
			return MDATE_MMDD
	
	return MDATE_INVALID


class MDate:
	'''This class is for simple handling of dates, unlike datetime.'''
	def __init__(self, year=0, month=0, day=0):
		self.year = year
		self.month = month
		self.day = day

		if _validate_date(year, month, day).error():
			self.format = MDATE_INVALID
		else:
			self.format = _get_format_type(year, month, day)

	def set(self, year, month, day) -> RetVal:
		self.year = year
		self.month = month
		self.day = day

		status = _validate_date(year, month, day).error()
		if status.error():
			self.format = MDATE_INVALID
		else:
			self.format = _get_format_type(year, month, day)
		return status

	def is_valid(self) -> RetVal:
		'''Returns an error if the object's values are invalid'''
		return _validate_date(self.year, self.month, self.day)

	def __str__(self) -> str:
		return self.as_string()

	def as_string(self) -> str:
		parts = []
		if self.year:
			parts.append(str(self.year))
		
		if self.month:
			if self.year:
				parts.append('-')
			parts.append(str(self.month))
		
		if self.day:
			if self.year or self.month:
				parts.append('-')
			parts.append(str(self.day))

		return ''.join(parts)
	
	def from_string(self, date: str) -> RetVal:
		'''Assigns a value to the object from a string. The format must be one of the following: 
		YYYY-MM-DD, YYYY-MM, MM-DD, or YYYY. The year may be from 1 to 9999.'''
		y = 0
		m = 0
		d = 0
		
		parts = date.split('-')
		if len(parts) == 3:
			try:
				y = int(parts[0])
				m = int(parts[1])
				d = int(parts[2])
			except:
				return RetVal(ErrBadValue, 'date component is not an integer')

			if len(y) != 4 or len(m) != 2 or len(d) != 2:
				return RetVal(ErrBadValue, 'date format must be YYYY-MM-DD')
			
		elif len(parts) == 2:
			try:
				first = int(parts[0])
				second = int(parts[1])
			except:
				return RetVal(ErrBadValue, 'date component is not an integer')

			if len(parts[0]) == 4 and len(parts[1] == 2):
				y = first
				m = second
			elif len(parts[0]) == 2 and len(parts[1] == 2):
				m = first
				d = second
			else:
				return RetVal(ErrBadValue, 'Short date format must be YYYY-MM or MM-DD')

		elif len(parts) == 1:		
			try:
				y = int(parts[0])
			except:
				return RetVal(ErrBadValue, 'date component is not an integer')

			if len(y) != 4:
				return RetVal(ErrBadValue, 'date format must be YYYY')
		
		else:
			return RetVal(ErrBadValue, 'invalid date format')
		
		status = _validate_date(y, m, d)
		if status.error():
			return status
		
		self.year = y
		self.month = m
		self.day = d
		self.format = _get_format_type(y,m,d)
		
		return RetVal()

	def unixtime(self) -> int:
		'''Returns the '''
		return int(dt.datetime(self.year, self.month, self.day, tzinfo=dt.timezone.utc).timestamp())

def today(self) -> MDate:
	'''Returns the current day in UTC time as an MDate object'''	
	cd = dt.date.today()
	return MDate(cd.year, cd.month, cd.day)


_re_date_time = re.compile(r'[0-3][0-9]{3}[0-1][0-9][0-3][0-0]T[0-2][0-9][0-5][0-9][0-5][0-9]Z')

class MDateTime:
	'''This class is for simplified handling of times, unlike time(), with resolution to the 
	second.'''
	def __init__(self, timestr=''):
		self.year = -1
		self.month = -1
		self.day = -1
		self.hour = -1
		self.minute = -1
		self.second = -1
		if timestr:
			self.from_string(timestr)

	def is_valid(self) -> bool:
		return self.year >= 0 and self.month >= 1 and self.day >= 1 \
			and self.hour >= 0 and self.minute >= 0 and self.second >= 0

	def now(self) -> object:
		'''Sets the current object to the current time UTC and returns itself'''
		t = time.gmtime()
		self.year = t.tm_year
		self.month = t.tm_mon
		self.day = t.tm_mday
		self.hour = t.tm_hour
		self.minute = t.tm_min
		self.second = t.tm_sec

		return self

	def as_string(self) -> str:
		'''Returns the object as a string'''
		return time.strftime(r"%Y%m%dT%H%M%SZ", 
						time.struct_time(tm_year=self.year, tm_mon=self.month, tm_mday=self.day, 
									tm_hour=self.hour, tm_min=self.minute, tm_sec=self.second,
									tm_isdst=0))

	def from_string(self, timestr: str) -> bool:
		if not timestr:
			self.year = self.month = self.day = self.hour = self.minute = self.second = -1
			return True
		
		# Strip out any separator characters and confirm that it meets the format
		t = timestr.translate(timestr.maketrans('','','-:/ '))
		if not _re_date_time.match(t):
			return False

		if len(t) < 16:
			return False
		
		try:
			year = int(t[0:4])
			mon = int(t[4:6])
			day = int(t[6:8])
			hour = int(t[9:11])
			min = int(t[11:13])
			sec = int(t[13:15])
		except:
			return False

		self.year = year
		self.month = mon
		self.day = day
		self.hour = hour
		self.min = min
		self.second = sec
		
		return True
