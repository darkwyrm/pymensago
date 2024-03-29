from pymensago.utils import UUID, WAddress, size_as_string
from pymensago.mdate import MDateTime

class Message:
	'''This is just the base Message class which defines the interface for all child classes'''
	def __init__(self) -> None:
		self.id = UUID()
		self.sender = WAddress()
		self.recipient = WAddress()
		self.time = MDateTime()
		self.type = ''

	def flatten(self) -> dict:
		out = {
			'Version': '1.0',
			'ID': self.id.as_string(),
			'From': self.sender.as_string(),
			'To': self.recipient.as_string(),
			'Date': self.time.as_string(),
			'Type': self.type,
		}


class UserMessage (Message):
	def __init__(self) -> None:
		super().__init__()
		self.type = 'usermessage'
		self.cc = list()
		self.bcc = list()
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
		out = super().flatten()
		out['ThreadID'] = self.thread_id.as_string()
		out['Subject'] = self.subject
		out['Body'] = self.body

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


class SystemMessage (Message):
	'''This is the base class for all system messages'''
	def __init__(self) -> None:
		super().__init__()
		self.type = 'sysmessage'
		self.subtype = ''

	def flatten(self) -> dict:
		out = super().flatten()
		out['Subtype'] = self.subtype
		return out


# Constants for the different subtypes
CONTACT_REQUEST_INITIATE = 'contactreq.1'
CONTACT_REQUEST_RESPONSE = 'contactreq.2'
CONTACT_REQUEST_ACK = 'contactreq.3'

class ContactRequest (SystemMessage):
	'''This message type is used for messages used during the contact request process. Note that 
	the subtype must be specified before a ContactRequest instance can be used.'''
	def __init__(self, subtype='', contact_info=dict(), msg='') -> None:
		super().__init__()
		self.type = 'sysmessage'
		self.subtype = subtype
		self.contact_info = contact_info
		self.message = msg

	def flatten(self) -> dict:
		out = super().flatten()
		out['Subtype'] = self.subtype
		out['ContactInfo'] = self.contact_info
		out['Message'] = self.message
		return out
