 # coding=utf-8

import os
import re
import time
import socket
import inspect
import threading
import subprocess
import traceback
import pexpect
import serial
import json
import regex

import logger

JSON_FILE = 'config.json'
JSON_CONFIG = json.load(open(JSON_FILE))

gsmThreadName = 'gsmReceptor'
gprsThreadName = 'gprsReceptor'
wifiThreadName = 'wifiReceptor'
emailThreadName = 'emailReceptor'
ethernetThreadName = 'ethernetReceptor'
bluetoothThreadName = 'bluetoothReceptor'

threadNameList = [gsmThreadName, gprsThreadName, wifiThreadName, ethernetThreadName, bluetoothThreadName, emailThreadName]

class Controller(threading.Thread):

	availableGsm = False       # Indica si el modo GSM está disponible
	availableGprs = False      # Indica si el modo GPRS está disponible
	availableWifi = False      # Indica si el modo WIFI está disponible
	availableEthernet = False  # Indica si el modo ETHERNET está disponible
	availableBluetooth = False # Indica si el modo BLUTOOTH está disponible
	availableEmail = False     # Indica si el modo EMAIL está disponible
	availableFtp = False

	gsmInstance = None
	gprsInstance = None
	wifiInstance = None
	ethernetInstance = None
	bluetoothInstance = None
	emailInstance = None
	ftpInstance = None
	
	telit_lock = threading.Condition(threading.Lock())
	internetConnection = None
	communicatorName = None

	isActive = False
	email_mode = 1

	def __init__(self, _REFRESH_TIME):
		threading.Thread.__init__(self, name = 'ControllerThread')
		self.gsmInstance.threadName = gsmThreadName
		self.gprsInstance.threadName = gprsThreadName
		self.gprsInstance.state = 'UNKNOWN'
		self.wifiInstance.threadName = wifiThreadName
		self.ethernetInstance.threadName = ethernetThreadName
		self.ethernetInstance.pattern = re.compile('eth[0-9]+')
		self.ethernetInstance.state = 'UP'
		self.emailInstance.threadName = emailThreadName
		self.gsmInstance.telit_lock = self.telit_lock
		self.emailInstance.telit_lock = self.telit_lock
		self.ftpInstance.telit_lock = self.telit_lock
		self.communicatorName = str(JSON_CONFIG["COMMUNICATOR"]["NAME"])
		self.REFRESH_TIME = _REFRESH_TIME

	def close(self):
		# Esperamos que terminen los hilos receptores
		self.closeInstance(self.emailInstance)
		self.closeInstance(self.gprsInstance)
		self.closeInstance(self.wifiInstance)
		self.closeInstance(self.ethernetInstance)
		self.closeInstance(self.bluetoothInstance)
		self.closeInstance(self.gsmInstance)
		#~ self.gsmInstance.isActive = False
		#~ self.gprsInstance.isActive = False
		#~ self.wifiInstance.isActive = False
		#~ self.ethernetInstance.isActive = False
		#~ self.bluetoothInstance.isActive = False
		#~ self.emailInstance.isActive = False
		#~ 
		#~ 
		#~ for receptorThread in threading.enumerate():
			#~ if receptorThread.getName() in threadNameList and receptorThread.isAlive():
				#~ receptorThread.join()
		#~ # Destruimos todas las instancias de comunicación
		#~ if self.emailInstance.successfulConnection:
			#~ self.emailInstance.close()
		#~ if self.gsmInstance.successfulConnection:
			#~ self.gsmInstance.close()
		#~ if self.gprsInstance.successfulConnection:
			#~ self.gprsInstance.close()
		#~ if self.wifiInstance.successfulConnection:
			#~ self.wifiInstance.close()
		#~ if self.ethernetInstance.successfulConnection:
			#~ self.ethernetInstance.close()
		#~ if self.bluetoothInstance.successfulConnection:
			#~ self.bluetoothInstance.close()
		logger.write('INFO', '[CONTROLLER] Objeto destruido.')
	
	def closeInstance(self, instance):
		if instance.isActive:
			instance.isActive = False
			if instance.thread.isAlive():
				instance.thread.join()
			instance.close()
		else:
			return 
			
	def run(self):
		self.isActive = True
		while self.isActive:
			self.availableGsm = self.verifyGsmConnection()
			if self.gsmInstance.androidConnected:
				self.verifyAndroidStatus()
			else:
				self.wifiInstance.pattern = re.compile('wlan[0-9]+')
				self.wifiInstance.state = 'UP'
				self.availableWifi = self.verifyNetworkConnection(self.wifiInstance)
				self.gprsInstance.pattern = re.compile('ppp[0-9]+')
				#self.availableGprs = self.verifyNetworkConnection(self.gprsInstance)
			self.availableEthernet = self.verifyNetworkConnection(self.ethernetInstance)
			self.availableBluetooth = self.verifyBluetoothConnection()
			internetConnection = self.gprsInstance.internetConnection or self.wifiInstance.internetConnection or self.ethernetInstance.internetConnection
			if internetConnection:
				#~ if not self.ftpInstance.isActive:
					#~ self.availableFtp = self.verifyFtpConnection()
				self.availableEmail = self.verifyEmailConnection()
			elif not self.gsmInstance.active_call:
				self.availableFtp = False
				self.availableEmail = False
				if self.emailInstance.isActive:
					logger.write('INFO', '[EMAIL] Se ha desconectado el medio (%s).' % self.emailInstance.emailAccount)
					self.emailInstance.successfulConnection = None
					self.emailInstance.isActive = False
					self.emailInstance.thread = threading.Thread(target = self.emailInstance.receive, name = emailThreadName)
			if self.gsmInstance.new_call:
				self.gsmInstance.answerVoiceCall()
			time.sleep(self.REFRESH_TIME)
		logger.write('WARNING', '[CONTROLLER] Función \'%s\' terminada.' % inspect.stack()[0][3])	

	def verifyGsmConnection(self):
		if self.gsmInstance.connectAndroid():
			if self.gsmInstance.localInterface is None:
					self.gsmInstance.localInterface = 'Android'
					self.gsmInstance.thread.start()
					logger.write('INFO', '[GSM] Listo para usarse (' + self.gsmInstance.localInterface + ').')
					return True
			elif self.gsmInstance.isActive:
					return True
			else:
					return False
		# Generamos la expresión regular
		ttyUSBPattern = re.compile('ttyUSB[0-9]+')
		lsDevProcess = subprocess.Popen(['ls', '/dev/'], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
		lsDevOutput, lsDevError = lsDevProcess.communicate()
		ttyUSBDevices = ttyUSBPattern.findall(lsDevOutput)
		# Se detectaron otros dispositivos GSM conectados
		for ttyUSBx in ttyUSBDevices:
			# Si el puerto serie nunca fue establecido, entonces la instancia no esta siendo usada
			if self.gsmInstance.localInterface is None:
				# Si no se produce ningún error durante la configuración, ponemos al módem a recibir SMS y llamadas
				if self.gsmInstance.connectAT('/dev/' + ttyUSBx):
					self.gsmInstance.thread.start()
					logger.write('INFO', '[GSM] Listo para usarse (' + ttyUSBx + ').')
					#~ if not self.gsmInstance.telitConnected:
						#~ ponOut, ponErr = subprocess.Popen('pon', stdout = subprocess.PIPE, stderr = subprocess.PIPE).communicate()
						#~ if ponErr != '':
							#~ logger.write('WARNING', '[GPRS] La conexion automatica ha fallado: %s' % ponErr )
						#~ else:
							#~ time.sleep(5)
					#~ else:
						#~ try:
							#~ self.telit_lock.acquire()
							#~ self.gsmInstance.sendAT('AT#SGACT=1,1','OK', 5)
							#~ self.telit_lock.release()
						#~ except RuntimeError:
							#~ self.telit_lock.release()
							#~ logger.write('WARNING', '[GPRS] La conexion automatica ha fallado - timeout de AT#SGACT')
						#~ except Exception as message:
							#~ logger.write('WARNING', '[GPRS] La conexion automatica ha fallado - %s' % message)
							#~ self.telit_lock.release()
							#~ pass
					#~ return True
				# Cuando se intenta una conexion sin exito (connect = False), debe cerrarse y probar con la siguiente
				else:
					self.gsmInstance.successfulConnection = None
					self.gsmInstance.localInterface = None
					self.gsmInstance.isActive = False
					self.gsmInstance.closePort()
			# Si el módem ya está en modo activo (funcionando), devolvemos 'True'
			elif self.gsmInstance.isActive:
				return True
			# Llegamos acá si se produce un error en el 'connect' del módem (y todavía está conectado)
			else:
				return False
		# Si anteriormente hubo un intento de 'connect()' con o sin éxito, debemos limpiar el puerto
		if self.gsmInstance.localInterface is not None:
			self.gsmInstance.telitConnected = False
			self.closeConnection(self.gsmInstance)
		return False
	
	def verifyNetworkConnection(self, instance):
		try:
 			if self.gsmInstance.isActive and instance == self.gprsInstance:
				if self.gsmInstance.telitConnected:
					return self.verifyTelitGprsConnection()
				elif not self.gprsInstance.isActive:
					ponOut, ponErr = subprocess.Popen('pon', stdout = subprocess.PIPE, stderr = subprocess.PIPE).communicate()
					if ponErr == '':
						time.sleep(5)
					else:
						return False
			#~ if self.gsmInstance.telitConnected and instance == self.gprsInstance:
				#~ try:
					#~ if not instance.isActive:
						#~ self.telit_lock.acquire()
						#~ address = self.gsmInstance.sendAT('AT#SGACT=1,1','OK', 5)
						#~ self.telit_lock.release()
						#~ instance.localAddress = address[-3][7:-2]
						#~ print instance.localAddress
						#~ instance.localInterface = self.gsmInstance.localInterface
						#~ info = instance.localInterface + ' - ' + instance.localAddress
						#~ logger.write('INFO', '[%s] Listo para usarse (%s).' % (instance.MEDIA_NAME, info))
						#~ return True
					#~ else:
						#~ self.telit_lock.acquire()
						#~ active = self.gsmInstance.sendAT('AT#SGACT?','OK', 5)	
						#~ if active[-4][-1] == '0':
							#~ raise
						#~ self.telit_lock.release()
				#~ except:
					#~ self.telit_lock.release()
					#~ if instance.isActive:
						#~ instance.localInterface = None
						#~ instance.localAddress = None
						#~ #DBG: Falta successfulConnection para los sockets TCP y UDP
						#~ logger.write('INFO', '[%s] Se ha desconectado el medio (%s).' % (instance.MEDIA_NAME, info))
					#~ return False
			#~ if self.gsmInstance.isActive and instance = self.gprsInstance and not instance.isActive:
				#~ ponOut, ponErr = subprocess.Popen('pon', stdout = subprocess.PIPE, stderr = subprocess.PIPE).communicate()
				#~ if ponErr == '':
					#~ time.sleep(5)
				#~ else:
					#~ return False
			for networkInterface in os.popen('ip link show').readlines():
				matchedPattern = instance.pattern.search(networkInterface)
				if matchedPattern is not None and networkInterface.find('state ' + instance.state) > 0:
					if instance.localInterface is None and not instance.isActive:
						instance.localInterface = matchedPattern.group()
						commandToExecute = 'ip addr show ' + instance.localInterface + ' | grep "inet "'
						localAddress = os.popen(commandToExecute).readline()
						while not localAddress:
							localAddress = os.popen(commandToExecute).readline()
							time.sleep(1)
						localAddress = localAddress.split()[1].split('/')[0]
						if instance.connect(localAddress):
							info = instance.localInterface + ' - ' + instance.localAddress
							logger.write('INFO', '[%s] Listo para usarse (%s).' % (instance.MEDIA_NAME, info))
							instance.thread.start()
							return True
						else:
							return False
					elif matchedPattern.group() == instance.localInterface:
						if instance.successfulConnection:
							return True
						else:
							return False
					else:
						continue
				else:
					continue
			if instance.localInterface is not None:
				self.closeConnection(instance)
			return False
		finally:
			instance.internetConnection = self.verifyInternetConnection(instance)
			
	def verifyInternetConnection(self, instance):
		TEST_REMOTE_SERVER = 'www.gmail.com'
		currentStatus = None
		try:
			if not instance.isActive:
				currentStatus = False
			elif instance == self.gprsInstance and self.gsmInstance.telitConnected:
				self.telit_lock.acquire()
				if self.gsmInstance.active_call:
					self.telit_lock.release()
					currentStatus = False
				else:
					result = self.gsmInstance.sendAT('AT#PING="%s"' % TEST_REMOTE_SERVER, wait = 21)
					self.telit_lock.release()
					ping = result[-3].split(',')
					if ping[-1].startswith('255'):
						currentStatus = False
					else:			
						currentStatus = True
			else:
				remoteHost = socket.gethostbyname(TEST_REMOTE_SERVER)
				testSocket = socket.create_connection((remoteHost, 80), 2) # Se determina si es alcanzable
				currentStatus = True
		except socket.error:
			print traceback.format_exc()
			currentStatus = False
		except:
			print traceback.format_exc() #DBG
		finally:
			if currentStatus != instance.internetConnection:
				if currentStatus:
					logger.write('INFO','[%s] Conexion a Internet disponible.' % instance.MEDIA_NAME) 
				else:
					logger.write('INFO','[%s] Se ha perdido la conexion a Internet.' % instance.MEDIA_NAME)
					self.ftpInstance.isActive = False
			return currentStatus
			
		
	def verifyTelitGprsConnection(self):
		try:
			self.telit_lock.acquire()
			if self.gsmInstance.active_call:
				self.telit_lock.release()
				return False
			if not self.gprsInstance.isActive:
				is_active = self.gsmInstance.sendAT('AT#CGPADDR=1')
				address = is_active[-3].split(',')[-1][1:-3]
				if address != '':
					self.gprsInstance.localAddress = address
				else:
					address = self.gsmInstance.sendAT('AT#SGACT=1,1','OK', 5)
					self.gprsInstance.localAddress = address[-3][8:-2]
				self.telit_lock.release()
				self.gprsInstance.localInterface = self.gsmInstance.localInterface
				info = self.gprsInstance.localInterface + ' - ' + self.gprsInstance.localAddress
				logger.write('INFO', '[%s] Listo para usarse (%s).' % (self.gprsInstance.MEDIA_NAME, info))
				end = time.time()
				self.gprsInstance.isActive = True
			else:
				active = self.gsmInstance.sendAT('AT#SGACT?','OK', 5)
				if active[-4][-3] == '0':
					raise
				self.telit_lock.release()
			return True
		except:
			self.telit_lock.release()
			if self.gprsInstance.isActive:
				self.gprsInstance.localInterface = None
				self.gprsInstance.localAddress = None
				#DBG: Falta successfulConnection para los sockets TCP y UDP
				logger.write('INFO', '[%s] Se ha desconectado el medio.' % instance.MEDIA_NAME)
			return False
		
	def verifyAndroidStatus(self):
		self.wifiInstance.pattern = re.compile('usb[0-9]+')
		self.wifiInstance.state = 'UNKNOWN'
		self.gprsInstance.pattern = re.compile('usb[0-9]+')
		if os.popen("adb shell dumpsys connectivity | grep -o 'ni{\[type: WIFI'").readline():
			if self.gprsInstance.localInterface is not None:
				self.closeConnection(self.gprsInstance)
			self.availableWifi = self.verifyNetworkConnection(self.wifiInstance)
		elif os.popen("adb shell dumpsys connectivity | grep -o 'ni{\[type: MOBILE'").readline():
			if self.wifiInstance.localInterface is not None:
				self.closeConnection(self.wifiInstance)
			self.availableGprs = self.verifyNetworkConnection(self.gprsInstance)
		else:
			if self.wifiInstance.localInterface is not None:
				self.closeConnection(self.wifiInstance)
			if self.gprsInstance.localInterface is not None:
				self.closeConnection(self.gprsInstance)
			shell = pexpect.spawn("adb shell")
			shell.expect("$")
			self.gsmInstance.sendPexpect(shell, "su", "#")
			self.gsmInstance.sendPexpect(shell, "svc data enable", "#")
			self.gsmInstance.sendPexpect(shell, "svc wifi enable", "#")
			shell.sendline('exit')
			shell.sendline('exit')

	def verifyBluetoothConnection(self):
		activeInterfacesList = open('/tmp/activeInterfaces', 'a+').read()
		# Ejemplo de bluetoothDevices: ['Devices:\n', '\thci0\t00:24:7E:64:7B:4A\n']
		bluetoothDevices = os.popen('hcitool dev').readlines()
		# Sacamos el primer elemento por izquierda ('Devices:\n')
		bluetoothDevices.pop(0)
		for btDevice in bluetoothDevices:
			# Ejemplo de btDevice: \thci0\t00:24:7E:64:7B:4A\n
			btInterface = btDevice.split('\t')[1]
			btAddress = btDevice.split('\t')[2].replace('\n', '')
			# La interfaz encontrada no está siendo usada y la instancia no está activa (habrá que habilitarla)
			if self.bluetoothInstance.localInterface is None and not self.bluetoothInstance.isActive:
				# Obtenemos la interfaz encontrada
				self.bluetoothInstance.localInterface = btInterface
				# Escribimos en nuestro archivo la interfaz, para indicar que está ocupada
				activeInterfacesFile = open('/tmp/activeInterfaces', 'a+')
				activeInterfacesFile.write(btInterface + '\n')
				activeInterfacesFile.close()
				# Si no se produce ningún error durante la configuración, ponemos a la MAC a escuchar
				if self.bluetoothInstance.connect(btAddress):
					bluetoothInfo = self.bluetoothInstance.localInterface + ' - ' + self.bluetoothInstance.localAddress
					logger.write('INFO', '[BLUETOOTH] Listo para usarse (' + bluetoothInfo + ').')
					self.bluetoothInstance.thread.start()
					return True
				# Si se produce un error durante la configuración, devolvemos 'False'
				else:
					return False
			# La interfaz encontrada es igual a la interfaz de la instancia
			elif btInterface == self.bluetoothInstance.localInterface:
				# Si no se produjo ningún error durante la configuración, devolvemos 'True'
				if self.bluetoothInstance.successfulConnection:
					return True
				# Entonces significa que hubo un error, devolvemos 'False'
				else:
					return False
			# La interfaz encontrada está siendo usado pero no es igual a la interfaz de la instancia
			else:
				continue
		# Si anteriormente hubo un intento de 'connect()' con o sin éxito, debemos limpiar la interfaz
		if self.bluetoothInstance.localInterface is not None:
			localInterface = self.bluetoothInstance.localInterface
			# Limpiamos todos los campos del objeto BLUETOOTH
			self.closeConnection(self.bluetoothInstance)
			# Eliminamos del archivo la interfaz de red usada
			dataToWrite = open('/tmp/activeInterfaces').read().replace(localInterface + '\n', '')
			activeInterfacesFile = open('/tmp/activeInterfaces', 'w')
			activeInterfacesFile.write(dataToWrite)
			activeInterfacesFile.close()
		return False

	def verifyEmailConnection(self):
		try:
			if self.ethernetInstance.internetConnection:
				if self.email_mode != 1 and self.emailInstance.thread.isAlive():
					self.emailInstance.isActive = False
					self.emailInstance.thread.join()
				self.email_mode = 1
			elif self.wifiInstance.internetConnection:
				if self.email_mode != 2 and self.emailInstance.thread.isAlive():
					self.emailInstance.isActive = False
					self.emailInstance.thread.join()
				self.email_mode = 2		
			elif self.gprsInstance.internetConnection:
				self.email_mode = 3
			else:
				return False
			# Comprobamos si aún no intentamos conectarnos con los servidores de GMAIL (por eso el 'None')
			if self.emailInstance.successfulConnection is False:
				# Si no se produce ningún error durante la configuración, ponemos a recibir
				if self.emailInstance.connect(self.email_mode):				
					self.emailInstance.thread.start()
					logger.write('INFO', '[EMAIL] Listo para usarse (' + self.emailInstance.emailAccount + ').')
					end = time.time()
					return True
				# Si se produce un error durante la configuración, devolvemos 'False'
				else:
					return False
			# Si EMAIL ya está en modo activo (funcionando), devolvemos 'True'
			elif self.emailInstance.isActive:
				return True
			# Llegamos acá si se produce un error en el 'connect' (servidores o puertos mal configurados)
			else:
				return False
		# No hay conexión a Internet (TEST_REMOTE_SERVER no es alcanzable), por lo que se vuelve a intentar
		except (RuntimeError, serial.serialutil.SerialException, socket.gaierror) as error:
			print traceback.format_exc()
			if self.emailInstance.isActive:
				logger.write('INFO', '[EMAIL] Se ha desconectado el medio (%s).' % self.emailInstance.emailAccount)
				logger.write('DEBUG', '[EMAIL] %s : %s.' % (type(error).__name__, error))
				self.emailInstance.successfulConnection = None
				self.emailInstance.isActive = False
				self.emailInstance.thread = threading.Thread(target = self.emailInstance.receive, name = emailThreadName)
			return False
			
	def verifyFtpConnection(self):
		try:
			if self.ethernetInstance.internetConnection or self.wifiInstance.internetConnection:
				self.ftpInstance.ftp_mode = 1
				self.ftpInstance.connect()
				lista = self.ftpInstance.ftpServer.nlst()
				for item in lista:
					if item.startswith(self.communicatorName):
						self.ftpInstance.receive(item)
						self.ftpServer.delete(item)
			elif self.gsmInstance.telitConnected:
				self.ftpInstance.ftp_mode = 2
				self.ftpInstance.connect()
				self.gsmInstance.sendAT('AT#FTPTYPE=0', wait = 5)
				lista = self.gsmInstance.sendAT('AT#FTPLIST', 'NO CARRIER', 10) 
				for item in lista:
					name = regex.findall('(' + self.communicatorName + '.*)', item)
					if name:
						self.ftpInstance.receive(name[0][:-1])
						self.gsmInstance.sendAT(('AT#FTPDELE="%s"'%name[0][:-1]).encode('utf-8'), wait = 5)
			if self.ftpInstance.ftp_mode == 1:
				self.ftpInstance.ftpServer.quit()
			else:
				self.gsmInstance.sendAT('AT#FTPCLOSE', wait=5)
				self.telit_lock.release()
			logger.write('INFO', '[FTP] Servidor disponible (%s).' % self.ftpInstance.ftpHost)
			self.ftpInstance.isActive = True
			return True
		except:
			print traceback.format_exc()
			return False
		
			
	def closeConnection(self, instance):
		instance.isActive = False
		if instance.MEDIA_NAME == 'GSM':
			info = instance.localInterface
			self.gsmInstance.closePort()
			if info == 'Android':
				if self.wifiInstance.localInterface is not None:
					self.closeConnection(self.wifiInstance)
				if self.gprsInstance.localInterface is not None:
					self.closeConnection(self.gprsInstance)
		else: 
			info = instance.localInterface + ' - ' + instance.localAddress
			instance.localAddress = None
		if instance.thread.isAlive():
			instance.thread.join()
		instance.thread = threading.Thread(target = instance.receive, name = instance.threadName)
		logger.write('INFO', '[%s] Se ha desconectado el medio (%s).' % (instance.MEDIA_NAME, info))
		instance.successfulConnection = None
		instance.localInterface = None
		
