 # coding=utf-8

import os
import io
import sys
import time
import json
import Queue
import subprocess
from subprocess import check_output
import regex
import pexpect
import threading
import gc #DBG
import traceback #DBG

currentDirectory = os.getcwd() 
if not currentDirectory.endswith('Communicator'):
	os.chdir(currentDirectory + '/Communicator')

sys.path.append(os.path.abspath('Email/'))
sys.path.append(os.path.abspath('Modem/'))
sys.path.append(os.path.abspath('Network/'))
sys.path.append(os.path.abspath('Bluetooth/'))
sys.path.append(os.path.abspath('File Transfer/'))
sys.path.append(os.path.abspath('Audio/'))

import emailClass
import modemClass
import networkClass
import bluetoothClass
import ftpClass

import logger
import contactList
import messageClass
import controllerClass
import transmitterClass
import callClass

os.chdir(currentDirectory)

alreadyOpen = False
receptionQueue = Queue.PriorityQueue
transmissionQueue = Queue.PriorityQueue

gsmInstance = modemClass.Gsm
emailInstance = emailClass.Email
gprsInstance = networkClass.Network
wifiInstance = networkClass.Network
ethernetInstance = networkClass.Network
bluetoothInstance = bluetoothClass.Bluetooth
ftpInstance = ftpClass.Ftp
callInstance = callClass.Call

controllerInstance = controllerClass.Controller    # Instancia que controla los medios
transmitterInstance = transmitterClass.Transmitter # Instancia para la transmisión de paquetes

JSON_FILE = 'config.json'
JSON_CONFIG = json.load(open(JSON_FILE))

# Creamos el logger de eventos
FILE_LOG = JSON_CONFIG["LOGGER"]["FILE_LOG"]
FILE_LOGGING_LEVEL = JSON_CONFIG["LOGGER"]["FILE_LOGGING_LEVEL"]
CONSOLE_LOGGING_LEVEL = JSON_CONFIG["LOGGER"]["CONSOLE_LOGGING_LEVEL"]
logger.set(FILE_LOG, FILE_LOGGING_LEVEL, CONSOLE_LOGGING_LEVEL)

def open():
	global alreadyOpen
	global receptionQueue, transmissionQueue
	global controllerInstance, transmitterInstance
	global gsmInstance, gprsInstance, wifiInstance, ethernetInstance, bluetoothInstance, emailInstance, ftpInstance

	if not alreadyOpen:
		logger.write('INFO', 'Abriendo el Comunicador...')
		# Creamos las colas de recepción y transmisión, respectivamente
		RECEPTION_QSIZE = JSON_CONFIG["COMMUNICATOR"]["RECEPTION_QSIZE"]
		TRANSMISSION_QSIZE = JSON_CONFIG["COMMUNICATOR"]["TRANSMISSION_QSIZE"]
		receptionQueue = Queue.PriorityQueue(RECEPTION_QSIZE)
		transmissionQueue = Queue.PriorityQueue(TRANSMISSION_QSIZE)
		# Creamos las instancias de los periféricos
		gsmInstance = modemClass.Gsm(receptionQueue)
		gprsInstance = networkClass.Network(receptionQueue, 'GPRS')
		wifiInstance = networkClass.Network(receptionQueue, 'WIFI')
		ethernetInstance = networkClass.Network(receptionQueue, 'ETHERNET')
		bluetoothInstance = bluetoothClass.Bluetooth(receptionQueue)
		emailInstance = emailClass.Email(receptionQueue)
		ftpInstance = ftpClass.Ftp(receptionQueue)
		callInstance = callClass.Call()
		# Creamos la instancia que levantará las conexiones
		REFRESH_TIME = JSON_CONFIG["COMMUNICATOR"]["REFRESH_TIME"]
		controllerInstance.gsmInstance = gsmInstance
		controllerInstance.gprsInstance = gprsInstance
		controllerInstance.wifiInstance = wifiInstance
		controllerInstance.ethernetInstance = ethernetInstance
		controllerInstance.bluetoothInstance = bluetoothInstance
		controllerInstance.emailInstance = emailInstance
		controllerInstance.ftpInstance = ftpInstance
		controllerInstance.callInstance = callInstance
		controllerInstance = controllerClass.Controller(REFRESH_TIME)
		
		emailInstance.gsmInstance = gsmInstance
		emailInstance.controllerInstance = controllerInstance
		
		gsmInstance.wifiInstance = wifiInstance
		gsmInstance.ethernetInstance = ethernetInstance
		gsmInstance.ftpInstance = ftpInstance
		gsmInstance.callInstance = callInstance
		ftpInstance.gsmInstance = gsmInstance
		
		callInstance.controllerInstance = controllerInstance
		callInstance.gsmInstance = gsmInstance
		callInstance.telit_lock = controllerInstance.telit_lock
		# Creamos la instancia para la transmisión de paquetes
		transmitterInstance = transmitterClass.Transmitter(transmissionQueue)
		transmitterInstance.gsmInstance = gsmInstance
		transmitterInstance.gprsInstance = gprsInstance
		transmitterInstance.wifiInstance = wifiInstance
		transmitterInstance.ethernetInstance = ethernetInstance
		transmitterInstance.bluetoothInstance = bluetoothInstance
		transmitterInstance.emailInstance = emailInstance
		transmitterInstance.ftpInstance = ftpInstance
		# Ponemos en marcha el controlador de medios de comunicación y la transmisión de mensajes
		controllerInstance.start()
		transmitterInstance.start()
		logger.write('INFO', 'Comunicador abierto exitosamente!')
		# Indicamos que inicio la sesión
		alreadyOpen = True
		return True
	else:
		logger.write('WARNING', 'El Comunicador ya se encuentra abierto!')
		return False

