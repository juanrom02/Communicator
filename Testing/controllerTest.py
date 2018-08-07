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


import controllerClass
import modemClass
import networkClass
import bluetoothClass
import emailClass
import ftpClass
import callClass

import json
import Queue
import threading
import time
import logger

JSON_FILE = 'config.json'
JSON_CONFIG = json.load(open(JSON_FILE))

controllerInstance = controllerClass.Controller
controllerInstance.gsmInstance = modemClass.Gsm
controllerInstance.gprsInstance = networkClass.Network
controllerInstance.wifiInstance = networkClass.Network
controllerInstance.ethernetInstance = networkClass.Network
controllerInstance.bluetoothInstance = bluetoothClass.Bluetooth
controllerInstance.emailInstance = emailClass.Email
controllerInstance.ftpInstance = ftpClass.Ftp
controllerInstance.callInstance = callClass.Call

class ClosingTest(unittest.TestCase):
	
	def setUp(self):
		logger.write = MagicMock()
		time.sleep = MagicMock()
		REFRESH_TIME = JSON_CONFIG["COMMUNICATOR"]["REFRESH_TIME"]
		global controllerInstance
		controllerInstance = controllerClass.Controller(REFRESH_TIME)
		
	def tearDown(self):
		global controllerInstance
		del controllerInstance
		patch.stopall()
		del logger.write
		del time.sleep
		
		 
#close()  --------------------------------------------------------------

	@patch('controllerClass.Controller.closeInstance')
	def test_close_OK(self, closeInstance):
		print "%s" % sys._getframe().f_code.co_name
		controllerInstance.close()
		closeInstance.assert_any_call(controllerInstance.ftpInstance)
		closeInstance.assert_any_call(controllerInstance.gsmInstance)
		closeInstance.assert_any_call(controllerInstance.bluetoothInstance)
		closeInstance.assert_any_call(controllerInstance.ethernetInstance)
		closeInstance.assert_any_call(controllerInstance.wifiInstance)
		closeInstance.assert_any_call(controllerInstance.gprsInstance)
		closeInstance.assert_any_call(controllerInstance.emailInstance)
			
			
#closeInstance()  ------------------------------------------------------

	def closeInstance_setUp(self, isActive, isAlive):
		controllerInstance.gsmInstance.isActive = PropertyMock(return_value = isActive)
		controllerInstance.gsmInstance.thread = threading.Thread
		threading.Thread.isAlive = MagicMock(return_value = isAlive)
		
	def closeInstance_tearDown(self):
		del controllerInstance.gsmInstance.isActive
		del threading.Thread.isAlive
		
	def patch_closeInstance(f):
		@patch('threading.Thread.join')
		@patch('modemClass.Gsm.close')
		def functor(*args, **kwargs):
			return f(*args, **kwargs)
		return functor

	@patch_closeInstance
	def test_closeInstance_OK(self, close_call, join_call):
		print "%s" % sys._getframe().f_code.co_name
		self.closeInstance_setUp(True, True)
		
		controllerInstance.closeInstance(controllerInstance.gsmInstance)
		
		join_call.assert_called_once()
		close_call.assert_called_once()
		
		self.closeInstance_tearDown()
	
	@patch_closeInstance
	def test_closeInstance_NOT_ALIVE(self, close_call, join_call):
		print "%s" % sys._getframe().f_code.co_name
		self.closeInstance_setUp(True, False)
		
		controllerInstance.closeInstance(controllerInstance.gsmInstance)
		
		join_call.assert_not_called()
		close_call.assert_called_once()
		
		self.closeInstance_tearDown()
		
	@patch_closeInstance
	def test_closeInstance_NOT_ACTIVE(self, close_call, join_call):
		print "%s" % sys._getframe().f_code.co_name
		self.closeInstance_setUp(False, True)
		
		controllerInstance.closeInstance(controllerInstance.gsmInstance)
		
		join_call.assert_not_called()
		close_call.assert_not_called()
		
		self.closeInstance_tearDown()
		
#closeConnection() -----------------------------------------------------

	def closeConnection_setUp(self, isAlive = [True]):
		threading.Thread.isAlive = MagicMock(side_effect = isAlive)
		controllerInstance.wifiInstance.localInterface = PropertyMock(return_value = "wlan0")
		controllerInstance.wifiInstance.localAddress = PropertyMock(return_value = "192.168.1.2")
		controllerInstance.wifiInstance.thread = threading.Thread
		
	def closeConnection_tearDown(self):
		del threading.Thread.isAlive
		del controllerInstance.wifiInstance.localInterface
		del controllerInstance.wifiInstance.localAddress
		del controllerInstance.wifiInstance.thread

	def patch_closeConnection(f):
		@patch('modemClass.Gsm.closePort')
		@patch('threading.Thread.join')
		def functor(*args, **kwargs):
			return f(*args, **kwargs)
		return functor

	@patch_closeConnection
	def test_closeConnection_OK(self, join_call, closePort_call):
		print "%s" % sys._getframe().f_code.co_name
		self.closeConnection_setUp()
		
		controllerInstance.closeConnection(controllerInstance.wifiInstance)
		
		closePort_call.assert_not_called()
		join_call.assert_called_once()
	
		self.closeConnection_tearDown()
		
		
	@patch_closeConnection
	def test_closeConnection_GSM(self, join_call, closePort_call):
		print "%s" % sys._getframe().f_code.co_name
		self.closeConnection_setUp()
		controllerInstance.gsmInstance.localInterface = PropertyMock(return_value = "ttyUSB0")
		controllerInstance.gsmInstance.thread = threading.Thread
		
		controllerInstance.closeConnection(controllerInstance.gsmInstance)
		
		closePort_call.assert_called_once()
		join_call.assert_called_once()
		
		del controllerInstance.gsmInstance.localInterface
		del controllerInstance.gsmInstance.thread
		self.closeConnection_tearDown()
		
	@patch_closeConnection
	def test_closeConnection_ANDROID(self, join_call, closePort_call):
		print "%s" % sys._getframe().f_code.co_name
		self.closeConnection_setUp(isAlive = [True, False, False])
		controllerInstance.gsmInstance.localInterface = PropertyMock(return_value = "Android")
		controllerInstance.gsmInstance.thread = threading.Thread
		
		controllerInstance.closeConnection(controllerInstance.gsmInstance)
		
		closePort_call.assert_called_once()
		join_call.assert_called_once()
		self.assertEqual(threading.Thread.isAlive.call_count, 2)
		
		del controllerInstance.gsmInstance.localInterface
		del controllerInstance.gsmInstance.thread	
		self.closeConnection_tearDown()
		
	@patch_closeConnection
	def test_closeConnection_NOT_ALIVE(self, join_call, closePort_call):
		print "%s" % sys._getframe().f_code.co_name
		self.closeConnection_setUp(isAlive = [False])
		
		controllerInstance.closeConnection(controllerInstance.wifiInstance)
		
		closePort_call.assert_not_called()
		join_call.assert_not_called()
		
		self.closeConnection_tearDown()


