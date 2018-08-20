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

import networkClass
import messageClass
import contactList

import json
import Queue
import logger
import time
import socket
import pickle
import threading

JSON_FILE = 'config.json'
JSON_CONFIG = json.load(open(JSON_FILE))

networkInstance = networkClass.Network

class ModemTest(unittest.TestCase):
	
	def setUp(self):
		logger.write = MagicMock()
		RECEPTION_QSIZE = JSON_CONFIG["COMMUNICATOR"]["RECEPTION_QSIZE"]
		receptionQueue = Queue.PriorityQueue(RECEPTION_QSIZE)
		global networkInstance
		networkInstance = networkClass.Network(receptionQueue, 'WIFI')
		
	def tearDown(self):
		global networkInstance
		del networkInstance
		patch.stopall()
		del logger.write
		
	def test_close(self):
		print "%s" % sys._getframe().f_code.co_name
		
		file_patch = mock_open()
		file_patch.read = MagicMock(return_value = "/dev/wlan0\n")
		file_patch.write = MagicMock()
		file_patch.close = MagicMock()
		networkInstance.localInterface = "/dev/wlan0"
		networkInstance.tcpReceptionSocket = MagicMock()
		networkInstance.tcpReceptionSocket.close = MagicMock()
		networkInstance.udpReceptionSocket = MagicMock()
		networkInstance.udpReceptionSocket.close  = MagicMock()
		
		networkInstance.close()
		
		networkInstance.tcpReceptionSocket.close.assert_called_once()
		networkInstance.udpReceptionSocket.close.assert_called_once()
		
		
	@patch("socket.socket")
	def test_connect(self, socket_call):
		print "%s" % sys._getframe().f_code.co_name
		
		networkInstance.successfulConnection = False		
		networkInstance.tcpReceptionSocket = MagicMock(spec = socket.socket)
		networkInstance.udpReceptionSocket = MagicMock(spec = socket.socket)
		
		self.assertTrue(networkInstance.connect("192.168.1.1"))
		self.assertEqual(socket_call.call_count, 2)
		self.assertTrue(networkInstance.successfulConnection)
		
	@patch("socket.socket")
	def test_connect_FALSE(self, socket_call):
		print "%s" % sys._getframe().f_code.co_name
		
		socket_call.side_effect = [socket.error]
		networkInstance.successfulConnection = False
		
		self.assertFalse(networkInstance.connect("192.168.1.1"))
		socket_call.assert_called_once()
		self.assertFalse(networkInstance.successfulConnection)
		
	@patch("socket.socket")
	def test_send_FILE(self, socket_call):
		print "%s" % sys._getframe().f_code.co_name
		
		patch("os.system", return_value = 0).start()
		patch("socket.socket.connect").start()
		message = messageClass.Message('client01', 'client02', 10)
		setattr(message, "fileName", "file.txt")
		networkInstance.sendFile = MagicMock(return_value = True)
		
		self.assertTrue(networkInstance.send(message, '192.168.1.6', 5000, 5010))
		socket_call.assert_called_once()
		networkInstance.sendFile.assert_called_once()
		
	@patch("socket.socket")
	def test_send_FILE_FAIL(self, socket_call):
		print "%s" % sys._getframe().f_code.co_name
		
		socket_call.side_effect = [socket.error]
		patch("os.system", return_value = 0).start()
		message = messageClass.Message('client01', 'client02', 10)
		setattr(message, "fileName", "file.txt")
		networkInstance.sendFile = MagicMock()
		
		self.assertFalse(networkInstance.send(message, '192.168.1.6', 5000, 5010))
		socket_call.assert_called_once()
		networkInstance.sendFile.assert_not_called()
		
	@patch("socket.socket")
	def test_send_TEXT(self, socket_call):
		print "%s" % sys._getframe().f_code.co_name
		
		patch("os.system", return_value = 0).start()
		message = messageClass.Message('client01', 'client02', 10)
		setattr(message, "plainText", "example")
		networkInstance.sendMessage = MagicMock(return_value = True)
		
		self.assertTrue(networkInstance.send(message, '192.168.1.6', 5000, 5010))
		socket_call.assert_not_called()
		networkInstance.sendMessage.assert_called_once()
		
	@patch("socket.socket")
	def test_send_INSTANCE(self, socket_call):
		print "%s" % sys._getframe().f_code.co_name
		
		patch("os.system", return_value = 0).start()
		message = messageClass.Message('client01', 'client02', 10)
		networkInstance.sendMessageInstance = MagicMock(return_value = True)
		
		self.assertTrue(networkInstance.send(message, '192.168.1.6', 5000, 5010))
		socket_call.assert_not_called()
		networkInstance.sendMessageInstance.assert_called_once()
		networkInstance.sendMessageInstance.assert_called_once()
		
	def test_sendFile(self):
		print "%s" % sys._getframe().f_code.co_name
		
		patch("os.path.abspath", return_value = "/path/to/file.txt").start()
		file_patch = mock_open()
		patch("__builtin__.open", file_patch).start()
		file_op = file_patch()
		file_op.tell = MagicMock(side_effect = ["", 10])
		file_op.seek = MagicMock()
		file_op.read = MagicMock(return_value = "0123456789")
		file_op.close = MagicMock()
		clientSkt = MagicMock(spec = socket.socket)
		clientSkt.recv = MagicMock(side_effect = ["READY", ""])
		
		self.assertTrue(networkInstance.sendFile("file.txt", clientSkt))
		file_op.read.assert_called_once()
		
	def test_sendFile_EXCEPT(self):
		print "%s" % sys._getframe().f_code.co_name
		
		patch("os.path.abspath", return_value = "/path/to/file.txt").start()
		file_patch = mock_open()
		file_patch.side_effect = [Exception]
		patch("__builtin__.open", file_patch).start()
		clientSkt = MagicMock(spec = socket.socket)
		
		self.assertFalse(networkInstance.sendFile("file.txt", clientSkt))
		
		
	@patch("socket.socket.sendto")
	@patch("socket.socket.close")
	def test_sendMessage(self, close_call, send_call):
		print "%s" % sys._getframe().f_code.co_name
		
		patch("socket.socket", return_value = socket.socket).start()
		
		self.assertTrue(networkInstance.sendMessage("plainText", "192.168.1.6", 5010))
		send_call.assert_called_once()
		close_call.assert_called_once()
		
	@patch("socket.socket.sendto")
	@patch("socket.socket.close")
	def test_sendMessage_EXCEPT(self, close_call, send_call):
		print "%s" % sys._getframe().f_code.co_name
		
		patch("socket.socket", return_value = socket.socket).start()
		send_call.side_effect = [socket.error]
		
		self.assertFalse(networkInstance.sendMessage("plainText", "192.168.1.6", 5010))
		send_call.assert_called_once()
		close_call.assert_called_once()
		
		
	@patch("socket.socket.sendto")
	@patch("socket.socket.close")
	@patch("pickle.dumps")
	def test_sendMessageInstance(self, dumps_call, close_call, send_call):
		print "%s" % sys._getframe().f_code.co_name
		
		patch("socket.socket", return_value = socket.socket).start()
		message = messageClass.Message('client01', 'client02', 10)
		
		self.assertTrue(networkInstance.sendMessageInstance(message, "192.168.1.6", 5010))
		dumps_call.assert_called_once()
		send_call.assert_called_once()
		close_call.assert_called_once()
		
	@patch("socket.socket.sendto")
	@patch("socket.socket.close")
	@patch("pickle.dumps")
	def test_sendMessageInstance_EXCEPT(self, dumps_call, close_call, send_call):
		print "%s" % sys._getframe().f_code.co_name
		
		patch("socket.socket", return_value = socket.socket).start()
		send_call.side_effect = [socket.error]
		message = messageClass.Message('client01', 'client02', 10)
		
		self.assertFalse(networkInstance.sendMessageInstance(message, "192.168.1.6", 5010))
		dumps_call.assert_called_once()
		send_call.assert_called_once()
		close_call.assert_called_once()
		
	@patch("threading.Thread.start")
	@patch("threading.Thread.join")
	def test_receive(self, join_call, start_call):
		print "%s" % sys._getframe().f_code.co_name
		
		thread_call = patch("threading.Thread", return_value = threading.Thread).start()
		
		networkInstance.receive()
		self.assertEqual(thread_call.call_count, 2)
		self.assertEqual(start_call.call_count, 2)
		self.assertEqual(join_call.call_count, 2)
		
	@patch("threading.Thread")
	def test_receiveTCP(self, thread_call):	
		print "%s" % sys._getframe().f_code.co_name
		
		patch("networkClass.Network.isActive", new_callable = PropertyMock, side_effect = [True, False]).start()
		networkInstance.tcpReceptionSocket = MagicMock()
		networkInstance.tcpReceptionSocket.accept = MagicMock(return_value = [socket.socket, ["192.168.1.6", ]])
		networkInstance.tcpReceptionSocket.close = MagicMock()
		
		networkInstance.receiveTCP()
		
		thread_call.assert_called_once()
		networkInstance.tcpReceptionSocket.close.assert_called_once()
		
	@patch("pickle.loads")
	def test_receiveUDP(self, loads_call):	
		print "%s" % sys._getframe().f_code.co_name
		
		patch("networkClass.Network.isActive", new_callable = PropertyMock, side_effect = [True, False]).start()
		patch("Queue.Queue.put").start()
		networkInstance.udpReceptionSocket = MagicMock()
		networkInstance.udpReceptionSocket.recvfrom = MagicMock(return_value = ["INSTANCEexample", ["192.168.1.6", ]])
		networkInstance.udpReceptionSocket.close = MagicMock()
		
		networkInstance.receiveUDP()
		
		loads_call.assert_called_once()
		networkInstance.udpReceptionSocket.close.assert_called_once()
	
	@patch("os.mkdir")
	def test_receiveFile(self, mkdir_call):
		print "%s" % sys._getframe().f_code.co_name
		
		patch("os.getcwd").start()
		patch("os.path.join").start()
		patch("os.listdir").start()
		patch("os.path.isfile", return_value = False).start()
		patch("Queue.Queue.put").start()
		remoteSkt = MagicMock(spec = socket.socket)
		remoteSkt.recv = MagicMock(side_effect = ["file.txt", "", "EOF"])
		file_patch = mock_open()
		patch("__builtin__.open", file_patch).start()
		file_op = file_patch()
		file_op.write = MagicMock()
		file_op.close = MagicMock()
		
		self.assertTrue(networkInstance.receiveFile(remoteSkt))
		mkdir_call.assert_called_once()
		file_op.write.assert_called_once()
		file_op.close.assert_called_once()
		
	@patch("os.mkdir")
	def test_receiveFile_FILE_EXISTS(self, mkdir_call):
		print "%s" % sys._getframe().f_code.co_name
		
		patch("os.getcwd").start()
		patch("os.path.join").start()
		patch("os.listdir").start()
		patch("os.path.isfile", return_value = True).start()
		patch("Queue.Queue.put").start()
		remoteSkt = MagicMock(spec = socket.socket)
		remoteSkt.recv = MagicMock(side_effect = ["file.txt", "", "EOF"])
		remoteSkt.send = MagicMock()
		
		self.assertFalse(networkInstance.receiveFile(remoteSkt))
		mkdir_call.assert_called_once()
		remoteSkt.recv.assert_called_once()
		remoteSkt.send.assert_called_once() 
		
		del remoteSkt	
	

if __name__ == '__main__':
	unittest.main()