def close():
	global alreadyOpen
	global receptionQueue, transmissionQueue
	global controllerInstance, transmitterInstance
	global gsmInstance, gprsInstance, wifiInstance, ethernetInstance, bluetoothInstance, emailInstance

	if alreadyOpen:
		logger.write('INFO', 'Cerrando el Comunicador...')		
		#~ if gprsInstance.isActive:
			#~ disconnectGprs()
		# Destruimos las colas de recepción y transmisión
		del receptionQueue
		del transmissionQueue
		# Frenamos la transmisión de mensajes
		transmitterInstance.isActive = False
		transmitterInstance.join()
		transmitterInstance.close()
		# Frenamos la verificación de las conexiones
		controllerInstance.isActive = False
		controllerInstance.join()
		controllerInstance.close()
		# Destruimos las instancias de manejo del comunicador		
		logger.write('INFO', 'Comunicador cerrado exitosamente!')
		# Indicamos que terminó la sesion
		alreadyOpen = False
		return True
	else:
		logger.write('WARNING', 'El Comunicador ya se encuentra cerrado!')
		return False

def send(message, receiver = None, media = None):
	if alreadyOpen:
		if not transmissionQueue.full():
			# Si el mensaje no es una instancia, la creamos para poder hacer el manejo de transmisión con prioridad
			if not isinstance(message, messageClass.Message):
				# Al no tratarse de una instancia, no podemos conocer el destino salvo que el usuario lo especifique
				if receiver is not None:
					tmpMessage = message
					# Creamos la instancia general de un mensaje
					message = messageClass.Message('client01', receiver, 10)
					# Verificamos si el mensaje es una ruta a un archivo (path relativo o path absoluto)...
					if os.path.isfile(tmpMessage):
						# Insertamos el campo 'fileName'
						setattr(message, 'fileName', tmpMessage)
					# Entonces es un mensaje de texto plano
					else:
						# Insertamos el campo 'plainText'
						setattr(message, 'plainText', tmpMessage)
				else:
					logger.write('ERROR', '[COMMUNICATOR] No se especificó un destino para el mensaje!')
					return False
			################################## VERIFICACIÓN DE CONTACTO ##################################
			# Antes de poner el mensaje en la cola, comprobamos que el cliente esté en algún diccionario
			clientList = list() + contactList.allowedHosts.keys()
			clientList += contactList.allowedBtAddress.keys()
			clientList += contactList.allowedEmails.keys()
			clientList += contactList.allowedNumbers.keys()
			# Quitamos los clientes repetidos
			clientList = list(set(clientList))
			# Buscamos por lo menos una coincidencia, para luego intentar hacer el envío
			if message.receiver not in clientList:
				# El cliente fue encontrado como entrada de un diccionario
				logger.write('WARNING', '[COMMUNICATOR] \'%s\' no registrado! Mensaje descartado...' % message.receiver)
				return False
			################################ FIN VERIFICACIÓN DE CONTACTO ################################
			# Ponemos en maýusculas el dispositivo preferido, si es que se estableció alguno
			if media is not None:
				media = media.upper()
			# Damos mayor prioridad al dispositivo referenciado por 'media' (si es que hay alguno)
			setattr(message, 'media', media)
			# Indicamos con una marca de tiempo, la hora exacta en la que se almacenó el mensaje en la cola de transmisión
			setattr(message, 'timeStamp', time.time())
			# Establecemos el tiempo que permanecerá el mensaje en la cola antes de ser desechado en caso de no ser enviado
			setattr(message, 'timeToLive', JSON_CONFIG["COMMUNICATOR"]["TIME_TO_LIVE"])
			# Almacenamos el mensaje en la cola de transmisión, con la prioridad correspondiente
			transmissionQueue.put((message.priority, message))
			logger.write('INFO', '[COMMUNICATOR] Mensaje almacenado en la cola esperando ser enviado...')
			return True
		else:
			logger.write('WARNING', '[COMMUNICATOR] La cola de transmisión esta llena, imposible enviar!')
			return False
	else:
		logger.write('WARNING', 'El Comunicador no se encuentra abierto!')
		return False

