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
import modemClass
import base64
import traceback

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

JSON_FILE = 'config.json'
JSON_CONFIG = json.load(open(JSON_FILE))

TIMEOUT = 5
ATTACHMENTS = 'Attachments'

class Email(object):

	smtpServer = smtplib.SMTP
	imapServer = imaplib.IMAP4_SSL

	successfulConnection = None
	receptionQueue = None
	isActive = False
	telitConnected = None
	
	smtpHost = None
	smtpPort = None
	imapHost = None
	imapPort = None
	emailPassword = None
	emailAccount = None
	clientName = None

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

	def __del__(self):
		try:
			self.smtpServer.quit()   # Terminamos la sesión SMTP y cerramos la conexión
			self.smtpServer.close()  # Cerramos el buzón seleccionado actualmente
			self.imapServer.logout() # Cerramos la conexión IMAP
		except:
			pass
		finally:
			logger.write('INFO','[EMAIL] Objeto destruido.' )

	def connect(self, telit):
		try:
			if not telit and not self.testConnection():
				self.smtpServer = smtplib.SMTP(self.smtpHost, self.smtpPort, timeout = 30) # Establecemos servidor y puerto SMTP
				self.imapServer = imaplib.IMAP4_SSL(self.imapHost, self.imapPort)          # Establecemos servidor y puerto IMAP
				self.smtpServer.ehlo()
				self.smtpServer.starttls()
				self.smtpServer.ehlo()
				self.smtpServer.login(self.emailAccount, self.emailPassword) # Nos logueamos en el servidor SMTP
				self.imapServer.login(self.emailAccount, self.emailPassword) # Nos logueamos en el servidor IMAP
				self.imapServer.select('INBOX')                         # Seleccionamos la Bandeja de Entrada
				self.telitConnected = False
			elif not self.testTelitConnection():
				self.telitIMAPConnect()
				self.telitConnected = True
			self.successfulConnection = True
			return True
		# Error con los servidores (probablemente estén mal escritos o los puertos son incorrectos)
		except Exception as errorMessage:
			print traceback.format_exc()
			logger.write('ERROR', '[EMAIL] Error al intentar conectar con los servidores SMTP e IMAP - %s' % errorMessage)
			self.successfulConnection = False
			return False
			
	def testConnection(self):
		try:
			self.smtpServer.noop()
			self.imapServer.noop()
			return True
		except smtplib.SMTPServerDisconnected, imaplib.IMAP4.error:
			return False
		except TypeError:
			return False
	
	def testTelitConnection(self):
		try:
			self.sendTelitCommand('. NOOP', '. OK')
			return True
		except:
			return False		
		
	def sendTelitCommand(self, command, expected):
		response = modemClass.sendAT(command + '\r')
		for line in response:
			if line.startswith(expected):
				return response
		raise Exception(' Telit: %s' % command)
		
	def telitSMTPConnect(self):
		self.sendTelitCommand('AT#SSLD=1,%s,"%s",0,0' % (self.smtpPort,self.smtpHost),'CONNECT')
		self.sendTelitCommand('EHLO %s' % self.clientName, '250-%s' % self.smtpHost)
		self.sendTelitCommand('AUTH LOGIN', '334')
		self.sendTelitCommand(base64.b64encode(self.emailAccount), '334')
		self.sendTelitCommand(base64.b64encode(self.emailPassword), '235')
		
	def telitIMAPConnect():
		self.sendTelitCommand('AT#SSLD=1,%s,"%s",0,0' % (self.imapPort,self.imapHost), 'CONNECT')				
		self.sendTelitCommand('. LOGIN %s %s' % (self.emailAccount,self.emailPassword), '. OK')
		self.sendTelitCommand('. SELECT INBOX', '. OK')	

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
			return self.sendMessage(mimeMultipart, telitConnected)
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
			if self.telitConnected:
				self.sendTelitCommand('. LOGOUT', '. OK')
				self.telitSMTPConnect()
				self.sendTelitCommand('MAIL FROM: %s' % self.emailAccount, '250')
				self.sendTelitCommand('RCPT TO: %s' % mime['To'], '250')
				self.sendTelitCommand('DATA', '354')
				self.sendTelitCommand(mime.as_string(), '250')
				self.sendTelitCommand('QUIT', '221')
				self.telitIMAPConnect()
			else:
				self.smtpServer.sendmail(mime['From'], mime['To'], mime.as_string())
			logger.write('INFO', '[EMAIL] Mensaje enviado a \'%s\'' % mime['To'])
			return True
		except Exception as errorMessage:
			logger.write('WARNING', '[EMAIL] Mensaje no enviado: %s' % str(errorMessage))
			return False

	#~ def sendAttachment(self, relativeFilePath, emailDestination, messageToSend = 'Este email tiene un archivo adjunto.'):
		#~ try:
