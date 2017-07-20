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

import logger

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

	gsmInstance = None
	gprsInstance = None
	wifiInstance = None
	ethernetInstance = None
	bluetoothInstance = None
	emailInstance = None

	isActive = False

	def __init__(self, _REFRESH_TIME):
		threading.Thread.__init__(self, name = 'ControllerThread')
		self.REFRESH_TIME = _REFRESH_TIME

	def __del__(self):
		self.gsmInstance.isActive = False
		self.gprsInstance.isActive = False
		self.wifiInstance.isActive = False
		self.ethernetInstance.isActive = False
		self.bluetoothInstance.isActive = False
		self.emailInstance.isActive = False
		# Esperamos que terminen los hilos receptores
		for receptorThread in threading.enumerate():
			if receptorThread.getName() in threadNameList and receptorThread.isAlive():
				receptorThread.join()
		logger.write('INFO', '[CONTROLLER] Objeto destruido.')

	def run(self):
		self.isActive = True
		self.gsmInstance.threadName = gsmThreadName
		self.gprsInstance.threadName = gprsThreadName
		self.gprsInstance.state = 'UNKNOWN'
		self.wifiInstance.threadName = wifiThreadName
		self.ethernetInstance.threadName = ethernetThreadName
		self.ethernetInstance.pattern = re.compile('eth[0-9]+')
		self.ethernetInstance.state = 'UP'
		while self.isActive:
			self.availableGsm = self.verifyGsmConnection()
			if self.gsmInstance.androidConnected:
				self.verifyAndroidStatus()
			else:
				self.wifiInstance.pattern = re.compile('wlan[0-9]+')
				self.wifiInstance.state = 'UP'
				self.availableWifi = self.verifyNetworkConnection(self.wifiInstance)
				self.gprsInstance.pattern = re.compile('ppp[0-9]+')
				self.availableGprs = self.verifyNetworkConnection(self.gprsInstance)
			self.availableEthernet = self.verifyNetworkConnection(self.ethernetInstance)
			self.availableBluetooth = self.verifyBluetoothConnection()
			self.availableEmail = self.verifyEmailConnection()
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
					subprocess.Popen('pon').communicate()
					return True
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
			self.closeConnection(self.gsmInstance)
		return False
	
	def verifyNetworkConnection(self, instance):
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
				
	def verifyEthernetConnection(self):
		# Generamos la expresión regular
		ethPattern = re.compile('eth[0-9]+')
		activeInterfacesList = open('/tmp/activeInterfaces', 'a+').read()
		for networkInterface in os.popen('ip link show').readlines():
			# Con 'ethPattern.search(networkInterface)' buscamos alguna coincidencia
			matchedPattern = ethPattern.search(networkInterface)
			# La interfaz actual coincide con un patrón 'eth'
			if matchedPattern is not None and networkInterface.find("state UP") > 0:
				# El patrón coincidente no está siendo usado y la instancia no está activa (habrá que habilitarla)
				if matchedPattern.group() not in activeInterfacesList and self.ethernetInstance.localInterface is None:
					# Obtenemos la interfaz que concide con el patrón
					self.ethernetInstance.localInterface = matchedPattern.group()
					# Escribimos en nuestro archivo la interfaz, para indicar que está ocupada
					activeInterfacesFile = open('/tmp/activeInterfaces', 'a+')
					activeInterfacesFile.write(self.ethernetInstance.localInterface + '\n')
					activeInterfacesFile.close()
					# Obtenemos la dirección IP local asignada estáticamente o por DHCP
					commandToExecute = 'ip addr show ' + self.ethernetInstance.localInterface + ' | grep inet'
					localAddress = os.popen(commandToExecute).readline().split()[1].split('/')[0]
					# Si no se produce ningún error durante la configuración, ponemos a la IP a escuchar
					if self.ethernetInstance.connect(localAddress):
						ethernetThread = threading.Thread(target = self.ethernetInstance.receive, name = ethernetThreadName)
						ethernetInfo = self.ethernetInstance.localInterface + ' - ' + self.ethernetInstance.localAddress
						logger.write('INFO', '[ETHERNET] Listo para usarse (' + ethernetInfo + ').')
						ethernetThread.start()
						return True
					# Si se produce un error durante la configuración, devolvemos 'False'
					else:
						return False
				# El patrón coincidente es igual a la interfaz de la instancia
				elif matchedPattern.group() == self.ethernetInstance.localInterface:
					# Si no se produjo ningún error durante la configuración, devolvemos 'True'
					if self.ethernetInstance.successfulConnection:
						return True
					# Entonces significa que hubo un error, devolvemos 'False'
					else:
						return False
				# El patrón coincidente está siendo usado pero no es igual a la interfaz de la instancia
				else:
					continue
			# No se encontró coincidencia en la iteración actual, entonces seguimos buscando
			else:
				continue
		# Si anteriormente hubo un intento de 'connect()' con o sin éxito, debemos limpiar la interfaz
		if self.ethernetInstance.localInterface is not None:
			localInterface = self.ethernetInstance.localInterface
			# Limpiamos todos los campos del objeto NETWORK
			closeConnection(self.ethernetInstance, 'ETHERNET')
			self.ethernetInstance.localAddress = None
			# Eliminamos del archivo la interfaz de red usada
			dataToWrite = open('/tmp/activeInterfaces').read().replace(localInterface + '\n', '')
			activeInterfacesFile = open('/tmp/activeInterfaces', 'w')
			activeInterfacesFile.write(dataToWrite)
			activeInterfacesFile.close()
		return False

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
		TEST_REMOTE_SERVER = 'www.gmail.com'
		try:
			remoteHost = socket.gethostbyname(TEST_REMOTE_SERVER)
			testSocket = socket.create_connection((remoteHost, 80), 2) # Se determina si es alcanzable
			# Comprobamos si aún no intentamos conectarnos con los servidores de GMAIL (por eso el 'None')
			if self.emailInstance.successfulConnection is None:
				# Si no se produce ningún error durante la configuración, ponemos a recibir EMAILs
				if self.emailInstance.connect():
					emailThread = threading.Thread(target = self.emailInstance.receive, name = emailThreadName)
					emailThread.start()
					logger.write('INFO', '[EMAIL] Listo para usarse (' + self.emailInstance.emailAccount + ').')
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
		except socket.error as DNSError:
			if self.emailInstance.isActive:
				self.emailInstance.successfulConnection = None
				self.emailInstance.emailAccount = None
				self.emailInstance.isActive = False
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