class RunTest(unittest.TestCase):
	
	def setUp(self):
		logger.write = MagicMock()
		time.sleep = MagicMock()
		REFRESH_TIME = JSON_CONFIG["COMMUNICATOR"]["REFRESH_TIME"]
		global controllerInstance
		controllerInstance = controllerClass.Controller(REFRESH_TIME)
		controllerInstance.verifyGsmConnection = MagicMock(return_value = True)		
		controllerInstance.verifyBluetoothConnection = MagicMock(return_value = True)
		
	def tearDown(self):
		del logger.write
		del time.sleep
		global controllerInstance
		del controllerInstance.verifyGsmConnection
		del controllerInstance.verifyBluetoothConnection
		del controllerClass.Controller.isActive
		del controllerInstance.ftpInstance.isActive
		del controllerInstance.emailInstance.isActive
		del controllerInstance.gsmInstance.androidConnected
		del controllerInstance.wifiInstance.online
		del controllerInstance
		patch.stopall()
	

	def patch_run(f):
		@patch('controllerClass.Controller.verifyAndroidStatus')
		@patch('controllerClass.Controller.verifyNetworkConnection')
		@patch('controllerClass.Controller.verifyFtpConnection')
		@patch('controllerClass.Controller.verifyEmailConnection')
		@patch('threading.Thread')
		@patch('modemClass.Gsm.answerVoiceCall')
		def functor(*args, **kwargs):
			return f(*args, **kwargs)
		return functor
		
	def run_setUp(self, isActive1 = True, isActive2 = False, android = False, online = True, 
					ftpActive = False, emailActive = False):
		controllerClass.Controller.isActive = PropertyMock(side_effect = [isActive1, isActive2])
		controllerInstance.gsmInstance.androidConnected = PropertyMock(return_value = android)
		controllerInstance.wifiInstance.online = PropertyMock(return_value = online)
		controllerInstance.ftpInstance.isActive = PropertyMock(return_value = ftpActive)
		controllerInstance.emailInstance.isActive = PropertyMock(return_value = emailActive)
		
	@patch_run
	def test_run_OK(self, answer_call, thread_call, email_call, ftp_call, network_call, android_call):
		print "%s" % sys._getframe().f_code.co_name
		self.run_setUp()
		
		controllerInstance.run()
		
		android_call.assert_not_called()
		network_call.assert_called_with(controllerInstance.wifiInstance)
		network_call.assert_called_with(controllerInstance.gprsInstance)
		ftp_call.assert_called_once()
		email_call.assert_called_once()
		thread_call.assert_not_called()
		answer_call.assert_not_called()
	
	@patch('controllerClass.Controller.verifyGsmConnection')
	def test_run_NOT_ACTIVE(self, gsm_call):
		print "%s" % sys._getframe().f_code.co_name
		self.run_setUp(isActive1 = False)
		
		controllerInstance.run()
		
		gsm_call.assert_not_called()
		
	@patch_run
	def test_run_ANDROID(self, answer_call, thread_call, email_call, ftp_call, network_call, android_call):
		print "%s" % sys._getframe().f_code.co_name
		self.run_setUp(android = True)
		
		controllerInstance.run()
		
		android_call.assert_called_once()
		network_call.assert_called_once()
		ftp_call.assert_called_once()
		email_call.assert_called_once()
		thread_call.assert_not_called()
		answer_call.assert_not_called()
		
	@patch_run
	def test_run_NO_INTERNET(self, answer_call, thread_call, email_call, ftp_call, network_call, android_call):
		print "%s" % sys._getframe().f_code.co_name
		self.run_setUp(online = False)
		
		controllerInstance.run()
		
		android_call.assert_not_called()
		network_call.assert_called_with(controllerInstance.wifiInstance)
		network_call.assert_called_with(controllerInstance.gprsInstance)
		ftp_call.assert_not_called()
		email_call.assert_not_called()
		thread_call.assert_not_called()
		answer_call.assert_not_called()
	
	@patch_run
	def test_run_FTP_ACTIVE(self, answer_call, thread_call, email_call, ftp_call, network_call, android_call):
		print "%s" % sys._getframe().f_code.co_name
		self.run_setUp(ftpActive = True)
		
		controllerInstance.run()
		
		android_call.assert_not_called()
		network_call.assert_called_with(controllerInstance.wifiInstance)
		network_call.assert_called_with(controllerInstance.gprsInstance)
		ftp_call.assert_not_called()
		email_call.assert_called_once()
		thread_call.assert_not_called()
		answer_call.assert_not_called()
 
	@patch_run
	def test_run_NO_INTERNET_EMAIL_ACTIVE(self, answer_call, thread_call, email_call, ftp_call, network_call, android_call):
		print "%s" % sys._getframe().f_code.co_name
		self.run_setUp(online = False, emailActive = True)
		
		controllerInstance.run()
		
		android_call.assert_not_called()
		network_call.assert_called_with(controllerInstance.wifiInstance)
		network_call.assert_called_with(controllerInstance.gprsInstance)
		ftp_call.assert_not_called()
		email_call.assert_not_called()
		thread_call.assert_called_once()
		answer_call.assert_not_called()
		
	@patch_run
	def test_run_NEW_CALL(self, answer_call, thread_call, email_call, ftp_call, network_call, android_call):
		print "%s" % sys._getframe().f_code.co_name
		self.run_setUp()
		
		controllerInstance.gsmInstance.new_call = PropertyMock(return_value = True)
		
		controllerInstance.run()
		
		android_call.assert_not_called()
		network_call.assert_called_with(controllerInstance.wifiInstance)
		network_call.assert_called_with(controllerInstance.gprsInstance)
		ftp_call.assert_called_once()
		email_call.assert_called_once()
		thread_call.assert_not_called()
		answer_call.assert_called_once()
		
		del controllerInstance.gsmInstance.new_call
		

