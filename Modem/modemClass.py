# coding=utf-8

import json
import time
import shlex
import serial
import pickle
import inspect
import subprocess
from messaging.sms import SmsSubmit, SmsDeliver  #Librería que codifica y decodifica los SMS en modo PDU
import regex
import traceback
import threading
import pexpect
import os
import requests
from tempfile import mkstemp
from shutil import move
from os import fdopen, remove
import inspect #DBG

import logger
import contactList
import messageClass

from curses import ascii # Para enviar el Ctrl-Z

JSON_FILE = 'config.json'
JSON_CONFIG = json.load(open(JSON_FILE))
JSON_GPRS = json.load(open('operators.json'))

class ATCommandError(Exception):
	def __init__(self, msg = ''):
		self.msg = msg

class AtTimeout(ATCommandError): pass

class AtNoCarrier(ATCommandError): pass

class AtNewCall(ATCommandError): pass

class Modem(object):

	receptionQueue = None
	androidConnected = None
	atConnected = None
	successfulConnection = androidConnected or atConnected
	localInterface = None
	active_call = False
	new_call = False

	def __init__(self):
			self.modemInstance = serial.Serial()
			self.modemInstance.xonxoff = False # Deshabilitamos el control de flujo por software
			self.modemInstance.rtscts = False  # Deshabilitamos el control de flujo por hardware RTS/CTS
			self.modemInstance.dsrdtr = False  # Deshabilitamos el control de flujo por hardware DSR/DTR
			self.modemInstance.bytesize = serial.EIGHTBITS
			self.modemInstance.parity = serial.PARITY_NONE
			self.modemInstance.stopbits = serial.STOPBITS_ONE
			self.modemInstance.timeout = JSON_CONFIG["MODEM"]["TIME_OUT"]
			self.modemInstance.baudrate = JSON_CONFIG["MODEM"]["BAUD_RATE"]

	def sendAT(self, atCommand, expected = 'OK', wait = 0, mode = 1):
			end = time.time() + wait
			#if atCommand in ['ATA', '+++', 'AT+CMGL=0', 'AT#SGACT?']:
			#~ if atCommand == '+++':
				#~ self.modemInstance.reset_input_buffer()
			if mode == 0:
				self.modemInstance.write(atCommand) 
			elif mode == 1:
				self.modemInstance.write(atCommand + '\r')
			elif mode == 2:
				self.modemInstance.write(atCommand + '\r\n')
			curframe = inspect.currentframe()
			calframe = inspect.getouterframes(curframe,2)
			print calframe[1][3] + ': ' + atCommand
			totalOutput = list()
			#~ if self.modemInstance.in_waiting != 0 and atCommand != '':
				#~ reception = self.modemInstance.read(self.modemInstance.in_waiting)
				#~ 
				#~ self.modemInstance.reset_input_buffer()
			while atCommand.startswith('AT') and  atCommand not in ['ATZ', 'ATE1']:
				modemOutput = self.modemInstance.readline()
				if modemOutput.startswith(atCommand):
					totalOutput.append(modemOutput)
					break
				elif modemOutput.startswith('RING'):
					expected = '+CLIP'
					wait = 0
					break
			while True and expected != None:
				modemOutput = self.modemInstance.readline()
				if modemOutput == '':
					if wait == 0:
						raise AtTimeout("%s" % atCommand)
				else:
					totalOutput.append(modemOutput)
					if modemOutput.startswith(expected):
						print totalOutput
						if expected == '+CLIP':
							self.callerID = self.getTelephoneNumber(regex.findall('"(.*)"', modemOutput.split(',')[0])[0])
							if self.callerID == '':
								self.callerID = 'desconocido'
							logger.write('INFO', '[GSM] El número %s está llamando.' % self.callerID)
							self.active_call = True
							self.new_call = True
						return totalOutput
					elif modemOutput.startswith(('. BAD', '. NO ', 'ERROR', '+CME ERROR', '+CMS ERROR')) and atCommand != 'AT+CNMA':
						errorMessage = modemOutput.replace('\r\n', '')
						logger.write('DEBUG', '[GSM] %s' % errorMessage)
						raise ATCommandError("%s" % atCommand)
					elif modemOutput.startswith('NO CARRIER'):
						print totalOutput
						raise AtNoCarrier
					elif modemOutput.startswith('RING'):
						expected = '+CLIP'
						wait = 0
					elif modemOutput.startswith('SSLSRING'):
						self.modemInstance.write(atCommand + '\r')
				if wait == 0:
					continue
				elif time.time() > end:
					print totalOutput
					raise AtTimeout("%s" % atCommand)
		#~ 
		#~ if expected != None:
			#~ totalOutput = []
			#~ while wait > 0:    
				#~ modemOutput = self.modemInstance.readlines() # Espero la respuesta
				#~ totalOutput += modemOutput
				#~ for outputElement in modemOutput:
					#~ if outputElement.startswith(expected):
						#~ print totalOutput
						#~ return totalOutput
					#~ elif outputElement.startswith(('. BAD', 'ERROR', '+CME ERROR', '+CMS ERROR')):
						#~ raise Exception(outputElement)
				#~ time.sleep(1)   
				#~ wait -= 1
			#~ print totalOutput
			#~ raise RuntimeError("%s: %s" % (atCommand, totalOutput[-1]))
		#~ else:
			#~ modemOutput = self.modemInstance.readlines() # Espero la respuesta
		#~ print modemOutput
		#~ # El módem devuelve una respuesta ante un comando
		#~ if len(modemOutput) > 0:
				#~ # Verificamos si se produjo algún tipo de error relacionado con el comando AT
				#~ for outputElement in modemOutput:
						#~ # El 'AT+CNMA' sólo es soportado en Dongles USB que requieren confirmación de SMS
						#~ if outputElement.startswith(('ERROR', '+CME ERROR', '+CMS ERROR')) and atCommand != 'AT+CNMA':
								#~ errorMessage = outputElement.replace('\r\n', '')
								#~ if atCommand.startswith('AT'):
									#~ logger.write('WARNING', '[GSM] %s - %s.' % (atCommand[:-1], errorMessage))
								#~ else:
									#~ logger.write('WARNING', '[GSM] No se pudo enviar el mensaje - %s.' % errorMessage)
								#~ raise
						#~ # El comando AT para llamadas de voz (caracterizado por su terminacion en ';') no es soportado
						#~ elif outputElement.startswith('NO CARRIER') and atCommand.startswith('ATD') and atCommand.endswith(';'):
								#~ raise
		#~ # Esto ocurre cuando el puerto 'ttyUSBx' no es un módem
		#~ else:
			#~ raise Exception("%s: No hubo respuesta" % atCommand)
		#~ # Si la respuesta al comando AT no era un mensaje de error, retornamos la salida
		#~ return modemOutput

	def closePort(self):
			self.modemInstance.close()

