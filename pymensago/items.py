# pylint: disable=too-many-instance-attributes,too-few-public-methods
# These classes are data containers and will have a lot of instance attributes and not many
# methods

from pymensago.utils import WAddress


class ClientItem():
	'''Provides a base interface for all client items'''
	def __init__(self):
		self.id = ''
		self.type = ''
		self.version = 0.0
		self.attachments = list()
		self.tags = list()	# client-side only field


class Event(ClientItem):
	'''Represents a calendar event'''
	def __init__(self):
		ClientItem.__init__(self)
		self.type = 'event'
		self.version = 0.1
		self.name = ''
		self.description = ''
		self.start = ''
		self.end = ''
		self.showstatus = 'busy'
		self.location = ''
		self.reminder = ''
		self.watchers = list()
		self.members = list()
		self.visibility = 'public'


class Message(ClientItem):
	'''Represents a message sent by a user.'''
	def __init__(self):
		ClientItem.__init__(self)
		self.type = 'usermessage'
		self.version = 1.0
		self.sender = WAddress()
		self.recipient = WAddress()
		self.cc = list()
		self.bcc = list()
		self.date = ''
		self.thread_id = ''
		self.subject = ''
		self.body = ''


class Note(ClientItem):
	'''Represents a note document'''
	def __init__(self):
		ClientItem.__init__(self)
		self.type = 'note'
		self.version = 1.0
		self.title = ''
		self.body = ''
		self.notebook = ''
		self.created = ''
		self.updated = ''
		self.watchers = list()
		self.members = list()


class Task(ClientItem):
	'''Represents a to-do item'''
	def __init__(self):
		ClientItem.__init__(self)
		self.type = 'task'
		self.version = 0.1
		self.title = ''
		self.description = ''
		self.created = ''
		self.due = ''
		self.status = 'Not started'
		self.completed = ''	# date of completion
		self.progress = 0	# Integer percentage of completion (0-100)
		self.checklist = list()
		self.watchers = list()
		self.members = list()