class VerifyGsmTest(unittest.TestCase):
	
	def setUp(self):
		logger.write = MagicMock()
		REFRESH_TIME = JSON_CONFIG["COMMUNICATOR"]["REFRESH_TIME"]
		global controllerInstance
		controllerInstance = controllerClass.Controller(REFRESH_TIME)
		
	def tearDown(self):
		global controllerInstance
		del controllerInstance
		patch.stopall()
		del logger.write
		
	def verifyGsm_setUp(self, android = False, usb_devices = ['ttyUSB0', 'ttyUSB1'], gsm_interface = None, isActive = True):
		controllerInstance.gsmInstance.connectAndroid = MagicMock(return_value = android)
		controllerClass.Controller.ttyUSBDevices = PropertyMock(return_value = usb_devices)
		controllerInstance.gsmInstance.localInterface = PropertyMock(return_value = gsm_interface)
		controllerInstance.gsmInstance.isActive = PropertyMock(return_value = isActive)
		subprocess.Popen.communicate = MagicMock(return_value = ['', ''])
		
	def verifyGsm_tearDown(self):
		del controllerInstance.gsmInstance.connectAndroid
		del controllerClass.Controller.ttyUSBDevices
		del controllerInstance.gsmInstance.localInterface
		del controllerInstance.gsmInstance.isActive
		del subprocess.Popen.communicate
	
	def patch_verifyGsm(f):
		@patch("threading.Thread.start")
		@patch("controllerClass.Controller.closeConnection")
		def functor(*args, **kwargs):
			return f(*args, **kwargs)
		return functor
		
	@patch("modemClass.Gsm.closePort")
	@patch_verifyGsm
	def test_verifyGsm_OK(self, closeConnection_call, start_call, closePort_call):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyGsm_setUp()
		controllerInstance.gsmInstance.connectAT = MagicMock(side_effect = [False, True])	
		
		self.assertTrue(controllerInstance.verifyGsmConnection())
		closePort_call.assert_called_once()
		closeConnection_call.assert_not_called()
		start_call.assert_called_once()
			
		self.verifyGsm_tearDown()
		
	@patch_verifyGsm
	def test_verifyGsm_ANDROID_START(self, close_call, start_call):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyGsm_setUp(android = True)
		
		self.assertTrue(controllerInstance.verifyGsmConnection())
		close_call.assert_not_called()
		start_call.assert_called_once()
		
		self.verifyGsm_tearDown()
	
	@patch_verifyGsm
	def test_verifyGsm_ANDROID_ACTIVE(self, close_call, start_call):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyGsm_setUp(android = True, gsm_interface = "ttyUSB0")
		
		self.assertTrue(controllerInstance.verifyGsmConnection())
		close_call.assert_not_called()
		start_call.assert_not_called()
		
		self.verifyGsm_tearDown()
		
	@patch_verifyGsm
	def test_verifyGsm_ANDROID_FALSE(self, close_call, start_call):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyGsm_setUp(android = True, gsm_interface = "ttyUSB0", isActive = False)
		
		self.assertFalse(controllerInstance.verifyGsmConnection())
		close_call.assert_not_called()
		start_call.assert_not_called()
		
		self.verifyGsm_tearDown()
	
	@patch('modemClass.Gsm.connectAT')
	@patch_verifyGsm
	def test_verifyGsm_ACTIVE(self, close_call, start_call, connect_call):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyGsm_setUp(gsm_interface = 'ttyUSB0')
		
		self.assertTrue(controllerInstance.verifyGsmConnection())
		close_call.assert_not_called()
		start_call.assert_not_called()
		connect_call.assert_not_called()
		
		self.verifyGsm_tearDown()
	
	@patch('modemClass.Gsm.connectAT')
	@patch_verifyGsm
	def test_verifyGsm_NOT_ACTIVE(self, close_call, start_call, connect_call):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyGsm_setUp(gsm_interface = 'ttyUSB0', isActive = False)
		
		self.assertFalse(controllerInstance.verifyGsmConnection())
		close_call.assert_not_called()
		start_call.assert_not_called()
		connect_call.assert_not_called()
		
		self.verifyGsm_tearDown()
		
	@patch_verifyGsm
	def test_verifyGsm_CLOSE(self, close_call, start_call):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyGsm_setUp(usb_devices = [], gsm_interface = 'ttyUSB0')
				
		self.assertFalse(controllerInstance.verifyGsmConnection())
		close_call.assert_called_once()
		start_call.assert_not_called()

		self.verifyGsm_tearDown()
	
	@patch_verifyGsm
	def test_verifyGsm_NO_CLOSE(self, close_call, start_call):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyGsm_setUp(usb_devices = [])
				
		self.assertFalse(controllerInstance.verifyGsmConnection())
		close_call.assert_not_called()
		start_call.assert_not_called()

		self.verifyGsm_tearDown()

import subprocess
import re
		
