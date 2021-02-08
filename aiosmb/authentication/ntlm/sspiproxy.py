from aiosmb import logger
from aiosmb.authentication.ntlm.native import NTLMAUTHHandler, NTLMHandlerSettings
from pyodidewsnet.sspiproxyws import SSPIProxyWS
import enum

class ISC_REQ(enum.IntFlag):
	DELEGATE = 1
	MUTUAL_AUTH = 2
	REPLAY_DETECT = 4
	SEQUENCE_DETECT = 8
	CONFIDENTIALITY = 16
	USE_SESSION_KEY = 32
	PROMPT_FOR_CREDS = 64
	USE_SUPPLIED_CREDS = 128
	ALLOCATE_MEMORY = 256
	USE_DCE_STYLE = 512
	DATAGRAM = 1024
	CONNECTION = 2048
	CALL_LEVEL = 4096
	FRAGMENT_SUPPLIED = 8192
	EXTENDED_ERROR = 16384
	STREAM = 32768
	INTEGRITY = 65536
	IDENTIFY = 131072
	NULL_SESSION = 262144
	MANUAL_CRED_VALIDATION = 524288
	RESERVED1 = 1048576
	FRAGMENT_TO_FIT = 2097152
	HTTP = 0x10000000

class SMBSSPIProxyNTLMAuth:
	def __init__(self, settings):
		self.settings = settings
		self.mode = None
		url = '%s://%s:%s' % (self.settings.proto, self.settings.host, self.settings.port)
		self.sspi = SSPIProxyWS(url, self.settings.agent_id)
		self.operator = None
		self.client = None
		self.target = None
		#self.ntlmChallenge = None
		self.iterations = 0
		
		self.session_key = None
		self.ntlm_ctx = NTLMAUTHHandler(NTLMHandlerSettings(None, 'MANUAL'))

	def setup(self):
		return
		
	@property
	def ntlmChallenge(self):
		return self.ntlm_ctx.ntlmChallenge
		
	def get_sealkey(self, mode = 'Client'):
		return self.ntlm_ctx.get_sealkey(mode = mode)
			
	def get_signkey(self, mode = 'Client'):
		return self.ntlm_ctx.get_signkey(mode = mode)
		
		
	def SEAL(self, signingKey, sealingKey, messageToSign, messageToEncrypt, seqNum, cipher_encrypt):
		return self.ntlm_ctx.SEAL(signingKey, sealingKey, messageToSign, messageToEncrypt, seqNum, cipher_encrypt)
		
	def SIGN(self, signingKey, message, seqNum, cipher_encrypt):
		return self.ntlm_ctx.SIGN(signingKey, message, seqNum, cipher_encrypt)
	
	def get_session_key(self):
		return self.session_key
		
	def get_extra_info(self):
		return self.ntlm_ctx.get_extra_info()
		
	def is_extended_security(self):
		return self.ntlm_ctx.is_extended_security()
	
	async def authenticate(self, authData = b'', flags = None, seq_number = 0, is_rpc = False):
		try:
			if is_rpc is True and flags is None:
				flags = ISC_REQ.REPLAY_DETECT | ISC_REQ.CONFIDENTIALITY| ISC_REQ.USE_SESSION_KEY| ISC_REQ.INTEGRITY| ISC_REQ.SEQUENCE_DETECT| ISC_REQ.CONNECTION
			elif flags is None:
				flags = ISC_REQ.CONNECTION

			if authData is None:
				status, ctxattr, data, err = await self.sspi.authenticate('NTLM', '', '', 3, flags.value, authdata = b'')
				if err is not None:
					raise err
				self.iterations += 1
				self.ntlm_ctx.load_negotiate(data)
				return data, True, None
			else:
				self.ntlm_ctx.load_challenge(authData)
				status, ctxattr, data, err = await self.sspi.authenticate('NTLM', '', '', 3, flags.value, authdata = authData)
				if err is not None:
					raise err
				if err is None:
					self.ntlm_ctx.load_authenticate(data)
					self.session_key, err = await self.sspi.get_sessionkey()
					if err is not None:
						raise err
					self.ntlm_ctx.load_sessionkey(self.get_session_key())
				
				await self.sspi.disconnect()
				return data, False, None
		except Exception as e:
			return None, None, e
		
	