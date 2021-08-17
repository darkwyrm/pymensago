from pymensago.utils import UUID, WAddress

class Message:
	def __init__(self):
		self.id = UUID()
		self.sender = WAddress()
		self.recipient = WAddress()
		# TODO: finish setup of Message class after date utility functions are complete
		# self.date = 
		self.thread_id = UUID()
		self.subject = ''
		self.body = ''
		self.images = list()
		self.attachments = list()