#~ 
			#~ #mimeMultipart.attach(mimeText)
			#~ if telitConnected:
				#~ self.sendTelitCommand('. LOGOUT', '. OK')
				#~ self.telitSMTPConnect()
				#~ self.sendTelitCommand('MAIL FROM: %s' % self.emailAccount, '250')
				#~ self.sendTelitCommand('RCPT TO: %s' % emailDestination, '250')
				#~ self.sendTelitCommand('DATA', '354')
				#~ self.sendTelitCommand(mimeMutlipart.as_string(), '250')
				#~ self.sendTelitCommand('QUIT', '221')
				#~ self.telitIMAPConnect()
			#~ else:
				#~ self.smtpServer.sendmail(mimeMultipart['From'], mimeMultipart['To'], mimeMultipart.as_string())
			#~ logger.write('INFO', '[EMAIL] Archivo \'%s\' enviado correctamente!' % fileName)
			#~ return True
		#~ except Exception as errorMessage:
			#~ logger.write('WARNING', '[EMAIL] Archivo \'%s\' no enviado: %s' % (fileName, str(errorMessage)))
			#~ return False

	#~ def sendMessageInstance(self, message, emailDestination, telitConnected):
		#~ try:
			#~ if telitConnected:
				#~ self.sendTelitCommand('. LOGOUT', '. OK')
				#~ self.telitSMTPConnect()
				#~ self.sendTelitCommand('MAIL FROM: %s' % self.emailAccount, '250')
				#~ self.sendTelitCommand('RCPT TO: %s' % emailDestination, '250')
				#~ self.sendTelitCommand('DATA', '354')
				#~ self.sendTelitCommand(mimeText.as_string(), '250')
				#~ self.sendTelitCommand('QUIT', '221')
				#~ self.telitIMAPConnect()
			#~ else:
				#~ self.smtpServer.sendmail(mimeText['From'], mimeText['To'], mimeText.as_string())
			#~ logger.write('INFO', '[EMAIL] Instancia de mensaje enviada a \'%s\'' % emailDestination)
			#~ return True
		#~ except Exception as errorMessage:
			#~ logger.write('WARNING', '[EMAIL] Instancia de mensaje no enviada: %s' % str(errorMessage))
			#~ return False

	def receive(self):
 		self.isActive = True
		while self.isActive:
			emailIds = ['']
			# Mientras no se haya recibido ningun correo electronico, el temporizador no haya expirado y no se haya detectado movimiento...
			while emailIds[0] == '' and self.isActive:
				try:
					if self.telitConnected:
						result = self.sendTelitCommand('. SEARCH UNSEEN', '. OK')
						emailIdsList = regex.findall('[0-9]+', result[0])
					else:
						self.imapServer.recent() # Actualizamos la Bandeja de Entrada
						result, emailIds = self.imapServer.uid('search', None, '(UNSEEN)') # Buscamos emails sin leer (nuevos)
						emailIdsList = emailIds[0].split()
				except Exception as e:
					pass
			# Si no se terminó la función (el modo EMAIL no dejó de funcionar), leemos los mensajes recibidos...
			if self.isActive:
				emailAmount = len(emailIdsList)
				logger.write('DEBUG', '[EMAIL] Ha(n) llegado ' + str(emailAmount) + ' nuevo(s) mensaje(s) de correo electronico!')
				# Recorremos los emails recibidos...
				for emailId in emailIdsList:
					if self.telitConnected:
						emailData = sendTelitIMAP('. FETCH %s RFC822' % emailId)
					else:
						result, emailData = self.imapServer.uid('fetch', emailId, '(RFC822)')
					# Retorna un objeto 'message', y podemos acceder a los items de su cabecera como un diccionario.
					emailReceived = email.message_from_string(emailData[0][1])
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
								logger.write('INFO', '[EMAIL] Ha llegado una nueva instancia de mensaje!')
							else:
								emailBody = emailBody[:emailBody.rfind('\r\n')] # Elimina el salto de línea del final
								self.receptionQueue.put((10, emailBody))
								logger.write('INFO', '[EMAIL] Ha llegado un nuevo mensaje!')
					else:
						logger.write('WARNING', '[EMAIL] Imposible procesar la solicitud. El correo no se encuentra registrado!')
						messageToSend = 'Imposible procesar la solicitud. Usted no se encuentra registrado!'
						self.sendMessage(messageToSend, sourceEmail)
					# Eliminamos el mensaje de la bandeja de entrada porque ya fue leído
					self.deleteEmail(emailId)
			# ... sino, dejamos de esperar mensajes
			else:
				break
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
		if self.telitConnected:
			self.sendTelitCommand('. STORE %s +FLAGS \Deleted' % emailId, '. OK')
			self.sendTelitCommand('. EXPUNGE', '. OK')
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
