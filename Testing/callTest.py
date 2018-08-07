import unittest
from mock import MagicMock, PropertyMock, patch, mock_open, call
import mock
import os
import sys
from package import sys.path

import callClass
import networkClass
import controllerClass
import modemClass
from modemClass import ATCommandError, AtNoCarrier, AtTimeout

from gtts import gTTS
from pydub import AudioSegment
from DTMFdetector import DTMFdetector
from tempfile import NamedTemporaryFile
import json
import tempfile
import traceback
import time
import threading
import Queue
import regex
import logger
import struct
import subprocess
import os
import speech_recognition
import serial
import pydub

JSON_FILE = 'config.json'
JSON_CONFIG = json.load(open(JSON_FILE))

callInstance = callClass.Call
callInstance.gsmInstance = modemClass.Gsm
callInstance.gsmInstance.wifiInstance = networkClass.Network
callInstance.gsmInstance.ethernetInstance = networkClass.Network
callInstance.modemInstance = serial.Serial
callInstance.controllerInstance = controllerClass.Controller

class CallTest(unittest.TestCase):
	
	def setUp(self):
		logger.write = MagicMock()
		time.sleep = MagicMock()
		global callInstance
		callInstance = callClass.Call()
		
	def tearDown(self):
		global callInstance
		del callInstance
		patch.stopall()
		del logger.write
		
	@patch("os.remove")
	@patch("serial.Serial.reset_input_buffer")
	@patch("serial.Serial.close")
	@patch("Queue.Queue.put")
	def test_voiceCall_MENU_1(self, put_call, close_call, buffer_call, remove_call):
		print "%s" % sys._getframe().f_code.co_name
		
		patch("callClass.Call.dtmfNumber", new_callable = PropertyMock, side_effect = ['1', '0']).start()
		patch("Queue.Queue.get").start()
		patch("Queue.Queue.qsize", side_effect = [1,1,0]).start()
		patch("modemClass.Modem.sendAT").start()
		patch("time.time", side_effect = [1, 2, 7, 1, 7]).start()
		patch("serial.Serial.read", return_value = "N").start()
		patch("serial.Serial.readline", return_value = "O CARRIER").start()
		patch("serial.Serial.open").start()
		patch("subprocess.Popen").start()
		
		modemClass.Gsm.receptionQueue = Queue.Queue
		modemClass.Gsm.callerID = "client02"
		callInstance.sendAudioFile = MagicMock()
		callInstance.dtmfThread = MagicMock()
		callInstance.dtmfThread.is_alive = MagicMock(return_value = True)
		callInstance.dtmfThread.join = MagicMock()
		callInstance.audioMsgQueue.qsize = MagicMock(side_effect = [1, 1, 0])
		callInstance.sendAudioFile = MagicMock()
		callInstance.audioMsgQueue.get = MagicMock(return_value = 'fileName')
		callInstance.closeCall = MagicMock()
		callInstance.audio_to_text = MagicMock(return_value = "audio2text")

		file_patch = mock_open()
		patch("__builtin__.open", file_patch).start()
		file_op = file_patch()
		file_op.seek = MagicMock()
		file_op.readline = MagicMock(side_effect = [None, "pppd[123]: local  IP address", "pppd[123]: Exit"])
		
		self.assertTrue(callInstance.voiceCall())
		self.assertEqual(callInstance.dtmfThread.join.call_count, 2)
		remove_call.assert_called_once()
		buffer_call.assert_called_once()
		close_call.assert_called_once()
		put_call.assert_called_once()
		callInstance.audio_to_text.assert_called_once()
		
	@patch("os.remove")
	@patch("serial.Serial.reset_input_buffer")
	@patch("serial.Serial.close")
	@patch("Queue.Queue.put")
	def test_voiceCall_MENU_2_OPCION_1(self, put_call, close_call, buffer_call, remove_call):
		print "%s" % sys._getframe().f_code.co_name
		
		flujoGrabacion = ['X'] * 8000
		
		patch("callClass.Call.dtmfNumber", new_callable = PropertyMock, side_effect = ['2', '1', '0']).start()
		patch("callClass.Call.tempAudioMsg").start()
		patch("callClass.Call.tempAudioMsg.name", side_effect = ['fileName']).start()
		patch("callClass.Call.flujoGrabacion", new_callable = PropertyMock, side_effect = [flujoGrabacion, flujoGrabacion]).start()
		patch("Queue.Queue.get").start()
		patch("Queue.Queue.qsize", side_effect = [1,1,0]).start()
		patch("modemClass.Modem.sendAT").start()
		patch("time.time", side_effect = [1, 2, 7, 1, 1, 7, 1, 7, 1, 7]).start()
		patch("serial.Serial.read", return_value = "N").start()
		patch("serial.Serial.readline", return_value = "O CARRIER").start()
		patch("serial.Serial.open").start()
		patch("serial.Serial.write").start()
		patch("subprocess.Popen").start()
		
		modemClass.Gsm.receptionQueue = Queue.Queue
		modemClass.Gsm.callerID = "client02"
		callInstance.sendAudioFile = MagicMock()
		callInstance.dtmfThread = MagicMock()
		callInstance.dtmfThread.is_alive = MagicMock(return_value = True)
		callInstance.dtmfThread.join = MagicMock()
		callInstance.audioMsgQueue.qsize = MagicMock(side_effect = [1, 1, 0])
		callInstance.audioMsgQueue.put = MagicMock()
		callInstance.sendAudioFile = MagicMock()
		callInstance.audioMsgQueue.get = MagicMock(return_value = 'fileName')
		callInstance.closeCall = MagicMock()
		callInstance.audio_to_text = MagicMock(return_value = "audio2text")
		callInstance.recordAudio = MagicMock()
		callInstance.checkHangUp = MagicMock()
		callInstance.saveAudioMessage = MagicMock()

		file_patch = mock_open()
		patch("__builtin__.open", file_patch).start()
		file_op = file_patch()
		file_op.seek = MagicMock()
		file_op.readline = MagicMock(side_effect = [None, "pppd[123]: local  IP address", "pppd[123]: Exit"])
		
		self.assertTrue(callInstance.voiceCall())
		self.assertEqual(callInstance.dtmfThread.join.call_count, 3)
		remove_call.assert_called_once()
		buffer_call.assert_called_once()
		close_call.assert_called_once()
		put_call.assert_called_once()
		callInstance.recordAudio.assert_called_once()
		callInstance.audio_to_text.assert_called_once()
		callInstance.saveAudioMessage.assert_called_once()
		
	@patch("os.remove")
	@patch("serial.Serial.reset_input_buffer")
	@patch("serial.Serial.close")
	@patch("Queue.Queue.put")
	def test_voiceCall_MENU_2_OPCION_2_NO_RECONOCIDO(self, put_call, close_call, buffer_call, remove_call):
		print "%s" % sys._getframe().f_code.co_name
		
		flujoGrabacion = ['X'] * 8000
		
		patch("callClass.Call.dtmfNumber", new_callable = PropertyMock, side_effect = ['2', '2', '0']).start()
		patch("callClass.Call.tempAudioMsg").start()
		patch("callClass.Call.tempAudioMsg.name", side_effect = ['fileName']).start()
		patch("callClass.Call.flujoGrabacion", new_callable = PropertyMock, return_value = flujoGrabacion).start()
		patch("Queue.Queue.get").start()
		patch("Queue.Queue.qsize", side_effect = [1,1,0]).start()
		patch("modemClass.Modem.sendAT").start()
		patch("time.time", side_effect = [1, 2, 7, 1, 1, 7, 1, 7, 1, 7]).start()
		patch("serial.Serial.read", return_value = "N").start()
		patch("serial.Serial.readline", return_value = "O CARRIER").start()
		patch("serial.Serial.open").start()
		patch("serial.Serial.write").start()
		patch("subprocess.Popen").start()
		patch("networkClass.Network.online", new_callable = PropertyMock, return_value = True).start()
		
		modemClass.Gsm.receptionQueue = Queue.Queue
		modemClass.Gsm.callerID = "client02"
		callInstance.sendAudioFile = MagicMock()
		callInstance.dtmfThread = MagicMock()
		callInstance.dtmfThread.is_alive = MagicMock(return_value = True)
		callInstance.dtmfThread.join = MagicMock()
		callInstance.audioMsgQueue.qsize = MagicMock(side_effect = [1, 1, 0])
		callInstance.audioMsgQueue.put = MagicMock()
		callInstance.sendAudioFile = MagicMock()
		callInstance.audioMsgQueue.get = MagicMock(return_value = 'fileName')
		callInstance.closeCall = MagicMock()
		callInstance.audio_to_text = MagicMock(side_effect = ['AUDIO_NO_RECONOCIDO',"audio2text"])
		callInstance.recordAudio = MagicMock()
		callInstance.checkHangUp = MagicMock()

		file_patch = mock_open()
		patch("__builtin__.open", file_patch).start()
		file_op = file_patch()
		file_op.seek = MagicMock()
		file_op.readline = MagicMock(side_effect = [None, "pppd[123]: local  IP address", "pppd[123]: Exit"])
		
		self.assertTrue(callInstance.voiceCall())
		self.assertEqual(callInstance.dtmfThread.join.call_count, 3)
		self.assertEqual(callInstance.audio_to_text.call_count, 2)
		remove_call.assert_called_once()
		buffer_call.assert_called_once()
		close_call.assert_called_once()
		put_call.assert_called_once()
		callInstance.recordAudio.assert_called_once()
		callInstance.sendAudioFile.assert_any_call('Audio/2_audio_no_reconocido.raw')
		
		
	@patch("os.remove")
	@patch("serial.Serial.reset_input_buffer")
	@patch("serial.Serial.close")
	@patch("Queue.Queue.put")
	def test_voiceCall_MENU_2_OPCION_2_SIN_CONEXION(self, put_call, close_call, buffer_call, remove_call):
		print "%s" % sys._getframe().f_code.co_name
		
		flujoGrabacion = ['X'] * 8000
		
		patch("callClass.Call.dtmfNumber", new_callable = PropertyMock, side_effect = ['2', '2', '0']).start()
		patch("callClass.Call.tempAudioMsg").start()
		patch("callClass.Call.tempAudioMsg.name", side_effect = ['fileName']).start()
		patch("callClass.Call.flujoGrabacion", new_callable = PropertyMock, return_value = flujoGrabacion).start()
		patch("Queue.Queue.get").start()
		patch("Queue.Queue.qsize", side_effect = [1,1,0]).start()
		patch("modemClass.Modem.sendAT").start()
		patch("time.time", side_effect = [1, 2, 7, 1, 1, 7, 1, 7, 1, 7]).start()
		patch("serial.Serial.read", return_value = "N").start()
		patch("serial.Serial.readline", return_value = "O CARRIER").start()
		patch("serial.Serial.open").start()
		patch("serial.Serial.write").start()
		patch("subprocess.Popen").start()
		patch("networkClass.Network.online", new_callable = PropertyMock, return_value = True).start()
		
		modemClass.Gsm.receptionQueue = Queue.Queue
		modemClass.Gsm.callerID = "client02"
		callInstance.sendAudioFile = MagicMock()
		callInstance.dtmfThread = MagicMock()
		callInstance.dtmfThread.is_alive = MagicMock(return_value = True)
		callInstance.dtmfThread.join = MagicMock()
		callInstance.audioMsgQueue.qsize = MagicMock(side_effect = [1, 1, 0])
		callInstance.audioMsgQueue.put = MagicMock()
		callInstance.sendAudioFile = MagicMock()
		callInstance.audioMsgQueue.get = MagicMock(return_value = 'fileName')
		callInstance.closeCall = MagicMock()
		callInstance.audio_to_text = MagicMock(side_effect = ['SIN_CONEXION',"audio2text"])
		callInstance.recordAudio = MagicMock()
		callInstance.checkHangUp = MagicMock()

		file_patch = mock_open()
		patch("__builtin__.open", file_patch).start()
		file_op = file_patch()
		file_op.seek = MagicMock()
		file_op.readline = MagicMock(side_effect = [None, "pppd[123]: local  IP address", "pppd[123]: Exit"])
		
		self.assertTrue(callInstance.voiceCall())
		self.assertEqual(callInstance.dtmfThread.join.call_count, 3)
		self.assertEqual(callInstance.audio_to_text.call_count, 2)
		self.assertEqual(put_call.call_count, 2)
		remove_call.assert_called_once()
		buffer_call.assert_called_once()
		close_call.assert_called_once()
		callInstance.recordAudio.assert_called_once()
		callInstance.sendAudioFile.assert_any_call('Audio/2_guardado_posterior.raw')
		
	@patch("os.remove")
	@patch("serial.Serial.reset_input_buffer")
	@patch("serial.Serial.close")
	def test_voiceCall_MENU_2_OPCION_3(self, close_call, buffer_call, remove_call):
		print "%s" % sys._getframe().f_code.co_name
		
		flujoGrabacion = ['X'] * 8000
		
		patch("callClass.Call.dtmfNumber", new_callable = PropertyMock, side_effect = ['2', '3', '0', "0"]).start()
		patch("callClass.Call.tempAudioMsg").start()
		patch("callClass.Call.tempAudioMsg.name", side_effect = ['fileName']).start()
		patch("callClass.Call.flujoGrabacion", new_callable = PropertyMock, return_value = flujoGrabacion).start()
		patch("Queue.Queue.get").start()
		patch("Queue.Queue.qsize", side_effect = [1,1,0]).start()
		patch("modemClass.Modem.sendAT").start()
		patch("time.time", side_effect = [1, 2, 7, 1, 1, 7, 1, 7, 1, 0, 7, 1, 7, 1, 7]).start()
		patch("serial.Serial.read", return_value = "N").start()
		patch("serial.Serial.readline", return_value = "O CARRIER").start()
		patch("serial.Serial.open").start()
		patch("serial.Serial.write").start()
		patch("subprocess.Popen").start()
		patch("networkClass.Network.online", new_callable = PropertyMock, return_value = True).start()
		
		modemClass.Gsm.receptionQueue = Queue.Queue
		modemClass.Gsm.callerID = "client02"
		callInstance.sendAudioFile = MagicMock()
		callInstance.dtmfThread = MagicMock()
		callInstance.dtmfThread.is_alive = MagicMock(return_value = True)
		callInstance.dtmfThread.join = MagicMock()
		callInstance.audioMsgQueue.qsize = MagicMock(side_effect = [1, 1, 0])
		callInstance.audioMsgQueue.put = MagicMock()
		callInstance.sendAudioFile = MagicMock()
		callInstance.audioMsgQueue.get = MagicMock(return_value = 'fileName')
		callInstance.closeCall = MagicMock()
		callInstance.audio_to_text = MagicMock(side_effect = ['SIN_CONEXION',"audio2text"])
		callInstance.recordAudio = MagicMock()
		callInstance.checkHangUp = MagicMock()

		file_patch = mock_open()
		patch("__builtin__.open", file_patch).start()
		file_op = file_patch()
		file_op.seek = MagicMock()
		file_op.readline = MagicMock(side_effect = [None, "pppd[123]: local  IP address", "pppd[123]: Exit"])
		
		self.assertTrue(callInstance.voiceCall())
		self.assertEqual(callInstance.dtmfThread.join.call_count, 4)
		self.assertEqual(callInstance.audio_to_text.call_count, 1)
		self.assertEqual(callInstance.recordAudio.call_count, 2)
		remove_call.assert_called_once()
		buffer_call.assert_called_once()
		close_call.assert_called_once()
		callInstance.sendAudioFile.assert_any_call('Audio/2_el_mensaje_es.raw')
		
	@patch("serial.Serial.reset_input_buffer")
	@patch("serial.Serial.close")
	@patch("Queue.Queue.put")
	def test_voiceCall_MENU_X(self, put_call, close_call, buffer_call):
		print "%s" % sys._getframe().f_code.co_name
		
		patch("callClass.Call.dtmfNumber", new_callable = PropertyMock, side_effect = ['4', '0']).start()
		patch("Queue.Queue.get").start()
		patch("Queue.Queue.qsize", side_effect = [1,1,0]).start()
		patch("modemClass.Modem.sendAT").start()
		patch("time.time", side_effect = [1, 2, 7, 1, 7]).start()
		patch("serial.Serial.read", return_value = "N").start()
		patch("serial.Serial.readline", return_value = "O CARRIER").start()
		patch("serial.Serial.open").start()
		patch("subprocess.Popen").start()
		
		modemClass.Gsm.receptionQueue = Queue.Queue
		modemClass.Gsm.callerID = "client02"
		callInstance.sendAudioFile = MagicMock()
		callInstance.dtmfThread = MagicMock()
		callInstance.dtmfThread.is_alive = MagicMock(return_value = True)
		callInstance.dtmfThread.join = MagicMock()
		callInstance.audioMsgQueue.qsize = MagicMock(side_effect = [1, 1, 0])
		callInstance.sendAudioFile = MagicMock()
		callInstance.audioMsgQueue.get = MagicMock(return_value = 'fileName')
		callInstance.closeCall = MagicMock()
		callInstance.audio_to_text = MagicMock(return_value = "audio2text")

		file_patch = mock_open()
		patch("__builtin__.open", file_patch).start()
		file_op = file_patch()
		file_op.seek = MagicMock()
		file_op.readline = MagicMock(side_effect = [None, "pppd[123]: local  IP address", "pppd[123]: Exit"])
		
		self.assertTrue(callInstance.voiceCall())
		self.assertEqual(callInstance.dtmfThread.join.call_count, 2)
		buffer_call.assert_called_once()
		close_call.assert_called_once()
		callInstance.sendAudioFile.assert_any_call('Audio/no_disponible.raw')
		
	def test_msgCall(self):
		print "%s" % sys._getframe().f_code.co_name
		
		patch("modemClass.Modem.sendAT").start()
		patch("os.remove").start()
		patch("time.sleep").start()
		
		callInstance.sendAudioFile = MagicMock()
		callInstance.voiceCall = MagicMock()
		
		self.assertTrue(callInstance.msgCall("fileName"))
		callInstance.voiceCall.assert_called_with(False)
		
	def test_closeCall(self):
		print "%s" % sys._getframe().f_code.co_name
		
		modemClass.Gsm.callerID = "client02"
		patch('modemClass.Gsm.telit_lock').start()
		patch('modemClass.Gsm.telit_lock.notifyAll').start()
		notifyAll = patch('modemClass.Gsm.telit_lock.release').start()
		
		callInstance.closeCall()
		
		self.assertEqual(None, modemClass.Gsm.callerID)
		notifyAll.assert_called_once()
		
	def test_dtmfDecoder(self):
		print "%s" % sys._getframe().f_code.co_name
		
		raw = ['1'] * 400
		flujoGrabacion = ['X'] * 8000
		
		goertzel = patch("DTMFdetector.DTMFdetector.goertzel").start()
		patch("DTMFdetector.DTMFdetector.clean_up_processing").start()
		patch("DTMFdetector.DTMFdetector.charStr", new_callable = PropertyMock, return_value = '2').start()
		patch("time.time").start()
		patch("callClass.Call.decodeActive", new_callable = PropertyMock, side_effect = [True, True, False]).start()
		patch("serial.Serial.read", side_effect = [raw]).start()
		patch("callClass.Call.flujoGrabacion", new_callable = PropertyMock, return_value = flujoGrabacion).start()
		callInstance.port_lock = MagicMock()
		callInstance.port_lock.acquire = MagicMock()
		callInstance.port_lock.release = MagicMock()
		
		callInstance.dtmfDecoder()
		
		callInstance.port_lock.acquire.assert_called_once()
		self.assertEqual(goertzel.call_count, 400)
		self.assertEqual(callInstance.dtmfNumber, '2')
		
	def test_hangUpVoiceCall(self):
		print "%s" % sys._getframe().f_code.co_name
		
		modemClass.Gsm.callerID = "client02"
		patch("modemClass.Modem.sendAT").start()
		
		self.assertTrue(callInstance.hangUpVoiceCall())
		self.assertEqual(None, modemClass.Gsm.callerID)
		
	def test_text2audio(self):
		print "%s" % sys._getframe().f_code.co_name

		name = "fileName"

		patch("gtts.gTTS.save").start()
		patch("pydub.AudioSegment.from_mp3").start()
		patch("pydub.AudioSegment.from_mp3.export").start()
		tempFile = patch("tempfile.NamedTemporaryFile")
		tempFile.name = PropertyMock(return_value = name)
		tempFile.seek = MagicMock()
		tempFile.start()
		
		callInstance.text_to_audio("text")
		
	def test_audio2text(self):
		print "%s" % sys._getframe().f_code.co_name
		
		source = ['1'] * 8000
		text = "example"
		recognizer = speech_recognition.Recognizer
		
		patch("speech_recognition.AudioData").start()
		patch("speech_recognition.AudioData.get_wav_data").start()
		patch("tempfile.NamedTemporaryFile").start()
		patch("tempfile.NamedTemporaryFile.write").start()
		patch("tempfile.NamedTemporaryFile.name", new_callable = PropertyMock, return_value = 'fileName').start()
		patch("speech_recognition.Recognizer", return_value = recognizer).start()
		patch("speech_recognition.AudioFile").start()
		recognizer.record = MagicMock()
		recognizer.recognize_google = MagicMock(return_value = text)
		
		self.assertEqual(text, callInstance.audio_to_text(source))
		
	def test_audio2text_AUDIO_NO_RECONOCIDO(self):
		print "%s" % sys._getframe().f_code.co_name
		
		source = ['1'] * 8000
		text = "example"
		recognizer = speech_recognition.Recognizer
		
		patch("speech_recognition.AudioData").start()
		patch("speech_recognition.AudioData.get_wav_data").start()
		patch("tempfile.NamedTemporaryFile").start()
		patch("tempfile.NamedTemporaryFile.write").start()
		patch("tempfile.NamedTemporaryFile.name", new_callable = PropertyMock, return_value = 'fileName').start()
		patch("speech_recognition.Recognizer", return_value = recognizer).start()
		patch("speech_recognition.AudioFile").start()
		recognizer.record = MagicMock()
		recognizer.recognize_google = MagicMock(side_effect = speech_recognition.UnknownValueError)
		
		self.assertEqual("AUDIO_NO_RECONOCIDO",callInstance.audio_to_text(source))
		
	def test_audio2text_SIN_CONEXION(self):
		print "%s" % sys._getframe().f_code.co_name
		
		source = ['1'] * 8000
		text = "example"
		recognizer = speech_recognition.Recognizer
		
		patch("speech_recognition.AudioData").start()
		patch("speech_recognition.AudioData.get_wav_data").start()
		patch("tempfile.NamedTemporaryFile").start()
		patch("tempfile.NamedTemporaryFile.write").start()
		patch("tempfile.NamedTemporaryFile.name", new_callable = PropertyMock, return_value = 'fileName').start()
		patch("speech_recognition.Recognizer", return_value = recognizer).start()
		patch("speech_recognition.AudioFile").start()
		recognizer.record = MagicMock()
		recognizer.recognize_google = MagicMock(side_effect = speech_recognition.RequestError)
		
		self.assertEqual("SIN_CONEXION",callInstance.audio_to_text(source))
		
		
	@patch("threading.Thread")
	@patch("time.sleep")
	def test_sendAudioFile(self, sleep_call, thread_call):
		print "%s" % sys._getframe().f_code.co_name

		source = "1" * 4000
		name = "fileName"
		audioSegment = pydub.AudioSegment
		audioSegment.duration_seconds = 1.0
		
		callClass.Call.dtmfAudio = name
		callClass.Call.dtmfNumber = None
		file_patch = mock_open(read_data = source)
		patch("__builtin__.open", file_patch).start()
		file_op = file_patch()
		file_op.close = MagicMock()		
		patch("pydub.AudioSegment.from_file", return_value = audioSegment).start()
		patch("callClass.Call.dtmfThread").start()
		patch("callClass.Call.dtmfThread.start").start()
		patch("time.time", new_callable = PropertyMock, side_effect = [1, 1, 1, 1, 1, 5]).start()
		patch("serial.Serial.write").start()
		callInstance.checkHangUp = MagicMock()
		callInstance.dtmfDecoder = MagicMock()
	
		self.assertTrue(callInstance.sendAudioFile(name))
		thread_call.assert_called_once()
		sleep_call.assert_called_once()
		callInstance.checkHangUp.assert_called_once()
		
	def test_checkHangUp(self):
		print "%s" % sys._getframe().f_code.co_name
		
		patch("serial.Serial.reset_input_buffer").start()
		patch("serial.Serial.in_waiting", new_callable = PropertyMock, side_effect = [1,1,0]).start()
		patch("serial.Serial.read", return_value = "N").start()
		patch("serial.Serial.readline", side_effect = ["O CARRIER", "", "ERROR"]).start()
		callInstance.port_lock = MagicMock()
		callInstance.port_lock.acquire = MagicMock()
		callInstance.port_lock.release = MagicMock()
		
		with self.assertRaises(ATCommandError) as err:
			callInstance.checkHangUp()
		callInstance.port_lock.release.assert_called_once()
		
	def test_recordAudio(self):
		print "%s" % sys._getframe().f_code.co_name
		
		callInstance.decodeActive = True
		patch("threading.Thread").start()
		patch("callClass.Call.dtmfThread").start()
		patch("callClass.Call.dtmfThread.start").start()
		patch("callClass.Call.dtmfThread.is_alive", return_value = True).start()
		patch("callClass.Call.dtmfThread.join").start()
		patch("serial.Serial.reset_input_buffer").start()
		patch("time.time", side_effect = [1, 1, 8000]).start()
		patch("callClass.Call.recordTime", new_callable = PropertyMock, return_value = 1).start()
		
		callInstance.recordAudio()
		
		self.assertFalse(callInstance.decodeActive)
		
	def test_saveAudioMessage(self):
		print "%s" % sys._getframe().f_code.co_name
		
		result = "'Audio/Mensajes/client02.-audio.-20121221.-142356"
		flujoGrabacion = ['X'] * 8000
		
		modemClass.Gsm.callerID = "client02"
		patch("callClass.Call.flujoGrabacion", new_callable = PropertyMock, return_value = flujoGrabacion).start()
		time.localtime = MagicMock(wraps = time.localtime)
		file_patch = mock_open()
		patch("__builtin__.open", file_patch).start()
		file_op = file_patch()
		file_op.write = MagicMock()	
		file_op.close = MagicMock()
		
		callInstance.saveAudioMessage()
		
		time.localtime.assert_called_once()
		
	@patch("time.sleep")
	def test_availableMedia(self, sleep_call):
		print "%s" % sys._getframe().f_code.co_name
		
		send_call = patch("callClass.Call.sendAudioFile", return_value = True).start()
		callClass.Call.gprsIsActive = True
		controllerClass.Controller.availableWifi = True
		controllerClass.Controller.availableEthernet = True
		controllerClass.Controller.availableBluetooth = True
		controllerClass.Controller.availableEmail = True
		controllerClass.Controller.availableFtp = True
		
		self.assertTrue(callInstance.availableMedia())
		self.assertEqual(send_call.call_count, 7)
		self.assertEqual(sleep_call.call_count, 7)
		
	@patch("time.sleep")
	def test_availableMedia_FIRST_FAIL(self, sleep_call):
		print "%s" % sys._getframe().f_code.co_name
		
		send_call = patch("callClass.Call.sendAudioFile", return_value = False).start()
		
		self.assertFalse(callInstance.availableMedia())
		send_call.assert_called_once()
		sleep_call.assert_not_called()
		
	@patch("time.sleep")
	def test_availableMedia_GPRS_FAIL(self, sleep_call):
		print "%s" % sys._getframe().f_code.co_name
		
		send_call = patch("callClass.Call.sendAudioFile", side_effect = [True, False]).start()
		callClass.Call.gprsIsActive = True
		
		self.assertFalse(callInstance.availableMedia())
		self.assertEqual(send_call.call_count, 2)
		sleep_call.assert_called_once()
		
	@patch("time.sleep")
	def test_availableMedia_WIFI_FAIL(self, sleep_call):
		print "%s" % sys._getframe().f_code.co_name
		
		send_call = patch("callClass.Call.sendAudioFile", side_effect = [True, True, False]).start()
		callClass.Call.gprsIsActive = True
		controllerClass.Controller.availableWifi = True
		
		self.assertFalse(callInstance.availableMedia())
		self.assertEqual(send_call.call_count, 3)
		self.assertEqual(sleep_call.call_count, 2)
		
	@patch("time.sleep")
	def test_availableMedia_ETHERNET_FAIL(self, sleep_call):
		print "%s" % sys._getframe().f_code.co_name
		
		send_call = patch("callClass.Call.sendAudioFile", side_effect = [True, True, True,False]).start()
		callClass.Call.gprsIsActive = True
		controllerClass.Controller.availableWifi = True
		controllerClass.Controller.availableEthernet = True
		
		self.assertFalse(callInstance.availableMedia())
		self.assertEqual(send_call.call_count, 4)
		self.assertEqual(sleep_call.call_count, 3)
		
	@patch("time.sleep")
	def test_availableMedia_BLUETOOTH_FAIL(self, sleep_call):
		print "%s" % sys._getframe().f_code.co_name
		
		send_call = patch("callClass.Call.sendAudioFile", side_effect = [True, True, True, True, False]).start()
		callClass.Call.gprsIsActive = True
		controllerClass.Controller.availableWifi = True
		controllerClass.Controller.availableEthernet = True
		controllerClass.Controller.availableBluetooth = True
		
		self.assertFalse(callInstance.availableMedia())
		self.assertEqual(send_call.call_count, 5)
		self.assertEqual(sleep_call.call_count, 4)
		
	@patch("time.sleep")
	def test_availableMedia_EMAIL_FAIL(self, sleep_call):
		print "%s" % sys._getframe().f_code.co_name
		
		send_call = patch("callClass.Call.sendAudioFile", side_effect = [True, True, True, True, True, False]).start()
		callClass.Call.gprsIsActive = True
		controllerClass.Controller.availableWifi = True
		controllerClass.Controller.availableEthernet = True
		controllerClass.Controller.availableBluetooth = True
		controllerClass.Controller.availableEmail = True
		
		self.assertFalse(callInstance.availableMedia())
		self.assertEqual(send_call.call_count, 6)
		self.assertEqual(sleep_call.call_count, 5)
		
	@patch("time.sleep")
	def test_availableMedia_FTP_FAIL(self, sleep_call):
		print "%s" % sys._getframe().f_code.co_name
		
		send_call = patch("callClass.Call.sendAudioFile", side_effect = [True, True, True, True, True, True, False]).start()
		callClass.Call.gprsIsActive = True
		controllerClass.Controller.availableWifi = True
		controllerClass.Controller.availableEthernet = True
		controllerClass.Controller.availableBluetooth = True
		controllerClass.Controller.availableEmail = True
		controllerClass.Controller.availableFtp = True
		
		self.assertFalse(callInstance.availableMedia())
		self.assertEqual(send_call.call_count, 7)
		self.assertEqual(sleep_call.call_count, 6)
		

if __name__ == '__main__':
	unittest.main()