class VerifyNetworkTest(unittest.TestCase):
	
	def setUp(self):
		logger.write = MagicMock()
		time.sleep = MagicMock()
		REFRESH_TIME = JSON_CONFIG["COMMUNICATOR"]["REFRESH_TIME"]
		global controllerInstance
		controllerInstance = controllerClass.Controller(REFRESH_TIME)
		
	def tearDown(self):
		global controllerInstance
		del controllerInstance
		patch.stopall()
		del logger.write
		del time.sleep
		
	def verifyInternet_setUp(self, networkInstance, pattern, connect = True, gsm_active = False, state = "UP", interface = None):
		controllerClass.Controller.netInterfaces = PropertyMock(return_value = ['wlan0 state UP', 'ppp0 state UP', 'eth0 state UP'])
		networkClass.Network.connect = MagicMock(return_value = connect)
		controllerInstance.gsmInstance.isActive = PropertyMock(return_value = gsm_active)
		controllerClass.Controller.localAddress = PropertyMock(side_effect = ['','', '', 'a', "x 192.168.1.1/24"])
		os.popen = MagicMock()
		networkInstance.pattern = re.compile(pattern)
		networkInstance.state = PropertyMock(return_value = state)
		networkInstance.localInterface = PropertyMock(return_value = interface)
		networkInstance.localAddress = PropertyMock(return_value = '192.168.1.1')
		networkInstance.isActive = PropertyMock(return_value = False)
		networkInstance.thread = threading.Thread
		
	def verifyInternet_tearDown(self, networkInstance):
		del controllerClass.Controller.netInterfaces
		del networkClass.Network.connect
		del controllerInstance.gsmInstance.isActive
		del controllerClass.Controller.localAddress
		del os.popen
		del networkInstance.pattern
		del networkInstance.state
		del networkInstance.localInterface
		del networkInstance.localAddress 
		del networkInstance.isActive
		del networkInstance.thread
		
	def patch_verifyInternet(f):
		@patch("controllerClass.Controller.verifyInternetConnection")
		@patch('controllerClass.Controller.closeConnection')
		def functor(*args, **kwargs):
			return f(*args, **kwargs)
		return functor
		
	@patch('threading.Thread.start')
	@patch_verifyInternet
	def test_verifyInternet_GPRS(self, close_call, internet_call, start_call):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyInternet_setUp(gsm_active = True, networkInstance = controllerInstance.gprsInstance, pattern = "ppp[0-9]+")
		subprocess.Popen.communicate = MagicMock(return_value = ['', ''])
		controllerInstance.gsmInstance.telitConnected = PropertyMock(return_value = False)
		
		self.assertTrue(controllerInstance.verifyNetworkConnection(controllerInstance.gprsInstance))
		close_call.assert_not_called()
		internet_call.assert_called_once()
		start_call.assert_called_once()
	
		del subprocess.Popen.communicate
		del controllerInstance.gsmInstance.telitConnected
		self.verifyInternet_tearDown(networkInstance = controllerInstance.gprsInstance)
		
	@patch_verifyInternet
	def test_verifyInternet_GPRS_ERROR(self, close_call, internet_call):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyInternet_setUp(gsm_active = True, networkInstance = controllerInstance.gprsInstance, pattern = "ppp[0-9]+")
		subprocess.Popen.communicate = MagicMock(return_value = ['', 'error'])
		controllerInstance.gsmInstance.telitConnected = PropertyMock(return_value = False)
		
		self.assertFalse(controllerInstance.verifyNetworkConnection(controllerInstance.gprsInstance))
		close_call.assert_not_called()
		internet_call.assert_called_once()
	
		del subprocess.Popen.communicate
		del controllerInstance.gsmInstance.telitConnected
		self.verifyInternet_tearDown(networkInstance = controllerInstance.gprsInstance)
		
	@patch_verifyInternet
	def test_verifyInternet_GPRS_TELIT(self, close_call, internet_call):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyInternet_setUp(gsm_active = True, networkInstance = controllerInstance.gprsInstance, pattern = "ppp[0-9]+")
		controllerInstance.gsmInstance.telitConnected = PropertyMock(return_value = True)
		controllerInstance.verifyTelitGprsConnection = MagicMock(return_value = True)
		
		self.assertTrue(controllerInstance.verifyNetworkConnection(controllerInstance.gprsInstance))
		close_call.assert_not_called()
		internet_call.assert_called_once()
	
		del controllerInstance.gsmInstance.telitConnected
		del controllerInstance.verifyTelitGprsConnection
		self.verifyInternet_tearDown(networkInstance = controllerInstance.gprsInstance)
	
	@patch('threading.Thread.start')
	@patch_verifyInternet
	def test_verifyInternet_NO_CONNECT(self, close_call, internet_call, start_call):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyInternet_setUp(connect = False, networkInstance = controllerInstance.wifiInstance, pattern = "wlan[0-9]+")
		
		self.assertFalse(controllerInstance.verifyNetworkConnection(controllerInstance.wifiInstance))
		close_call.assert_not_called()
		internet_call.assert_called_once()
		start_call.assert_not_called()
	
		self.verifyInternet_tearDown(networkInstance = controllerInstance.wifiInstance)
		
	@patch_verifyInternet
	def test_verifyInternet_GROUP_SUCCESS(self, close_call, internet_call):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyInternet_setUp(networkInstance = controllerInstance.wifiInstance, pattern = "wlan[0-9]+", interface = "wlan0")
		controllerInstance.wifiInstance.successfulConnection = PropertyMock(return_value = True)
		
		self.assertTrue(controllerInstance.verifyNetworkConnection(controllerInstance.wifiInstance))
		close_call.assert_not_called()
		internet_call.assert_called_once()
	
		del controllerInstance.wifiInstance.successfulConnection
		self.verifyInternet_tearDown(networkInstance = controllerInstance.wifiInstance)
		
	@patch_verifyInternet
	def test_verifyInternet_GROUP_FAIL(self, close_call, internet_call):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyInternet_setUp(networkInstance = controllerInstance.wifiInstance, pattern = "wlan[0-9]+", interface = "wlan0")
		controllerInstance.wifiInstance.successfulConnection = PropertyMock(return_value = False)
		
		self.assertFalse(controllerInstance.verifyNetworkConnection(controllerInstance.wifiInstance))
		close_call.assert_not_called()
		internet_call.assert_called_once()
	
		del controllerInstance.wifiInstance.successfulConnection
		self.verifyInternet_tearDown(networkInstance = controllerInstance.wifiInstance)

	@patch_verifyInternet
	def test_verifyInternet_CONTINUE(self, close_call, internet_call):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyInternet_setUp(networkInstance = controllerInstance.wifiInstance, pattern = "wlan[0-9]+", interface = "lo")
		
		self.assertFalse(controllerInstance.verifyNetworkConnection(controllerInstance.wifiInstance))
		close_call.assert_called_once()
		internet_call.assert_called_once()
	
		del controllerInstance.wifiInstance.successfulConnection
		self.verifyInternet_tearDown(networkInstance = controllerInstance.wifiInstance)
		
import socket
import serial

