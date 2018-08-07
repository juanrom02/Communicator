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

import ftpClass
import modemClass
import messageClass

import json
import Queue
import logger
import ftplib
import threading
import serial
import pickle
import time
import tempfile
import shutil

JSON_FILE = 'config.json'
JSON_CONFIG = json.load(open(JSON_FILE))

ftpInstance = ftpClass.Ftp
ftpInstance.ftpServer = ftplib.FTP
ftpInstance.gsmInstance = modemClass.Gsm

class FtpTest(unittest.TestCase):

	def setUp(self):
		logger.write = MagicMock()
		RECEPTION_QSIZE = JSON_CONFIG["COMMUNICATOR"]["RECEPTION_QSIZE"]
		receptionQueue = Queue.PriorityQueue(RECEPTION_QSIZE)
		global ftpInstance
		ftpInstance = ftpClass.Ftp(receptionQueue)
		ftpInstance.ftpServer = MagicMock(spec = ftplib.FTP)
		
	def tearDown(self):
		global ftpInstance
		del ftpInstance
		patch.stopall()
		del logger.write
		
	@patch("ftplib.FTP")
	def test_connect(self, ftplib_call):
		print "%s" % sys._getframe().f_code.co_name
		ftpClass.Ftp.ftp_mode = PropertyMock(return_value = 1)
		ftpInstance.ftpServer.cwd = MagicMock()
		
		self.assertTrue(ftpInstance.connect())
		ftplib_call.assert_called_once()
		
		del ftpClass.Ftp.ftp_mode 
		
	def test_connect_TELIT(self):
		print "%s" % sys._getframe().f_code.co_name
		ftpClass.Ftp.ftp_mode  = PropertyMock(return_value = 2)
		ftpInstance.telit_lock = MagicMock(spec = threading.Condition)
		ftpInstance.telit_lock.acquire = MagicMock()
		ftpInstance.telit_lock.wait = MagicMock()
		ftpInstance.telit_lock.release = MagicMock(side_effect = Exception)
		ftpInstance.gsmInstance.active_call = PropertyMock(side_effect = [True, False])
		ftpInstance.gsmInstance.sendAT = MagicMock(side_effect = ["", serial.serialutil.SerialException])
		ftpInstance.isActive = PropertyMock(return_value = True)
		
		with self.assertRaises(serial.serialutil.SerialException):
			ftpInstance.connect()
		self.assertEqual(ftpInstance.gsmInstance.sendAT.call_count, 2)
		ftpInstance.telit_lock.wait.assert_called_once()
		logger.write.assert_called_once()

		del ftpClass.Ftp.ftp_mode 
		
	@patch("tempfile.NamedTemporaryFile")
	@patch("pickle.dumps")
	def test_send_INSTANCE(self, dumps_call, ntf_call):
		print "%s" % sys._getframe().f_code.co_name
		message = messageClass.InfoMessage('client01', 'client02', "example")
		ftpInstance.sendFile = MagicMock(return_value = True)
		
		self.assertTrue(ftpInstance.send(message))
		dumps_call.assert_called_once()
		ntf_call.assert_called_once()
		
		del message
		
	@patch("tempfile.NamedTemporaryFile")
	@patch("pickle.dumps")
	def test_send_TEXT(self, dumps_call, ntf_call):
		print "%s" % sys._getframe().f_code.co_name
		message = messageClass.Message('client01', 'client02', 10)
		setattr(message, "plainText", "example")
		ftpInstance.sendFile = MagicMock(return_value = True)
		
		self.assertTrue(ftpInstance.send(message))
		dumps_call.assert_not_called()
		ntf_call.assert_called_once()
		
		del message
		
	@patch("tempfile.NamedTemporaryFile")
	@patch("pickle.dumps")
	def test_send_FILE(self, dumps_call, ntf_call):
		print "%s" % sys._getframe().f_code.co_name
		message = messageClass.Message('client01', 'client02', 10)
		setattr(message, "fileName", "/tmp/activeInterfaces")
		ftpInstance.sendFile = MagicMock(return_value = True)
		file_patch = mock_open()
		patch("__builtin__.open", file_patch).start()
		
		self.assertTrue(ftpInstance.send(message))
		dumps_call.assert_not_called()
		ntf_call.assert_not_called()
		file_patch.assert_called_once()
		
		del message
		del file_patch
		
	def test_sendFile(self):
		print "%s" % sys._getframe().f_code.co_name
		ftpInstance.connect = MagicMock()
		ftpClass.Ftp.ftp_mode  = PropertyMock(return_value = 1)
		file_patch = mock_open()
		file_patch.name = "/tmp/activeInterfaces"
		file_patch.close = MagicMock()
		patch("__builtin__.open", file_patch).start()
		ftpInstance.ftpServer.storbinary = MagicMock()
		
		self.assertTrue(ftpInstance.sendFile(file_patch))
		ftpInstance.ftpServer.storbinary.assert_called_once()
		
		del ftpClass.Ftp.ftp_mode
		del file_patch
		
	def test_sendFile_TELIT(self):
		print "%s" % sys._getframe().f_code.co_name
		ftpInstance.connect = MagicMock()
		ftpClass.Ftp.ftp_mode  = PropertyMock(return_value = 2)
		ftpInstance.gsmInstance.sendAT = MagicMock()
		time.sleep = MagicMock()
		ftpInstance.telit_lock = MagicMock(spec = threading.Condition)
		ftpInstance.telit_lock.release = MagicMock()
		file_patch = mock_open()
		file_patch.name = "/tmp/activeInterfaces"
		file_patch.read = MagicMock()
		file_patch.close = MagicMock()
		patch("__builtin__.open", file_patch).start()
		
		self.assertTrue(ftpInstance.sendFile(file_patch))
		ftpInstance.telit_lock.release.assert_called_once()
		
		del ftpClass.Ftp.ftp_mode
		del time.sleep
		del file_patch
		
	@patch("tempfile.NamedTemporaryFile")
	@patch("pickle.loads")
	def test_receive_TEXT(self, loads_call, ntf_call):
		print "%s" % sys._getframe().f_code.co_name
		ftpClass.Ftp.ftp_mode  = PropertyMock(return_value = 2)
		ftpInstance.gsmInstance.sendAT = MagicMock(side_effect = ["", ["filecontents", "OK"]])
		ftpInstance.receptionQueue.put = MagicMock()
		fileName = "Client01.-text.-Client02.-20180402.-143517"
		
		self.assertTrue(ftpInstance.receive(fileName))
		self.assertEqual(ftpInstance.gsmInstance.sendAT.call_count, 2)
		loads_call.assert_not_called()
		
		del ftpClass.Ftp.ftp_mode
		del fileName
		
	@patch("tempfile.NamedTemporaryFile")
	@patch("pickle.loads")
	def test_receive_INSTANCE(self, loads_call, ntf_call):
		print "%s" % sys._getframe().f_code.co_name
		ftpClass.Ftp.ftp_mode  = PropertyMock(return_value = 2)
		ftpInstance.gsmInstance.sendAT = MagicMock(side_effect = ["", ["filecontents", "OK"]])
		ftpInstance.receptionQueue.put = MagicMock()
		fileName = "Client01.-instance.-Client02.-20180402.-143625"
		
		self.assertTrue(ftpInstance.receive(fileName))
		self.assertEqual(ftpInstance.gsmInstance.sendAT.call_count, 2)
		loads_call.assert_called_once()
		
		del ftpClass.Ftp.ftp_mode
		del fileName
		
	@patch("tempfile.NamedTemporaryFile")
	@patch("pickle.loads")
	@patch("os.mkdir")
	@patch("shutil.copyfileobj")
	def test_receive_FILE(self, shutil_call, mkdir_call, loads_call, ntf_call):
		print "%s" % sys._getframe().f_code.co_name
		ftpClass.Ftp.ftp_mode  = PropertyMock(return_value = 2)
		ftpInstance.gsmInstance.sendAT = MagicMock(side_effect = ["", ["filecontents", "OK"]])
		fileName = "Client01.-imagen.jpg.-Client02.-20180402.-143746"
		os.listdir = MagicMock(return_value = [""])
		file_patch = mock_open()
		patch("__builtin__.open", file_patch).start()
		
		self.assertTrue(ftpInstance.receive(fileName))
		self.assertEqual(ftpInstance.gsmInstance.sendAT.call_count, 2)
		loads_call.assert_not_called()
		mkdir_call.assert_called_once()
		shutil_call.assert_called_once()
		
		del os.listdir
		del ftpClass.Ftp.ftp_mode
		del fileName
		
if __name__ == '__main__':
	unittest.main()
	
		
		
