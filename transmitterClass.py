# coding=utf-8

import time
import json
import Queue
import inspect
import threading

import logger
import contactList

JSON_FILE = 'config.json'
JSON_CONFIG = json.load(open(JSON_FILE))

class Transmitter(threading.Thread):

	gsmPriority = 0
	gprsPriority = 0
	wifiPriority = 0
	ethernetPriority = 0
	emailPriority = 0
	bluetoothPriority = 0
	ftpPriority = 0

	gsmInstance = None
	gprsInstance = None
	wifiInstance = None
	ethernetInstance = None
	emailInstance = None
	bluetoothInstance = None
	androidInstance = None
	ftpInstance = None

	isActive = False
	transmissionQueue = None

	def __init__(self, _transmissionQueue):
		threading.Thread.__init__(self, name = 'TransmitterThread')
		self.transmissionQueue = _transmissionQueue

	def close(self):
		logger.write('INFO', '[TRANSMITTER] Objeto destruido.')

	def run(self):
 		self.isActive = True
		while self.isActive:
			try:
				# El elemento 0 es la prioridad, por eso sacamos el 1 que es el mensaje
				messageInstance = self.transmissionQueue.get(True, 1.5)[1]
				# Calculamos el tiempo transcurrido desde la creación del mensaje
				elapsedTime = time.time() - messageInstance.timeStamp
				# Actualizamos el tiempo de vida restante del mensaje
				messageInstance.timeToLive = messageInstance.timeToLive - elapsedTime
				# Si todavía no se alcanzó el tiempo de vida, el mensaje sigue siendo válido...
				if messageInstance.timeToLive > 0:
					transmitterThread = threading.Thread(target = self.trySend, args = (messageInstance,), name = 'TransmitterThread')
					transmitterThread.start()
				# ... sino, el tiempo fue excedido y el mensaje debe ser descartado.
				else:
					logger.write('WARNING', '[COMMUNICATOR] Mensaje para \'%s\' descartado (el tiempo expiró).' % messageInstance.receiver)
					# Eliminamos la instancia de mensaje, dado que ya no está en el buffer de transmisión
					del messageInstance
			# Para que el bloque 'try' (en la funcion 'get') no se quede esperando indefinidamente
			except Queue.Empty:
				pass
		logger.write('WARNING', '[TRANSMITTER] Funcion \'%s\' terminada.' % inspect.stack()[0][3])

	def trySend(self, messageInstance):
		# Establecemos el orden jerárquico de los medios de comunicación
		self.setPriorities(messageInstance.receiver, messageInstance.media)
		# Hacemos una copia de los campos del objeto
		media = messageInstance.media
		timeStamp = messageInstance.timeStamp
		timeToLive = messageInstance.timeToLive
		# Eliminamos los campos del objeto, ya que el receptor no los necesita
		delattr(messageInstance, 'media')
		delattr(messageInstance, 'timeStamp')
		delattr(messageInstance, 'timeToLive')
		# Intentamos enviar el mensaje por todos los medios disponibles
		if not self.send(messageInstance):
			# Insertamos nuevamente los campos eliminados para manejar el próximo envío
			setattr(messageInstance, 'media', media)
			setattr(messageInstance, 'timeStamp', timeStamp)
			setattr(messageInstance, 'timeToLive', timeToLive)
			# Esperamos un tiempo ‘retryTime’ antes de un posterior reintento
			time.sleep(JSON_CONFIG["COMMUNICATOR"]["RETRY_TIME"])
			# Como el envío falló, se vuelve a colocar el mensaje en la cola
			self.transmissionQueue.put((messageInstance.priority, messageInstance), True)
		# Como el mensaje fue enviado con éxito, se lo elimina del sistema
		else:
			del messageInstance

	def setPriorities(self, receiver, media):
		self.gsmPriority = 0
		self.gprsPriority = 0
		self.wifiPriority = 0
		self.ethernetPriority = 0
		self.emailPriority = 0
		self.bluetoothPriority = 0
		self.ftpPriority = 0
		# Para GSM
		if contactList.allowedNumbers.has_key(receiver) and self.gsmInstance.isActive:
			# En caso de preferencia se da máxima prioridad
			if media == 'GSM':
				self.gsmPriority = 10
			else:
				self.gsmPriority = JSON_CONFIG["PRIORITY_LEVELS"]["GSM"]
		# Para GPRS
		if contactList.allowedHosts.has_key(receiver) and self.gprsInstance.isActive:
			# En caso de preferencia se da máxima prioridad
			if media == 'GPRS':
				self.gprsPriority = 10
			else:
				self.gprsPriority = JSON_CONFIG["PRIORITY_LEVELS"]["GPRS"]
		# Para WIFI
		if contactList.allowedHosts.has_key(receiver) and self.wifiInstance.isActive:
			# En caso de preferencia se da máxima prioridad
			if media == 'WIFI':
				self.wifiPriority = 10
			else:
				self.wifiPriority = JSON_CONFIG["PRIORITY_LEVELS"]["WIFI"]
		# Para ETHERNET
		if contactList.allowedHosts.has_key(receiver) and self.ethernetInstance.isActive:
			# En caso de preferencia se da máxima prioridad
			if media == 'ETHERNET':
				self.ethernetPriority = 10
			else:
				self.ethernetPriority = JSON_CONFIG["PRIORITY_LEVELS"]["ETHERNET"]
		# Para BLUETOOTH
		if contactList.allowedBtAddress.has_key(receiver) and self.bluetoothInstance.isActive:
			# En caso de preferencia se da máxima prioridad
			if media == 'BLUETOOTH':
				self.bluetoothPriority = 10
			else:
				self.bluetoothPriority = JSON_CONFIG["PRIORITY_LEVELS"]["BLUETOOTH"]
		# Para EMAIL
		if contactList.allowedEmails.has_key(receiver) and self.emailInstance.isActive:
			# En caso de preferencia se da máxima prioridad
			if media == 'EMAIL':
				self.emailPriority = 10
			else:
				self.emailPriority = JSON_CONFIG["PRIORITY_LEVELS"]["EMAIL"]
		#Para FTP
		if self.ftpInstance.isActive:
			if media == 'FTP':
				self.ftpPriority = 10
			else:
				self.ftpPriority = JSON_CONFIG["PRIORITY_LEVELS"]["FTP"]
		

	def send(self, messageInstance):
		priorities = [self.gprsPriority, self.emailPriority, self.wifiPriority, self.ethernetPriority, self.bluetoothPriority, self.ftpPriority]
		# Intentamos transmitir por GSM
		if all(self.gsmPriority != 0 and self.gsmPriority >= x for x in priorities):
			destinationNumber = contactList.allowedNumbers[messageInstance.receiver]
			if not self.gsmInstance.send(messageInstance, destinationNumber):
				logger.write('DEBUG', '[COMMUNICATOR-GSM] Falló. Reintentando con otro medio.')
				self.gsmPriority = 0              # Se descarta para la próxima selección
				return self.send(messageInstance) # Se reintenta con otro medio
			else:
				return True
		#priorities.remove(self.gsmPriority)
		# Intentamos transmitir por GPRS
		if all(self.gprsPriority != 0 and self.gprsPriority >= x for x in priorities):
			destinationHost, destinationTcpPort, destinationUdpPort = contactList.allowedHosts[messageInstance.receiver]
			if not self.gprsInstance.send(messageInstance, destinationHost, destinationTcpPort, destinationUdpPort):
				logger.write('DEBUG', '[COMMUNICATOR-GPRS] Falló. Reintentando con otro medio.')
				self.gprsPriority = 0             # Se descarta para la próxima selección
				return self.send(messageInstance) # Se reintenta con otro medio
			else:
				return True
		#priorities.remove(self.gprsPriority)
		# Intentamos transmitir por EMAIL
		if all(self.emailPriority != 0 and self.emailPriority >= x for x in priorities):
			destinationEmail = contactList.allowedEmails[messageInstance.receiver]
			if not self.emailInstance.send(messageInstance, destinationEmail):
				logger.write('DEBUG', '[COMMUNICATOR-EMAIL] Falló. Reintentando con otro medio.')
				self.emailPriority = 0            # Se descarta para la próxima selección
				return self.send(messageInstance) # Se reintenta con otro medio
			else:
				return True
		#priorities.remove(self.emailPriority)
		# Intentamos transmitir por WIFI
		if all(self.wifiPriority != 0 and self.wifiPriority >= x for x in priorities):
			destinationHost, destinationTcpPort, destinationUdpPort = contactList.allowedHosts[messageInstance.receiver]
			if not self.wifiInstance.send(messageInstance, destinationHost, destinationTcpPort, destinationUdpPort):
				logger.write('DEBUG', '[COMMUNICATOR-WIFI] Falló. Reintentando con otro medio.')
				self.wifiPriority = 0             # Se descarta para la próxima selección
				return self.send(messageInstance) # Se reintenta con otro medio
			else:
				return True
		#priorities.remove(self.wifiPriority)
		# Intentamos transmitir por ETHERNET
		if all(self.ethernetPriority != 0 and self.ethernetPriority >= x for x in priorities):
			destinationHost, destinationTcpPort, destinationUdpPort = contactList.allowedHosts[messageInstance.receiver]
			if not self.ethernetInstance.send(messageInstance, destinationHost, destinationTcpPort, destinationUdpPort):
				logger.write('DEBUG', '[COMMUNICATOR-ETHERNET] Falló. Reintentando con otro medio.')
				self.ethernetPriority = 0         # Se descarta para la próxima selección
				return self.send(messageInstance) # Se reintenta con otro medio
			else:
				return True
		#priorities.remove(self.ethernetPriority)
		# Intentamos transmitir por BLUETOOTH
		if all(self.bluetoothPriority != 0 and self.bluetoothPriority >= x for x in priorities):
			destinationServiceName, destinationMAC, destinationUUID = contactList.allowedBtAddress[messageInstance.receiver]
			if not self.bluetoothInstance.send(messageInstance, destinationServiceName, destinationMAC, destinationUUID):
				logger.write('DEBUG', '[COMMUNICATOR-BLUETOOTH] Falló. Reintentando con otro medio.')
				self.bluetoothPriority = 0        # Entonces se descarta para la proxima selección
				return self.send(messageInstance) # Se reintenta con otro medio
			else:
				return True
		#Intentamos transmitir por FTP
		if self.ftpPriority != 0:
			if not self.ftpInstance.send(messageInstance):
				logger.write('DEBUG', '[COMMUNICATOR-FTP] Fallo. Reintentando con otro medio.')
				self.ftpPriority = 0
				return self.send(messageInstance)
			else:
				return True			
		# No fue posible transmitir por ningún medio
		else:
			logger.write('WARNING', '[COMMUNICATOR] No hay módulos para el envío a \'%s\'...' % messageInstance.receiver)
			return False
