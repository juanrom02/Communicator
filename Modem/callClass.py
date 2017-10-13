from gtts import gTTS
from pydub import AudioSegment
from DTMFdetector import DTMFdetector
from modemClass import ATCommandError, AtNoCarrier, AtTimeout
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

JSON_FILE = 'config.json'
JSON_CONFIG = json.load(open(JSON_FILE))

class CallEnded(Exception): pass

class Call():
	
	modemInstance = None
	gsmInstance = None
	controllerInstance = None
	
	audioMsgQueue = None
	language = None
	thread = None
	isActive = False
	telit_lock = None
	dtmfThread = threading.Thread()
	port_lock = threading.Lock()
	dtmfNumber = None
	decodeActive = False
	dtmfAudio = ['Audio/menu.raw', 'Audio/2_opciones_guardado.raw', 'Audio/M_menu.raw']
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
		
	def voiceCall(self, bienvenida = True):
		end_a2t = None
		try:
			self.gsmInstance.sendAT('AT+IPR=230400')
			self.modemInstance.baudrate = 230400
			isActive = True
			if bienvenida:
				self.gsmInstance.sendAT('AT#SPCM=3,1','CONNECT', 5)
				self.sendAudioFile('Audio/bienvenida.raw', False)
			time.sleep(0.5)
			audio = 'Audio/menu.raw'
			while True:
				self.sendAudioFile(audio)
				#~ self.dtmfThread = threading.Thread(target=self.dtmfDecoder)
				#~ self.dtmfThread.start()
				print 'waitDTMF 5'
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
					self.sendAudioFile('Audio/tono.raw', False)
					print 'recordAudio' #DBG
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
						self.sendAudioFile('Audio/no_disponible.raw')
						time.sleep(1)
				elif numero is '4':
					self.sendAudioFile('Audio/2_grabar_tono.raw', False)
					self.sendAudioFile('Audio/tono.raw', False)
					print 'recordAudio' #DBG
					self.recordAudio()
					self.checkHangUp()
					ppp = not self.gsmInstance.wifiInstance.online and not self.gsmInstance.ethernetInstance.online
					if ppp:
						self.sendAudioFile('Audio/4_guardado_posterior.raw', False)
						end_a2t = self.flujoGrabacion
					else:
						text = self.audio_to_text(self.flujoGrabacion)
						if text.startswith("AUDIO_NO_RECONOCIDO"):
							logger.write('WARNING','[GSM] Un mensaje de voz no ha podido ser reconocido.')
							self.sendAudioFile('Audio/4_audio_no_reconocido.raw')
						elif text.startswith("SIN_CONEXION"):
							self.sendAudioFile('Audio/4_guardado_posterior.raw')
							end_a2t = self.flujoGrabacion
						else:
							self.gsmInstance.receptionQueue.put((10,text))
							self.sendAudioFile('Audio/4_mensaje_recibido.raw')
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
			self.gsmInstance.sendAT('AT+IPR=115200')
			self.modemInstance.baudrate = 115200
			if end_a2t is not None:
				self.gsmInstance.sendAT('AT#SSLH=1')
				self.gsmInstance.sendAT('AT#SGACT=1,0')
				self.modemInstance.close()
				time.sleep(5)
				logfile = open('/var/log/messages','r')
				logfile.seek(0,2) #Va al final del archivo
				subprocess.Popen('pon', stdout = subprocess.PIPE, stderr = subprocess.PIPE)
				poff = False
				while True:
					line = logfile.readline()
					if not line:
						time.sleep(0.1)
					else:
						pppMsg = regex.findall('pppd\[.*\]: (.*)', line)
						if not pppMsg:
							pass
						elif pppMsg[0].startswith('Exit'):
							if not poff:
								logger.write('WARNING','[GSM] Un mensaje de voz no ha sido decodificado porque no hay conexion a Internet.')
							break
						elif pppMsg[0].startswith('local  IP address'):
							print 'a2t'
							text = self.audio_to_text(end_a2t)
							print 'text ' + text
							if text.startswith("AUDIO_NO_RECONOCIDO"):
								logger.write('WARNING','[GSM] Un mensaje de voz no ha podido ser reconocido.')
							elif text.startswith("SIN_CONEXION"):
								logger.write('WARNING','[GSM] Un mensaje de voz no ha sido decodificado porque no hay conexion a Internet.')
							else:
								self.gsmInstance.receptionQueue.put((10,text))
								logger.write('INFO', '[GSM] Mensaje de ' + self.gsmInstance.callerID + ' recibido correctamente!')
							subprocess.Popen('poff', stdout = subprocess.PIPE, stderr = subprocess.PIPE).communicate()
							poff = True
				self.modemInstance.open()
				#~ self.modemInstance.dsrdtr = True
				#~ self.modemInstance.dtr = 1
				#~ time.sleep(2)
				#~ self.gsmInstance.sendAT('AT')
			self.closeCall()
			return True
		except: #DBG
			print traceback.format_exc()
			
	def msgCall(self, audioMsg):
		try:
			self.gsmInstance.sendAT('AT#SPCM=3,1','CONNECT', 5)
			self.sendAudioFile('Audio/M_tiene_mensaje.raw')
			self.sendAudioFile('Audio/tono.raw')
			self.sendAudioFile(audioMsg)
			os.remove(audioMsg)
			time.sleep(0.5)
			self.sendAudioFile('Audio/tono.raw')
			self.voiceCall(False)
			return True
		except CallEnded:
			self.closeCall()
			return True			
						
	def closeCall(self):
		if self.gsmInstance.callerID is not None:
			logger.write('INFO', '[GSM] Llamada con el numero %s finalizada.' % self.gsmInstance.callerID)
			self.gsmInstance.callerID = None
		self.gsmInstance.telit_lock.notifyAll()
		self.gsmInstance.telit_lock.release()
		self.gsmInstance.active_call = False
			
	def dtmfDecoder(self, grabar = False):
		try:
			dtmf = DTMFdetector()
			self.flujoGrabacion = ''
			#self.modemInstance.reset_input_buffer() #DBG
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
				self.modemInstance.read(800)
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
		except IndexError:
			pass
		except: #DBG
			print traceback.format_exc()
			
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
			tts.save("temp.mp3")
			audio = AudioSegment.from_mp3("temp.mp3")
			g = tempfile.NamedTemporaryFile(delete = False)
			audio.export(g.name, format="s8", codec = "pcm_s8", bitrate="64k", parameters=["-ar","8000"])
			g.seek(0)
			return g.name
		except:
			raise
			
	def audio_to_text(self, source):
		try:
			raw = speech_recognition.AudioData(source, 8000, 1)
			f = tempfile.NamedTemporaryFile()
			f.write(raw.get_wav_data())
			recognizer = speech_recognition.Recognizer()
			with speech_recognition.AudioFile(f.name) as source:
				audio = recognizer.record(source)
			text = recognizer.recognize_google(audio, language="es-AR")
			return text
		except speech_recognition.UnknownValueError:
			return "AUDIO_NO_RECONOCIDO"
		except speech_recognition.RequestError as e:
			print("Could not request results from Google Speech Recognition service; {0}".format(e))		
			return "SIN_CONEXION"
			
	def sendAudioFile(self, fileName, hangUp = True):
		try:
			audioFile = open(fileName, 'rb')
			audioDuration = AudioSegment.from_file(fileName, format="raw", frame_rate=8000, channels=1, sample_width=1).duration_seconds
			print fileName + " " + str(audioDuration) #DBG
			if fileName in self.dtmfAudio:
				self.dtmfThread = threading.Thread(target=self.dtmfDecoder)
				self.dtmfThread.start()
			start = time.time()
			r = audioFile.read(8000)
			print 'A', #DBG
			while self.dtmfNumber is None and time.time() < (start + audioDuration):
				i = time.time()
				self.modemInstance.write(r)
				r = audioFile.read(8000)
				time.sleep(1 + i - time.time())
			print 'B' #DBG
			#Con esto corta antes el audio cuando marco un numero
			if self.dtmfNumber is not None:
				pass
				#~ self.modemInstance.dtr = 0
				#~ print 'B1', #DBG
				#~ while self.modemInstance.in_waiting is not 0:
					#~ ene = self.modemInstance.readline()
					#~ print ene,
					#~ l = regex.findall('(NO CARRIER)', ene)
					#~ if l:
						#~ break
						#~ etc = self.modemInstance.read(9)
						#~ print etc,
						#~ if etc == 'O CARRIER':
							#~ break
				#~ self.gsmInstance.sendAT('AT#SPCM=3,1','CONNECT', 5)	
				#~ self.modemInstance.dtr = 1
			elif hangUp:
				self.checkHangUp()
			print 'C'
			#~ if hangUp and self.dtmfNumber is None:
				#~ self.checkHangUp()
			#self.modemInstance.write(audioFile.read())
			#~ while time.time() < (start + audioDuration) and self.dtmfNumber is None:
				#~ pass
			#~ if self.dtmfThread.is_alive():
				#~ self.decodeActive = False
				#~ self.dtmfThread.join()
			audioFile.close()
			return True
		except CallEnded:
			raise
		except: #DBG
			print traceback.format_exc()
		
	def checkHangUp(self):
		try:
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
		except:
			print traceback.format_exc()
			raise
		finally:
			self.port_lock.release()
			self.modemInstance.dtr = 1
				
	def recordAudio(self):
		try:
			self.dtmfThread = threading.Thread(target=self.dtmfDecoder, args=(True,))
			self.dtmfThread.start()
			start = time.time()
			while self.dtmfThread.is_alive() and time.time() < (start + self.recordTime):
				pass
			if self.dtmfThread.is_alive():
				self.decodeActive = False
				self.dtmfThread.join()
			self.dtmfNumber = None
		except CallEnded:
			raise
		except:
			print traceback.format_exc()
				
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
		
		