class VerifyInternetTest(unittest.TestCase):
	
	def setUp(self):
		time.sleep = MagicMock()
		logger.write = MagicMock()
		REFRESH_TIME = JSON_CONFIG["COMMUNICATOR"]["REFRESH_TIME"]
		global controllerInstance
		controllerInstance = controllerClass.Controller(REFRESH_TIME)
		
	def tearDown(self):
		global controllerInstance
		del controllerInstance
		patch.stopall()
		del time.sleep
		del logger.write
		
	def verifyInternet_setUp(self, isActive = True, online = True):
		controllerInstance.telit_lock = MagicMock(spec = threading.Lock)
		controllerInstance.telit_lock.release = MagicMock()
		controllerInstance.gprsInstance.isActive = PropertyMock(return_value = isActive)
		controllerInstance.gprsInstance.online = PropertyMock(return_value = online)
		
	def verifyInternet_tearDown(self):
		del controllerInstance.telit_lock.release
		del controllerInstance.telit_lock
		del controllerInstance.gprsInstance.isActive
		del controllerInstance.gprsInstance.online
	
	def test_verifyInternet_ACTIVE(self):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyInternet_setUp(isActive = False, online = False)
				
		controllerInstance.verifyInternetConnection(controllerInstance.gprsInstance)
		logger.write.assert_not_called()
		controllerInstance.telit_lock.release.assert_not_called()
		
		self.verifyInternet_tearDown()
		
	def test_verifyInternet_ACTIVE_CHANGE(self):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyInternet_setUp(isActive = False)
		controllerInstance.ftpInstance.isActive = PropertyMock()
		
		controllerInstance.verifyInternetConnection(controllerInstance.gprsInstance)
		logger.write.assert_called_once()
		controllerInstance.telit_lock.release.assert_not_called()
		
		del controllerInstance.ftpInstance.isActive
		self.verifyInternet_tearDown()
	
	def test_verifyInternet_TELIT(self):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyInternet_setUp(online = False)
		controllerInstance.gsmInstance.telitConnected = PropertyMock(return_value = True)
		controllerInstance.gsmInstance.active_call = PropertyMock(return_value = False)
		controllerInstance.gsmInstance.sendAT = MagicMock()
		controllerInstance.telit_lock.acquire = MagicMock()
		
		controllerInstance.verifyInternetConnection(controllerInstance.gprsInstance)
		self.assertEqual(controllerInstance.gsmInstance.sendAT.call_count, 2)
		controllerInstance.telit_lock.acquire.assert_called_once()
		logger.write.assert_called_once()
		controllerInstance.telit_lock.release.assert_called_once()
		
		del controllerInstance.gsmInstance.telitConnected
		del controllerInstance.gsmInstance.active_call
		del controllerInstance.gsmInstance.sendAT
		del controllerInstance.telit_lock.acquire		
		self.verifyInternet_tearDown()
	
	def test_verifyInternet_CALL(self):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyInternet_setUp(online = False)
		controllerInstance.gsmInstance.telitConnected = PropertyMock(return_value = True)
		controllerInstance.gsmInstance.active_call = PropertyMock(return_value = True)
		controllerInstance.telit_lock.acquire = MagicMock()
		
		controllerInstance.verifyInternetConnection(controllerInstance.gprsInstance)
		controllerInstance.telit_lock.acquire.assert_called_once()
		logger.write.assert_not_called()
		controllerInstance.telit_lock.release.assert_called_once()
		
		del controllerInstance.gsmInstance.telitConnected
		del controllerInstance.gsmInstance.active_call
		del controllerInstance.telit_lock.acquire
		self.verifyInternet_tearDown()

	def test_verifyInternet_SOCKET_CONN(self):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyInternet_setUp()
		controllerInstance.gsmInstance.telitConnected = PropertyMock(return_value = False)
		socket.gethostbyname = MagicMock()
		socket.create_connection = MagicMock()
		
		controllerInstance.verifyInternetConnection(controllerInstance.gprsInstance)
		socket.gethostbyname.assert_called_once()
		logger.write.assert_not_called()
		controllerInstance.telit_lock.release.assert_not_called()
		
		del controllerInstance.gsmInstance.telitConnected
		del socket.gethostbyname
		del socket.create_connection
		self.verifyInternet_tearDown()
	
	def test_verifyInternet_ERROR_SOCKET(self):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyInternet_setUp(online = False)
		controllerInstance.gsmInstance.telitConnected = PropertyMock(return_value = False)
		socket.gethostbyname = MagicMock(side_effect = socket.error)
		
		self.assertRaises(socket.error, controllerInstance.verifyInternetConnection(controllerInstance.gprsInstance))
		socket.gethostbyname.assert_called_once()
		logger.write.assert_not_called()
		controllerInstance.telit_lock.release.assert_not_called()
		
		del controllerInstance.gsmInstance.telitConnected
		del socket.gethostbyname
		self.verifyInternet_tearDown()
	
	def test_verifyInternet_ERROR_AT(self):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyInternet_setUp(online = False)
		controllerInstance.gsmInstance.telitConnected = PropertyMock(return_value = True)
		controllerInstance.gsmInstance.active_call = PropertyMock(return_value = False)
		controllerInstance.gsmInstance.sendAT = MagicMock(side_effect = modemClass.AtTimeout)
		controllerInstance.telit_lock.acquire = MagicMock()
		
		self.assertRaises(modemClass.AtTimeout, controllerInstance.verifyInternetConnection(controllerInstance.gprsInstance))
		controllerInstance.gsmInstance.sendAT.assert_called_once()
		controllerInstance.telit_lock.acquire.assert_called_once()
		logger.write.assert_not_called()
		controllerInstance.telit_lock.release.assert_called_once()
		
		del controllerInstance.gsmInstance.telitConnected
		del controllerInstance.gsmInstance.active_call
		del controllerInstance.gsmInstance.sendAT
		del controllerInstance.telit_lock.acquire		
		self.verifyInternet_tearDown()
	
	def test_verifyInternet_ERROR_SERIAL(self):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyInternet_setUp(online = False)
		controllerInstance.gsmInstance.telitConnected = PropertyMock(return_value = True)
		controllerInstance.gsmInstance.active_call = PropertyMock(return_value = False)
		controllerInstance.gsmInstance.sendAT = MagicMock(side_effect = serial.SerialException)
		controllerInstance.telit_lock.acquire = MagicMock()
		
		self.assertRaises(serial.SerialException, controllerInstance.verifyInternetConnection(controllerInstance.gprsInstance))
		controllerInstance.gsmInstance.sendAT.assert_called_once()
		controllerInstance.telit_lock.acquire.assert_called_once()
		logger.write.assert_not_called()
		controllerInstance.telit_lock.release.assert_called_once()
		
		del controllerInstance.gsmInstance.telitConnected
		del controllerInstance.gsmInstance.active_call
		del controllerInstance.gsmInstance.sendAT
		del controllerInstance.telit_lock.acquire		
		self.verifyInternet_tearDown()
		

