from gtts import gTTS
from pydub import AudioSegment
from DTMFdetector import DTMFdetector
from modemClass import NoCarrier, ATCommandError
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

JSON_FILE = 'config.json'
JSON_CONFIG = json.load(open(JSON_FILE))

class CallEnded(Exception): pass

class Call():
	
	modemInstance = None
	gsmInstance = None
	controllerInstance = None
	telephoneNumber = None
	audioMsgQueue = None
	language = None
	thread = None
	isActive = False
	telit_lock = None
	dtmfThread = threading.Thread()
	port_lock = threading.Lock()
	dtmfNumber = None
	decodeActive = False
	dtmfAudio = ['Audio/menu.raw', 'Audio/2_opciones_guardado.raw']
	flujoGrabacion = None
	recordTime = None
	tempAudioMsg = None
	
	def __init__(self):
		RECEPTION_QSIZE = JSON_CONFIG["COMMUNICATOR"]["RECEPTION_QSIZE"]
		self.audioMsgQueue = Queue.Queue(RECEPTION_QSIZE)
		self.recordTime = JSON_CONFIG["AUDIO"]["RECORD_SECS"]
		self.language = JSON_CONFIG["AUDIO"]["LANGUAGE"]
		if self.language not in gTTS.LANGUAGES:
			logger.write('WARNING', '[AUDIO] El idioma no esta soportado. Revise el archivo de configuracion')
		self.audioMsgQueue.put("Audio/Mensajes/3517502317.-audio.-20170926.-123525")
		self.audioMsgQueue.put("Audio/Mensajes/3517502317.-audio.-20170926.-123559")
		self.audioMsgQueue.put("Audio/Mensajes/3517502317.-audio.-20170926.-123629")
		
	def voiceCall(self):
		try:
			isActive = True
			self.gsmInstance.sendAT('AT#SPCM=3,1','CONNECT', 5)
			self.sendAudioFile('Audio/bienvenida.raw')
			time.sleep(0.5)
			audio = 'Audio/menu.raw'
			while True:
				self.sendAudioFile(audio)
				#~ self.dtmfThread = threading.Thread(target=self.dtmfDecoder)
				#~ self.dtmfThread.start()
				start = time.time()
				while self.dtmfThread.is_alive() and time.time() < (start + 5):
					pass
				if self.dtmfThread.is_alive():
					self.decodeActive = False
					self.dtmfThread.join()
				numero = self.dtmfNumber
				self.dtmfNumber = None
				if numero is '1': 
					if audio == 'Audio/menu.raw': #Audios sin escuchar
						cantidad = self.audioMsgQueue.qsize()
						if self.audioMsgQueue.qsize() > 0:
							self.sendAudioFile('Audio/1_hay_mensajes.raw')
							self.sendAudioFile('Audio/tono.raw')
							while self.audioMsgQueue.qsize() > 0:
								fileName = self.audioMsgQueue.get()
								self.sendAudioFile(fileName)
								os.remove(fileName)
								self.sendAudioFile('Audio/tono.raw')
						else:
							self.sendAudioFile('Audio/1_no_hay_mensajes.raw')
							time.sleep(0.5)
					elif audio == 'Audio/2_opciones_guardado.raw': #Guardar mensaje de audio
						self.sendAudioFile('Audio/2_guardado_exito.raw')
						self.audioMsgQueue.put(self.tempAudioMsg.name)
						logger.write('INFO', '[GSM] Mensaje de voz de %s guardado.' % str(self.gsmInstance.callerID))
						self.tempAudioMsg = None
						audio = 'Audio/menu.raw'
				elif numero is '2': #Grabar mensaje de audio
					if self.tempAudioMsg is not None:
						os.remove(self.tempAudioMsg.name)
						self.tempAudioMsg = None
					self.sendAudioFile('Audio/2_grabar_tono.raw')
					self.sendAudioFile('Audio/tono.raw')
					self.recordAudio()
					self.checkHangUp()
					self.saveAudioMessage()
					self.sendAudioFile('Audio/2_el_mensaje_es.raw')
					self.sendAudioFile(self.tempAudioMsg.name)
					audio = 'Audio/2_opciones_guardado.raw'				
				elif numero is '3': #Medios disponibles
					if audio == 'Audio/menu.raw':
						self.availableMedia()
						time.sleep(1)
					else:
						self.sendAudioFile('no_disponible.raw')
						time.sleep(1)
				elif numero is '0': #Salir
					if audio == 'Audio/menu.raw':
						time.sleep(0.5)
						self.sendAudioFile('Audio/salir.raw', False)
						self.modemInstance.reset_input_buffer()
						self.modemInstance.dtr = 0
						time.sleep(0.1)
						while self.modemInstance.in_waiting is not 0:
							if self.modemInstance.read(1) == 'N' and self.modemInstance.readline().startswith('O CARRIER'):
								break
						self.gsmInstance.sendAT('ATH')
						self.modemInstance.dtr = 1
						raise CallEnded
					else:
						audio = 'Audio/menu.raw'
				elif numero is not None:
					self.sendAudioFile('Audio/no_disponible.raw')
				else:
					self.checkHangUp()
		except CallEnded:					
			if self.gsmInstance.callerID is not None:
				logger.write('INFO', '[GSM] Llamada con el numero %s finalizada.' % self.gsmInstance.callerID)
				self.gsmInstance.callerID = None
			self.gsmInstance.telit_lock.notifyAll()
			self.gsmInstance.telit_lock.release()
			self.gsmInstance.active_call = False
			return False
				
	#~ def dtmfDecoder(self):
		#~ self.gsmInstance.sendAT('AT#DTMF=1')
		#~ start = time.time()
		#~ try:
			#~ while True:
				#~ if self.modemInstance.in_waiting is not 0:
					#~ bytesToRead = self.modemInstance.in_waiting
					#~ receptionList = self.modemInstance.read(bytesToRead).split('\r\n')
					#~ print receptionList #DBG
					#~ for item in receptionList:
						#~ if item.startswith('#DTMFEV'):
							#~ n = regex.findall('[*#0-9]', item[1:])[0]
							#~ return n
						#~ elif item.startswith(('NO CARRIER', 'ERROR', '+CME ERROR', '+CMS ERROR')):
							#~ if self.callerID is not None:
								#~ logger.write('INFO', '[GSM] Conexion con el numero %s finalizada.' % self.callerID)
								#~ self.callerID =- None
								#~ raise CallEnded
				#~ else:
					#~ if (start + 10) > time.time():
						#~ time.sleep(1)
					#~ else:
						#~ return None
		#~ finally:
			#~ self.gsmInstance.sendAT('AT#DTMF=0')
			
	def dtmfDecoder(self, grabar = False):
		dtmf = DTMFdetector()
		self.flujoGrabacion = ''
		self.modemInstance.reset_input_buffer()
		self.decodeActive = True
		while self.decodeActive:
			self.port_lock.acquire()
			raw = self.modemInstance.read(800)
			self.port_lock.release()
			count = 0
			while count < 800: 
				(sample,) = struct.unpack("b", raw[count])
				dtmf.goertzel(sample)
				count += 1
			dtmf.clean_up_processing()
			if dtmf.charStr != '':
				print dtmf.charStr
				if grabar:
					if dtmf.charStr == "#":
						break
					else:
						dtmf.chartStr = ''
				else:
					self.dtmfNumber = dtmf.charStr
					break
			elif grabar:
				self.flujoGrabacion += raw

	def hangUpVoiceCall(self):
			try:
					self.gsmInstance.sendAT('ATH') # Cuelga la llamada en curso
					if self.gsmInstance.callerID is not None:
							logger.write('INFO', '[GSM] Conexion con el numero %s finalizada.' % self.gsmInstance.callerID)
							self.gsmInstance.callerID = None
					return True
			except:
					return False
	
	def text_to_audio(self, text):
		try:
			tts = gTTS(text= text, lang= self.language)
			f = tempfile.NamedTemporaryFile()
			tts.write_to_fp(f)
			tts.save("bienvenida.mp3")
			audio = AudioSegment.from_mp3(f.name)
			f.close()
			g = tempfile.NamedTemporaryFile()
			audio.export(g.name, format="s8", codec = "pcm_s8", bitrate="64k", parameters=["-ar","8000"])
			g.seek(0)
			return g
		except:
			print traceback.format_exc()
			
	def sendAudioFile(self, fileName, hangUp = True):
		try:
			audioFile = open(fileName, 'rb')
			audioDuration = AudioSegment.from_file(fileName, format="raw", frame_rate=8000, channels=1, sample_width=1).duration_seconds
			print fileName + " " + str(audioDuration) #DBG
			if fileName in self.dtmfAudio:
				self.dtmfThread = threading.Thread(target=self.dtmfDecoder)
				self.dtmfThread.start()
			start = time.time()
			r = audioFile.read(800)
			while r != '' and self.dtmfNumber is None:
				self.modemInstance.write(r)
				r = audioFile.read(800)
				#Esta linea sirve porque la velocidad de escritura y transmision no son las mismas.
				#Entonces si recibo un comando DTMF, a veces el audio posterior no se escucha.
				#El numero se decidio por prueba y error. Una demora mas chica no soluciona el problema,
				#y una mas grande hace que el audio se entrecorte.
				time.sleep(0.04)
			#self.modemInstance.write(audioFile.read())
			while time.time() < (start + audioDuration) and self.dtmfNumber is None:
				pass
			#~ if self.dtmfThread.is_alive():
				#~ self.decodeActive = False
				#~ self.dtmfThread.join()
			if hangUp and self.dtmfNumber is None:
				self.checkHangUp()
			return True
		except CallEnded:
			raise
		
	def checkHangUp(self):
		self.port_lock.acquire()
		self.modemInstance.reset_input_buffer()
		self.modemInstance.dtr = 0
		#~ print self.modemInstance.dtr
		#self.gsmInstance.sendAT('+++', 'NO CARRIER', 10, 0)
		#time.sleep(0.2)
		while self.modemInstance.in_waiting is not 0:
			if self.modemInstance.read(1) == 'N' and self.modemInstance.readline().startswith('O CARRIER'):
				print 'NO CARRIER' #DBG
				if self.modemInstance.in_waiting is not 0:
					self.modemInstance.readline()
					status = self.modemInstance.readline() 
					if status.startswith('NO CARRIER'):
						raise CallEnded
					elif status.startswith(('ERROR', '+CME ERROR', '+CMS ERROR')):
						status.replace('\r\n','')
						raise ATCommandError(status)
				else:
					self.gsmInstance.sendAT('AT#SPCM=3,1','CONNECT', 5)
					break
		self.port_lock.release()
		self.modemInstance.dtr = 1
				
	def recordAudio(self):
		self.dtmfThread = threading.Thread(target=self.dtmfDecoder(True))
		self.dtmfThread.start()
		start = time.time()
		while self.dtmfThread.is_alive() and time.time() < (start + self.recordTime):
			pass
		if self.dtmfThread.is_alive():
			self.decodeActive = False
			self.dtmfThread.join()
				
	def saveAudioMessage(self):
		timestamp = time.localtime()
		day = str(timestamp.tm_year).zfill(4) + str(timestamp.tm_mon).zfill(2) + str(timestamp.tm_mday).zfill(2)
		hour = str(timestamp.tm_hour).zfill(2) + str(timestamp.tm_min).zfill(2) + str(timestamp.tm_sec).zfill(2)
		fileName = 'Audio/Mensajes/' + str(self.gsmInstance.callerID) + ".-audio.-" + str(day) + ".-" + str(hour)
		self.tempAudioMsg = open(fileName, "wb")
		self.tempAudioMsg.write(self.flujoGrabacion)
		self.tempAudioMsg.close()
		return True
		
		
	def availableMedia(self): 
		if self.sendAudioFile('Audio/3_medios_disponibles.raw'):
			time.sleep(0.5)
		else:
			return False
		if self.controllerInstance.availableGsm:
			if self.sendAudioFile('Audio/3_gsm.raw'):
				time.sleep(0.5)
			else:
				return False
		if self.controllerInstance.gprsInstance.isActive:
			if self.sendAudioFile('Audio/3_gprs.raw'):
				time.sleep(0.5)
			else:
				return False
		if self.controllerInstance.availableWifi:
			if self.sendAudioFile('Audio/3_wifi.raw'):
				time.sleep(0.5)
			else:
				return False
		if self.controllerInstance.availableEthernet:
			if self.sendAudioFile('Audio/3_ethernet.raw'):
				time.sleep(0.5)
			else:
				return False
		if self.controllerInstance.availableBluetooth:
			if self.sendAudioFile('Audio/3_bluetooth.raw'):
				time.sleep(0.5)
			else:
				return False
		if self.controllerInstance.availableEmail:
			if self.sendAudioFile('Audio/3_email.raw'):
				time.sleep(0.5)
			else:
				return False
		if self.controllerInstance.availableFtp:
			if not self.sendAudioFile('Audio/3_ftp.raw'):
				return False			
		time.sleep(2)
		return True
		
	#~ def getAudioMessages(self):
		#~ 
		
		
