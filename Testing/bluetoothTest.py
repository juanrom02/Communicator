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

import bluetoothClass
import bluetoothTransmitter
import bluetoothReceptor
import messageClass

import json
import Queue
import logger
import bluetooth
import threading
import socket

JSON_FILE = 'config.json'
JSON_CONFIG = json.load(open(JSON_FILE))

bluetoothInstance = bluetoothClass.Bluetooth

class BluetoothTest(unittest.TestCase):
	
	def setUp(self):
		logger.write = MagicMock()
		RECEPTION_QSIZE = JSON_CONFIG["COMMUNICATOR"]["RECEPTION_QSIZE"]
		receptionQueue = Queue.PriorityQueue(RECEPTION_QSIZE)
		global bluetoothInstance
		bluetoothInstance = bluetoothClass.Bluetooth(receptionQueue)
		
	def tearDown(self):
		global bluetoothInstance
		del bluetoothInstance
		patch.stopall()
		del logger.write
		
	@patch("bluetooth.BluetoothSocket")
	@patch("bluetooth.advertise_service")
	def test_Bluetooth_CONNECT(self, bt_service, bt_socket):
		print "%s" % sys._getframe().f_code.co_name
		bluetooth.advertise_service = MagicMock()
		error = bluetooth._bluetooth.error(10,1024)
		btTransmitter = patch("bluetoothTransmitter.BluetoothTransmitter", new = MagicMock(side_effect = error))
		btTransmitter.start()
		
		self.assertFalse(bluetoothInstance.connect("11:22:33:44:55:66"))
		
		del bluetooth.advertise_service
		del error

	@patch("bluetooth.BluetoothSocket")
	def test_Bluetooth_SEND(self, bt_socket):
		print "%s" % sys._getframe().f_code.co_name
		btServices = {}
		btServices["host"] = "11:22:33:44:55:66"
		btServices["port"] = 1
		btServices["name"] = "example"
		btList = list()
		btList.append(btServices) 
		bluetooth.find_service = MagicMock(return_value = btList)
		bluetoothInstance.bluetoothTransmitter = MagicMock()
		error = bluetooth.btcommon.BluetoothError(4)
		bluetoothInstance.bluetoothTransmitter.send = MagicMock(side_effect = error)
		
		self.assertFalse(bluetoothInstance.send("message", "serviceName", "destMAC", "destUUID"))
		
		del btServices
		del btList
		del bluetooth.find_service
		del error
		del bluetoothInstance.bluetoothTransmitter.send 
		del bluetoothInstance.bluetoothTransmitter
		
	@patch("threading.Thread")
	def test_Bluetooth_RECEIVE(self, thread_call):
		print "%s" % sys._getframe().f_code.co_name
		bluetoothInstance.isActive = PropertyMock()
		
		bluetoothInstance.receive()
		thread_call.assert_called_once()
		
		del bluetoothInstance.isActive
		
	@patch("bluetoothReceptor.BluetoothReceptor")
	def test_Bluetooth_RECEIVE_RFCOMM(self, receptor_call):
		print "%s" % sys._getframe().f_code.co_name
		bluetoothClass.Bluetooth.isActive = PropertyMock(side_effect = [True, False])
		btSocket = socket.socket()
		bluetoothInstance.serverSocketRFCOMM = MagicMock(spec = bluetooth.BluetoothSocket)
		bluetoothInstance.serverSocketRFCOMM.accept = MagicMock(return_value = [btSocket, ["11:11:11:11:11:11"]])
		
		bluetoothInstance.receiveRFCOMM()
		receptor_call.assert_called_once()
		
		del bluetoothClass.Bluetooth.isActive
		del btSocket
		del bluetoothInstance.serverSocketRFCOMM.accept
		del bluetoothInstance.serverSocketRFCOMM
		
		
btTransmitterInstance = bluetoothTransmitter.BluetoothTransmitter
		