class VerifyTelitTest(unittest.TestCase):
	
	def setUp(self):
		logger.write = MagicMock()
		time.sleep = MagicMock()
		REFRESH_TIME = JSON_CONFIG["COMMUNICATOR"]["REFRESH_TIME"]
		global controllerInstance
		controllerInstance = controllerClass.Controller(REFRESH_TIME)
		
	def tearDown(self):
		global controllerInstance
		del controllerInstance
		patch.stopall()
		del logger.write
		del time.sleep
		
	def verifyTelit_setUp(self, call = False, isActive = False):
		controllerInstance.telit_lock = MagicMock()
		controllerInstance.telit_lock.acquire = MagicMock()
		controllerInstance.telit_lock.release = MagicMock()
		controllerInstance.gsmInstance.active_call = PropertyMock(return_value = call)
		controllerInstance.gprsInstance.isActive = PropertyMock(return_value = isActive)
		
	def verifyTelit_tearDown(self):
		del controllerInstance.telit_lock.acquire
		del controllerInstance.telit_lock.release
		del controllerInstance.telit_lock
		del controllerInstance.gsmInstance.active_call
		del controllerInstance.gprsInstance.isActive
		
	def test_verifyTelit_CGPADDR(self):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyTelit_setUp()
		controllerInstance.gsmInstance.sendAT = MagicMock(return_value= ['#CGPADDR: 0,"192.168.1.1"  ', "", "OK"])
		controllerInstance.gsmInstance.localInterface = MagicMock(return_value = 'ttyUSB0')
		
		self.assertTrue(controllerInstance.verifyTelitGprsConnection())
		self.assertEqual(controllerInstance.gprsInstance.localAddress, "192.168.1.1")
		
		del controllerInstance.gsmInstance.sendAT
		del controllerInstance.gsmInstance.localInterface
		self.verifyTelit_tearDown()
		
	def test_verifyTelit_SGACT(self):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyTelit_setUp()
		controllerInstance.gsmInstance.sendAT = MagicMock(side_effect = [["", "", "OK"], ['#SGACT: 192.168.1.2  ', "", "OK"]])
		controllerInstance.gsmInstance.localInterface = MagicMock(return_value = 'ttyUSB0')
		
		self.assertTrue(controllerInstance.verifyTelitGprsConnection())
		self.assertEqual(controllerInstance.gprsInstance.localAddress, "192.168.1.2")
		
		del controllerInstance.gsmInstance.sendAT
		del controllerInstance.gsmInstance.localInterface
		self.verifyTelit_tearDown()
	
	def test_verifyTelit_ACTIVE(self):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyTelit_setUp(isActive = True)
		controllerInstance.gsmInstance.sendAT = MagicMock(return_value = ['1  ','#SGACT: 192.168.1.2  ', "", "OK"])

		self.assertTrue(controllerInstance.verifyTelitGprsConnection())
		logger.write.assert_not_called()
		
		del controllerInstance.gsmInstance.sendAT
		self.verifyTelit_tearDown()
		
	def test_verifyTelit_ACTIVE_RAISE(self):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyTelit_setUp(isActive = True)
		controllerInstance.gsmInstance.sendAT = MagicMock(return_value = ['0  ','#SGACT: 192.168.1.2  ', "", "OK"])

		self.assertFalse(controllerInstance.verifyTelitGprsConnection())
		logger.write.assert_called_once()
		
		del controllerInstance.gsmInstance.sendAT
		self.verifyTelit_tearDown()
		
	def test_verifyTelit_NOT_ACTIVE_RAISE(self):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyTelit_setUp()
		controllerInstance.gsmInstance.sendAT = MagicMock(side_effect = serial.SerialException)

		self.assertFalse(controllerInstance.verifyTelitGprsConnection())
		logger.write.assert_not_called()
		
		del controllerInstance.gsmInstance.sendAT
		self.verifyTelit_tearDown()

class VerifyAndroidTest(unittest.TestCase):
	
	def setUp(self):
		logger.write = MagicMock()
		time.sleep = MagicMock()
		REFRESH_TIME = JSON_CONFIG["COMMUNICATOR"]["REFRESH_TIME"]
		global controllerInstance
		controllerInstance = controllerClass.Controller(REFRESH_TIME)
		
	def tearDown(self):
		global controllerInstance
		del controllerInstance
		patch.stopall()
		del logger.write
		del time.sleep
		
	def verifyAndroid_setUp(self, first = None, second = None, android_wifi = '', android_3G = '', error = ''):
		subprocess.Popen.communicate = MagicMock(side_effect = [[android_wifi, error], [android_3G, error]])
		networkClass.Network.localInterface = PropertyMock(side_effect = [first, second])
		
	def verifyAndroid_tearDown(self):
		del networkClass.Network.localInterface
		del subprocess.Popen.communicate
		
	def patch_verifyAndroid(f):
		@patch("controllerClass.Controller.verifyNetworkConnection")
		@patch('controllerClass.Controller.closeConnection')
		def functor(*args, **kwargs):
			return f(*args, **kwargs)
		return functor
		
	@patch_verifyAndroid
	def test_verifyAndroid_WIFI_NONE(self, close_call, network_call):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyAndroid_setUp(android_wifi = 'WIFI')
		
		controllerInstance.verifyAndroidStatus()
		close_call.assert_not_called()
		network_call.assert_called_once()
		
		self.verifyAndroid_tearDown()
		
	@patch_verifyAndroid
	def test_verifyAndroid_WIFI(self, close_call, network_call):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyAndroid_setUp(first = "wlan0", android_wifi = 'WIFI')
		
		controllerInstance.verifyAndroidStatus()
		close_call.assert_called_once()
		network_call.assert_called_once()
		
		self.verifyAndroid_tearDown()
		
	@patch_verifyAndroid
	def test_verifyAndroid_GPRS_NONE(self, close_call, network_call):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyAndroid_setUp(android_3G = 'GPRS')
		
		controllerInstance.verifyAndroidStatus()
		close_call.assert_not_called()
		network_call.assert_called_once()
		
		self.verifyAndroid_tearDown()
		
	@patch_verifyAndroid
	def test_verifyAndroid_GPRS(self, close_call, network_call):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyAndroid_setUp(first = "ppp0", android_3G = 'GPRS')
		
		controllerInstance.verifyAndroidStatus()
		close_call.assert_called_once()
		network_call.assert_called_once()
		
		self.verifyAndroid_tearDown()
		
	@patch_verifyAndroid
	def test_verifyAndroid_NO_CONNECTIVITY(self, close_call, network_call):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyAndroid_setUp(first = "wlan0", second = "ppp0")
		
		controllerInstance.verifyAndroidStatus()
		self.assertEqual(close_call.call_count, 2)
		network_call.assert_not_called()
		
		self.verifyAndroid_tearDown()
		
	@patch_verifyAndroid
	def test_verifyAndroid_WIFI_ERROR(self, close_call, network_call):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyAndroid_setUp(android_wifi = "WIFI", error = 'ERROR', first = "wlan0", second = "ppp0")
		
		controllerInstance.verifyAndroidStatus()
		self.assertEqual(close_call.call_count, 2)
		network_call.assert_not_called()
		
		self.verifyAndroid_tearDown()
		
	@patch_verifyAndroid
	def test_verifyAndroid_WIFI_ERROR(self, close_call, network_call):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyAndroid_setUp(android_3G = "GPRS", error = 'ERROR', first = "wlan0", second = "ppp0")
		
		controllerInstance.verifyAndroidStatus()
		self.assertEqual(close_call.call_count, 2)
		network_call.assert_not_called()
		
		self.verifyAndroid_tearDown()


