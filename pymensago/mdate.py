from retval import ErrUnimplemented, RetVal, ErrBadValue, ErrBadType

# This module greatly simplifies working with dates and times within the Mensago codebase because
# only concerns itself with one date format and one time format in UTC only. It also is restricted
# to one of four groups of components: year, year-month, year-month-day, or month-day. All date
# components are required to be padded by zeroes to ensure that the string is of the proper size.

class MDate:
	'''This class is for simple handling of dates, unlike datetime.'''
	def __init__(self, year=0, month=0, day=0):
		self.year = year
		self.month = month
		self.day = day
	
	def to_string(self):
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
		elif len(parts) == 2:
			try:
				first = int(parts[0])
				second = int(parts[1])
			except:
				return RetVal(ErrBadValue, 'date component is not an integer')

			if len(parts[0]) == 4:
				y = first
				m = second
			elif len(parts[0]) == 2:
				m = first
				d = second
			else:
				return RetVal(ErrBadValue, 'Short date format must be YYYY-MM or MM-DD')
			
		return RetVal(ErrUnimplemented)
