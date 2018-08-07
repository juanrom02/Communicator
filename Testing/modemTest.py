import unittest
from mock import MagicMock, PropertyMock, patch, mock_open, call
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

import modemClass
import callClass
from modemClass import ATCommandError, AtNewCall, AtNoCarrier, AdbError
import messageClass
import networkClass
import ftpClass

import json
import Queue
import logger
import time
import subprocess
import pexpect
import regex
import threading
import messaging
import requests
from messaging.sms import SmsDeliver
import serial
import pickle

JSON_FILE = 'config.json'
JSON_CONFIG = json.load(open(JSON_FILE))

modemInstance = modemClass.Modem

class ModemTest(unittest.TestCase):
	
	def setUp(self):
		logger.write = MagicMock()
		global modemInstance
		modemInstance = modemClass.Modem()
		
	def tearDown(self):
		global modemInstance
		del modemInstance
		patch.stopall()
		del logger.write
		
	def test_sendAT_CALL(self):
		print "%s" % sys._getframe().f_code.co_name
		modemClass.Modem.active_call= False
		modemInstance.modemInstance.write = MagicMock()
		modemInstance.modemInstance.readline = MagicMock(side_effect = ["AT+CLIP=1","RING", '+CLIP: "0303456",', "OK"])
		modemInstance.getTelephoneNumber = MagicMock(return_value = '')
		
		modemInstance.sendAT("AT+CLIP=1")
		self.assertTrue(modemInstance.active_call)
		self.assertTrue(modemInstance.new_call)
		self.assertEqual("desconocido", modemInstance.callerID)

	def test_sendAT_INSTANT_CALL(self):
		print "%s" % sys._getframe().f_code.co_name
		modemInstance.modemInstance.write = MagicMock()
		modemInstance.modemInstance.readline = MagicMock(side_effect = ["RING", '+CLIP: "0303456",', "OK"])
		modemInstance.getTelephoneNumber = MagicMock(return_value = 'client02')
		
		modemInstance.sendAT("AT+CLIP=1")
		self.assertTrue(modemInstance.active_call)
		self.assertTrue(modemInstance.new_call)
		self.assertEqual("client02", modemInstance.callerID)
		
		
	def test_sendAT_ERROR(self):
		print "%s" % sys._getframe().f_code.co_name
		modemInstance.modemInstance.write = MagicMock()
		modemInstance.modemInstance.readline = MagicMock(side_effect = ["AT+CLIP=1","ERROR"])
		modemInstance.getTelephoneNumber = MagicMock(return_value = '')
		
		with self.assertRaises(ATCommandError) as err:
			modemInstance.sendAT("AT+CLIP=1")
		self.assertFalse(modemInstance.active_call)
		self.assertFalse(modemInstance.new_call)
		
	def test_sendAT_NO_CARRIER(self):
		print "%s" % sys._getframe().f_code.co_name
		modemInstance.modemInstance.write = MagicMock()
		modemInstance.modemInstance.readline = MagicMock(side_effect = ["AT+CLIP=1","NO CARRIER"])
		modemInstance.getTelephoneNumber = MagicMock(return_value = '')
		
		with self.assertRaises(AtNoCarrier) as err:
			modemInstance.sendAT("AT+CLIP=1")
		self.assertFalse(modemInstance.active_call)
		self.assertFalse(modemInstance.new_call)
		
	@patch("serial.Serial.close")
	def test_Modem_close(self, close_call):
		print "%s" % sys._getframe().f_code.co_name
		
		modemInstance.closePort()
		close_call.assert_called_once()
		

gsmInstance = modemClass.Gsm
gsmInstance.modemInstance = modemClass.Modem
gsmInstance.callInstance = callClass.Call
gsmInstance.wifiInstance = networkClass.Network
gsmInstance.ethernetInstance = networkClass.Network
gsmInstance.ftpInstance = ftpClass.Ftp
		