class VerifyBluetoothTest(unittest.TestCase):
	
	def setUp(self):
		logger.write = MagicMock()
		REFRESH_TIME = JSON_CONFIG["COMMUNICATOR"]["REFRESH_TIME"]
		global controllerInstance
		controllerInstance = controllerClass.Controller(REFRESH_TIME)
		
	def tearDown(self):
		global controllerInstance
		del controllerInstance
		patch.stopall()
		del logger.write
		
	def verifyBluetooth_setUp(self, comm = ['Devices:\n', '\thci0\t00:11:22:33:44:55\n', '\thci1\tAA:BB:CC:DD:EE:FF\n'], err = "", interface = None, isActive = False):
		subprocess.Popen.communicate = MagicMock(return_value = [comm, err])
		controllerInstance.bluetoothInstance.localInterface = PropertyMock(return_value = interface)
		controllerInstance.bluetoothInstance.isActive = PropertyMock(return_value = isActive)
		
	def verifyBluetooth_tearDown(self):
		del controllerInstance.bluetoothInstance.localInterface
		del controllerInstance.bluetoothInstance.isActive
		del subprocess.Popen.communicate
		
	@patch("threading.Thread.start")
	def test_verifyBluetooth_CONNECT(self, start_call):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyBluetooth_setUp()
		controllerInstance.bluetoothInstance.thread = threading.Thread
		file_open = mock_open()
		controllerInstance.bluetoothInstance.connect = MagicMock(return_value = True)
		controllerInstance.bluetoothInstance.localAddress = PropertyMock(return_value = "11:22:33:44:55:66")
		
		self.assertTrue(controllerInstance.verifyBluetoothConnection())
		start_call.assert_called_once()
		
		del controllerInstance.bluetoothInstance.thread
		del file_open
		del controllerInstance.bluetoothInstance.connect
		del controllerInstance.bluetoothInstance.localAddress
		self.verifyBluetooth_tearDown()
		
	@patch("threading.Thread.start")
	def test_verifyBluetooth_NO_CONNECT(self, start_call):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyBluetooth_setUp()
		controllerInstance.bluetoothInstance.thread = threading.Thread
		file_open = mock_open()
		controllerInstance.bluetoothInstance.connect = MagicMock(return_value = False)
		
		self.assertFalse(controllerInstance.verifyBluetoothConnection())
		start_call.assert_not_called()
		
		del controllerInstance.bluetoothInstance.thread
		del file_open
		del controllerInstance.bluetoothInstance.connect
		self.verifyBluetooth_tearDown()
	
	def test_verifyBluetooth_INTERFACE(self):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyBluetooth_setUp(interface = "hci0")
		controllerInstance.bluetoothInstance.successfulConnection = PropertyMock(return_value = True)
		
		self.assertTrue(controllerInstance.verifyBluetoothConnection())
		
		del controllerInstance.bluetoothInstance.successfulConnection
		self.verifyBluetooth_tearDown()
		
	def test_verifyBluetooth_INTERFACE_NO_SUCCESS(self):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyBluetooth_setUp(interface = "hci0")
		controllerInstance.bluetoothInstance.successfulConnection = PropertyMock(return_value = False)
		
		self.assertFalse(controllerInstance.verifyBluetoothConnection())
		
		del controllerInstance.bluetoothInstance.successfulConnection
		self.verifyBluetooth_tearDown()
		
	def test_verifyBluetooth_CONTINUE(self):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyBluetooth_setUp(interface = "hci1")
		controllerInstance.bluetoothInstance.successfulConnection = PropertyMock(return_value = True)
		
		self.assertTrue(controllerInstance.verifyBluetoothConnection())
		
		del controllerInstance.bluetoothInstance.successfulConnection
		self.verifyBluetooth_tearDown()
		
	@patch("controllerClass.Controller.closeConnection")
	def test_verifyBluetooth_CLOSE(self, close_call):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyBluetooth_setUp(interface = "hci2")
		file_open = mock_open()
		
		self.assertFalse(controllerInstance.verifyBluetoothConnection())
		close_call.assert_called_once()
		
		del file_open
		self.verifyBluetooth_tearDown()
		
	@patch("controllerClass.Controller.closeConnection")
	def test_verifyBluetooth_NO_CLOSE(self, close_call):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyBluetooth_setUp(comm = ['Devices:\n'])
		
		self.assertFalse(controllerInstance.verifyBluetoothConnection())
		close_call.assert_not_called()
		
		self.verifyBluetooth_tearDown()
		
	
class VerifyEmailTest(unittest.TestCase):
	
	def setUp(self):
		logger.write = MagicMock()
		REFRESH_TIME = JSON_CONFIG["COMMUNICATOR"]["REFRESH_TIME"]
		global controllerInstance
		controllerInstance = controllerClass.Controller(REFRESH_TIME)
		
	def tearDown(self):
		global controllerInstance
		del controllerInstance
		patch.stopall()
		del logger.write
		
	def verifyEmail_setUp(self, online = [True], mode = 1, success = False, isAlive = False):
		networkClass.Network.online = PropertyMock(side_effect = online)
		emailClass.Email.mode = PropertyMock(return_value = mode)
		emailClass.Email.thread = threading.Thread
		emailClass.Email.successfulConnection = PropertyMock(return_value = success)
		threading.Thread.isAlive = MagicMock(return_value = isAlive)
		
		
	def verifyEmail_tearDown(self):
		del networkClass.Network.online
		del emailClass.Email.mode
		del emailClass.Email.thread
		del emailClass.Email.successfulConnection
		del threading.Thread.isAlive
		
	@patch("threading.Thread.join")
	@patch("threading.Thread.start")
	def test_verifyEmail_MODE_1(self, start_call, join_call):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyEmail_setUp(mode = 2, isAlive = True)
		self.verifyEmail_MODES(1, start_call, join_call)
		self.verifyEmail_tearDown()
	
	@patch("threading.Thread.join")
	@patch("threading.Thread.start")
	def test_verifyEmail_MODE_2(self, start_call, join_call):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyEmail_setUp(online = [False, True], mode = 3, isAlive = True)
		self.verifyEmail_MODES(2, start_call, join_call)
		self.verifyEmail_tearDown()
	
	@patch("threading.Thread.join")
	@patch("threading.Thread.start")
	def test_verifyEmail_MODE_3(self, start_call, join_call):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyEmail_setUp(online = [False, False, True], mode = 4, isAlive = True)
		modemClass.Gsm.telitConnected = PropertyMock(return_value = True)
		self.verifyEmail_MODES(3, start_call, join_call)
		del modemClass.Gsm.telitConnected
		self.verifyEmail_tearDown()
		
	@patch("threading.Thread.join")
	@patch("threading.Thread.start")		
	def test_verifyEmail_MODE_4(self, start_call, join_call):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyEmail_setUp(online = [False, False, False, True], mode = 1, isAlive = True)
		self.verifyEmail_MODES(4, start_call, join_call)
		self.verifyEmail_tearDown()
	
	def verifyEmail_MODES(self, mode, start_call, join_call):
		emailClass.Email.isActive = PropertyMock()
		emailClass.Email.connect = MagicMock(return_value = True)
		emailClass.Email.emailAccount = PropertyMock(return_value = "example@domain.com")
		
		self.assertTrue(controllerInstance.verifyEmailConnection())
		self.assertEqual(emailClass.Email.mode, mode)
		start_call.assert_called_once()
		join_call.assert_called_once()
		
		del emailClass.Email.isActive
		del emailClass.Email.connect
		del emailClass.Email.emailAccount
		
	def test_verifyEmail_MODE_FALSE(self):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyEmail_setUp(online = [False, False, False, False])
		
		self.assertFalse(controllerInstance.verifyEmailConnection())
		
		self.verifyEmail_tearDown()
		
	
	@patch("threading.Thread.join")
	@patch("threading.Thread.start")
	def test_verifyEmail_NO_CONNECT(self, start_call, join_call):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyEmail_setUp()
		emailClass.Email.connect = MagicMock(return_value = False)
		
		self.assertFalse(controllerInstance.verifyEmailConnection())
		start_call.assert_not_called()
		join_call.assert_not_called()
		
		del emailClass.Email.connect
		self.verifyEmail_tearDown()
		
	def test_verifyEmail_ACTIVE(self):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyEmail_setUp(success = True)
		emailClass.Email.isActive = PropertyMock(return_value = True)
		
		self.assertTrue(controllerInstance.verifyEmailConnection())
		
		del emailClass.Email.isActive
		self.verifyEmail_tearDown()
		
	def test_verifyEmail_FALSE(self):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyEmail_setUp(success = True)
		emailClass.Email.isActive = PropertyMock(return_value = False)
		
		self.assertFalse(controllerInstance.verifyEmailConnection())
		
		del emailClass.Email.isActive
		self.verifyEmail_tearDown()
		
	@patch("threading.Thread.start")
	@patch("threading.Thread")
	def test_verifyEmail_EXCEPT(self, thread_call, start_call):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyEmail_setUp()
		emailClass.Email.connect = MagicMock(side_effect = socket.gaierror)
		emailClass.Email.isActive = PropertyMock(return_value = True)
		
		self.assertFalse(controllerInstance.verifyEmailConnection())
		start_call.assert_not_called()
		thread_call.assert_called_once()
		
		del emailClass.Email.connect
		del emailClass.Email.isActive
		self.verifyEmail_tearDown()
			
