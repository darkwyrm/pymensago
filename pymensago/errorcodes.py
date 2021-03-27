# These are the RetVal error constants used to represent protocol errors

# Info Codes
MsgContinue = '100-Continue'
MsgPending = '101-Pending'
MsgItem = '102-Item'
MsgUpdate = '103-Update'
MsgTransfer = '104-Transfer'

# Success Codes
MsgOK = '200-OK'
MsgRegistered = '201-Registered'
MsgUnregistered = '202-Unregistered'

# Server Error Codes
MsgInternal = '300-Internal Server Error'
MsgNotImplemented = '301-Not Implemented'
MsgServerMaint = '302-Server Maintenance'
MsgServerUnavail = '303-Server Unavailable'
MsgRegClosed = '304-Registration Closed'
MsgInterrupted = '305-Interrupted'
MsgKeyFail = '306-Key Failure'
MsgDeliveryFailLimit = '307-Delivery Failure Limit Exceeded'
MsgDeliveryDelay = '308-Delivery Delay Not Reached'
MsgAlgoNotSupported = '309-Algorithm Not Supported'

# Client Error Codes
MsgBadRequest = '400-Bad Request'
MsgUnauthorized = '401-Unauthorized'
MsgAuthFailure = '402-Authentication Failure'
MsgForbidden = '403-Forbidden'
MsgNotFound = '404-Not Found'
MsgTerminated = '405-Terminated'
MsgPaymentReqd = '406-Payment Required'
MsgUnavailable = '407-Unavailable'
MsgResExists = '408-Resource Exists'
MsgQuotaInsuff = '409-Quota Insufficient'
MsgHashMismatch = '410-Hash Mismatch'
MsgBadKeycard = '411-Bad Keycard Data'
MsgNonComKeycard = '412-Noncompliant Keycard'
MsgInvalidSig = '413-Invalid Signature'
MsgLimitReached = '414-Limit Reached'
MsgExpired = '415-Expired'
