# coding=utf-8

import os
import time
import pickle
import bluetooth

import logger
import messageClass
import traceback

BUFFER_SIZE = 4096 # Tamano del buffer en bytes (cantidad de caracteres)

class BluetoothTransmitter():

	def __init__(self):
		pass

	def send(self, message, clientSocket):
		# Comprobación de envío de texto plano
		if isinstance(message, messageClass.Message) and hasattr(message, 'plainText'):
			return self.sendMessage(message.plainText, clientSocket)
		# Comprobación de envío de archivo
		elif isinstance(message, messageClass.Message) and hasattr(message, 'fileName'):
			return self.sendFile(message.fileName, clientSocket)
		# Entonces se trata de enviar una instancia de mensaje
		else:
			return self.sendMessageInstance(message, clientSocket)

	def sendMessage(self, plainText, clientSocket):
		try:
			clientSocket.send(plainText)
			logger.write('INFO', '[BLUETOOTH] Mensaje enviado correctamente!')
			return True
		except Exception as errorMessage:
			logger.write('WARNING', '[BLUETOOTH] Mensaje no enviado: %s' % str(errorMessage))
			return False
		finally:
			# Cierra la conexion del socket cliente
			clientSocket.close()

	def sendFile(self, fileName, clientSocket):
		try:
			absoluteFilePath = os.path.abspath(fileName)
			fileDirectory, fileName = os.path.split(absoluteFilePath)
			fileObject = open(absoluteFilePath, 'rb')
			clientSocket.send('START_OF_FILE')
			clientSocket.recv(BUFFER_SIZE) # ACK
			clientSocket.send(fileName) # Enviamos el nombre del archivo
			# Recibe confirmación para comenzar a transmitir (READY)
			if clientSocket.recv(BUFFER_SIZE) == "READY":
				# Guardamos la posición inicial del archivo (donde comienza)
				fileBeginning = fileObject.tell()
				# Apuntamos al final del archivo
				fileObject.seek(0, os.SEEK_END)
				# Obtenemos la posición final del mismo (que sería el tamaño)
				fileSize = fileObject.tell()
				# Apuntamos nuevamente al comienzo del archivo, para comenzar a transmitir
				fileObject.seek(fileBeginning, os.SEEK_SET)
				# Envio del contenido del archivo
				bytesSent = 0
				logger.write('DEBUG', '[BLUETOOTH] Transfiriendo archivo \'%s\'...' % fileName)
				while bytesSent < fileSize:
					outputData = fileObject.read(BUFFER_SIZE)
					clientSocket.send(outputData)
					bytesSent += len(outputData)
					clientSocket.recv(BUFFER_SIZE) # ACK
				fileObject.close()
				clientSocket.send('EOF')
				clientSocket.recv(BUFFER_SIZE) # IMPORTANTE ACK, no borrar.
				logger.write('INFO', '[BLUETOOTH] Archivo \'%s\' enviado correctamente!' % fileName)
				return True
			# Recibe 'FILE_EXISTS'
			else:
				logger.write('WARNING', '[BLUETOOTH] El archivo \'%s\' ya existe, fue rechazado!' % fileName)
				return True # Para que no se vuelva a intentar el envio. El control esta en la notificación		
		except Exception as errorMessage:
			print traceback.format_exc() #DBG
			logger.write('WARNING', '[BLUETOOTH] Archivo \'%s\' no enviado: %s' % (fileName, str(errorMessage)))
			return False
		finally:
			# Cierra la conexion del socket cliente
			clientSocket.close()

	def sendMessageInstance(self, message, clientSocket):
		try:
			# Serializamos el objeto para poder transmitirlo
			serializedMessage = 'INSTANCE' + pickle.dumps(message)
			# Transmitimos la instancia serializada al destino correspondiente
			clientSocket.send(serializedMessage)
			logger.write('INFO', '[BLUETOOTH] Instancia de mensaje enviada correctamente!')
			return True
		except Exception as errorMessage:
			logger.write('WARNING', '[BLUETOOTH] Instancia de mensaje no enviada: %s' % str(errorMessage))
			return False
		finally:
			# Cierra la conexion del socket cliente
			clientSocket.close()