import ftplib
from modemClass import AtTimeout

class VerifyFtpTest(unittest.TestCase):
	
	def setUp(self):
		logger.write = MagicMock()
		REFRESH_TIME = JSON_CONFIG["COMMUNICATOR"]["REFRESH_TIME"]
		global controllerInstance
		controllerInstance = controllerClass.Controller(REFRESH_TIME)
		
	def tearDown(self):
		global controllerInstance
		del controllerInstance
		patch.stopall()
		del logger.write
		
	def verifyFtp_setUp(self, mode = 2):
		ftpClass.Ftp.ftp_mode = PropertyMock(return_value = mode)
		ftpClass.Ftp.isActive = PropertyMock()
		
		
	def verifyFtp_tearDown(self):
		del ftpClass.Ftp.ftp_mode
		del ftpClass.Ftp.isActive
		
	def patch_verifyEmail(f):
		@patch("threading.Thread.join")
		def functor(*args, **kwargs):
			return f(*args, **kwargs)
		return functor
		
	@patch('ftpClass.Ftp.connect')
	def test_verifyFtp_NETWORK(self, connect_call):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyFtp_setUp()
		networkClass.Network.online = PropertyMock(side_effect = [False, True])
		ftpClass.Ftp.ftpServer = ftplib.FTP
		controllerClass.Controller.communicatorName = PropertyMock(return_value = "controller")
		ftplib.FTP.nlst = MagicMock(return_value = ["controller.-text.-origin.-20180705.-123456", "notcontroller.-instance.-origin.-20180705.-123524", "controller.-archivo.txt.-origin.-20180705.-124524"])
		ftpClass.Ftp.receive = MagicMock()
		ftplib.FTP.delete = MagicMock()
		ftplib.FTP.quit = MagicMock()
		
		self.assertTrue(controllerInstance.verifyFtpConnection())
		connect_call.assert_called_once()
		self.assertEqual(ftpClass.Ftp.receive.call_count, 2)
		
		del networkClass.Network.online
		del ftpClass.Ftp.ftpServer
		del controllerClass.Controller.communicatorName
		del ftplib.FTP.nlst
		del ftpClass.Ftp.receive
		del ftplib.FTP.delete
		del ftplib.FTP.quit
		self.verifyFtp_tearDown()
		
	@patch('ftpClass.Ftp.connect')
	def test_verifyFtp_TELIT(self, connect_call):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyFtp_setUp()
		networkClass.Network.online = PropertyMock(side_effect = [False, False])
		modemClass.Gsm.telitConnected = PropertyMock(return_value = True)
		modemClass.Gsm.sendAT = MagicMock(side_effect = ["", ["controller.-text.-origin.-20180705.-123456", "notcontroller.-instance.-origin.-20180705.-123524", "controller.-archivo.txt.-origin.-20180705.-124524"], "", "", ""])
		controllerClass.Controller.communicatorName = PropertyMock(return_value = "controller")
		ftpClass.Ftp.receive = MagicMock()
		controllerInstance.telit_lock = threading.Condition
		threading.Condition.release = MagicMock()
		
		self.assertTrue(controllerInstance.verifyFtpConnection())
		connect_call.assert_called_once()
		self.assertEqual(ftpClass.Ftp.receive.call_count, 2)
		
		del networkClass.Network.online
		del modemClass.Gsm.telitConnected
		del modemClass.Gsm.sendAT
		del controllerClass.Controller.communicatorName
		del ftpClass.Ftp.receive
		del controllerInstance.telit_lock
		del threading.Condition.release
		self.verifyFtp_tearDown()
		
		
	@patch('ftpClass.Ftp.connect')
	def test_verifyFtp_EXCEPT(self, connect_call):
		print "%s" % sys._getframe().f_code.co_name
		self.verifyFtp_setUp()
		networkClass.Network.online = PropertyMock(side_effect = [False, False])
		modemClass.Gsm.telitConnected = PropertyMock(return_value = True)
		modemClass.Gsm.sendAT = MagicMock(side_effect = AtTimeout)
		controllerInstance.telit_lock = threading.Condition
		threading.Condition.acquire = MagicMock()
		threading.Condition.release = MagicMock()
		
		self.assertFalse(controllerInstance.verifyFtpConnection())
		threading.Condition.release.assert_called_once()
		
		del networkClass.Network.online
		del modemClass.Gsm.telitConnected
		del modemClass.Gsm.sendAT
		del controllerInstance.telit_lock
		del threading.Condition.acquire
		del threading.Condition.release
		self.verifyFtp_tearDown()
		
		
		
		
				
if __name__ == '__main__':
	unittest.main()
		