def receive():
	if alreadyOpen:
		if receptionQueue.qsize() > 0:
			# El elemento 0 es la prioridad, por eso sacamos el 1 porque es el mensaje
			return receptionQueue.get_nowait()[1]
		else:
			logger.write('INFO', '[COMMUNICATOR] La cola de mensajes esta vacía!')
			return None
	else:
		logger.write('WARNING', 'El Comunicador no se encuentra abierto!')
		return False

#def length():
	#if alreadyOpen:
		#if receptionQueue.qsize() == None:
			#return 0
		#else:
			#return receptionQueue.qsize()
	#else:
		#logger.write('WARNING', 'El Comunicador no se encuentra abierto!')
		#return False

#def sendVoiceCall(telephoneNumber):
	#if gsmInstance.isActive:
		#return gsmInstance.sendVoiceCall(telephoneNumber)
	#else:
		#logger.write('WARNING', '[COMMUNICATOR] No hay un módulo para el manejo de llamadas de voz!')
		#return False

#def answerVoiceCall():
	#if gsmInstance.isActive:
		#return gsmInstance.answerVoiceCall()
	#else:
		#logger.write('WARNING', '[COMMUNICATOR] No hay un módulo para el manejo de llamadas de voz!')
		#return False

#def hangUpVoiceCall():
	#if gsmInstance.isActive:
		#return gsmInstance.hangUpVoiceCall()
	#else:
		#logger.write('WARNING', '[COMMUNICATOR] No hay un módulo para el manejo de llamadas de voz!')
		#return False

