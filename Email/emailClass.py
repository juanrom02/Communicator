 # coding=utf-8

import os
import json
import shlex
import email
import pickle
import socket
import inspect
import smtplib
import imaplib
import mimetypes
import subprocess
import communicator
import base64
import traceback
import regex
import threading
import serial
import time #DBG

from email import encoders
from email.header import decode_header
from email.header import make_header

from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.audio import MIMEAudio
from email.mime.image import MIMEImage

import logger
import contactList
import messageClass
from modemClass import ATCommandError

JSON_FILE = 'config.json'
JSON_CONFIG = json.load(open(JSON_FILE))

TIMEOUT = 10
ATTACHMENTS = 'Attachments'

class Email(object):

	smtpServer = smtplib.SMTP
	imapServer = imaplib.IMAP4_SSL

	successfulConnection = False
	receptionQueue = None
	isActive = False
	
	smtpHost = None
	smtpPort = None
	imapHost = None
	imapPort = None
	emailPassword = None
	emailAccount = None
	clientName = None
	threadName = None
	thread = None
	
	gsmInstance = None
	controllerInstance = None
	
	telit_lock = None
	mode = 1

	def __init__(self, _receptionQueue):
		self.receptionQueue = _receptionQueue
		# Establecemos tiempo maximo antes de reintentar lectura (válido para 'imapServer')
		socket.setdefaulttimeout(TIMEOUT)
		self.smtpHost = JSON_CONFIG["EMAIL"]["SMTP_SERVER"]
		self.smtpPort = JSON_CONFIG["EMAIL"]["SMTP_PORT"]
		self.imapHost = JSON_CONFIG["EMAIL"]["IMAP_SERVER"]
		self.imapPort = JSON_CONFIG["EMAIL"]["IMAP_PORT"]
		self.emailPassword = JSON_CONFIG["EMAIL"]["PASSWORD"]
		self.emailAccount = JSON_CONFIG["EMAIL"]["ACCOUNT"]
		self.clientName = JSON_CONFIG["COMMUNICATOR"]["NAME"]
		self.thread = threading.Thread(target = self.receive, name = self.threadName)

	def close(self):
		try:
			if self.gsmInstance.telitConnected: 
				self.telit_lock.acquire()
				while self.gsmInstance.active_call:
					self.telit_lock.wait()
				self.gsmInstance.sendAT('AT#SSLH=1')
				self.telit_lock.release()
			else:
				self.smtpServer.quit()   # Terminamos la sesión SMTP y cerramos la conexión
				self.smtpServer.close()  # Cerramos el buzón seleccionado actualmente
				self.imapServer.logout() # Cerramos la conexión IMAP
		except:
			pass
		finally:
			logger.write('INFO','[EMAIL] Objeto destruido.' )

	def connect(self, mode = 1):
		self.mode = mode
		try:
			if mode in [1,2]:
				self.smtpServer = smtplib.SMTP_SSL(self.smtpHost, self.smtpPort, timeout = 30) # Establecemos servidor y puerto SMTP
				self.imapServer = imaplib.IMAP4_SSL(self.imapHost, self.imapPort) # Establecemos servidor y puerto IMAP
				self.smtpServer.ehlo()
				#self.smtpServer.starttls()
				#self.smtpServer.ehlo()
				self.smtpServer.login(self.emailAccount, self.emailPassword) # Nos logueamos en el servidor SMTP
				self.imapServer.login(self.emailAccount, self.emailPassword) # Nos logueamos en el servidor IMAP
				self.imapServer.select('INBOX')                         # Seleccionamos la Bandeja de Entrada
			else:
				self.telit_lock.acquire()
				while self.gsmInstance.active_call:
					self.telit_lock.wait()
				self.telitIMAPConnect()
				self.telit_lock.release()
			self.successfulConnection = True
			return True
		# Error con los servidores (probablemente estén mal escritos o los puertos son incorrectos)
		except (Exception, ATCommandError):
			print traceback.format_exc()
			logger.write('ERROR', '[EMAIL] Error al intentar conectar con los servidores SMTP e IMAP.')
			self.successfulConnection = False
			return False
		
	def sendSSLCommand(self, command, expected = None):
		try:
			self.gsmInstance.sendAT('AT#SSLSEND=1', '>', 1)
			self.gsmInstance.sendAT((command + '\r\n\x1A').encode('utf-8'), 'SSLSRING', 30)
			response = self.gsmInstance.sendAT('AT#SSLRECV=1,1000', expected, 5)
			return response
		except (serial.serialutil.SerialException, ATCommandError):
			raise
		
	def telitIMAPConnect(self):
		try:
			self.gsmInstance.sendAT(('AT#SSLD=1,%s,"%s",0,1' % (self.imapPort,self.imapHost)).encode('utf-8'), 'SSLSRING', 30)
			self.gsmInstance.sendAT('AT#SSLRECV=1,1000'.encode('utf-8'), 'OK', 2)
			self.sendSSLCommand('. LOGIN %s %s' % (self.emailAccount,self.emailPassword), '. OK')
		except:
			if self.isActive:
				logger.write('INFO', '[EMAIL] Se ha desconectado el medio (%s).' % self.emailInstance.emailAccount)
				logger.write('DEBUG', '[EMAIL] %s : %s.' % (type(error).__name__, error))
				self.successfulConnection = None
				self.isActive = False
				self.thread = threading.Thread(target = self.receive, name = self.threadName)
		
	def send(self, message, emailDestination):
		# Comprobación de envío de texto plano
		if isinstance(message, messageClass.Message) and hasattr(message, 'plainText'):
			mimeText = MIMEText(message.plainText, 'plain')
			mimeText['From'] = '%s <%s>' % (self.clientName, self.emailAccount)
			mimeText['To'] = emailDestination
			mimeText['Subject'] = JSON_CONFIG["EMAIL"]["SUBJECT"]
			return self.sendMessage(mimeText)
		# Comprobación de envío de archivo
		elif isinstance(message, messageClass.Message) and hasattr(message, 'fileName'):
			mimeMultipart = MIMEMultipart()
			mimeMultipart['From'] = '%s <%s>' % (self.clientName, self.emailAccount)
			mimeMultipart['To'] = emailDestination
			mimeMultipart['Subject'] = JSON_CONFIG["EMAIL"]["SUBJECT"]
			absoluteFilePath = os.path.abspath(message.fileName)
			fileDirectory, fileName = os.path.split(absoluteFilePath)
			cType = mimetypes.guess_type(absoluteFilePath)[0]
			mainType, subType = cType.split('/', 1)
			if mainType == 'text':
				fileObject = open(absoluteFilePath)
				# Note: we should handle calculating the charset
				attachmentFile = MIMEText(fileObject.read(), _subtype = subType)
				fileObject.close()
			elif mainType == 'image':
				fileObject = open(absoluteFilePath, 'rb')
				attachmentFile = MIMEImage(fileObject.read(), _subtype = subType)
				fileObject.close()
			elif mainType == 'audio':
				fileObject = open(absoluteFilePath, 'rb')
				attachmentFile = MIMEAudio(fileObject.read(), _subtype = subType)
				fileObject.close()
			else:
				fileObject = open(absoluteFilePath, 'rb')
				attachmentFile = MIMEBase(mainType, subType)
				attachmentFile.set_payload(fileObject.read())
				fileObject.close()
				# Codificamos el payload (carga útil) usando Base64
				encoders.encode_base64(attachmentFile)
			# Agregamos una cabecera al email, de nombre 'Content-Disposition' y valor 'attachment' ('filename' es el parámetro)
			attachmentFile.add_header('Content-Disposition', 'attachment', filename = fileName)
			#mimeText = MIMEText(messageToSend, _subtype = 'plain')
			mimeMultipart.attach(attachmentFile)
			return self.sendMessage(mimeMultipart)
		# Entonces se trata de enviar una instancia de mensaje
		else:
			# Serializamos el objeto para poder transmitirlo
			serializedMessage = 'INSTANCE' + pickle.dumps(message)
			# Se construye un mensaje simple
			mimeText = MIMEText(serializedMessage)
			mimeText['From'] = '%s <%s>' % (self.clientName, self.emailAccount)
			mimeText['To'] = emailDestination
			mimeText['Subject'] = JSON_CONFIG["EMAIL"]["SUBJECT"]
			return self.sendMessage(mimeText)

	def sendMessage(self, mime):
		try:
			if self.gsmInstance.telitConnected:
				self.telit_lock.acquire()
				while self.gsmInstance.active_call:
					self.telit_lock.wait()
				self.sendSSLCommand('. LOGOUT', 'NO CARRIER')
				self.gsmInstance.sendAT(('AT#SSLD=1,%s,"%s",0,1' % (self.smtpPort,self.smtpHost)).encode('utf-8'),'SSLSRING', 10)
				self.gsmInstance.sendAT('AT#SSLRECV=1,1000'.encode('utf-8'), '220', 10)
				self.sendSSLCommand('EHLO %s' % self.clientName, '250 ')
				self.sendSSLCommand('AUTH LOGIN', '334')
				self.sendSSLCommand(base64.b64encode(self.emailAccount), '334')
				self.sendSSLCommand(base64.b64encode(self.emailPassword), '235')
				self.sendSSLCommand('MAIL FROM: <%s>' % self.emailAccount, '250')
				self.sendSSLCommand('RCPT TO: <%s>' % mime['To'], '250')
				self.sendSSLCommand('DATA', '354')
				self.gsmInstance.sendAT('AT#SSLO=1'.encode('utf-8'))
				self.gsmInstance.sendAT((mime.as_string() + '\r\n\x2E\r\n').encode('utf-8'), '250', 30)
				self.gsmInstance.sendAT('+++', 'OK', 10, 0)
				self.sendSSLCommand('ABC', '502')
				self.sendSSLCommand('QUIT', '221')
			else:
				self.smtpServer.sendmail(mime['From'], mime['To'], mime.as_string())
			logger.write('INFO', '[EMAIL] Mensaje enviado a \'%s\'' % mime['To'])
			return True
		except Exception as errorMessage:
			logger.write('WARNING', '[EMAIL] Mensaje no enviado: %s' % str(errorMessage))
			return False
		except ATCommandError:
			logger.write('ERROR', '[EMAIL] Mensaje no enviado: fallo en los comandos AT.')
		finally:
			if self.gsmInstance.telitConnected:
				self.gsmInstance.sendAT('AT#SSLH=1')
				self.telitIMAPConnect()
				self.telit_lock.release()

	def receive(self):
 		self.isActive = True
 		punito = 1.0 #DBG
 		try:
			while self.isActive:
				emailIdsList = list()
				# Mientras no se haya recibido ningun correo electronico, el temporizador no haya expirado y no se haya detectado movimiento...
				while len(emailIdsList) == 0 and self.isActive:
					if self.mode in [1,2]:
						self.imapServer.recent() # Actualizamos la Bandeja de Entrada
						result, emailIds = self.imapServer.uid('search', None, '(UNSEEN)') # Buscamos emails sin leer (nuevos)
						emailIdsList = emailIds[0].split()
					else:
						self.telit_lock.acquire()
						while self.gsmInstance.active_call:
							self.telit_lock.wait()
						self.punito = time.time() #DBG
						self.sendSSLCommand('. SELECT INBOX', '. OK')
						result = self.sendSSLCommand('. SEARCH UNSEEN', '. OK')
						self.telit_lock.release()
						emailIdsList = regex.findall('[0-9]+',result[2])
				# Si no se terminó la función (el modo EMAIL no dejó de funcionar), leemos los mensajes recibidos...
				if self.isActive or len(emailIdsList) != 0:
					emailAmount = len(emailIdsList)
					logger.write('DEBUG', '[EMAIL] Ha(n) llegado ' + str(emailAmount) + ' nuevo(s) mensaje(s) de correo electronico!')
					# Recorremos los emails recibidos...
					for emailId in emailIdsList:
						if self.mode in [1,2]:
							result, emailData = self.imapServer.uid('fetch', emailId, '(RFC822)')
							emailReceived = email.message_from_string(emailData[0][1])
							# Retorna un objeto 'message', y podemos acceder a los items de su cabecera como un diccionario.'
							#~ print emailData[0][1]
							#~ emailReceived = email.message_from_string(emailData[0][1])
						else:
							self.telit_lock.acquire()
							while self.gsmInstance.active_call:
								self.telit_lock.wait()
							self.gsmInstance.sendAT('AT#SSLO=1')
							fetch = self.gsmInstance.sendAT(('. FETCH %s RFC822' % emailId).encode('utf-8'), '. OK', 30, 2)
							emailData = ''.join(fetch[1:-2])
							self.gsmInstance.sendAT('+++', 'OK', 10, 0)
							self.telit_lock.release()
							emailReceived = email.message_from_string(emailData)
						sourceName = self.getSourceName(emailReceived)     # Almacenamos el nombre del remitente
						sourceEmail = self.getSourceEmail(emailReceived)   # Almacenamos el correo del remitente
						emailSubject = self.getEmailSubject(emailReceived) # Almacenamos el asunto correspondiente
						logger.write('DEBUG', '[EMAIL] Procesando correo de \'%s\'' % sourceEmail)
						# Comprobamos si el remitente del mensaje (un correo) está registrado...
						if sourceEmail in contactList.allowedEmails.values() or not JSON_CONFIG["COMMUNICATOR"]["RECEPTION_FILTER"]:
							for emailHeader in emailReceived.walk():
								if emailHeader.get('Content-Disposition') is not None:
									self.receiveAttachment(emailHeader)
							emailBody = self.getEmailBody(emailReceived) # Obtenemos el cuerpo del email
							if emailBody is not None:
								#self.sendOutput(sourceEmail, emailSubject, emailBody) # -----> SOLO PARA LA DEMO <-----
								if emailBody.startswith('INSTANCE'):
									# Quitamos la 'etiqueta' que hace refencia a una instancia de mensaje
									serializedMessage = emailBody[len('INSTANCE'):]
									# 'Deserializamos' la instancia de mensaje para obtener el objeto en sí
									messageInstance = pickle.loads(serializedMessage)
									self.receptionQueue.put((messageInstance.priority, messageInstance))
									end = time.time()
									print ('Lectura de MAIL demora ' + str(end - self.punito) + '\r\n') #DBG
									logger.write('INFO', '[EMAIL] Ha llegado una nueva instancia de mensaje!')
								else:
									emailBody = emailBody[:emailBody.rfind('\r\n')] # Elimina el salto de línea del final
									self.receptionQueue.put((10, emailBody))
									end = time.time()
									print ('Lectura de MAIL demora ' + str(end - self.punito) + '\r\n') #DBG
									logger.write('INFO', '[EMAIL] Ha llegado un nuevo mensaje!')
						else:
							logger.write('WARNING', '[EMAIL] Imposible procesar la solicitud. El correo no se encuentra registrado!')
							messageToSend = 'Imposible procesar la solicitud. Usted no se encuentra registrado!'
							self.sendMessage(messageToSend, sourceEmail)
						# Eliminamos el mensaje de la bandeja de entrada porque ya fue leído
						#self.deleteEmail(emailId) #DBG
				# ... sino, dejamos de esperar mensajes
				else:
					break
		except (serial.serialutil.SerialException, Exception) as message:
			logger.write('INFO', '[EMAIL] Se ha desconectado el medio (%s).' % self.emailAccount)
			logger.write('DEBUG', '[EMAIL] %s : %s' % (type(message).__name__, message))
		except ATCommandError:
			logger.write('WARNING', '[EMAIL] Recepcion fallida: error en los comandos AT.')
		finally:
			print traceback.format_exc()
			self.successfulConnection = False
			self.isActive = False
			self.thread = threading.Thread(target = self.receive, name = self.threadName)
			logger.write('WARNING', '[EMAIL] Función \'%s\' terminada.' % inspect.stack()[0][3])

	def receiveAttachment(self, emailHeader):
		# Obtenemos el directorio actual de trabajo
		currentDirectory = os.getcwd()
		# Obtenemos el nombre del archivo adjunto
		fileName = emailHeader.get_filename()
		# Obtenemos el path relativo del archivo a descargar
		filePath = os.path.join(currentDirectory, ATTACHMENTS, fileName)
		# Verificamos si el directorio 'ATTACHMENTS' no está creado en el directorio actual
		if ATTACHMENTS not in os.listdir(currentDirectory):
			os.mkdir(ATTACHMENTS)
		# Verificamos si el archivo a descargar no existe en la carpeta 'ATTACHMENTS'
		if not os.path.isfile(filePath):
			fileObject = open(filePath, 'w+')
			fileObject.write(emailHeader.get_payload(decode = True))
			fileObject.close()
			self.receptionQueue.put((10, fileName))
			logger.write('INFO', '[EMAIL] Archivo adjunto \'%s\' descargado correctamente!' % fileName)
			return True
		else:
			logger.write('WARNING', '[EMAIL] El archivo \'%s\' ya existe! Imposible descargar.' % fileName)
			return False

	def getSourceName(self, emailReceived):
		sourceNameList = list()
		decodedHeader = decode_header(emailReceived.get('From'))
		senderInformation = unicode(make_header(decodedHeader)).encode('utf-8')
		# Ejemplo de senderInformation: Mauricio Gonzalez <mauriciolg.90@gmail.com>
		for senderElement in senderInformation.split():
			if not senderElement.startswith('<') and not senderElement.endswith('>'):
				sourceNameList.append(senderElement)
		# Ejemplo de sourceNameList: ['Mauricio', 'Gonzalez']
		sourceName = ' '.join(sourceNameList)
		# Ejemplo de sourceName: Mauricio Gonzalez
		return sourceName

	def getSourceEmail(self, emailReceived):
		sourceEmail = None
		decodedHeader = decode_header(emailReceived.get('From'))
		senderInformation = unicode(make_header(decodedHeader)).encode('utf-8')
		# Ejemplo de senderInformation: Mauricio Gonzalez <mauriciolg.90@gmail.com>
		for senderElement in senderInformation.split():
			if senderElement.startswith('<') and senderElement.endswith('>'):
				sourceEmail = senderElement.replace('<', '').replace('>', '')
		# Ejemplo sourceEmail: mauriciolg.90@gmail.com
		return sourceEmail
		
	def getEmailSubject(self, emailReceived):
		decodedHeader = decode_header(emailReceived.get('subject'))
		return unicode(make_header(decodedHeader)).encode('utf-8')

	def getEmailBody(self, emailReceived):
		plainText = None
		for emailHeader in emailReceived.walk():
			if emailHeader.get_content_type() == 'text/plain':
				plainText = emailHeader.get_payload()
				# Se debe convertir texto de DOS(windows) a UNIX (LINUX) porque 
				# de la forma que lo devulve email, da errores en pickle
				plainText = plainText.replace('\r\n', '\n')
				break
		# Si el cuerpo del email no está vacío, retornamos el texto plano
		if plainText:
			return plainText
		else:
			return None

	def deleteEmail(self, emailId):
		if self.gsmInstance.telitConnected:
			self.sendSSLCommand('. STORE %s +FLAGS \x5CDeleted' % emailId)
			self.sendSSLCommand('. EXPUNGE')
		else:
			self.imapServer.store(emailId, '+FLAGS', '\\Deleted')
			self.imapServer.expunge()

	def sendOutput(self, sourceEmail, emailSubject, emailBody):
		try:
			unixProcess = subprocess.Popen(shlex.split(emailBody), stdout = subprocess.PIPE, stderr = subprocess.PIPE)
			unixOutput, unixError = unixProcess.communicate()
			if len(unixOutput) > 0:
				emailBody = unixOutput[:unixOutput.rfind('\n')] # Quita la ultima linea en blanco
			else:
				emailBody = unixError[:unixError.rfind('\n')] # Quita la ultima linea en blanco
		except OSError as e: # El comando no fue encontrado (el ejecutable no existe)
			emailBody = str(e)
		finally:
			# Enviamos la respuesta del SO al remitente
			self.sendMessage(emailBody, sourceEmail)
