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

import transmitterClass
import messageClass
import contactList
import controllerClass
import modemClass
import networkClass
import bluetoothClass
import emailClass
import ftpClass
import callClass

import json
import Queue
import logger
import threading
import time

JSON_FILE = 'config.json'
JSON_CONFIG = json.load(open(JSON_FILE))

transmitterInstance = transmitterClass.Transmitter
transmitterInstance.gsmInstance = modemClass.Gsm
transmitterInstance.gprsInstance = networkClass.Network
transmitterInstance.wifiInstance = networkClass.Network
transmitterInstance.ethernetInstance = networkClass.Network
transmitterInstance.bluetoothInstance = bluetoothClass.Bluetooth
transmitterInstance.emailInstance = emailClass.Email
transmitterInstance.ftpInstance = ftpClass.Ftp
transmitterInstance.callInstance = callClass.Call


class TransmitterTest(unittest.TestCase):
	
	def setUp(self):
		logger.write = MagicMock()
		TRANSMISSION_QSIZE = JSON_CONFIG["COMMUNICATOR"]["TRANSMISSION_QSIZE"]
		transmissionQueue = Queue.PriorityQueue(TRANSMISSION_QSIZE)
		global transmitterInstance
		transmitterInstance = transmitterClass.Transmitter(transmissionQueue)
		
	def tearDown(self):
		global transmitterInstance
		del transmitterInstance
		patch.stopall()
		del logger.write
		
	def patch_verifyInternet(f):
		@patch("controllerClass.Controller.verifyInternetConnection")
		@patch('controllerClass.Controller.closeConnection')
		def functor(*args, **kwargs):
			return f(*args, **kwargs)
		return functor
	
	@patch("threading.Thread")
	def test_Transmitter_RUN(self, thread_call):
		print "%s" % sys._getframe().f_code.co_name
		transmitterClass.Transmitter.isActive = PropertyMock(side_effect = [True, True, False])
		message = messageClass.Message('client01', 'client02', 10)
		setattr(message, 'timeStamp', time.time())
		setattr(message, 'timeToLive', JSON_CONFIG["COMMUNICATOR"]["TIME_TO_LIVE"])
		transmitterInstance.transmissionQueue.get = MagicMock(return_value = [message.priority, message])
		
		transmitterInstance.run()
		thread_call.assert_called_once()
		
		del transmitterClass.Transmitter.isActive
		del message
		del transmitterInstance.transmissionQueue.get
		thread_call.stop()
		
	def test_Transmitter_TRY_SEND(self):
		print "%s" % sys._getframe().f_code.co_name
		message = messageClass.Message('client01', 'client02', 10)
		setattr(message, 'media', "GSM")
		setattr(message, 'timeStamp', time.time())
		setattr(message, 'timeToLive', JSON_CONFIG["COMMUNICATOR"]["TIME_TO_LIVE"])
		transmitterClass.Transmitter.setPriorities = MagicMock()
		transmitterClass.Transmitter.send = MagicMock(return_value = False)
		time.sleep = MagicMock()
		transmitterInstance.transmissionQueue.put = MagicMock()
		
		transmitterInstance.trySend(message)
		transmitterInstance.transmissionQueue.put.assert_called_once()
		
		del message
		del transmitterClass.Transmitter.setPriorities
		del transmitterClass.Transmitter.send
		del time.sleep
		del transmitterInstance.transmissionQueue.put
	
	def test_Transmitter_SET_PRIORITIES(self):
		modemClass.Gsm.telitConnected = PropertyMock(return_value = True)
		modemClass.Gsm.isActive = PropertyMock(return_value = True)
		networkClass.Network.isActive = PropertyMock(return_value = True)
		bluetoothClass.Bluetooth.isActive = PropertyMock(return_value = True)
		emailClass.Email.isActive = PropertyMock(return_value = True)
		ftpClass.Ftp.isActive = PropertyMock(return_value = True)
		
		print "%s: VOZ" % sys._getframe().f_code.co_name
		transmitterInstance.setPriorities("client02", "VOZ")
		self.assertEqual(transmitterInstance.callPriority, 10)

		print "%s: SMS" % sys._getframe().f_code.co_name
		transmitterInstance.setPriorities("client02", "SMS")
		self.assertEqual(transmitterInstance.smsPriority, 10)
		
		print "%s: GPRS" % sys._getframe().f_code.co_name
		transmitterInstance.setPriorities("client02", "GPRS")
		self.assertEqual(transmitterInstance.gprsPriority, 10)
		
		print "%s: WIFI" % sys._getframe().f_code.co_name
		transmitterInstance.setPriorities("client02", "WIFI")
		self.assertEqual(transmitterInstance.wifiPriority, 10)
		
		print "%s: ETHERNET" % sys._getframe().f_code.co_name
		transmitterInstance.setPriorities("client02", "ETHERNET")
		self.assertEqual(transmitterInstance.ethernetPriority, 10)
		
		print "%s: BLUETOOTH" % sys._getframe().f_code.co_name
		transmitterInstance.setPriorities("client02", "BLUETOOTH")
		self.assertEqual(transmitterInstance.bluetoothPriority, 10)
		
		print "%s: EMAIL" % sys._getframe().f_code.co_name
		transmitterInstance.setPriorities("client02", "EMAIL")
		self.assertEqual(transmitterInstance.emailPriority, 10)
		
		print "%s: FTP" % sys._getframe().f_code.co_name
		transmitterInstance.setPriorities("client02", "FTP")
		self.assertEqual(transmitterInstance.ftpPriority, 10)
		
		del modemClass.Gsm.telitConnected
		del modemClass.Gsm.isActive
		del networkClass.Network.isActive
		del bluetoothClass.Bluetooth.isActive
		del emailClass.Email.isActive
		del ftpClass.Ftp.isActive
		
	def test_Transmitter_SEND(self):
		message = messageClass.Message('client01', 'client02', 10)
		setattr(message, 'media', "GSM")
		setattr(message, 'timeStamp', time.time())
		setattr(message, 'timeToLive', JSON_CONFIG["COMMUNICATOR"]["TIME_TO_LIVE"])
		modemClass.Gsm.send = MagicMock(return_value = False)
		networkClass.Network.send = MagicMock(return_value = False)
		bluetoothClass.Bluetooth.send = MagicMock(return_value = False)
		emailClass.Email.send = MagicMock(return_value = False)
		ftpClass.Ftp.send = MagicMock(return_value = False)
		transmitterInstance.send = MagicMock(wraps = transmitterInstance.send)
		
		print "%s: VOZ" % sys._getframe().f_code.co_name
		transmitterInstance.callPriority = PropertyMock(return_value = 10)
		self.assertFalse(transmitterInstance.send(message))
		del transmitterInstance.callPriority
		
		print "%s: SMS" % sys._getframe().f_code.co_name
		transmitterInstance.smsPriority = PropertyMock(return_value = 10)
		self.assertFalse(transmitterInstance.send(message))
		self.assertEqual(modemClass.Gsm.send.call_count, 2)
		del transmitterInstance.smsPriority
		
		print "%s: GPRS" % sys._getframe().f_code.co_name
		transmitterInstance.gprsPriority = PropertyMock(return_value = 10)
		self.assertFalse(transmitterInstance.send(message))
		del transmitterInstance.gprsPriority
		
		print "%s: WIFI" % sys._getframe().f_code.co_name
		transmitterInstance.wifiPriority = PropertyMock(return_value = 10)
		self.assertFalse(transmitterInstance.send(message))
		del transmitterInstance.wifiPriority
		
		print "%s: ETHERNET" % sys._getframe().f_code.co_name
		transmitterInstance.ethernetPriority = PropertyMock(return_value = 10)
		self.assertFalse(transmitterInstance.send(message))
		self.assertEqual(networkClass.Network.send.call_count, 3)
		del transmitterInstance.ethernetPriority
		
		
		print "%s: BLUETOOTH" % sys._getframe().f_code.co_name
		transmitterInstance.bluetoothPriority = PropertyMock(return_value = 10)
		self.assertFalse(transmitterInstance.send(message))
		bluetoothClass.Bluetooth.send.assert_called_once()
		del transmitterInstance.bluetoothPriority
		
		print "%s: EMAIL" % sys._getframe().f_code.co_name
		transmitterInstance.emailPriority = PropertyMock(return_value = 10)
		self.assertFalse(transmitterInstance.send(message))
		emailClass.Email.send.assert_called_once()
		del transmitterInstance.emailPriority
		
		print "%s: FTP" % sys._getframe().f_code.co_name
		transmitterInstance.ftpPriority = PropertyMock(return_value = 10)
		self.assertFalse(transmitterInstance.send(message))
		ftpClass.Ftp.send.assert_called_once()
		del transmitterInstance.ftpPriority
		
		del message
		del modemClass.Gsm.send
		del networkClass.Network.send
		del bluetoothClass.Bluetooth.send
		del emailClass.Email.send
		del ftpClass.Ftp.send
		


if __name__ == '__main__':
	unittest.main()