class Gsm(Modem):

	successfulSending = None
	isActive = False
	SmsReceiverResult = None
	telitConnected = False
	MEDIA_NAME = 'GSM'
	thread = None
	threadName = None
	telit_lock = None
	callerID = None
	
	wifiInstance = None
	ethernetInstance = None
	ftpInstance = None
	callInstance = None

	def __init__(self, _receptionQueue):
			Modem.__init__(self)
			self.receptionQueue = _receptionQueue
			self.thread = threading.Thread(target = self.receive, name = self.threadName)

	def close(self):
		self.modemInstance.close()
		#self.callInstance.close()
		logger.write('INFO', '[GSM] Objeto destruido.')


	def connectAT(self, _serialPort):
		self.localInterface = _serialPort
		try:
			self.modemInstance.port = _serialPort
			self.modemInstance.open()
			time.sleep(self.modemInstance.timeout)
			self.sendAT('ATZ')                               # Enviamos un reset
			self.sendAT('ATE1')     #Habilitamos el echo
			#Verificamos conectividad con la red
			while True:
				registration = self.sendAT('AT+CREG?')
				reg_status = regex.findall(",([0-9])\r", registration[1])[0]
				if reg_status == '1':
					break
				elif reg_status == '2':
					return False
				else:
					logger.write('WARNING', '[GSM] El dispositivo no se ha podido registrar en la red.')
					logger.write('DEBUG', '[GSM] AT+CREG status = %s' % reg_status)
					return False
			#En base al modulo conectado, el comportamiento es distinto
			model = self.sendAT('AT+GMM')
			if model[1].startswith('UL865-NAR'):
					self.modemInstance.dsrdtr = True
					self.modemInstance.dtr = 1
					logger.write('DEBUG', '[GSM] Telit UL865-NAR conectada en %s.' % _serialPort)
					self.sendAT('AT#EXECSCR')       #Ejecuto el script de inicio
					#~ self.sendAT('AT+IPR=230400')
					#~ self.modemInstance.baudrate = 230400
					self.telitConnected = True
					self.configPPP()
			elif model[1].startswith('MF626'):
					logger.write('DEBUG', '[GSM] Dongle ZTE MF626 conectado en %s.' % _serialPort)
					self.sendAT('AT+CPMS="SM"')         #Si no le mando esto, el dongle ZTE me manda advertencias cada 2 segundos\;
					self.sendAT('AT+CMEE=2')                 # Habilitamos reporte de error
					self.sendAT('AT+CMGF=0')                 # Establecemos el modo PDU para SMS
					self.sendAT('AT+CNMI=1,2,0,0,0') # Habilitamos notificacion de mensaje entrante
					self.configPPP('mf626')
			else:
					self.sendAT('AT+CMEE=2')                 # Habilitamos reporte de error
					self.sendAT('AT+CMGF=0')                 # Establecemos el modo PDU para SMS
					self.sendAT('AT+CLIP=1')                 # Habilitamos identificador de llamadas
					self.sendAT('AT+CNMI=1,2,0,0,0') # Habilitamos notificacion de mensaje entrante
					self.configPPP()
			#self.atConnection = True
			self.callInstance.modemInstance = self.modemInstance
			return True
		except:
			#self.atConnection = False
			return False
					
	def connectAndroid(self):
		try:
			output = subprocess.pPopen(['adb','devices','-l'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			devicesList, error = output.communicate()
			model = regex.findall('model:(.*) ', devicesList)
			if error=='' and model:
				#Detecta por primera vez el dispositivo
				if not self.androidConnected:
					tethering = 'adb shell su -c service call connectivity 30 i32 1'
					adbProcess = subprocess.Popen(tethering.split(), stdout = subprocess.PIPE, stderr = subprocess.PIPE)
					adbProcess.communicate()
					logger.write('DEBUG', '[GSM] Dispositivo Android conectado: %s.' % model[0])
					time.sleep(2)
				self.androidConnected = True
			else:
					
					self.androidConnected = False
		except:
				self.androidConnected = False
		finally:
				return self.androidConnected
				
	def receive(self):
		if self.androidConnected:
			self.receiveAndroid()
		else:
			self.receiveAT()

	def receiveAndroid(self):
			try:
					smsAmount = 0
					unreadList = list()
					shell = pexpect.spawn("adb shell")
					shell.expect("$")
					self.sendPexpect(shell, "su", "#")
					self.sendPexpect(shell, "sqlite3 /data/data/com.android.providers.telephony/databases/mmssms.db", "sqlite>")
			except:
					pass                       

			#Ejemplo de unreadList[0] = 1285|+543517502317|Hola 13/06 11:53
			#Ejemplo de unreadList[1] = 1286|+543517502317|Hola 13/06 11:58
			smsAmount = len(unreadList)
			self.isActive = True
			while self.isActive:
					try:
							# Leemos los mensajes de texto recibidos...
							if smsAmount is not 0:
									smsPart = list()
									logger.write('DEBUG', '[SMS] Ha(n) llegado ' + str(smsAmount) + ' nuevo(s) mensaje(s) de texto!')
									for sms in unreadList:
											smsPart = sms.split('|')
											smsId = smsPart[0]
											smsAddress = smsPart[1]
											smsBody = smsPart[2]
											#smsBody = smsBody[:-2] #Elimino el \r\r
											telephoneNumber = self.getTelephoneNumber(smsAddress) # Obtenemos el numero de telefono
											# Comprobamos si el remitente del mensaje (un teléfono) está registrado...
											if telephoneNumber in contactList.allowedNumbers.values() or not JSON_CONFIG["COMMUNICATOR"]["RECEPTION_FILTER"]:
													if smsBody.startswith('INSTANCE'):
															# Quitamos la 'etiqueta' que hace refencia a una instancia de mensaje
															serializedMessage = smsBody[len('INSTANCE'):]
															# 'Deserializamos' la instancia de mensaje para obtener el objeto en sí
															try:
																	messageInstance = pickle.loads(serializedMessage)
																	self.receptionQueue.put((messageInstance.priority, messageInstance))
															except:
																	print traceback.format_exc()
																	logger.write('ERROR', '[GSM] No se pudo rearmar la instancia recibida de ' + str(telephoneNumber))
													else:
															self.receptionQueue.put((10, smsBody))
													#self.sendOutput(telephoneNumber, smsMessage) # -----> SOLO PARA LA DEMO <-----
													logger.write('INFO', '[GSM] Mensaje de ' + str(telephoneNumber) + ' recibido correctamente!')
											# ... sino, rechazamos el mensaje entrante.
											else:
													logger.write('WARNING', '[GSM] Mensaje de ' + str(telephoneNumber) + 'rechazado!')
											# Marco como leido el mensaje
											self.sendPexpect(shell, 'UPDATE sms SET read=1 WHERE _id=' + smsId + ';', "sqlite>") #DEBUG
											# Eliminamos el mensaje de la lista
											unreadList.remove(sms)
											# Decrementamos la cantidad de mensajes a procesar
											smsAmount -= 1
							else:
									sql_query = self.sendPexpect(shell, "SELECT _id, address, body FROM sms WHERE read = 0;", "sqlite>")
									#Le damos formato a la consulta
									sql_query = sql_query + "0000|"
									sql_query = sql_query.replace('\r\r','')
									sql_query = sql_query[len("SELECT _id, address, body FROM sms WHERE read = 0;"):]
									#Buscamos la expresion regular. El parametro overlapped es necesario porque los resultados se superponen
									unreadList = regex.findall('\n([0-9]+\|.*?)\n[0-9]+\|', sql_query, regex.DOTALL, overlapped = True)
									smsAmount = len(unreadList)
									#Determino cada cuanto voy a revisar los mensajes recibidos
									time.sleep(5)
					except:
							print traceback.format_exc() #DEBUG
							time.sleep(1.5)
			logger.write('WARNING', '[GSM] Funcion \'receiveAndroid\' terminada.')
							   
	def receiveAT(self):
		try:
				time.sleep(3)
				smsAmount = 0
				smsBodyList = list()
				smsHeaderList = list()
				smsConcatList = list()
				self.telit_lock.acquire()
				while self.active_call:
					self.telit_lock.wait()
				unreadList = self.sendAT('AT+CMGL=0', wait = 2)   #Equivale al "REC UNREAD" en modo texto
				self.telit_lock.release()
				for unreadIndex, unreadData in enumerate(unreadList):
					if unreadData.startswith('+CMGL'):
							smsHeaderList.append(unreadList[unreadIndex])
							smsBodyList.append(unreadList[unreadIndex + 1])
							smsAmount += 1
					elif unreadData.startswith('OK'):
							break
		except:
				print traceback.format_exc()
				pass
		# Ejemplo de unreadList[0]: AT+CMGL=0\r\n
		# Ejemplo de unreadList[1]: +CMGL: 0,1,"",43\r\n
		# Ejemplo de unreadList[2]: 0791452300008001040D91945171928062F70003714012816350291AD4F29C0EA296D9693A68DA9C8264B1178C068AE174B31A\r\n
		# Ejemplo de unreadList[3]: +CMGL: 1,1,"",45\r\n
		# Ejemplo de unreadList[4]: 0791452300008090040D91453915572013F70000714042415564291CD4F29C0EA296D9693A68DA9C8264B4178C068AD174B55A4301\r\n
		# Ejemplo de unreadList[5]: \r\n
		# Ejemplo de unreadList[6]: OK\r\n
		# Ejemplo de smsHeaderList[0]: +CMGL: 0,1,"",43\r\n
		# Ejemplo de smsBodyList[0]  : 0791452300008001040D91945171928062F70003714012816350291AD4F29C0EA296D9693A68DA9C8264B1178C068AE174B31A\r\n
		# Ejemplo de smsHeaderList[1]: +CMGL: 1,1,"",45\r\n
		# Ejemplo de smsBodyList[1]  : 0791452300008090040D91453915572013F70000714042415564291CD4F29C0EA296D9693A68DA9C8264B4178C068AD174B55A4301\r\n
		self.isActive = True
		while self.isActive:
				try:
						# Leemos los mensajes de texto recibidos...
						if smsAmount is not 0:
								logger.write('DEBUG', '[SMS] Ha(n) llegado ' + str(smsAmount) + ' nuevo(s) mensaje(s) de texto!')
								time.sleep(1) #DEBUG
								for smsHeader, smsBody in zip(smsHeaderList, smsBodyList):
										print smsBody
										# Ejemplo smsHeader: +CMGL: 0,1,"",43\r\n
										# Ejemplo smsBody  : 0791452300008001040D91945171928062F70003714012816350291AD4F29C0EA296D9693A68DA9C8264B1178C068AE174B31A\r\n
										# Ejemplo smsHeader: +CMGL: 1,1,"",45\r\n
										# Ejemplo smsBody  : 0791452300008090040D91453915572013F70000714042415564291CD4F29C0EA296D9693A68DA9C8264B4178C068AD174B55A4301\r\n
										PDU = smsBody.replace('\r\n','')
										sms = SmsDeliver(PDU)
										telephoneNumber = self.getTelephoneNumber(sms.number) # Obtenemos el numero de telefono
										# Comprobamos si el remitente del mensaje (un teléfono) está registrado...
										if telephoneNumber in contactList.allowedNumbers.values() or not JSON_CONFIG["COMMUNICATOR"]["RECEPTION_FILTER"]:
												smsMessage = sms.text
												#Si son SMS concatenados, se unen
												if sms.udh is not None:
														logger.write('DEBUG','[SMS] Mensaje multiparte recibido: ' + str(sms.udh.concat.seq) + '/' + str(sms.udh.concat.cnt))
														smsConcatList.append(smsMessage)
														#Es el ultimo mensaje?
														if sms.udh.concat.cnt==sms.udh.concat.seq:
																smsMessage = ''.join(smsConcatList)
																#Corrige el problema de envio de guion bajo para las instancias
																smsMessage = regex.sub('\xbf','_', smsMessage)
																del smsConcatList[:]    #Vacio la lista
														else:
																# Eliminamos la cabecera y el cuerpo del mensaje de las listas correspondientes
																smsHeaderList.remove(smsHeader)
																smsBodyList.remove(smsBody)
																smsAmount -=1
																break

												if smsMessage.startswith('INSTANCE'):
														# Quitamos la 'etiqueta' que hace refencia a una instancia de mensaje
														serializedMessage = smsMessage[len('INSTANCE'):]
														# 'Deserializamos' la instancia de mensaje para obtener el objeto en sí
														try:
																messageInstance = pickle.loads(serializedMessage)
																self.receptionQueue.put((messageInstance.priority, messageInstance))
														except:
																logger.write('ERROR', '[GSM] No se pudo rearmar la instancia recibida de ' + str(telephoneNumber))
												else:
														self.receptionQueue.put((10, smsMessage))
												#self.sendOutput(telephoneNumber, smsMessage) # -----> SOLO PARA LA DEMO <-----
												logger.write('INFO', '[GSM] Mensaje de ' + str(telephoneNumber) + ' recibido correctamente!')
										# ... sino, rechazamos el mensaje entrante.
										else:
												logger.write('WARNING', '[GSM] Mensaje de ' + str(telephoneNumber) + 'rechazado!')
										# Si el mensaje fue leído desde la memoria, entonces lo borramos
										if smsHeader.startswith('+CMGL'):
												# Obtenemos el índice del mensaje en memoria
												smsIndex = self.getSmsIndex(smsHeader.split(',')[0])
												# Eliminamos el mensaje desde la memoria porque ya fue leído
												self.telit_lock.acquire()
												while self.active_call:
													self.telit_lock.wait()
												self.removeSms(smsIndex)
												self.telit_lock.release()
										# Eliminamos la cabecera y el cuerpo del mensaje de las listas correspondiente
										smsHeaderList.remove(smsHeader)
										smsBodyList.remove(smsBody)
										# Decrementamos la cantidad de mensajes a procesar
										smsAmount -= 1
						elif self.telitConnected:
							time.sleep(5)
							while self.active_call:
								pass
							self.telit_lock.acquire()
							unreadList = self.sendAT('AT+CMGL=0', wait = 2)
							self.telit_lock.release()
							for unreadIndex, unreadData in enumerate(unreadList):
								if unreadData.startswith('+CMGL'):
										smsHeaderList.append(unreadList[unreadIndex])
										smsBodyList.append(unreadList[unreadIndex + 1])
										smsAmount += 1
								elif unreadData.startswith('OK'):
										break
						elif self.modemInstance.in_waiting is not 0:
								bytesToRead = self.modemInstance.in_waiting
								receptionList = self.modemInstance.read(bytesToRead).split('\r\n')
								# Ejemplo receptionList: ['+CMT: ,35', '0791452300001098040D91453915572013F700007150133104022911C8373B0C9AC55EB01A2836D3']
								# Ejemplo receptionList: ['RING', '', '+CLIP: "+543512641040",145,"",0,"",0']
								# Ejemplo receptionList: ['+CMS ERROR: Requested facility not subscribed']
								# Ejemplo receptionList: ['NO CARRIER']
								for index, data in enumerate(receptionList):
										# Significa un mensaje entrante
										if receptionList[index].startswith('+CMT') or receptionList[index].startswith('+CMGL'):
												try:
														smsHeaderList.append(receptionList[index])
														smsBodyList.append(receptionList[index + 1])
														self.sendAT('AT+CNMA')  # Enviamos el ACK (ńecesario sólo para los Dongle USB
												except:
														pass # La excepción aparece cuando el módem no soporta (no necesita) el ACK
												finally:
														smsAmount += 1
										elif receptionList[index].startswith('+CMGS:'):
												self.successfulSending = True   #Se envio el mensaje PDU correctamente
										# Significa que no se pudo enviar el mensaje
										elif receptionList[index].startswith('+CMS ERROR'):
												self.successfulSending = False
										############################### LLAMADAS DE VOZ ###############################
										# Significa una llamade entrante
										elif receptionList[index].startswith('RING'):
												self.callerID = self.getTelephoneNumber(receptionList[index + 2])
												logger.write('INFO', '[GSM] El número %s está llamando...' % self.callerID)
										# Significa que el destino se encuentra en otra llamada
										elif receptionList[index].startswith('BUSY'):
												logger.write('WARNING', '[GSM] El télefono destino se encuentra ocupado.')
										# Significa que la llamada saliente pasó al buzón de voz
										elif receptionList[index].startswith('NO ANSWER'):
												logger.write('WARNING', '[GSM] No hubo respuesta durante la llamada de voz.')
										# Significa que la llamada entrante se perdió (llamada perdida) o que el extremo colgo
										elif receptionList[index].startswith('NO CARRIER'):
												self.callerID = None
												logger.write('WARNING', '[GSM] Se perdió la conexión con el otro extremo.')
										############################# FIN LLAMADAS DE VOZ #############################
						else:
							time.sleep(1.5)
				except IOError:
					print traceback.format_exc()
					self.isActive = False
				except:
					print traceback.format_exc()
					time.sleep(1.5)
		logger.write('WARNING', '[GSM] Función \'receiveAT\' terminada.')

	def send(self, message, telephoneNumber, call = False):
		# Comprobación de envío de texto plano
		if isinstance(message, messageClass.Message) and hasattr(message, 'plainText'):
			if call:
				ppp = not self.wifiInstance.online and not self.ethernetInstance.online
				try:
					if ppp:
						print "pon" #DBG
						self.telit_lock.acquire()
						self.sendAT('AT#SSLH=1')
						self.sendAT('AT#SGACT=1,0')
						self.modemInstance.close()
						ponOut, ponErr = subprocess.Popen('pon', stdout = subprocess.PIPE, stderr = subprocess.PIPE).communicate()
						time.sleep(5)
						audioMsg = self.callInstance.text_to_audio(message.plainText)
						subprocess.Popen('poff', stdout = subprocess.PIPE, stderr = subprocess.PIPE).communicate()
						self.modemInstance.open()
						self.telit_lock.release()
					else:
						audioMsg = self.callInstance.text_to_audio(message.plainText)
					return self.sendVoiceCall(audioMsg, telephoneNumber)
				except requests.exceptions.ConnectionError:
					if ppp:
						subprocess.Popen('poff', stdout = subprocess.PIPE, stderr = subprocess.PIPE).communicate()
						self.telit_lock.release()
					logger.write('WARNING', '[GSM] No se puede convertir el mensaje a audio porque no hay conexion a Internet.')
					logger.write('INFO', '[GSM] El mensaje sera enviado por SMS.')
			return self.sendMessage(message.plainText, telephoneNumber)
		# Comprobación de envío de archivo
		elif isinstance(message, messageClass.Message) and hasattr(message, 'fileName'):
			fileDirectory, fileName = os.path.split(message.fileName)
			if call:
				logger.write('WARNING', '[GSM] No es posible enviar archivos mediante llamadas de voz.')
			else:
				logger.write('WARNING', '[GSM] Imposible enviar archivos por SMS.')		
			logger.write('INFO', '[GSM] Archivo %s subido al servidor FTP. Receptor informado por SMS.' % fileName)	
			ftpHost = JSON_CONFIG["FTP"]["FTP_SERVER"]
			if self.ftpInstance.send(message, False):
				aviso = 'El comunicador 2.0 ha subido el archivo ' + fileName + ' para usted, al servidor FTP ' + ftpHost + '.'
				return self.sendMessage(aviso,  telephoneNumber)
			return False
		# Entonces se trata de enviar una instancia de mensaje
		else:
			if call:
				logger.write('WARNING', '[GSM] No es posible enviar instancias mediante llamadas de voz. Enviando por SMS.')
			isInstance = True
			# Serializamos el objeto para poder transmitirlo
			serializedMessage = 'INSTANCE' + pickle.dumps(message)
			return self.sendMessage(serializedMessage, telephoneNumber, True)

	def sendMessage(self, plainText, telephoneNumber, isInstance = False):
		try:
			#############################
			timeCounter = 0
			self.successfulSending = None
			self.successfulList = list()      #Util en SMS concatenados
			smsLine = list()
			index = 1
			#############################
			if self.androidConnected:
				#Para enviar un SMS de multiples lineas, debo enviar una a la vez
				smsLine = plainText.split('\n')
				#Consulto el tiempo del dispositivo, para cuando quiera ver los eventos posteriores
				time_device = self.sendADB('adb shell date')
				time_device = time_device[:-11]
				#Desbloqueo el celular
				self.sendADB('adb shell input keyevent 26')
				self.sendADB('adb shell input swipe 540 1900 540 1000')
				self.sendADB('adb shell input text 7351')
				#Envio el SMS y bloqueo el celular
				self.sendADB('adb shell am start -a android.intent.action.SENDTO -d sms:' + str(telephoneNumber) + ' --ez exit_on_sent true')
				for line in smsLine:
					self.sendADB('adb shell input text "' + line + '"')
					self.sendADB('adb shell input keyevent 66')
				self.sendADB('adb shell input keyevent 67') #Elimino el ultimo \n
			   #self.sendADB('adb shell am start -a android.intent.action.SENDTO -d sms:' + str(telephoneNumber) + ' --es sms_body "' + plainText + '" --ez exit_on_sent true')
				self.sendADB('adb shell input keyevent 22')
				self.sendADB('adb shell input keyevent 66')
				self.sendADB('adb shell input keyevent 26')
				#Consulto si se envio correctamente el mensaje
				thread = threading.Thread(target=self.logcat, args=(time_device, "adb logcat -v brief Microlog:D *:S"))
				thread.start()

				thread.join(10)
				if thread.is_alive():
					self.process.terminate()
					thread.join()
				if self.SmsReceiverResult == None:
					logger.write('WARNING', '[ANDROID] El estado del envio es desconocido. Revisar la conexion')
					self.successfulList.append(False)
				else:
					self.successfulList.append(self.SmsReceiverResult)
					self.SmsReceiverResult = None
			else:    
				self.telit_lock.acquire()
				while self.active_call:
					self.telit_lock.wait()
				csca = self.sendAT('AT+CSCA?')  #Consulta el numero del SMSC, util para el Dongle ZTE
				smsc = regex.findall('"(.*)"', csca[1])       #Me devuelve una lista con las expresiones entre comillas, solo hay una
				sms = SmsSubmit(str(telephoneNumber), plainText)
				sms.csca = smsc[0]
				pdus = sms.to_pdu()
				amount = len(pdus)
				for pdu in pdus:
						# Enviamos los comandos AT correspondientes para efectuar el envío el mensaje de texto
						info01 = self.sendAT('AT+CMGS=' + str(pdu.length), '>') # Envío la longitud del paquete PDU
						# ------------------ Caso de envío EXITOSO ------------------
						# Ejemplo de info01[0]: AT+CMGS=38\r\n
						# Ejemplo de info01[1]: >
						# Comprobamos que el módulo esté listo para mandar el mensaje
						try:
							info02 = self.sendAT(str(pdu.pdu) + ascii.ctrl('z'), 'OK', 10, 1)   # Mensaje de texto terminado en Ctrl+z
							self.successfulSending = True
						except RuntimeError:
							self.successfulSending = False
						break
						# Agregamos la respuesta de la red a la lista
						self.successfulList.append(self.successfulSending)
						if self.successfulSending:
							if (amount > 1):
								logger.write('DEBUG', '[SMS] Mensaje ' + str(index)+ '/' + str(amount) + ' enviado a ' + str(telephoneNumber) + '.')
								index += 1
						else:
							break
				self.telit_lock.release()

			if False in self.successfulList:
				if isInstance:
					logger.write('WARNING', '[GSM] No se pudo enviar la instancia de mensaje a %s.' % str(telephoneNumber))
				else:
					logger.write('WARNING', '[GSM] No se pudo enviar el mensaje a %s.' % str(telephoneNumber))
				return False
			else:
				logger.write('INFO', '[GSM] Mensaje de texto enviado a %s.' % str(telephoneNumber))
				# Borramos el mensaje enviado almacenado en la memoria
				print info02[-3]
				smsIndex = self.getSmsIndex(info02[-3])
				self.telit_lock.acquire()
				while self.active_call:
					self.telit_lock.wait()
				self.sendAT('AT+CMGD=1,2')
				self.telit_lock.release()
				return True

		except:
				print traceback.format_exc()
				logger.write('ERROR', '[GSM] Error al enviar el mensaje de texto a %s.' % str(telephoneNumber))
				return False

	def sendVoiceCall(self, audioMsg, telephoneNumber):
		try:
			self.telit_lock.acquire()
			self.sendAT('ATD' + str(telephoneNumber) + ';', wait = 10) # Numero al cual se quiere llamar
			logger.write('INFO', '[GSM] Llamando al número %s...' % str(telephoneNumber))
			active = False
			while not active:
				status = self.sendAT('AT+CLCC')[1].split(',')[2] 
				if status == '0':
					self.callInstance.thread = threading.Thread(target = self.callInstance.msgCall, args=(audioMsg,))
					self.callInstance.thread.start()
					active = True
				time.sleep(0.5)					
			return True
		except:
			print traceback.format_exc()
			self.telit_lock.release()
			logger.write('ERROR', '[GSM] Se produjo un error al intentar realizar la llamada!')
			return False

	def answerVoiceCall(self):
		self.telit_lock.acquire()
		self.new_call = False
		telephoneNumber = self.getTelephoneNumber(str(self.callerID))
		if telephoneNumber in contactList.allowedNumbers.values() or not JSON_CONFIG["COMMUNICATOR"]["RECEPTION_FILTER"]:
			self.sendAT('AT#SSLH=1')
			self.sendAT('AT#SGACT=1,0')
			self.sendAT('ATA') # Atiende la llamada entrante
			logger.write('INFO', '[GSM] Conectado con el número %s.' % self.callerID)
			self.callInstance.thread = threading.Thread(target = self.callInstance.voiceCall)
			self.callInstance.telephoneNumber = self.callerID
			self.callInstance.thread.start()
			return True
		else:
			self.sendAT('ATH')
			logger.write('INFO', '[GSM] Llamada de %s rechazada.' % self.callerID)
			self.telit_lock.release()
			return False
				
	def hangUpVoiceCall(self):
			try:
				self.active_call = False
				if self.callInstance.thread.isAlive():
					self.callInstance.thread.join()
				else:
					logger.write('INFO', '[GSM] No hay llamada en curso.')
					return True
				self.sendAT('ATH') # Cuelga la llamada en curso
				self.telit_lock.notifyAll()
				self.telit_lock.release()
				if self.callerID is not None:
						logger.write('INFO', '[GSM] Conexión con el número %s finalizada.' % self.callerID)
						self.callerID = None
				return True
			except:
				return False

	def removeSms(self, smsIndex):
			try:
					self.sendAT('AT+CMGD=' + str(smsIndex)) # Elimina el mensaje especificado
					return True
			except:
					return False

	def getSmsIndex(self, atOutput):
			# Ejemplo de 'atOutput' (para un mensaje enviado) : +CMGS: 17
			# Ejemplo de 'atOutput' (para un mensaje recibido): +CMGL: 2
			# Quitamos el comando AT, dejando solamente el índice del mensaje en 
			print atOutput
			if atOutput.startswith('+CMGS'):
					print 'a'
					atOutput = atOutput.replace('+CMGS: ', '')
			elif atOutput.startswith('+CMGL'):
					atOutput = atOutput.replace('+CMGL: ', '')
			smsIndex = int(atOutput)
			print smsIndex
			return smsIndex

	def getTelephoneNumber(self, telephoneNumber):
		############################### QUITAMOS EL CODIGO DE PAIS ###############################
		# Ejemplo de telephoneNumber: +543512641040 | +5493512560536 | 876966 | 100 | PromRecarga
		if telephoneNumber.startswith('+549'):
			telephoneNumber = telephoneNumber.replace('+549', '')
			# Ejemplo de telephoneNumber: 3512560536
			return int(telephoneNumber)
		elif telephoneNumber.startswith('+54'):
			telephoneNumber = telephoneNumber.replace('+54', '')
			# Ejemplo de telephoneNumber: 3512641040
			return int(telephoneNumber)
		################################### FIN CODIGO DE PAIS ###################################
		else:
			# Entonces es 876966 | 100 | PromRecarga
			return telephoneNumber

	def sendOutput(self, telephoneNumber, smsMessage):
			try:
					subprocess.Popen(['gnome-terminal', '-x', 'sh', '-c', smsMessage + '; exec bash'], stderr = subprocess.PIPE)
					#subprocess.check_output(shlex.split(smsMessage), stderr = subprocess.PIPE)
					smsMessage = 'El comando se ejecuto exitosamente!'
			except subprocess.CalledProcessError as e: # El comando es correcto pero le faltan parámetros
					smsMessage = 'El comando es correcto pero le faltan parámetros!'
			except OSError as e: # El comando no fue encontrado (el ejecutable no existe)
					smsMessage = 'El comando es incorrecto! No se encontró el ejecutable.'
			finally:
					#self.send(telephoneNumber, smsMessage)
					pass
			
	def sendADB(self,adbCommand):
			pipe = subprocess.Popen(adbCommand.split(), stdout = subprocess.PIPE, stderr=subprocess.PIPE)
			output, error = pipe.communicate()
			time.sleep(0.5)
			if error=='error: device not found\n':
					logger.write('WARNING','[GSM] El dispositivo Android se ha desconectado.')
					self.androidConnected = False
			elif not error=='':
					logger.write('WARNING','[GSM] Ha fallado el dispositivo Android - %s' % error)
					self.androidConnected = False
			else:
					return output

	def sendPexpect(self, child, command, response):
		try:
			child.sendline(command)
			r = child.expect([response, pexpect.TIMEOUT], 5)
			return child.before
		except:
			print traceback.format_exc() #DEBUG
			logger.write('DEBUG', '[GSM] Shell Android - %s.' % child.before)


	def logcat(self, time_device, adbCommand):
			self.process = subprocess.Popen(adbCommand.split(), stdout = subprocess.PIPE, stderr = subprocess.PIPE)
			output, error = self.process.communicate()
			timestamp = regex.findall('\d{2}-\d{2} \d{2}:\d{2}:\d{2}', output)
			message = regex.findall('\d{2}:\d{2}:\d{2} \S{4} (.*)', output)
			log = zip(timestamp, message)
			for timestamp, message in log:
					if time.strptime(timestamp, "%m-%d %H:%M:%S") > time.strptime(time_device,"%a %b %d %H:%M:%S"):
							result = regex.findall('result: (.*) \r', message)
							if result and result[0] == '-1':
									self.SmsReceiverResult = True
									return
							elif result and result[0] == '1':
									self.SmsReceiverResult = False
									return
									
	def configPPP(self, model = None):
		try:
			self.sendAT("AT+COPS=0,2")
			cops = self.sendAT("AT+COPS?")
			operator = cops[1].split(',')[2]
			operator = operator[1:-1]
			user = JSON_GPRS[operator]["USER"]
			password = JSON_GPRS[operator]["PASSWORD"]
			apn = JSON_GPRS[operator]["APN"]
			mobileauth = open("/etc/ppp/peers/mobile-auth","w")
			mobileauth.write("file /etc/ppp/options-mobile\n")
			mobileauth.write('user "%s"\n' % user)
			mobileauth.write('password "%s"\n' % password)
			mobileauth.write('connect "/usr/sbin/chat -v -t15 -f /etc/ppp/chatscripts/mobile-modem.chat"\n')
			mobileauth.close()
			cgdcont = open("/etc/ppp/chatscripts/apn.operator","w")
			cgdcont.write('AT+CGDCONT=1,"IP","%s"\r' % apn)
			cgdcont.close()
			temp, temp_path = mkstemp()
			new_options = fdopen(temp, "w")
			old_options = open("/etc/ppp/options-mobile", "r")
			lines = old_options.readlines()
			lines = lines[2:]
			old_options.close()
			if model == 'mf626':
				gprs_port = int(self.modemInstance.port[-1:]) + 1
				new_options.write(self.modemInstance.port[:-1] + str(gprs_port) + '\r\n')
			else:
				new_options.write(self.modemInstance.port + '\r\n')
			new_options.write(str(self.modemInstance.baudrate) + '\r\n')
			for line in lines:
				new_options.write(line)
			remove("/etc/ppp/options-mobile")
			move(temp_path, "/etc/ppp/options-mobile")
			new_options.close()
			return True
		except:
			print traceback.format_exc()
			return False		
