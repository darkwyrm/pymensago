from pymensago.utils import UUID, WAddress, size_as_string

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

	def to_string(self):
		out = [	f"Message ID: {self.id.as_string()}",
			f"Sender: {self.sender.as_string()}",
			f"Recipient: {self.recipient.as_string()}",
			# f"Date: f{self.date.as_string()}",
			f"Thread ID: {self.thread_id.as_string()}",
			f"Subject: {self.subject}",
			"Body:",
			self.body,
		]
		
		if len(self.images) > 0:
			imageline = [ "\nImages:" ]
			for image in self.images:
				imageline.append(image['Name'])
			out.append(' '.join(imageline))
		
		if len(self.attachments) > 0:
			out.append('\nAttachments:')
			for file in self.attachmetns:
				filesize = size_as_string((len(file['Data']) * 4) / 5)
				out.append(f"  {file['Name']}, {filesize}")
		
		return '\n'.join(out)