#def connectGprs():
	## Si no existe una conexión GPRS activa, intentamos conectarnos a la red
	#if not gprsInstance.isActive:                          
		#try:
			#logger.write('INFO', '[COMMUNICATOR] Intentando conectar con la red GPRS...')
			#if gsmInstance.androidConnected:
				#pattern = 'usb[0-9]+'
				#command = "adb shell dumpsys connectivity | grep -o 'ni{\[type: WIFI'"
				#gprsError = check_output(command.split())
			#else:
				#pattern = 'ppp[0-9]+'
				#gprsProcess = subprocess.Popen('pon', stdout = subprocess.PIPE, stderr = subprocess.PIPE)
				#gprsOutput, gprsError = gprsProcess.communicate()
			## Si no se produjo ningún error, entonces se intenta iniciar la conexión con el APN
			#if gprsError == '':
				#notAvailable = True
				#while notAvailable:
					#time.sleep(1)
					#ipOutput = check_output(['ip','link','show'])
					#interface = regex.findall(pattern, ipOutput)
					#if interface:
						#notAvailable = False
				#ifconfig = 'ifconfig ' + interface[0]
				#notAvailable = True
				#while notAvailable:
					#time.sleep(1)
					#ifconfigProcess = subprocess.Popen(ifconfig.split(), stdout = subprocess.PIPE, stderr = subprocess.PIPE)
					#ifconfigOutput, ifconfigError = ifconfigProcess.communicate()
					#ipv4 = regex.findall('inet addr:(.*)  Bcast', str(ifconfigOutput))
					#if ipv4:
							#notAvailable = False
				#ipv6 = regex.findall('inet6 addr: (.*) Scope', str(ifconfigOutput))
				#logger.write('DEBUG', '[COMMUNICATOR] Dirección IPv4: %s' % ipv4[0])
				#logger.write('DEBUG', '[COMMUNICATOR] Dirección IPv6: %s' % ipv6[0])
				#return True
			## El puerto serial en '/etc/ppp/options-mobile' está mal configurado
			#elif gprsError.startswith('ni'):
				#change = raw_input('El telefono Android utiliza una conexion WiFi, desea cambiar a GPRS?[s/n]:')
				#if change in ['s','S','Y','y']:
					#shell = pexpect.spawn("adb shell")
					#shell.expect("$")
					#gsmInstance.sendPexpect(shell, "su", "#")
					#gsmInstance.sendPexpect(shell, "svc data enable", "#")
					#gsmInstance.sendPexpect(shell, "svc wifi disable", "#")
					#time.sleep(5)
					#gsmInstance.sendPexpect(shell, "dumpsys connectivity | grep -o 'ni{\[type: MOBILE'", "#")
					#if not shell.expect(['ni',pexpect.TIMEOUT],1):
						#shell.sendline('exit')
						#shell.sendline('exit')
						#return True
					#else:
						#gsmInstance.sendPexpect(shell, "svc wifi enable", "#")
						#gsmInstance.sendPexpect(shell, "svc data disable", "#")
						#shell.sendline('exit')
						#shell.sendline('exit')						
						#logger.write('WARNING', '[COMMUNICATOR] Conexion GPRS fallida. WiFi activado nuevamente')
						#return False
				#else:
					#logger.write('INFO', '[COMMUNICATOR] Se usara la conexion WiFi del telefono')
					#return False
			#else:
				#logger.write('WARNING', '[COMMUNICATOR] Ningún módem conectado para realizar la conexión!')
				#return False
		#except Exception as error:
			#print error
			#logger.write('ERROR', '[COMMUNICATOR] Se produjo un error al intentar realizar la conexión!')
			#return False
	#else:
		#logger.write('WARNING', '[COMMUNICATOR] Ya existe una conexión GPRS activa!')
		#return True

#def disconnectGprs():
	## Si ya existe una conexión GPRS activa, intentamos desconectarnos de la red
	#if gprsInstance.isActive:
		#try:
			#if gsmInstance.androidConnected:
				#change = raw_input('El telefono posee conexion WiFi, desea activarla?[s/n]:')
				#if change in ['s','S','Y','y']:
					#shell = pexpect.spawn("adb shell")
					#shell.expect("$")
					#gsmInstance.sendPexpect(shell, "svc wifi enable", "#")
					#gsmInstance.sendPexpect(shell, "svc data disable", "#")	
					#shell.sendline('exit')
					#shell.sendline('exit')
			#elif gsmInstance.telitConnected:
				#controllerInstance.telit_lock.acquire()
				#gsmInstance.sendAT('AT#SGACT=1,0')
				#self.controllerInstance.telit_lock.release()
			#else:
					#command = 'poff'
			#poffProcess = subprocess.Popen(command.split(), stdout = subprocess.PIPE, stderr = subprocess.PIPE)
			#poffOutput, poffError = poffProcess.communicate()
			#if poffOutput.find('Not connected') > 0 or poffOutput.startswith('Result: Parcel'):
				#logger.write('WARNING', '[COMMUNICATOR] No hay conexión!')
				#return False
			#else:
				#logger.write('INFO', '[COMMUNICATOR] La red GPRS ha sido desconectada correctamente!')
				#return True
		#except:
			#print traceback.format_exc()
			#logger.write('ERROR', '[COMMUNICATOR] Se produjo un error al intentar desconectarse de la red GPRS!')
			#return False
	#else:
		#logger.write('WARNING', '[COMMUNICATOR] No existe una conexión GPRS activa para desconectar!')
		#return False
