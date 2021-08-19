from retval import RetVal, ErrBadValue, ErrBadType

# This module greatly simplifies working with dates and times within the Mensago codebase because
# only concerns itself with one date format and one time format in UTC only. It also is restricted
# to one of four groups of components: year, year-month, year-month-day, or month-day

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
	
