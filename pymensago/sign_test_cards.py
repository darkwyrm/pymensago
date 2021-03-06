# Script used to generate hashes and signatures for unit tests based on standard test data

# User Signing Key: p;XXU0XF#UO^}vKbC-wS(#5W6=OEIFmR2z`rS1j+
# User Verification Key: 6|HBWrxMY6-?r&Sm)_^PLPerpqOj#b&x#N_#C3}p

# User Contact Request Signing Key: ip52{ps^jH)t$k-9bc_RzkegpIW?}FFe~BX&<V}9
# User Contact Request Verification Key: d0-oQb;{QxwnO{=!|^62+E=UYk2Y3mr2?XKScF4D

# User Contact Request Encryption Key: j(IBzX*F%OZF;g77O8jrVjM1a`Y<6-ehe{S;{gph
# User Contact Request Decryption Key: 55t6A0y%S?{7c47p(R@C*X#at9Y`q5(Rc#YBS;r}

# User Primary Encryption Key: nSRso=K(WF{P+4x5S*5?Da-rseY-^>S8VN#v+)IN
# User Primary Decryption Key: 4A!nTPZSVD#tm78d=-?1OIQ43{ipSpE;@il{lYkg

# Organization Primary Signing Key: msvXw(nII<Qm6oBHc+92xwRI3>VFF-RcZ=7DEu3|
# Organization Primary Verification Key: )8id(gE02^S<{3H>9B;X4{DuYcb`%wo^mC&1lN88

# Organization Encryption Key: @b?cjpeY;<&y+LSOA&yUQ&ZIrp(JGt{W$*V>ATLG
# Organization Decryption Key: nQxAR1Rh{F4gKR<KZz)*)7}5s_^!`!eb!sod0<aT

import base64
import os
from pathlib import Path

import hashlib
import nacl.signing

def sign_org_card():
	'''Create a signed organization keycard from test_org_card.kc'''
	current_dir = Path(os.path.realpath(__file__)).parent
	orgcard_path = current_dir.joinpath("test_org_card.kc")

	orgcard_data = b''
	try:
		with open(orgcard_path, 'rb') as f:
			orgcard_data = f.read()
	except Exception as e:
		print(f"Couldn't open {orgcard_path}: {e}")
		return
	
	org_signing_key85 = "msvXw(nII<Qm6oBHc+92xwRI3>VFF-RcZ=7DEu3|"
	key = nacl.signing.SigningKey(base64.b85decode(org_signing_key85))

	# Add the entry hash
	hasher = hashlib.blake2b(digest_size=32)
	hasher.update(orgcard_data)
	orgcard_data = orgcard_data + b"Hash:BLAKE2B-256:" + base64.b85encode(hasher.digest()) + \
		b"\r\n"
	
	# Org sign the keycard
	signed = key.sign(orgcard_data)
	signature = base64.b85encode(signed.signature)
	orgcard_data = orgcard_data + b"Organization-Signature:ED25519:" + signature + b"\r\n"

	signedcard_path = current_dir.joinpath("test_org_card_signed.kc")
	try:
		with open(signedcard_path, 'wb') as f:
			f.write(orgcard_data)
		print(f"Saved signed data to {signedcard_path}")
	except Exception as e:
		print(f"Couldn't save {signedcard_path}: {e}")
		return

	print(orgcard_data.decode())


def sign_user_card():
	'''Create a signed user keycard from test_user_card.kc'''
	current_dir = Path(os.path.realpath(__file__)).parent
	usercard_path = current_dir.joinpath("test_user_card.kc")

	usercard_data = b''
	try:
		with open(usercard_path, 'rb') as f:
			usercard_data = f.read()
	except Exception as e:
		print(f"Couldn't open {usercard_path}: {e}")
		return
	
	org_signing_key85 = "msvXw(nII<Qm6oBHc+92xwRI3>VFF-RcZ=7DEu3|"
	okey = nacl.signing.SigningKey(base64.b85decode(org_signing_key85))

	# user sign the keycard
	signed = okey.sign(usercard_data)
	signature = base64.b85encode(signed.signature)
	usercard_data = usercard_data + b"Organization-Signature:ED25519:" + signature + b"\r\n"
	
	# Add the entry hash
	hasher = hashlib.blake2b(digest_size=32)
	hasher.update(usercard_data)
	usercard_data = usercard_data + b"Hash:BLAKE2B-256:" + base64.b85encode(hasher.digest()) + \
		b"\r\n"
	
	# user sign the keycard
	user_signing_key85 = "p;XXU0XF#UO^}vKbC-wS(#5W6=OEIFmR2z`rS1j+"
	ukey = nacl.signing.SigningKey(base64.b85decode(user_signing_key85))

	signed = ukey.sign(usercard_data)
	signature = base64.b85encode(signed.signature)
	usercard_data = usercard_data + b"User-Signature:ED25519:" + signature + b"\r\n"

	signedcard_path = current_dir.joinpath("test_user_card_signed.kc")
	try:
		with open(signedcard_path, 'wb') as f:
			f.write(usercard_data)
		print(f"Saved signed data to {signedcard_path}")
	except Exception as e:
		print(f"Couldn't save {signedcard_path}: {e}")
		return

	print(usercard_data.decode())


if __name__ == '__main__':
	sign_org_card()
	sign_user_card()