class BtTransmitterTest(unittest.TestCase):
	
	def setUp(self):
		logger.write = MagicMock()
		global btTransmitterInstance
		btTransmitterInstance = bluetoothTransmitter.BluetoothTransmitter()
		
	def tearDown(self):
		global btTransmitterInstance
		del btTransmitterInstance
		patch.stopall()
		del logger.write
		
	def test_btTransmitter_SEND(self):
		message = messageClass.Message('client01', 'client02', 10)
		btTransmitterInstance.sendFile = MagicMock(return_value = True)
		btTransmitterInstance.sendMessage = MagicMock(return_value = True)
		btTransmitterInstance.sendMessageInstance = MagicMock(return_value = True)
		clientSkt = MagicMock()
		
		print "%s: PLAINTEXT" % sys._getframe().f_code.co_name
		setattr(message, "plainText", "example")
		self.assertTrue(btTransmitterInstance.send(message, clientSkt))
		btTransmitterInstance.sendMessage.assert_called_once()
		delattr(message, "plainText")
		
		print "%s: FILE" % sys._getframe().f_code.co_name
		setattr(message, "fileName", "/tmp/activeInterfaces")
		self.assertTrue(btTransmitterInstance.send(message, clientSkt))
		btTransmitterInstance.sendFile.assert_called_once()
		delattr(message, "fileName")
		
		print "%s: INSTANCE" % sys._getframe().f_code.co_name
		setattr(message, "instance", "INSTANCEexample")
		self.assertTrue(btTransmitterInstance.send(message, clientSkt))
		btTransmitterInstance.sendMessageInstance.assert_called_once()
		delattr(message, "instance")
		
		del message
		del btTransmitterInstance.sendMessage
		del btTransmitterInstance.sendFile
		del btTransmitterInstance.sendMessageInstance
		del clientSkt
		
	def test_btTransmitter_SENDMESSAGE_TRUE(self):
		print "%s" % sys._getframe().f_code.co_name
		clientSkt = MagicMock(spec = socket.socket)
		clientSkt.send = MagicMock()
		
		self.assertTrue(btTransmitterInstance.sendMessage("example", clientSkt))
		clientSkt.send.assert_called_once()
		
		del clientSkt
		
	@patch("socket.socket.send")
	def test_btTransmitter_SENDMESSAGE_FALSE(self, send_call):
		print "%s" % sys._getframe().f_code.co_name
		clientSkt = MagicMock(spec = socket.socket)
		clientSkt.send = MagicMock(side_effect = [Exception])
		
		self.assertFalse(btTransmitterInstance.sendMessage("example", clientSkt))
		clientSkt.send.assert_called_once()
		
		del clientSkt
		
	def test_btTransmitter_SENDFILE(self):
		print "%s" % sys._getframe().f_code.co_name
		clientSkt = MagicMock(spec = socket.socket)
		clientSkt.recv = MagicMock(return_value = "READY")
		file_patch = mock_open()
		patch("__builtin__.open", file_patch).start()
		file_op = file_patch()
		file_op.tell = MagicMock(return_value = 10)
		file_op.read = MagicMock(return_value = "0123456789")
		
		self.assertTrue(btTransmitterInstance.sendFile("/home/pi/Communicator/grabacion.raw", clientSkt))
		file_op.read.assert_called_once()
		
		del clientSkt
		del file_op
		del file_patch
		
	def test_btTransmitter_SENDFILE_FALSE(self):
		print "%s" % sys._getframe().f_code.co_name
		clientSkt = MagicMock(spec = socket.socket)
		clientSkt.send = MagicMock(side_effect = [Exception])
		clientSkt.recv = MagicMock()
		file_patch = mock_open()
		patch("__builtin__.open", file_patch).start()
		file_op = file_patch()
		
		self.assertFalse(btTransmitterInstance.sendFile("/home/pi/Communicator/grabacion.raw", clientSkt))
		clientSkt.recv.assert_not_called()

		del clientSkt
		del file_op
		del file_patch
		
	def test_btTransmitter_SENDMESSAGEINSTANCE(self):
		print "%s" % sys._getframe().f_code.co_name
		clientSkt = MagicMock(spec = socket.socket)
		
		self.assertTrue(btTransmitterInstance.sendMessageInstance("example", clientSkt))
		
		del clientSkt
		
