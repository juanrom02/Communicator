import unittest
from mock import Mock, MagicMock, PropertyMock, patch
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

import communicator
import logger
import controllerClass
import transmitterClass
import emailClass
import modemClass
import networkClass
import ftpClass
import bluetoothClass
import callClass

import json

JSON_FILE = 'config.json'
JSON_CONFIG = json.load(open(JSON_FILE))

class CommunicatorTest(unittest.TestCase):
		
	def setUp(self):
		logger.write = MagicMock()
		
	#def tearDown(self):

#open()  ---------------------------------------------------------------

	def test_open_OK(self):
		print "%s" % sys._getframe().f_code.co_name
		communicator.alreadyOpen = False
		modemClass.Gsm = MagicMock()
		networkClass.Network = MagicMock()
		bluetoothClass.Bluetooth = MagicMock()
		emailClass.Email = MagicMock()
		ftpClass.Ftp = MagicMock()
		callClass.Call = MagicMock()
		controllerClass.Controller = MagicMock()
		transmitterClass.Transmitter = MagicMock()
		self.assertTrue(communicator.open())
		
		
	def test_open_ALREADY_OPEN(self):
		print "%s" % sys._getframe().f_code.co_name
		communicator.alreadyOpen = True;
		self.assertFalse(communicator.open())
		
#close()  --------------------------------------------------------------
		
	def test_close_OK(self):
		print "%s" % sys._getframe().f_code.co_name
		communicator.alreadyOpen = True;
		communicator.controllerInstance.join = MagicMock()
		communicator.controllerInstance.close = MagicMock()
		communicator.transmitterInstance.join = MagicMock()
		communicator.transmitterInstance.close = MagicMock()
		self.assertTrue(communicator.close())
		
		
	def test_close_ALREADY_CLOSED(self):
		print "%s" % sys._getframe().f_code.co_name
		communicator.alreadyOpen = False
		self.assertFalse(communicator.close())
		
#send()  ---------------------------------------------------------------
	
	msg = "test"
	receiver = "client04"	#contactList.py
	media = "EMAIL"
		
	def test_send_PLAINTEXT(self):
		print "%s" % sys._getframe().f_code.co_name
		communicator.alreadyOpen = True
		communicator.transmissionQueue.full = MagicMock(return_value = False)
		self.assertTrue(communicator.send(self.msg, self.receiver, self.media))
		
		
	def test_send_INSTANCE(self):
		print "%s" % sys._getframe().f_code.co_name
		communicator.alreadyOpen = True
		msg = "INSTANCEline1\nline2\nline3"
		communicator.transmissionQueue.full = MagicMock(return_value = False)
		self.assertTrue(communicator.send(msg, self.receiver, self.media))
		
		
	def test_send_FILE(self):
		print "%s" % sys._getframe().f_code.co_name
		communicator.alreadyOpen = True
		msg = "/home/pi/Communicator/Testing/communicatorTest.py"
		communicator.transmissionQueue.full = MagicMock(return_value = False)
		self.assertTrue(communicator.send(msg, self.receiver, self.media))
		
		
	def test_send_NOT_OPEN(self):
		print "%s" % sys._getframe().f_code.co_name
		communicator.alreadyOpen = False
		communicator.transmissionQueue.full = MagicMock(return_value = False)
		self.assertFalse(communicator.send(self.msg, self.receiver, self.media))
		
		
	def test_send_FULL_QUEUE(self):
		print "%s" % sys._getframe().f_code.co_name
		communicator.alreadyOpen = True
		communicator.transmissionQueue.full = MagicMock(return_value = True)
		self.assertFalse(communicator.send(self.msg, self.receiver, self.media))
		
		
	def test_send_NO_RECEIVER(self):
		print "%s" % sys._getframe().f_code.co_name
		communicator.alreadyOpen = True
		communicator.transmissionQueue.full = MagicMock(return_value = False)
		self.assertFalse(communicator.send(self.msg, None, self.media))
		
		
	def test_send_NO_MEDIA(self):
		print "%s" % sys._getframe().f_code.co_name
		communicator.alreadyOpen = True
		communicator.transmissionQueue.full = MagicMock(return_value = False)
		self.assertTrue(communicator.send(self.msg, self.receiver))
		
		
	def test_send_RECEIVER_NOT_ALLOWED(self):
		print "%s" % sys._getframe().f_code.co_name
		communicator.alreadyOpen = True
		receiver = "not_valid"
		communicator.transmissionQueue.full = MagicMock(return_value = False)
		self.assertFalse(communicator.send(self.msg, receiver, self.media))
		
#receive()  ------------------------------------------------------------

	def test_receive_OK(self):
		print "%s" % sys._getframe().f_code.co_name
		communicator.alreadyOpen = True
		communicator.receptionQueue.qsize = MagicMock(return_value = 2)
		msg = "mensaje"
		communicator.receptionQueue.get_nowait = MagicMock(return_value = [0, msg])
		self.assertEquals(communicator.receive(), msg)
		
	def test_receive_NOT_OPEN(self):
		print "%s" % sys._getframe().f_code.co_name
		communicator.alreadyOpen = False
		self.assertFalse(communicator.receive())
		
	def test_receive_QUEUE_EMPTY(self):
		print "%s" % sys._getframe().f_code.co_name
		communicator.alreadyOpen = True
		communicator.receptionQueue.qsize = MagicMock(return_value = 0)
		self.assertIsNone(communicator.receive())
		
#-----------------------------------------------------------------------

		
if __name__ == '__main__':
	unittest.main()
