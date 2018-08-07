import unittest
from mock import MagicMock, PropertyMock, patch, mock_open
import mock
import os
import sys

os.chdir("..")
	
sys.path.append(os.getcwd())
sys.path.append(os.path.abspath('Email/'))
sys.path.append(os.path.abspath('Modem/'))
sys.path.append(os.path.abspath('Network/'))
sys.path.append(os.path.abspath('Bluetooth/'))
sys.path.append(os.path.abspath('File Transfer/'))
sys.path.append(os.path.abspath('Audio/'))

import emailClass
import modemClass
import messageClass
from modemClass import ATCommandError, AtNewCall

import json
import Queue
import logger
import smtplib
import imaplib
import threading
import email
from email import encoders
from email.header import decode_header, make_header
import mimetypes
import pickle

JSON_FILE = 'config.json'
JSON_CONFIG = json.load(open(JSON_FILE))

emailInstance = emailClass.Email
emailInstance.gsmInstance = modemClass.Gsm
emailInstance.smtpServer = smtplib.SMTP_SSL
emailInstance.imapServer = imaplib.IMAP4_SSL

emailString = '''Date: Mon, 06 Nov 2016 16:33:29-0300 
From: Telit <client02.datalogger@gmail.com>
Subject: Asunto del mensaje 
To: destino@dominio.com
MIME-Version: 1.0 
Content-Type: multipart/mixed; boundary="delimitador"

--delimitador
Content-Type: text/plain 

Cuerpo del mensaje 

--delimitador 
Content-Type: text/plain

INSTANCEccopy_reg\n_reconstructor\np0\n(cmessageClass\nInfoMessage\np1\nc__builtin__\nobject\np2\nNtp3\nRp4\n(dp5\nS'infoText'\np6\nS'alskeufhd'\np7\nsS'sender'\np8\nS'Juancete'\np9\nsS'receiver'\np10\nS'client05'\np11\nsS'priority'\np12\nI10\nsb.

--delimitador 
Content-Type: image/jpeg
Content-Disposition: attachment; filename="imagen.jpg"
Content-Transfer-Encoding: base64
 AAQSkZJRgABAQAAAQABAAD2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODwwQFxQYGBcUFhYaHSUfGhsjHBYWICwgIyYnKSopGR8tMC0oMCUoKSj2wBDAQcHBwoIChMKChMoGhYaKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCj/wAARCAAWABYDASIAAhEBAxEB8QAFwABAQEBAAAAAAAAAAAAAAAAAAUGBEACkQAAEDAwMDAwUBAAAAAAAAAAECAwQABhEFEiETMUEUYaEHFSIycYH/xAAWAQEBAQAAAAAAAAAAAAAAAAAAAQLxAAWEQEBAQAAAAAAAAAAAAAAAAAAAUH/2gAMAwEAAhEDEQAAO8XreH2N1MOEwH5yk7ju/VsHtnHc+1YlF63Qh3qqdaWjOemWU7fgZavX3a7WoapMXNfkRok9tKPVMK2qZUABjdghJwAQTxyajSpnpqoMoOXBrrbbzDDJc9YkbA0E3gKSdvClbcqPkk9s1qSbUb6zbnbuKO6FNdCWzjqN5yCD2I9uP8pUyxNFETUJM5veIxaDDSl8dTkEq/nA585NKyrbEBQIIBB8GoU2247jyXISxC/NK3ENo GxZBBzjjCvGfPkGlKC9SlKD//2Q== 

--delimitador--'''

