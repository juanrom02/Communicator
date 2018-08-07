
import ftplib
import json
import time
import tempfile
import pickle
import logger
import os
import shutil
import threading
import serial
import socket
import traceback #DBG

import messageClass

JSON_FILE = 'config.json'
JSON_CONFIG = json.load(open(JSON_FILE))

ATTACHMENTS = 'Attachments'

class Ftp(object):
	
	ftpServer = ftplib.FTP
	ftpHost = None
	ftpPort = None
	ftpUser = None
	ftpPassword = None
	ftpDirectory = None
	
	communicatorName = None
	receptionQueue = None
	
	gsmInstance = None
	telit_lock = None
	ftp_mode = 1
	
	isActive = False
	
	def __init__(self, _receptionQueue):
		self.receptionQueue = _receptionQueue
		self.ftpHost = JSON_CONFIG["FTP"]["FTP_SERVER"]
		self.ftpPort = JSON_CONFIG["FTP"]["FTP_PORT"]
		self.ftpUser = JSON_CONFIG["FTP"]["USER"]
		self.ftpPassword = JSON_CONFIG["FTP"]["PASSWORD"]
		self.ftpDirectory = JSON_CONFIG["FTP"]["DIRECTORY"]
		self.communicatorName = str(JSON_CONFIG["COMMUNICATOR"]["NAME"])
		
	def connect(self):
		try:
			if self.ftp_mode == 2:
				self.telit_lock.acquire()
				while self.gsmInstance.active_call:
					self.telit_lock.wait()
				ftpOpen = 'AT#FTPOPEN="%s:%s","%s","%s",1' % (self.ftpHost, self.ftpPort, self.ftpUser, self.ftpPassword)
				self.gsmInstance.sendAT(ftpOpen.encode('utf-8'), wait=5)
				self.gsmInstance.sendAT(('AT#FTPCWD="%s"' % self.ftpDirectory).encode('utf-8'), wait=5)
			else:
				self.ftpServer = ftplib.FTP(self.ftpHost, self.ftpUser, self.ftpPassword, timeout = 10)
				self.ftpServer.cwd(self.ftpDirectory)
			return True
		except (socket.timeout, ftplib.error_perm, serial.serialutil.SerialException):
			if self.isActive:
				#print traceback.format_exc()
				logger.write('WARNING', '[FTP] La conexion con el servidor ha fallado (%s).' % self.ftpHost)
				self.isActive = False
			raise	
		
	def send(self, message, changeName = True):
		try:
			timestamp = time.localtime()
			day = str(timestamp.tm_year).zfill(4) + str(timestamp.tm_mon).zfill(2) + str(timestamp.tm_mday).zfill(2)
			hour = str(timestamp.tm_hour).zfill(2) + str(timestamp.tm_min).zfill(2) + str(timestamp.tm_sec).zfill(2)
			if isinstance(message, messageClass.InfoMessage):
				fileName = message.receiver + ".-instance.-" + message.sender + '.-' + day + '.-' + hour
				serialized = pickle.dumps(message)
				tf = tempfile.NamedTemporaryFile(delete=False)
				tf.name = fileName
				tf.write('INSTANCE' + serialized)
				tf.seek(0)
			elif isinstance(message, messageClass.Message) and hasattr(message, 'plainText'):
				fileName = message.receiver + ".-text.-" + message.sender + '.-' + day + '.-' + hour 
				tf = tempfile.NamedTemporaryFile(delete=False)
				tf.name = fileName
				tf.write(message.plainText)
				tf.seek(0)
			elif isinstance(message, messageClass.Message) and hasattr(message, 'fileName'):
				absoluteFilePath = os.path.abspath(message.fileName)
				archivo = open(absoluteFilePath, 'rb')
				fileDirectory, fileName = os.path.split(absoluteFilePath)
				if changeName:
					nombre = message.receiver + '.-' + fileName + '.-' + message.sender + '.-' + day + '.-' + hour 
				else:
					nombre = fileName
				return self.sendFile(archivo, nombre)
			return self.sendFile(tf)
		except:
			print traceback.format_exc()	
			return False
		
	def sendFile(self, archivo, nombre = None):
		try:
			self.connect()
			if nombre == None:
				fileDirectory, nombre = os.path.split(archivo.name)
			if self.ftp_mode == 2:
				self.gsmInstance.sendAT(('AT#FTPPUT="%s"' % nombre).encode('utf-8'), 'CONNECT', 5)
				self.gsmInstance.sendAT(archivo.read(), None, mode=0)
				time.sleep(2)
				self.gsmInstance.sendAT('+++', 'NO CARRIER', 10, 0)
				self.gsmInstance.sendAT('AT#FTPCLOSE'.encode('utf-8'), wait=5)
				self.telit_lock.release()
			else:
				self.ftpServer.storbinary('STOR ' + nombre, archivo)
				self.ftpServer.quit()
			archivo.close()
			logger.write('INFO','[FTP] Mensaje subido al servidor.')
			return True
		except ftplib.error_perm: #DBG: Falta especificar
			print traceback.format_exc()
			return False
		#~ except:
			#~ print traceback.format_exc()
		
	def receive(self, fileName):
		try:
			tf = tempfile.NamedTemporaryFile(delete = False)
			tf.name = fileName
			if self.ftp_mode == 2:
				self.gsmInstance.sendAT(('AT#FTPGET="%s"' % fileName).encode('utf-8'), 'CONNECT', 5)
				output = self.gsmInstance.sendAT('', 'NO CARRIER', 30, 0)
				tf.write(''.join(output[:-1]))
			else:
				self.ftpServer.retrbinary('RETR %s' % fileName, tf.write)
			tf.seek(0)
			origin = ''
			if fileName.startswith(self.communicatorName):
				elements = fileName.split('.-')
				fileName = elements[1]
				origin = 'de ' + elements[2]
				print "%s" % fileName
			if fileName.startswith('text'):
				message = tf.read()
				self.receptionQueue.put((10, message))
				logger.write('INFO','[FTP] Mensaje %s recibido correctamente!' % origin)
			elif fileName.startswith('instance'):
				serializedMessage = tf.read()
				messageInstance = pickle.loads(serializedMessage[len('INSTANCE'):])
				self.receptionQueue.put((messageInstance.priority, messageInstance))
				logger.write('INFO','[FTP] Instancia %s recibida correctamente!' % origin)
			else:
				currentDirectory = os.getcwd()
				filePath = os.path.join(currentDirectory, ATTACHMENTS, fileName)
				if ATTACHMENTS not in os.listdir(currentDirectory):
					os.mkdir(ATTACHMENTS)
				if not os.path.isfile(filePath):
					archivo = open(filePath, 'w+')
					shutil.copyfileobj(tf, archivo)
					logger.write('INFO','[FTP] Archivo %s descargado correctamente!' % fileName)
				else:
					logger.write('WARNING','[FTP] El archivo %s ya existe! Imposible descargar.' % fileName)
					tf.close()
					return False				
			tf.close()
			return True				
		except:
			print traceback.format_exc()
			tf.close()
			raise
