from pymensago.utils import UUID, WAddress, size_as_string
from pymensago.mdate import MDateTime

class Message:
	def __init__(self):
		self.id = UUID()
		self.sender = WAddress()
		self.recipient = WAddress()
		self.cc = list()
		self.bcc = list()
		self.time = MDateTime()
		self.thread_id = UUID()
		self.subject = ''
		self.body = ''
		self.images = list()
		self.attachments = list()

	def as_string(self):
		out = [	f"Message ID: {self.id.as_string()}",
			f"Sender: {self.sender.as_string()}",
			f"Recipient: {self.recipient.as_string()}",
			f"Date: {self.time.as_string()}",
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
			for file in self.attachments:
				filesize = "~" + size_as_string(int((len(file['Data']) * 4) / 5))
				out.append(f"  {file['Name']}, {filesize}")
		
		return '\n'.join(out)

	def flatten(self) -> dict:
		out = {
			'Type': 'usermessage',
			'Version': '1.0',
			'ID': self.id.as_string(),
			'From': self.sender.as_string(),
			'To': self.recipient.as_string(),
			'Date': self.time.as_string(),
			'ThreadID': self.thread_id.as_string(),
			'Subject': self.subject,
			'Body': self.body
		}

		if len(self.cc) > 0:
			out['CC'] = list()
			for item in self.cc:
				out['CC'].append(item.as_string())

		if len(self.bcc) > 0:
			out['BCC'] = list()
			for item in self.cc:
				out['BCC'].append(item.as_string())

		if len(self.images) > 0:
			out['Images'] = self.images

		if len(self.attachments) > 0:
			out['Attachments'] = self.attachments

		return out
