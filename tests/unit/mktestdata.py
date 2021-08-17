from pymensago.utils import UUID
from retval import RetVal

import pymensago.contacts as contacts
from pymensago.userprofile import profman

test_contacts = [
	{	'FormattedName': 					'Charlene Manley',
		'Gender': 							'Female',
		'Birthday': 						'19821105',
		'MailingAddresses.0.Label': 		'Home',
		'MailingAddresses.0.StreetAddress': '3224 Irish Ln.',
		'MailingAddresses.0.City': 			'La Crosse',
		'MailingAddresses.0.Region': 		'WI',
		'MailingAddresses.0.PostalCode': 	'54601',
		'Phone.0.Label': 					'Mobile',
		'Phone.0.Value': 					'555-770-1452',
		'Email.0.Label':					'Personal',
		'Email.0.Value':					'cmanley423@gmail.com',
		'Mensago.0.Label':					'Personal',
		'Mensago.0.UserID':					'charlene.manley',
		'Mensago.0.Workspace':				'0c147b47-36c5-4aff-8b6b-6916cc616eba',
		'Mensago.0.Domain':					'example.com',
		'Photo':							'images/female1.webp',
	},
	{	'FormattedName': 					'Alan Ortiz',
		'Gender': 							'Male',
		'Birthday': 						'19900110',
		'Bio':								'Proud zombie junkie. Gamer. Bacon trailblazer.',
		'MailingAddresses.0.Label': 		'Home',
		'MailingAddresses.0.StreetAddress': '1125 Mulberry St.',
		'MailingAddresses.0.City': 			'Coldspring',
		'MailingAddresses.0.Region': 		'TX',
		'MailingAddresses.0.PostalCode': 	'77331',
		'Phone.0.Label': 					'Mobile',
		'Phone.0.Value': 					'555-504-0699',
		'Email.0.Label':					'Personal',
		'Email.0.Value':					'ortiz-alan@hotmail.com',
		'Mensago.0.Label':					'Personal',
		'Mensago.0.UserID':					'alan.ortiz',
		'Mensago.0.Workspace':				'9f59e70a-0606-4725-9da1-c7850d66cef2',
		'Mensago.0.Domain':					'example.com',
		'Photo':							'images/male1.webp',
	},
	{	'FormattedName': 					'Stan Burbach',
		'Gender': 							'Male',
		'Birthday': 						'19710226',
		'MailingAddresses.0.Label': 		'Home',
		'MailingAddresses.0.StreetAddress': '1356 Lena Ln.',
		'MailingAddresses.0.City': 			'Jackson',
		'MailingAddresses.0.Region': 		'MS',
		'MailingAddresses.0.PostalCode': 	'39201',
		'Phone.0.Label': 					'Mobile',
		'Phone.0.Value': 					'555-573-3216',
		'Email.0.Label':					'Personal',
		'Email.0.Value':					'stantheman7@outlook.com',
		'Mensago.0.Label':					'Personal',
		'Mensago.0.UserID':					'stan.burbach',
		'Mensago.0.Workspace':				'da329fe1-d4bd-4a0d-80a4-8db879a83729',
		'Mensago.0.Domain':					'example.com',
		'Photo':							'images/male2.webp',
	},
	{	'FormattedName': 					'Lisa Behr',
		'Gender': 							'Female',
		'Birthday': 						'19631203',
		'MailingAddresses.0.Label': 		'Home',
		'MailingAddresses.0.StreetAddress': '3933 Braxton St.',
		'MailingAddresses.0.City': 			'Crystal Lake',
		'MailingAddresses.0.Region': 		'IL',
		'MailingAddresses.0.PostalCode': 	'60014',
		'Phone.0.Label': 					'Mobile',
		'Phone.0.Value': 					'555-595-8812',
		'Email.0.Label':					'Personal',
		'Email.0.Value':					'lbehr1963@gmail.com',
		'Mensago.0.Label':					'Personal',
		'Mensago.0.UserID':					'lisa.behr',
		'Mensago.0.Workspace':				'75fff6ee-1162-4ee6-b94a-aa4a10b67221',
		'Mensago.0.Domain':					'example.com',
		'Photo':							'images/female2.webp',
	},
	{	'FormattedName': 					'Rob Porter',
		'Gender': 							'Male',
		'Birthday': 						'20000715',
		'MailingAddresses.0.Label': 		'Home',
		'MailingAddresses.0.StreetAddress': '3540 Farm Meadow Dr.',
		'MailingAddresses.0.City': 			'Monterey',
		'MailingAddresses.0.Region': 		'TN',
		'MailingAddresses.0.PostalCode': 	'38574',
		'Phone.0.Label': 					'Mobile',
		'Phone.0.Value': 					'555-200-8030',
		'Email.0.Label':					'Personal',
		'Email.0.Value':					'bikerrob2@protonmail.com',
		'Mensago.0.Label':					'Personal',
		'Mensago.0.UserID':					'rob.porter',
		'Mensago.0.Workspace':				'a8f5629f-8adb-4687-8ff0-0fe755cee095',
		'Mensago.0.Domain':					'example.com',
	},
]

def mkcontacts() -> RetVal:
	'''Generates test contacts'''
	status = profman.get_active_profile()
	if status.error():
		return status
	profile = status['profile']
	
	conids = [	'3e15877f-28ce-46e5-924f-ea9b52c6c55e',
				'8a58af4c-15f6-4899-b630-65e257892c1d',
				'8a0067b7-fb16-44a3-8bfb-a8323008134c',
				'22029b1a-ada3-45d8-8038-861d98f1b24b',
				'7e3fdb59-14f3-4c10-b185-40a535b62184',
	]
	conindex = 0
	for item in test_contacts:
		conid = UUID(conids[conindex])
		contacts.delete_field(profile.db, conid, '*')
		for k,v in item.items():
			status = contacts.save_field(profile.db, conid, k, v, 'test')
			if status.error():
				return status.set_values({ 'key':k, 'value':v })
		conindex = conindex + 1

if __name__ == '__main__':
	profman.load_profiles()
	mkcontacts()
