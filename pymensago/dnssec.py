import dns.name
import dns.query
import dns.dnssec
import dns.message
import dns.resolver
import dns.rdatatype
import socket

import pymensago.utils as utils
from retval import RetVal, ErrBadValue, ErrNotFound, ErrBadType, ErrNetworkError

ErrNoDNSSEC = 'no DNSSEC for domain'
ErrDNSError = 'DNS error'
ErrValidationFailure = 'validation failure'

# def check_dnssec(domain: str) -> RetVal:
# 	'''Checks if the domain given is covered by DNSSEC'''

# 	# Doing a DNSSEC resolution is... involved... even with the great DNS package. :(
	
# 	# First get the nameservers for the domain
# 	try:
# 		response = dns.resolver.query(domain, dns.rdatatype.NS)
# 	except Exception as e:
# 		return RetVal().wrap_exception(e).set_error(ErrNotFound)

# 	# The NS records returned will give the names, not IP addresses, of the authoritative
# 	# name servers for the domain, so look up the IP address of the first name server
# 	ns_domain = response.rrset[0].to_text()
# 	response = dns.resolver.query(ns_domain, dns.rdatatype.A)
# 	ns_ip = response.rrset[0].to_text()

# 	# The DNSKEY record contains the verification key for the zone
# 	request = dns.message.make_query(domain, dns.rdatatype.DNSKEY, want_dnssec=True)
# 	response = dns.query.udp(request, ns_ip)
# 	if response.rcode():
# 		# Query failed -- either a server error or no DNSKEY record
# 		return RetVal(ErrNoDNSSEC)
	
# 	# The response should contain two RRSET records: DNSKEY and RRSIG
# 	records = response.answer
# 	if len(records) != 2:
# 		return RetVal(ErrNetworkError)

# 	# the DNSKEY should be self-signed, validate it
# 	name = dns.name.from_text(domain)
# 	try:
# 		dns.dnssec.validate(records[0], records[1], { name: records[0] } )
# 	except dns.dnssec.ValidationFailure:
# 		return RetVal(ErrValidationFailure)
	
# 	return RetVal()

drdnssec_support = ''
drdnssec_ips = list()

def check_resolver_support() -> str:
	'''Checks for the source to use to check DNSSEC signatures and returns a string indicating the
	source.
	
	Parameters:
	  * None
	
	Returns:
	  * 'default': the DNS servers in the network config support DNSSEC
	  * 'upstream': the authoritative server for the domain needs to be queried directly for DNSSEC
	'''
	global drdnssec_support, drdnssec_ips

	if drdnssec_support:
		return drdnssec_support

	drdnssec_support = 'upstream'
	
	# On most platforms, the OS has its own stub resolver and DNS cache. We'll try that first.
	# We know that the root domain is signed, so we'll try to get the DNSKEY for the root zone.
	# If our resolver doesn't return a record, then we know it doesn't support DNSSEC
	res = dns.resolver.get_default_resolver()
	for nsip in res.nameservers:
		request = dns.message.make_query('.', dns.rdatatype.DNSKEY, want_dnssec=True)
		response = dns.query.udp(request, nsip)
		if response.rcode() == 0 and len(response.answer) > 0:
			drdnssec_ips.append(nsip)
			drdnssec_support = 'default'

	return drdnssec_support
	

def check_dnssec(domain: str) -> RetVal:
	'''Checks if the domain given is covered by DNSSEC and validates records found.'''

	global drdnssec_support, drdnssec_ips

	if not drdnssec_support:
		check_resolver_support()

	# Get the nameserver for the domain
	ns_ips = list()
	if drdnssec_support == 'upstream':
		try:
			response = dns.resolver.resolve(domain, dns.rdatatype.NS)
		except Exception as e:
			return RetVal().wrap_exception(e).set_error(ErrNotFound)

		nslist = list()
		for rr in range(response.rrset):
			nslist.append(rr.to_text())
		
		if len(nslist) < 1:
			return RetVal(ErrDNSError, 'no nameservers found for domain')
		
		# TODO: translate domains to IP addresses and place into drdnssec_ips
		response = None
		for ns in nslist:
			try:
				response = dns.resolver.resolve(ns, dns.rdatatype.NS)
			except:
				# We'll skip the ones that have errors and just use the good entries
				continue

			if len(response.rrset) > 0:
				ns_ips.append(response.rrset[0].to_text())
		
		if len(ns_ips) == 0:
			return RetVal(ErrDNSError, 'no IP addresses found for nameservers')

	else:
		ns_ips.extend(drdnssec_ips)

	# Now that we have the IP address(es) to query for a DNSSEC record, start the resolution process

	# TODO: finish implementing check_dnssec()

	return RetVal(ErrNoDNSSEC)


status = check_dnssec('mensago.org')
if status.error():
	print(status)
else:
	print("No errors")

def check_ipv6(n):
    try:
        socket.inet_pton(socket.AF_INET6, n)
        return True
    except socket.error:
        return False