class EmailTest(unittest.TestCase):
	
	def setUp(self):
		logger.write = MagicMock()
		RECEPTION_QSIZE = JSON_CONFIG["COMMUNICATOR"]["RECEPTION_QSIZE"]
		receptionQueue = Queue.PriorityQueue(RECEPTION_QSIZE)
		global emailInstance
		emailInstance = emailClass.Email(receptionQueue)
		emailInstance.smtpServer = MagicMock(spec = smtplib.SMTP_SSL)
		emailInstance.imapServer = MagicMock(spec = imaplib.IMAP4_SSL)
		
	def tearDown(self):
		global emailInstance
		del emailInstance
		patch.stopall()
		del logger.write
		
	def test_Email_CLOSE_TELIT(self):
		print "%s" % sys._getframe().f_code.co_name
		modemClass.Gsm.telitConnected = PropertyMock(return_value = True)
		emailInstance.telit_lock = MagicMock(spec = threading.Condition)
		emailInstance.telit_lock.acquire = MagicMock()
		emailInstance.telit_lock.wait = MagicMock()
		modemClass.Gsm.active_call = PropertyMock(side_effect = [True, False])
		emailInstance.sendSSLCommand = MagicMock()
		modemClass.Gsm.sendAT = MagicMock()
		
		emailInstance.close()
		emailInstance.telit_lock.wait.assert_called_once()
		
		del modemClass.Gsm.telitConnected
		del emailInstance.telit_lock
		del modemClass.Gsm.active_call
		del emailInstance.sendSSLCommand
		del modemClass.Gsm.sendAT
		
	def test_Email_CLOSE_SERVERS(self):
		print "%s" % sys._getframe().f_code.co_name
		emailInstance.smtpServer.quit = MagicMock()
		
		emailInstance.close()
		emailInstance.smtpServer.quit.assert_called_once()
		
		del emailInstance.smtpServer.quit
		
	@patch("smtplib.SMTP_SSL")
	@patch("imaplib.IMAP4_SSL")
	def test_Email_CONNECT(self, imap_call, smtp_call):
		print "%s" % sys._getframe().f_code.co_name
		emailClass.Email.mode = PropertyMock(return_value = 1)
		emailInstance.smtpServer.login = MagicMock()
		
		self.assertTrue(emailInstance.connect())
		emailInstance.smtpServer.login.assert_called_once()
		
		del emailInstance.smtpServer.login
		del emailClass.Email.mode
		
	def test_Email_CONNECT_TELIT(self):
		print "%s" % sys._getframe().f_code.co_name
		emailClass.Email.mode = PropertyMock(return_value = 3)
		emailInstance.telit_lock = MagicMock(spec = threading.Condition)
		emailInstance.telit_lock.acquire = MagicMock()
		emailInstance.telit_lock.wait = MagicMock()
		emailInstance.telit_lock.release = MagicMock(side_effect = Exception)
		modemClass.Gsm.active_call = PropertyMock(side_effect = [True, False])
		
		self.assertFalse(emailInstance.connect())
		logger.write.assert_called_once()
		
		del emailClass.Email.mode
		del emailInstance.telit_lock
		del modemClass.Gsm.active_call
		
	def test_Email_SEND_SSL(self):
		print "%s" % sys._getframe().f_code.co_name
		modemClass.Gsm.new_call = PropertyMock(return_value = False)
		modemClass.Gsm.sendAT = MagicMock(side_effect = ["","", "executed"])
		
		self.assertEqual("executed", emailInstance.sendSSLCommand("CMD"))
		
		del modemClass.Gsm.new_call
		del modemClass.Gsm.sendAT
	
	@patch("threading.Thread")
	def test_Email_TELIT_IMAP(self, thread_call):
		print "%s" % sys._getframe().f_code.co_name
		modemClass.Gsm.sendAT = MagicMock()
		emailInstance.sendSSLCommand = MagicMock(side_effect = Exception("error"))
		emailClass.Email.isActive = PropertyMock(return_value = True)
		
		emailInstance.telitIMAPConnect()
		thread_call.assert_called_once()
		
		del modemClass.Gsm.sendAT
		del emailInstance.sendSSLCommand
		del emailClass.Email.isActive
		
	@patch("email.mime.text.MIMEText")
	def test_Email_SEND_PLAINTEXT(self, mimetext_call):
		print "%s" % sys._getframe().f_code.co_name
		message = messageClass.Message('client01', 'client02', 10)
		setattr(message, "plainText", "example")
		emailInstance.clientName = PropertyMock(return_value = "client")
		emailInstance.emailAccount = PropertyMock(return_value = "example@domain.com")
		emailInstance.sendMessage = MagicMock(return_value = True)
		
		self.assertTrue(emailInstance.send(message, "destination@domain.com"))
		mimetext_call.assert_called_once()
		
		del message
		del emailInstance.clientName
		del emailInstance.emailAccount
		del emailInstance.sendMessage
		
	def Email_sendFile(self, mime_call, mimetype):
		message = messageClass.Message('client01', 'client02', 10)
		setattr(message, "fileName", "/tmp/activeInterfaces")
		emailInstance.clientName = PropertyMock(return_value = "client")
		emailInstance.emailAccount = PropertyMock(return_value = "example@domain.com")
		emailInstance.sendMessage = MagicMock(return_value = True)
		mimetypes.guess_type = MagicMock(return_value = [mimetype])
		file_patch = mock_open()
		patch("__builtin__.open", file_patch).start()
		file_op = file_patch()
		file_op.read = MagicMock()		
		
		self.assertTrue(emailInstance.send(message, "destination@domain.com"))
		mime_call.assert_called_once()
		
		del message
		del emailInstance.clientName
		del emailInstance.emailAccount
		del emailInstance.sendMessage
		del mimetypes.guess_type
		del file_patch
		del file_op
		
		
	@patch("email.mime.text.MIMEText")
	def test_Email_SEND_FILE_TEXT(self, mimetext_call):
		print "%s" % sys._getframe().f_code.co_name
		self.Email_sendFile(mimetext_call, "text/subtype")
		
	@patch("email.mime.image.MIMEImage")
	def test_Email_SEND_FILE_IMAGE(self, mimeimage_call):
		print "%s" % sys._getframe().f_code.co_name
		self.Email_sendFile(mimeimage_call, "image/subtype")
		
	@patch("email.mime.audio.MIMEAudio")
	def test_Email_SEND_FILE_AUDIO(self, mimeaudio_call):
		print "%s" % sys._getframe().f_code.co_name
		self.Email_sendFile(mimeaudio_call, "audio/subtype")
		
	@patch("email.mime.base.MIMEBase")
	def test_Email_SEND_FILE_OTHER(self, mimebase_call):
		print "%s" % sys._getframe().f_code.co_name
		encoders.encode_base64 = MagicMock()
		
		self.Email_sendFile(mimebase_call, "other/subtype")
		
		del encoders.encode_base64
		
	@patch("pickle.dumps")
	def test_Email_SEND_INSTANCE(self, dumps_call):
		print "%s" % sys._getframe().f_code.co_name
		message = messageClass.Message('client01', 'client02', 10)
		emailInstance.clientName = PropertyMock(return_value = "client")
		emailInstance.emailAccount = PropertyMock(return_value = "example@domain.com")
		emailInstance.sendMessage = MagicMock(return_value = True)
		
		self.assertTrue(emailInstance.send(message, "destination@domain.com"))
		dumps_call.assert_called_once()
		
		del message
		del emailInstance.clientName
		del emailInstance.emailAccount
		del emailInstance.sendMessage
		
	@patch("email.mime.text.MIMEText.as_string")
	def test_Email_SENDMESSAGE_TELIT(self, asstr_call):
		print "%s" % sys._getframe().f_code.co_name
		mime = email.mime.text.MIMEText("example")
		emailInstance.gsmInstance.telitConnected = PropertyMock(return_value = True)
		emailInstance.telit_lock = MagicMock(spec = threading.Lock)
		emailInstance.telit_lock.acquire = MagicMock()
		emailInstance.telit_lock.release = MagicMock()
		emailInstance.telit_lock.wait = MagicMock()
		emailInstance.gsmInstance.active_call = PropertyMock(side_effect = [True, False])
		emailInstance.sendSSLCommand = MagicMock()
		emailInstance.gsmInstance.sendAT = MagicMock()
		emailInstance.telitIMAPConnect = MagicMock()
		
		self.assertTrue(emailInstance.sendMessage(mime))
		emailInstance.telit_lock.wait.assert_called_once()
		
		del mime
		del emailInstance.gsmInstance.telitConnected
		del emailInstance.telit_lock
		del emailInstance.gsmInstance.active_call
		del emailInstance.sendSSLCommand
		del emailInstance.gsmInstance.sendAT
		del emailInstance.telitIMAPConnect
	
	
	def test_Email_SENDMESSAGE_EXCEPT(self):
		print "%s" % sys._getframe().f_code.co_name
		mime_msg = email.mime.text.MIMEText("example")
		emailInstance.gsmInstance.telitConnected = PropertyMock(return_value = True)
		emailInstance.telit_lock = MagicMock(spec = threading.Lock)
		emailInstance.telit_lock.acquire = MagicMock()
		emailInstance.telit_lock.release = MagicMock()
		emailInstance.gsmInstance.active_call = PropertyMock(return_value = False)
		emailInstance.sendSSLCommand = MagicMock()
		emailInstance.gsmInstance.sendAT = MagicMock(side_effect = [AtNewCall, ""])
		emailInstance.telitIMAPConnect = MagicMock()
		
		self.assertRaises(AtNewCall, emailInstance.sendMessage(mime_msg))
		
		del mime_msg
		del emailInstance.gsmInstance.telitConnected
		del emailInstance.telit_lock
		del emailInstance.gsmInstance.active_call
		del emailInstance.sendSSLCommand
		del emailInstance.gsmInstance.sendAT
		del emailInstance.telitIMAPConnect
		
	@patch("emailClass.Email.receiveAttachment")
	@patch("pickle.loads")
	@patch("threading.Thread")
	def test_Email_RECEIVE(self, thread_call, loads_call, receiveatt_call):
		print "%s" % sys._getframe().f_code.co_name
		emailClass.Email.isActive = PropertyMock(side_effect = [True, True, True, True, False, False])
		emailClass.Email.mode = PropertyMock(return_value = 1)
		search = ["OK", ["123",""]]
		fetch = ["OK", [["", emailString], ""]]
		emailInstance.imapServer.uid = MagicMock(side_effect = [search, fetch])
		emailInstance.getSourceName = MagicMock()
		emailInstance.getSourceEmail = MagicMock(return_value = "client02.datalogger@gmail.com")
		emailInstance.receptionQueue.put = MagicMock()
		
		emailInstance.receive()
		emailInstance.imapServer.recent.assert_called_once()
		self.assertEqual(emailInstance.imapServer.uid.call_count, 2)
		receiveatt_call.assert_called_once()
		loads_call.assert_called_once()
		self.assertEqual(emailInstance.receptionQueue.put.call_count, 2)
		thread_call.assert_called_once()
		
		del emailClass.Email.isActive
		del emailClass.Email.mode
		del search
		del fetch
		del emailInstance.imapServer.uid
		del emailInstance.getSourceName
		del emailInstance.getSourceEmail
		del emailInstance.receptionQueue.put
		
	@patch("threading.Thread")
	def test_Email_RECEIVE_TELIT(self, thread_call):
		print "%s" % sys._getframe().f_code.co_name
		emailClass.Email.isActive = PropertyMock(side_effect = [True, True, True, True, False, False])
		emailClass.Email.mode = PropertyMock(return_value = 3)
		emailInstance.telit_lock = MagicMock(spec = threading.Condition)
		emailInstance.telit_lock.acquire = MagicMock()
		emailInstance.telit_lock.release = MagicMock()
		emailInstance.gsmInstance.active_call = PropertyMock(return_value = False)
		emailInstance.sendSSLCommand = MagicMock(side_effect = ["", ["", "", "123"]])
		emailInstance.gsmInstance.sendAT = MagicMock(side_effect = ["", "x" + emailString + "xx", ""])
		emailInstance.getSourceName = MagicMock()
		emailInstance.getSourceEmail = MagicMock(return_value = "clientnotvalid@gmail.com")
		emailInstance.sendMessage = MagicMock(side_effect = Exception)
		
		emailInstance.receive()
		emailInstance.imapServer.recent.assert_not_called()
		emailInstance.sendMessage.assert_called_once()
		thread_call.assert_called_once()
		
		del emailClass.Email.isActive
		del emailClass.Email.mode
		del emailInstance.telit_lock.acquire
		del emailInstance.telit_lock.release
		del emailInstance.telit_lock
		del emailInstance.gsmInstance.active_call
		del emailInstance.sendSSLCommand
		del emailInstance.gsmInstance.sendAT
		del emailInstance.getSourceName
		del emailInstance.getSourceEmail
		del emailInstance.sendMessage
		
	@patch("os.mkdir")
	@patch("os.path.isfile")
	def test_Email_RECEIVEATT(self, isfile_call, mkdir_call):
		print "%s" % sys._getframe().f_code.co_name
		emailHeader = email.message.Message()
		emailHeader.get_filename = MagicMock(return_value = "file.txt")
		emailHeader.get_payload = MagicMock()
		isfile_call.return_value = False
		file_patch = mock_open()
		patch("__builtin__.open", file_patch).start()
		file_op = file_patch()
		file_op.write = MagicMock()
		emailInstance.receptionQueue.put = MagicMock()
		
		self.assertTrue(emailInstance.receiveAttachment(emailHeader))
		mkdir_call.assert_not_called()
		emailInstance.receptionQueue.put.assert_called_once()
		
		del emailHeader
		del file_patch
		del file_op
		del emailInstance.receptionQueue.put
		
	def test_Email_GETSOURCENAME(self):
		print "%s" % sys._getframe().f_code.co_name
		emailExample = email.message.Message()
		emailExample.get = MagicMock(return_value = "Juan Perez <example@domain.com>")
		
		self.assertEqual(emailInstance.getSourceName(emailExample), "Juan Perez")

		del emailExample.get
		del emailExample
		
			
	def test_Email_GETSOURCEEMAIL(self):
		print "%s" % sys._getframe().f_code.co_name
		emailExample = email.message.Message()
		emailExample.get = MagicMock(return_value = "Juan Perez <example@domain.com>")
		
		self.assertEqual(emailInstance.getSourceEmail(emailExample), "example@domain.com")

		del emailExample.get
		del emailExample
		
	def test_Email_DELETEEMAIL(self):
		print "%s" % sys._getframe().f_code.co_name
		emailInstance.gsmInstance.telitConnected = PropertyMock(return_value = False)
		
		emailInstance.deleteEmail(123)
		emailInstance.imapServer.store.assert_called_once()
		emailInstance.imapServer.expunge.assert_called_once()
					
		del emailInstance.gsmInstance.telitConnected
		
	def test_Email_DELETEEMAIL_TELIT(self):
		print "%s" % sys._getframe().f_code.co_name
		emailInstance.gsmInstance.telitConnected = PropertyMock(return_value = True)
		emailInstance.sendSSLCommand = MagicMock()
		
		emailInstance.deleteEmail(123)
		self.assertEqual(emailInstance.sendSSLCommand.call_count, 2)
					
		del emailInstance.sendSSLCommand
		
if __name__ == '__main__':
	unittest.main()
		
