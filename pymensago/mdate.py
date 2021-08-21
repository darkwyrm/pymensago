from retval import ErrOutOfRange, ErrUnimplemented, RetVal, ErrBadValue, ErrBadType

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
		
		# Now that we've obtained the date components and they have a valid length, let's make sure
		# the component values are in the basic ranges. We don't worry about leap year because this
		# class is just about storing, formatting, and transmitting the dates. It is the 
		# application's responsibility to ensure that the date itself actually existed.

		if y < 0 or m < 0 or d < 0:
			return RetVal(ErrOutOfRange, 'date components may not be negative')
		
		# Values of zero are ignored.
		
		if m > 12:
			return RetVal(ErrOutOfRange, 'month component out of range')
		
		if d > 31:
			return RetVal(ErrOutOfRange, 'day component out of range')

		self.year = y
		self.month = m
		self.day = d
		
		return RetVal()
