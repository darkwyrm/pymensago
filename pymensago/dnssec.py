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

	# Now that we have the IP address(es) to query for a DNSSEC record, start checking to see
	# if the domain is signed by DNSSEC
	
	# The DNSKEY record contains the verification key for the zone
	
	for ns_ip in ns_ips:
		request = dns.message.make_query(domain, dns.rdatatype.DNSKEY, want_dnssec=True)
		try:
			response = dns.query.udp(request, ns_ip, timeout=2.0)
		except:
			continue
		else:
			break

	if response.rcode():
		# Query failed -- either a server error or no DNSKEY record
		return RetVal(ErrNoDNSSEC)
	
	# The response should contain two RRSET items: DNSKEY and RRSIG
	records = response.answer
	if len(records) != 2:
		return RetVal(ErrNetworkError)

	# the DNSKEY should be self-signed, validate it

	dname = dns.name.from_text(domain)
	try:
		dns.dnssec.validate(records[0], records[1], { dname: records[0] } )
	except dns.dnssec.ValidationFailure as e:
		return RetVal().wrap_exception(e).set_error(ErrValidationFailure)

	return RetVal()


def check_ipv6(n):
    try:
        socket.inet_pton(socket.AF_INET6, n)
        return True
    except socket.error:
        return False


if __name__ == '__main__':
	status = check_dnssec('mensago.org')
	if status.error():
		print(status)
	else:
		print("No errors")