import pickle
import time
		
btReceptorInstance = bluetoothReceptor.BluetoothReceptor
socket_mock = MagicMock
		
class BtReceptorTest(unittest.TestCase):
	
	def setUp(self):
		logger.write = MagicMock()
		RECEPTION_QSIZE = JSON_CONFIG["COMMUNICATOR"]["RECEPTION_QSIZE"]
		receptionQueue = Queue.PriorityQueue(RECEPTION_QSIZE)
		global socket_mock
		socket_mock = MagicMock(spec = socket.socket)
		global btReceptorInstance
		btReceptorInstance = bluetoothReceptor.BluetoothReceptor("example", socket_mock, receptionQueue)
		
	def tearDown(self):
		global btReceptorInstance
		del btReceptorInstance
		global socket_mock
		del socket_mock
		patch.stopall()
		del logger.write
		
	@patch("bluetoothReceptor.BluetoothReceptor.receiveFile")
	def test_btReceptor_RUN_FILE(self, file_call):
		print "%s" % sys._getframe().f_code.co_name
		btReceptorInstance.remoteSocket.recv = MagicMock(return_value = "START_OF_FILE")
		
		btReceptorInstance.run()
		file_call.assert_called_once()
		
		del btReceptorInstance.remoteSocket.recv
		
	
	def test_btReceptor_RUN_INSTANCE(self):
		print "%s" % sys._getframe().f_code.co_name
		btReceptorInstance.remoteSocket.recv = MagicMock(return_value = "INSTANCE example")
		message = messageClass.Message('client01', 'client02', 10)
		pickle.loads = MagicMock(return_value = message)
		
		btReceptorInstance.run()
		pickle.loads.assert_called_once()
		
		del btReceptorInstance.remoteSocket.recv
		del message
		del pickle.loads
		
	@patch("bluetoothReceptor.BluetoothReceptor.receiveFile")
	def test_btReceptor_RUN_PLAINTEXT(self, file_call):
		print "%s" % sys._getframe().f_code.co_name
		btReceptorInstance.remoteSocket.recv = MagicMock(return_value = "message")
		pickle.loads = MagicMock()
		
		btReceptorInstance.run()
		pickle.loads.assert_not_called()
		file_call.assert_not_called()
		
		del pickle.loads
		del btReceptorInstance.remoteSocket.recv
		
	def test_btReceptor_RECEIVEFILE(self):
		print "%s" % sys._getframe().f_code.co_name
		socket_mock.recv = MagicMock(side_effect = ["file.txt", "primero", "segundo", "EOF"])
		patch("os.mkdir").start()
		patch("os.path.isfile", return_value = False).start()
		sleep_call = patch("time.sleep").start()
		file_patch = mock_open()
		patch("__builtin__.open", file_patch).start()
		btReceptorInstance.remoteSocket.send = MagicMock()
		
		self.assertTrue(btReceptorInstance.receiveFile())
		os.mkdir.assert_called_once()
		self.assertEqual(sleep_call.call_count, 2)
		
		del socket_mock.recv
		del file_patch
		
	def test_btReceptor_RECEIVEFILE_FILE_EXISTS(self):
		print "%s" % sys._getframe().f_code.co_name
		socket_mock.recv = MagicMock(side_effect = ["file.txt"])
		patch("os.mkdir").start()
		patch("os.path.isfile", return_value = True).start()
		btReceptorInstance.remoteSocket.send = MagicMock()
		
		self.assertFalse(btReceptorInstance.receiveFile())
		os.mkdir.assert_called_once()
		btReceptorInstance.remoteSocket.send.assert_any_call("FILE_EXISTS")
		
		del socket_mock.recv		
	
		
if __name__ == '__main__':
	unittest.main()
		