class GsmTest(unittest.TestCase):
	
	def setUp(self):
		logger.write = MagicMock()
		RECEPTION_QSIZE = JSON_CONFIG["COMMUNICATOR"]["RECEPTION_QSIZE"]
		receptionQueue = Queue.PriorityQueue(RECEPTION_QSIZE)
		global gsmInstance
		gsmInstance = modemClass.Gsm(receptionQueue)
		
	def tearDown(self):
		global gsmInstance
		del gsmInstance
		patch.stopall()
		del logger.write
		
	@patch("serial.Serial.close")
	def test_Gsm_close(self, close_call):
		print "%s" % sys._getframe().f_code.co_name
		
		gsmInstance.close()
		close_call.assert_called_once()
		
	@patch("time.sleep")
	def test_connectAT_NO_REG(self, sleep_call):
		print "%s" % sys._getframe().f_code.co_name
		gsmInstance.modemInstance.open = MagicMock()
		gsmInstance.sendAT = MagicMock(side_effect = ["", "", ["","+CREG: 0,0\r"]])
		
		self.assertFalse(gsmInstance.connectAT("ttyUSB0"))
		
	@patch("time.sleep")
	@patch("modemClass.Gsm.configPPP")
	def test_connectAT_TELIT(self, sleep_call, ppp_call):
		print "%s" % sys._getframe().f_code.co_name
		gsmInstance.modemInstance.open = MagicMock()
		gsmInstance.sendAT = MagicMock(side_effect = ["", "", ["","+CREG: 0,1\r"], ["AT+GMM", "UL865-NAR"], ""])
		
		self.assertTrue(gsmInstance.connectAT("ttyUSB0"))
		self.assertTrue(gsmInstance.modemInstance.dsrdtr)
		self.assertEqual(1, gsmInstance.modemInstance.dtr)
		self.assertTrue(gsmInstance.telitConnected)
		ppp_call.assert_called_once()
		
	@patch("time.sleep")
	@patch("modemClass.Gsm.configPPP")
	def test_connectAT_TELIT(self, sleep_call, ppp_call):
		print "%s" % sys._getframe().f_code.co_name
		gsmInstance.modemInstance.open = MagicMock()
		gsmInstance.sendAT = MagicMock(side_effect = ["", "", ["","+CREG: 0,1\r"], ["AT+GMM", "UL865-NAR"], ""])
		
		self.assertTrue(gsmInstance.connectAT("ttyUSB0"))
		self.assertTrue(gsmInstance.modemInstance.dsrdtr)
		self.assertEqual(1, gsmInstance.modemInstance.dtr)
		self.assertTrue(gsmInstance.telitConnected)
		gsmInstance.sendAT.assert_has_calls([call('AT#EXECSCR')], True)
		
		
	@patch("time.sleep")
	@patch("modemClass.Gsm.configPPP")
	def test_connectAT_MF626(self, sleep_call, ppp_call):
		print "%s" % sys._getframe().f_code.co_name
		gsmInstance.modemInstance.open = MagicMock()
		gsmInstance.sendAT = MagicMock(side_effect = ["", "", ["","+CREG: 0,1\r"], ["AT+GMM", "MF626"], "", "", "", ""])
		
		self.assertTrue(gsmInstance.connectAT("ttyUSB0"))
		self.assertFalse(gsmInstance.telitConnected)
		gsmInstance.sendAT.assert_has_calls([call('AT+CPMS="SM"')], True)
		
	@patch("time.sleep")
	@patch("modemClass.Gsm.configPPP")
	def test_connectAT_OTHER(self, sleep_call, ppp_call):
		print "%s" % sys._getframe().f_code.co_name
		gsmInstance.modemInstance.open = MagicMock()
		gsmInstance.sendAT = MagicMock(side_effect = ["", "", ["","+CREG: 0,1\r"], ["AT+GMM", "OTHER"], "", "", "", ""])
		
		self.assertTrue(gsmInstance.connectAT("ttyUSB0"))
		self.assertFalse(gsmInstance.telitConnected)
		gsmInstance.sendAT.assert_has_calls([call('AT+CLIP=1')], True)
		
	@patch("subprocess.Popen.communicate")
	@patch("subprocess.call")
	@patch("time.sleep")
	def test_connectAndroid(self, sleep_call, spcall_call, popen_call):
		print "%s" % sys._getframe().f_code.co_name
		popen_call.side_effect = [["model: Xiaomi Mi 5S", ""], ["", ""]]
		file_patch = mock_open()
		
		self.assertTrue(gsmInstance.connectAndroid())
		self.assertEqual(popen_call.call_count, 2)
		self.assertEqual(spcall_call.call_count, 2)

	def test_receive_ANDROID(self):
		print "%s" % sys._getframe().f_code.co_name
		modemClass.Gsm.androidConnected = True
		gsmInstance.receiveAndroid = MagicMock()
		gsmInstance.receiveAT = MagicMock()
		
		gsmInstance.receive()
		gsmInstance.receiveAndroid.assert_called_once()
		gsmInstance.receiveAT.assert_not_called()
		
		
	def test_receive_AT(self):
		print "%s" % sys._getframe().f_code.co_name
		modemClass.Gsm.androidConnected = False
		gsmInstance.receiveAndroid = MagicMock()
		gsmInstance.receiveAT = MagicMock()
		
		gsmInstance.receive()
		gsmInstance.receiveAndroid.assert_not_called()
		gsmInstance.receiveAT.assert_called_once()
		
	@patch("pexpect.spawn")
	@patch("Queue.PriorityQueue.put")
	@patch("pickle.loads")
	def test_receiveAndroid(self, pickle_call, put_call, spawn_call):
		print "%s" % sys._getframe().f_code.co_name
		patch("regex.findall").start()
		patch("time.sleep").start()
		modemClass.Gsm.isActive = PropertyMock(side_effect = [True, True, True, True, False])
		gsmInstance.sendPexpect = MagicMock(side_effect = ["", "", "", "SELECT _id, address, body FROM sms WHERE read = 0;"])
		regex.findall.return_value = ["1285|+54987654321|INSTANCEccopy_reg\n_reconstructor\np0\n(cmessageClass\nInfoMessage\np1\nc__builtin__\nobject\np2\nNtp3\nRp4\n(dp5\nS'infoText'\np6\nS'alskeufhd'\np7\nsS'sender'\np8\nS'Juancete'\np9\nsS'receiver'\np10\nS'client05'\np11\nsS'priority'\np12\nI10\nsb."
									 ,"1286|+54123456789|Hola 13/06 11:58"]
		gsmInstance.getTelephoneNumber = MagicMock(side_effect = [3512560536, 3512641040])
		
		gsmInstance.receiveAndroid()
		spawn_call.assert_called_once()
		self.assertEqual(2, gsmInstance.getTelephoneNumber.call_count)
		self.assertEqual(2, put_call.call_count)
		pickle_call.assert_called_once()
		
	@patch("pexpect.spawn")
	@patch("Queue.PriorityQueue.put")
	@patch("pickle.loads")
	def test_receiveAndroid_PICKLE_ERROR(self, pickle_call, put_call, spawn_call):
		print "%s" % sys._getframe().f_code.co_name
		patch("regex.findall").start()
		patch("time.sleep").start()
		pickle_call.side_effect = pickle.PickleError
		modemClass.Gsm.isActive = PropertyMock(side_effect = [True, True, True, True, False])
		gsmInstance.sendPexpect = MagicMock(side_effect = ["", "", "", "SELECT _id, address, body FROM sms WHERE read = 0;"])
		regex.findall.return_value = ["1285|+54987654321|INSTANCEccopy_reg\n_reconstructor\np0\n(cmessageClass\nInfoMessage\np1\nc__builtin__\nobject\np2\nNtp3\nRp4\n(dp5\nS'infoText'\np6\nS'alskeufhd'\np7\nsS'sender'\np8\nS'Juancete'\np9\nsS'receiver'\np10\nS'client05'\np11\nsS'priority'\np12\nI10\nsb."
									 ,"1286|+54123456789|Hola 13/06 11:58"]
		gsmInstance.getTelephoneNumber = MagicMock(side_effect = [3512560536, 3512641040])
		
		gsmInstance.receiveAndroid()
		spawn_call.assert_called_once()
		self.assertEqual(2, gsmInstance.getTelephoneNumber.call_count)
		put_call.assert_called_once()
		logger.write.assert_any_call('ERROR', '[GSM] No se pudo rearmar la instancia recibida de 3512560536')
		
	def receiveAT_setUp(self, udh):
		patch("time.sleep").start()
		patch("modemClass.Gsm.isActive",		new_callable = PropertyMock, 	side_effect = [True, True, True, False]).start()
		smsAmount = 	patch("modemClass.Gsm.smsAmount",	  	new_callable = PropertyMock, side_effect = [0,2,2,1,1,0,0])
		smsHeaderList = patch("modemClass.Gsm.smsHeaderList", 	new_callable = PropertyMock, side_effect = [["1", "2"], ["1", "2"], ["2"], ["2"]])
		smsBodyList = 	patch("modemClass.Gsm.smsBodyList",   	new_callable = PropertyMock, side_effect = [["1", "2"], ["1", "2"], ["2"], ["2"]])
		smsAmount.start()
		smsHeaderList.start()
		smsBodyList.start()

		sms1 = messaging.sms.deliver.SmsDeliver
		sms1.number = "0303456"
		sms1.text = "multi"
		sms1.udh = udh
		sms2 = messaging.sms.deliver.SmsDeliver
		sms2.number = "0303456"
		sms2.text = "part"
		sms2.udh = udh
		
		gsmInstance.smsDeliverFncn = MagicMock(side_effect = [sms1, sms2])
		gsmInstance.resetSmsValues = MagicMock()
		gsmInstance.getTelephoneNumber = MagicMock(side_effect = [3512641040, 3512641040, 3512641040])
		gsmInstance.putSms = MagicMock()
		gsmInstance.readTelitSms = MagicMock()
		gsmInstance.readModemSms = MagicMock()

	def test_receiveAT_TELIT_INSTANCE(self):
		print "%s" % sys._getframe().f_code.co_name
		
		patch("serial.Serial.in_waiting", new_callable = PropertyMock,	return_value = 0).start()
		patch("modemClass.Gsm.telitConnected", new_callable = PropertyMock, side_effect = [True, False]).start()
		self.receiveAT_setUp("udh")
		gsmInstance.orderMultipartSms = MagicMock(side_effect = [[False, "partial message"],[True, "full message"]])
		
		gsmInstance.receiveAT()
		gsmInstance.putSms.assert_called_once()
		self.assertEqual(gsmInstance.orderMultipartSms.call_count, 2)
		gsmInstance.readTelitSms.assert_called_once()
		gsmInstance.readModemSms.assert_not_called()		
		
		
	def test_receiveAT_MODEM_PLAINTEXT(self):
		print "%s" % sys._getframe().f_code.co_name
		patch("time.sleep").start()
		
		patch("serial.Serial.in_waiting", 		new_callable = PropertyMock,	side_effect = [1, 0]).start()
		patch("modemClass.Gsm.telitConnected", 	new_callable = PropertyMock, 	return_value = False).start()
		self.receiveAT_setUp(None)
		gsmInstance.orderMultipartSms = MagicMock()
		
		gsmInstance.receiveAT()
		self.assertEqual(gsmInstance.putSms.call_count, 2)
		gsmInstance.orderMultipartSms.assert_not_called()
		gsmInstance.readTelitSms.assert_not_called()
		gsmInstance.readModemSms.assert_called_once()		
		
	def test_resetSmsValues(self):
		print "%s" % sys._getframe().f_code.co_name
		
		gsmInstance.smsAmount = 1
		gsmInstance.smsBodyList = ["a"]
		gsmInstance.smsHeaderList = ["b"]
		gsmInstance.smsConcatList = ["c"]
		
		gsmInstance.resetSmsValues()
	
		self.assertEqual(0, gsmInstance.smsAmount)
		self.assertFalse(gsmInstance.smsBodyList)
		self.assertFalse(gsmInstance.smsHeaderList)
		self.assertFalse(gsmInstance.smsConcatList)
		
	def test_readTelitSms(self):
		print "%s" % sys._getframe().f_code.co_name

		patch("time.sleep").start()
		
		modemClass.Modem.active_call= PropertyMock(side_effect = [True, False])
		gsmInstance.smsHeaderList = list()
		gsmInstance.telit_lock = MagicMock()
		gsmInstance.telit_lock.acquire = MagicMock()
		gsmInstance.telit_lock.wait = MagicMock()
		gsmInstance.telit_lock.release = MagicMock()
		gsmInstance.sendAT = MagicMock(return_value = ["+CMGL: 1", "PDU1", "+CMGL: 2", "PDU2", "OK"])
		
		gsmInstance.readTelitSms()
		self.assertEqual(2, gsmInstance.smsAmount)
		self.assertEqual(["+CMGL: 1", "+CMGL: 2"], gsmInstance.smsHeaderList)
		gsmInstance.telit_lock.wait.assert_called_once()
		
	def test_readModemSms_CMT_CMGL(self):
		print "%s" % sys._getframe().f_code.co_name
		
		patch("serial.Serial.in_waiting", new_callable = PropertyMock, return_value = 10).start()
		patch("serial.Serial.read", new_callable = MagicMock, return_value = "+CMT: 1\r\nPDU1\r\n+CMGL: 2\r\nPDU2").start()
		gsmInstance.smsHeaderList = list()
		gsmInstance.sendAT = MagicMock()
		
		gsmInstance.readModemSms()
		
		self.assertEqual(2, gsmInstance.sendAT.call_count)
		self.assertEqual(["+CMT: 1", "+CMGL: 2"], gsmInstance.smsHeaderList)
		
	def test_readModemSms_CMGS(self):
		print "%s" % sys._getframe().f_code.co_name
		
		patch("serial.Serial.in_waiting", new_callable = PropertyMock, return_value = 10).start()
		patch("serial.Serial.read", new_callable = MagicMock, return_value = "+CMGS:").start()
		gsmInstance.successfulSending = False
		gsmInstance.sendAT = MagicMock()
		
		gsmInstance.readModemSms()
		
		gsmInstance.sendAT.assert_not_called()
		self.assertTrue(gsmInstance.successfulSending)
		
	def test_readModemSms_CMS_ERROR(self):
		print "%s" % sys._getframe().f_code.co_name
		
		patch("serial.Serial.in_waiting", new_callable = PropertyMock, return_value = 10).start()
		patch("serial.Serial.read", new_callable = MagicMock, return_value = "+CMS ERROR").start()
		gsmInstance.successfulSending = True
		gsmInstance.sendAT = MagicMock()
		
		gsmInstance.readModemSms()
		
		gsmInstance.sendAT.assert_not_called()
		self.assertFalse(gsmInstance.successfulSending)
		
	def test_readModemSms_RING(self):
		print "%s" % sys._getframe().f_code.co_name
		
		patch("serial.Serial.in_waiting", new_callable = PropertyMock, return_value = 10).start()
		patch("serial.Serial.read", new_callable = MagicMock, return_value = "RING\r\n\r\n0303456").start()
		gsmInstance.sendAT = MagicMock()
		gsmInstance.getTelephoneNumber = MagicMock(return_value = 0303456)
		
		gsmInstance.readModemSms()
		
		gsmInstance.sendAT.assert_not_called()
		gsmInstance.getTelephoneNumber.assert_called_once()
		
	def readModemSms_setUp(self, read, arg):
		patch("serial.Serial.in_waiting", new_callable = PropertyMock, return_value = 10).start()
		patch("serial.Serial.read", new_callable = MagicMock, return_value = read).start()
		gsmInstance.sendAT = MagicMock()
		
		gsmInstance.readModemSms()
		
		gsmInstance.sendAT.assert_not_called()
		logger.write.assert_called_with('WARNING', arg)
		
	def test_readModemSms_BUSY(self):
		print "%s" % sys._getframe().f_code.co_name
		
		self.readModemSms_setUp('BUSY', '[GSM] El telefono destino se encuentra ocupado.')
		
	def test_readModemSms_NO_ANSWER(self):
		print "%s" % sys._getframe().f_code.co_name
		
		self.readModemSms_setUp('NO ANSWER', '[GSM] No hubo respuesta durante la llamada de voz.')
		
	def test_readModemSms_NO_CARRIER(self):
		print "%s" % sys._getframe().f_code.co_name
		
		self.readModemSms_setUp('NO CARRIER', '[GSM] Se perdio la conexion con el otro extremo.')
		
	def test_orderMultipartSms(self):
		print "%s" % sys._getframe().f_code.co_name
		
		gsmInstance.smsConcatList = ["multi"]
		
		sms = messaging.sms.deliver.SmsDeliver
		sms.text = "part"
		sms.udh = messaging.sms.udh.UserDataHeader
		sms.udh.concat = messaging.sms.udh.ConcatReference
		sms.udh.concat.cnt = 2
		sms.udh.concat.seq = 2
		
		hasEnded, smsMessage = gsmInstance.orderMultipartSms(sms)
		self.assertTrue(hasEnded)
		self.assertEqual("multipart", smsMessage)
		self.assertFalse(gsmInstance.smsConcatList)
		
	@patch("pickle.loads")
	def test_putSms_INSTANCE(self, pickle_call):
		print "%s" % sys._getframe().f_code.co_name
		
		patch("Queue.PriorityQueue.put").start()
		
		sms = "INSTANCE12345"
		
		gsmInstance.putSms(sms)
		
		pickle_call.assert_called_once()
		
	@patch("pickle.loads")
	def test_putSms_PLAIN_TEXT(self, pickle_call):
		print "%s" % sys._getframe().f_code.co_name
		
		patch("Queue.PriorityQueue.put").start()
		
		sms = "text"
		
		gsmInstance.putSms(sms)
		
		pickle_call.assert_not_called()
		
	def test_send_PLAINTEXT_CALL(self):
		print "%s" % sys._getframe().f_code.co_name
		
		message = messageClass.Message("sender", "receiver", 10)
		setattr(message, "plainText", "example")
		
		patch("networkClass.Network.online", new_callable = PropertyMock, return_value = False).start()
		patch("serial.Serial.open").start()
		patch("serial.Serial.close").start()
		patch("time.sleep").start()
		patch("subprocess.Popen.communicate", side_effect = [["",""],["",""]]).start()
		text_to_audio = patch("callClass.Call.text_to_audio").start()
		gsmInstance.telit_lock = MagicMock()
		gsmInstance.telit_lock.acquire = MagicMock()
		gsmInstance.telit_lock.release = MagicMock()
		gsmInstance.sendAT = MagicMock()
		gsmInstance.sendVoiceCall = MagicMock(return_value = True)
		gsmInstance.sendMessage = MagicMock()
		
		self.assertTrue(gsmInstance.send(message, 0303456, True))
		text_to_audio.assert_called_once()
		gsmInstance.sendVoiceCall.assert_called_once()
		gsmInstance.sendMessage.assert_not_called()
		
	def test_send_PLAINTEXT_CALL_EXCEPT(self):
		print "%s" % sys._getframe().f_code.co_name
		
		message = messageClass.Message("sender", "receiver", 10)
		setattr(message, "plainText", "example")
		
		patch("networkClass.Network.online", new_callable = PropertyMock, return_value = False).start()
		patch("serial.Serial.open").start()
		patch("serial.Serial.close").start()
		patch("time.sleep").start()
		patch("subprocess.Popen.communicate", side_effect = [requests.exceptions.ConnectionError,["",""]]).start()
		text_to_audio = patch("callClass.Call.text_to_audio").start()
		gsmInstance.telit_lock = MagicMock()
		gsmInstance.telit_lock.acquire = MagicMock()
		gsmInstance.telit_lock.release = MagicMock()
		gsmInstance.sendAT = MagicMock()
		gsmInstance.sendVoiceCall = MagicMock()
		gsmInstance.sendMessage = MagicMock(return_value = True)
		
		self.assertTrue(gsmInstance.send(message, 0303456, True))
		text_to_audio.assert_not_called()
		gsmInstance.sendVoiceCall.assert_not_called()
		gsmInstance.sendMessage.assert_called_once()
		
		
	def test_send_FILE(self):
		print "%s" % sys._getframe().f_code.co_name
		
		message = messageClass.Message("sender", "receiver", 10)
		setattr(message, "fileName", "/path/to/file")
		
		patch("ftpClass.Ftp.send", return_value = True).start()
		gsmInstance.sendMessage = MagicMock(return_value = True)
		
		self.assertTrue(gsmInstance.send(message, 0303456, True))
		ftpHost = JSON_CONFIG["FTP"]["FTP_SERVER"]
		gsmInstance.sendMessage.assert_called_with('El comunicador 2.0 ha subido el archivo file para usted, al servidor FTP ' + ftpHost + '.', 0303456)
	
	@patch("pickle.dumps")
	def test_send_INSTANCE(self, pickle_call):
		print "%s" % sys._getframe().f_code.co_name
		
		message = messageClass.Message("sender", "receiver", 10)
		
		gsmInstance.sendMessage = MagicMock(return_value = True)
		
		self.assertTrue(gsmInstance.send(message, 0303456, True))
		pickle_call.assert_called_once()
		
		
	def test_sendMessage_ANDROID(self):
		print "%s" % sys._getframe().f_code.co_name
		
		modemClass.Gsm.androidConnected = True
		patch("time.sleep").start()
		patch("pexpect.spawn").start()
		
		plainText = "line1\nline2"
		
		gsmInstance.sendADB = MagicMock(side_effect = ["1234","","","","","","","","","","","","",""])
		gsmInstance.sendPexpect = MagicMock(side_effect = ["","","", "a\n" + plainText])
		gsmInstance.successfulList = []
		
		self.assertTrue(gsmInstance.sendMessage(plainText, 0303456))
		self.assertEqual([True], gsmInstance.successfulList)
		
	def test_sendMessage_ANDROID_EXCEPT(self):
		print "%s" % sys._getframe().f_code.co_name
		
		modemClass.Gsm.androidConnected = True
		plainText = "line1\nline2"
		
		gsmInstance.sendADB = MagicMock(side_effect = Exception)
		gsmInstance.successfulList = []
		
		self.assertFalse(gsmInstance.sendMessage(plainText, 0303456))
		logger.write.assert_called_with('ERROR', '[GSM] Error al enviar el mensaje de texto a 100142.')
		
	def test_sendMessage_TELIT(self):
		print "%s" % sys._getframe().f_code.co_name
		
		modemClass.Gsm.androidConnected = False
		
		modemClass.Modem.active_call= PropertyMock(side_effect = [True, False])
		gsmInstance.telit_lock = MagicMock()
		gsmInstance.telit_lock.acquire = MagicMock()
		gsmInstance.telit_lock.wait = MagicMock()
		gsmInstance.sendAT = MagicMock(side_effect = [['','+CSCA:"0303456",7'], "", "", "", RuntimeError, ""])
		sms = messaging.sms.submit.SmsSubmit
		pdu = messaging.sms.pdu.Pdu
		pdu.length = 8
		pdu.pdu = 1043893298
		
		gsmInstance.getPDUs = MagicMock(return_value = [pdu, pdu])
		gsmInstance.SmsSubmitFncn = MagicMock()
		
		self.assertFalse(gsmInstance.sendMessage("plainText", 0303456))
		gsmInstance.telit_lock.wait.assert_called_once()
		gsmInstance.sendAT.assert_any_call('AT+CMGS=8', '>')
		
	@patch("threading.Thread")
	def test_sendVoiceCall(self, thread_call):
		print "%s" % sys._getframe().f_code.co_name
		
		patch("callClass.Call.thread").start()
		patch("callClass.Call.thread.start").start()
		patch("time.sleep", side_effect = Exception).start()
		gsmInstance.telit_lock = MagicMock()
		gsmInstance.telit_lock.acquire = MagicMock()
		gsmInstance.telit_lock.release = MagicMock()
		gsmInstance.sendAT = MagicMock(side_effect = ["", ['',',,0']])
		
		self.assertFalse(gsmInstance.sendVoiceCall("message", 0303456))
		
		thread_call.assert_called_once()
		gsmInstance.telit_lock.release.assert_called_once()
		
	@patch("threading.Thread")
	def test_answerVoiceCall(self, thread_call):
		print "%s" % sys._getframe().f_code.co_name
		
		patch("callClass.Call.thread").start()
		patch("callClass.Call.thread.start").start()
		gsmInstance.telit_lock = MagicMock()
		gsmInstance.telit_lock.acquire = MagicMock()
		gsmInstance.getTelephoneNumber = MagicMock(return_value = 3512560536)
		gsmInstance.sendAT = MagicMock()
		
		self.assertTrue(gsmInstance.answerVoiceCall())
		thread_call.assert_called_once()
		
	@patch("threading.Thread")
	def test_answerVoiceCall_NOT_ALLOWED(self, thread_call):
		print "%s" % sys._getframe().f_code.co_name
		
		gsmInstance.telit_lock = MagicMock()
		gsmInstance.telit_lock.acquire = MagicMock()
		gsmInstance.telit_lock.release = MagicMock()
		gsmInstance.getTelephoneNumber = MagicMock(return_value = 12345678)
		gsmInstance.sendAT = MagicMock()
		
		self.assertFalse(gsmInstance.answerVoiceCall())
		thread_call.assert_not_called()
		
	def test_hangUpVoiceCall(self):
		print "%s" % sys._getframe().f_code.co_name
		
		patch("callClass.Call.thread").start()
		patch("callClass.Call.thread.isAlive", return_value = True).start()
		join_call = patch("callClass.Call.thread.join").start()
		gsmInstance.telit_lock = MagicMock()
		gsmInstance.telit_lock.notifyAll = MagicMock()
		gsmInstance.telit_lock.release = MagicMock()
		gsmInstance.sendAT = MagicMock()
		gsmInstance.callerID = "0303456"
		
		self.assertTrue(gsmInstance.hangUpVoiceCall())
		
		self.assertEqual(None, gsmInstance.callerID)
		logger.write.assert_called_with('INFO', '[GSM] Conexion con el numero 0303456 finalizada.')
		join_call.assert_called_once()
		
	def test_removeSms(self):
		print "%s" % sys._getframe().f_code.co_name
		
		modemClass.Modem.active_call= PropertyMock(side_effect = [True, False])
		gsmInstance.telit_lock = MagicMock()
		gsmInstance.telit_lock.acquire = MagicMock()
		gsmInstance.telit_lock.wait = MagicMock()
		gsmInstance.getSmsIndex = MagicMock(return_value = 6)
		gsmInstance.sendAT = MagicMock()
		
		self.assertTrue(gsmInstance.removeSms("+CMGL"))
		
		gsmInstance.telit_lock.wait.assert_called_once()
		
		
	def test_getSmsIndex_CMGS(self):
		print "%s" % sys._getframe().f_code.co_name

		patch("serial.Serial.close").start()

		self.assertEqual(4, gsmInstance.getSmsIndex("+CMGS: 4"))
		
	def test_getSmsIndex_CMGL(self):
		print "%s" % sys._getframe().f_code.co_name
		
		patch("serial.Serial.close").start()

		self.assertEqual(6, gsmInstance.getSmsIndex("+CMGL: 6"))
		
	def test_getTelephoneNumber_549(self):
		print "%s" % sys._getframe().f_code.co_name
		
		self.assertEqual(12345, gsmInstance.getTelephoneNumber('+54912345'))
		
	def test_getTelephoneNumber_54(self):
		print "%s" % sys._getframe().f_code.co_name
		
		self.assertEqual(12345, gsmInstance.getTelephoneNumber('+5412345'))
		
	def test_sendADB_NOT_FOUND(self):
		print "%s" % sys._getframe().f_code.co_name
		
		patch("time.sleep").start()
		patch("subprocess.Popen.communicate", return_value = ["", 'error: device not found\n']).start()
		gsmInstance.androidConnected = True
		
		gsmInstance.sendADB("adb command")
		
		self.assertFalse(gsmInstance.androidConnected)
		logger.write.assert_called_with('WARNING','[GSM] El dispositivo Android se ha desconectado.')
		
	def test_sendADB_OTHER_ERRORS(self):
		print "%s" % sys._getframe().f_code.co_name
		
		error = 'some error'
		patch("time.sleep").start()
		patch("subprocess.Popen.communicate", return_value = ["", error]).start()
		gsmInstance.androidConnected = True
		
		gsmInstance.sendADB("adb command")
		
		self.assertFalse(gsmInstance.androidConnected)
		logger.write.assert_called_with('WARNING','[GSM] Ha fallado el dispositivo Android - %s' % error)
		
	def test_sendPexpect_0(self):
		print "%s" % sys._getframe().f_code.co_name
		
		child = pexpect.spawn("adb shell")
		child.sendline = MagicMock()
		child.expect_exact = MagicMock(return_value = 0)
		child.before = MagicMock()
		
		self.assertEqual(child.before, gsmInstance.sendPexpect(child, "cmd", "OK"))
		
	def test_sendPexpect_1(self):
		print "%s" % sys._getframe().f_code.co_name
		
		child = pexpect.spawn("adb shell")
		child.sendline = MagicMock()
		child.expect_exact = MagicMock(return_value = 1)
		
		with self.assertRaises(AdbError) as err:
			gsmInstance.sendPexpect(child, "cmd", "OK")
			
		logger.write.assert_called_with('WARNING', '[GSM] Timeout del shell de Android.')
		
	def test_sendPexpect_2(self):
		print "%s" % sys._getframe().f_code.co_name
		
		child = pexpect.spawn("adb shell")
		child.sendline = MagicMock()
		child.expect_exact = MagicMock(return_value = 2)
		
		with self.assertRaises(AdbError) as err:
			gsmInstance.sendPexpect(child, "cmd", "OK")
			
		logger.write.assert_called_with('WARNING', '[GSM] El shell de Android se ha cerrado inesperadamente.')
		
		
	def test_logcat_TRUE(self):
		print "%s" % sys._getframe().f_code.co_name
		
		patch("subprocess.Popen.communicate", return_value = ["12-02 03:04:05 1234 result: -1 \r", ""]).start()
		gsmInstance.logcat("Tue Nov 12 12:34:56","adb shell")
		self.assertTrue(gsmInstance.SmsReceiverResult)
		
	def test_logcat_FALSE(self):
		print "%s" % sys._getframe().f_code.co_name
		
		patch("subprocess.Popen.communicate", return_value = ["12-02 03:04:05 1234 result: 1 \r", ""]).start()
		gsmInstance.logcat("Tue Nov 12 12:34:56","adb shell")
		self.assertFalse(gsmInstance.SmsReceiverResult)
		
	def test_configPPP(self):
		print "%s" % sys._getframe().f_code.co_name
		
		serial.Serial.port = "/dev/ttyUSB0"
		gsmInstance.sendAT = MagicMock(side_effect = ["", ["AT+COPS?", ',, 722310 ']])
		file_patch = mock_open()
		file_patch.write = MagicMock()
		file_patch.readlines = MagicMock(return_value = ["","","",""])
		file_patch.close = MagicMock()
		
		self.assertTrue(gsmInstance.configPPP("mf626"))
		
if __name__ == '__main__':
	unittest.main()
