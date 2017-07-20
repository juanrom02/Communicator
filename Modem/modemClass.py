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

import logger
import contactList
import messageClass

from curses import ascii # Para enviar el Ctrl-Z

JSON_FILE = 'config.json'
JSON_CONFIG = json.load(open(JSON_FILE))

class Modem(object):

        receptionQueue = None
        androidConnected = None
        atConnected = None
        successfulConnection = androidConnected or atConnected
        localInterface = None

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

        def sendAT(self, atCommand):
			self.modemInstance.write(atCommand + '\r')       # Envio el comando AT al modem                
			modemOutput = self.modemInstance.readlines() # Espero la respuesta
			# El módem devuelve una respuesta ante un comando
			if len(modemOutput) > 0:
					# Verificamos si se produjo algún tipo de error relacionado con el comando AT
					for outputElement in modemOutput:
							# El 'AT+CNMA' sólo es soportado en Dongles USB que requieren confirmación de SMS
							if outputElement.startswith(('ERROR', '+CME ERROR', '+CMS ERROR')) and atCommand != 'AT+CNMA':
									errorMessage = outputElement.replace('\r\n', '')
									if atCommand.startswith('AT'):
										logger.write('WARNING', '[GSM] %s - %s.' % (atCommand, errorMessage))
									else:
										logger.write('WARNING', '[GSM] No se pudo enviar el mensaje - %s.' % errorMessage)
									raise
							# El comando AT para llamadas de voz (caracterizado por su terminacion en ';') no es soportado
							elif outputElement.startswith('NO CARRIER') and atCommand.startswith('ATD') and atCommand.endswith(';'):
									raise
			# Esto ocurre cuando el puerto 'ttyUSBx' no es un módem
			else:
				raise
			# Si la respuesta al comando AT no era un mensaje de error, retornamos la salida
			return modemOutput

        def closePort(self):
                self.modemInstance.close()

class Gsm(Modem):

        successfulSending = None
        isActive = False
        SmsReceiverResult = None
        MEDIA_NAME = 'GSM'
        thread = None
        threadName = None

        def __init__(self, _receptionQueue):
                Modem.__init__(self)
                self.receptionQueue = _receptionQueue
                self.thread = threading.Thread(target = self.receive, name = self.threadName)

        def __del__(self):
                self.modemInstance.close()
                logger.write('INFO', '[GSM] Objeto destruido.')


        def connectAT(self, _serialPort):
                self.localInterface = _serialPort
                try:
                        self.modemInstance.port = _serialPort
                        self.modemInstance.open()
                        time.sleep(self.modemInstance.timeout)
                        self.sendAT('ATZ')                               # Enviamos un reset
                        self.sendAT('ATE1')     #Habilitamos el echo
                        #En base al modulo conectado, el comportamiento es distinto
                        model = self.sendAT('AT+GMM')
                        if model[1].startswith('UL865-NAR'):
                                logger.write('DEBUG', '[GSM] Telit UL865-NAR conectada en %s.' % _serialPort)
                                self.sendAT('AT#EXECSCR')       #Ejecuto el script de inicio
                        elif model[1].startswith('MF626'):
                                logger.write('DEBUG', '[GSM] Dongle ZTE MF626 conectado en %s.' % _serialPort)
                                self.sendAT('AT+CPMS="SM","SM","SM"')         #Si no le mando esto, el dongle ZTE me manda advertencias cada 2 segundos\;
                                self.sendAT('AT+CMEE=2')                 # Habilitamos reporte de error
                                self.sendAT('AT+CMGF=0')                 # Establecemos el modo PDU para SMS
                                self.sendAT('AT+CNMI=1,2,0,0,0') # Habilitamos notificacion de mensaje entrante
                        else:
                                self.sendAT('AT+CMEE=2')                 # Habilitamos reporte de error
                                self.sendAT('AT+CMGF=0')                 # Establecemos el modo PDU para SMS
                                self.sendAT('AT+CLIP=1')                 # Habilitamos identificador de llamadas
                                self.sendAT('AT+CNMI=1,2,0,0,0') # Habilitamos notificacion de mensaje entrante
                        self.atConnection = True
                        return True
                except:
						self.atConnection = False
						return False
                        

        def connectAndroid(self):
			try:
				output = subprocess.Popen(['adb','devices','-l'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
					smsAmount = 0
					smsBodyList = list()
					smsHeaderList = list()
					smsConcatList = list()
					unreadList = self.sendAT('AT+CMGL=0')   #Equivale al "REC UNREAD" en modo texto
			except:
					pass
			# Ejemplo de unreadList[0]: AT+CMGL=0\r\n
			# Ejemplo de unreadList[1]: +CMGL: 0,1,"",43\r\n
			# Ejemplo de unreadList[2]: 0791452300008001040D91945171928062F70003714012816350291AD4F29C0EA296D9693A68DA9C8264B1178C068AE174B31A\r\n
			# Ejemplo de unreadList[3]: +CMGL: 1,1,"",45\r\n
			# Ejemplo de unreadList[4]: 0791452300008090040D91453915572013F70000714042415564291CD4F29C0EA296D9693A68DA9C8264B4178C068AD174B55A4301\r\n
			# Ejemplo de unreadList[5]: \r\n
			# Ejemplo de unreadList[6]: OK\r\n
			for unreadIndex, unreadData in enumerate(unreadList):
					if unreadData.startswith('+CMGL'):
							smsHeaderList.append(unreadList[unreadIndex])
							smsBodyList.append(unreadList[unreadIndex + 1])
							smsAmount += 1
					elif unreadData.startswith('OK'):
							break
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
													self.removeSms(smsIndex)
											# Eliminamos la cabecera y el cuerpo del mensaje de las listas correspondiente
											smsHeaderList.remove(smsHeader)
											smsBodyList.remove(smsBody)
											# Decrementamos la cantidad de mensajes a procesar
											print 'smsAmount' #DEBUG
											smsAmount -= 1
							elif self.modemInstance.inWaiting() is not 0:
									bytesToRead = self.modemInstance.inWaiting()
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
						self.isActive = False
					except:
						time.sleep(1.5)
			logger.write('WARNING', '[GSM] Función \'receiveAT\' terminada.')

        def send(self, message, telephoneNumber):
                # Comprobación de envío de texto plano
                if isinstance(message, messageClass.Message) and hasattr(message, 'plainText'):
                        return self.sendMessage(message.plainText, telephoneNumber, False)
                # Comprobación de envío de archivo
                elif isinstance(message, messageClass.Message) and hasattr(message, 'fileName'):
                        logger.write('ERROR', '[GSM] Imposible enviar \'%s\' por este medio!' % message.fileName)
                        return False
                # Entonces se trata de enviar una instancia de mensaje
                else:
                        isInstance = True
                        # Serializamos el objeto para poder transmitirlo
                        serializedMessage = 'INSTANCE' + pickle.dumps(message)
                        return self.sendMessage(serializedMessage, telephoneNumber, True)

        def sendMessage(self, plainText, telephoneNumber, isInstance):
                try:
                        #############################
                        timeCounter = 0
                        self.successfulSending = None
                        self.successfulList = list()      #Util en SMS concatenados
                        smsLine = list()
                        index = 1
                        #############################
                        print 'plainText'
                        print repr(plainText)

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
                                csca = self.sendAT('AT+CSCA?')  #Consulta el numero del SMSC, util para el Dongle ZTE
                                smsc = regex.findall('"(.*)"', csca[1])       #Me devuelve una lista con las expresiones entre comillas, solo hay una
                                sms = SmsSubmit(str(telephoneNumber), plainText)
                                sms.csca = smsc[0]
                                pdu = sms.to_pdu()
                                amount = len(sms.to_pdu())

                                for pdu in sms.to_pdu():
                                        # Enviamos los comandos AT correspondientes para efectuar el envío el mensaje de texto
                                        info01 = self.sendAT('AT+CMGS=' + str(pdu.length)) # Envío la longitud del paquete PDU
                                        # ------------------ Caso de envío EXITOSO ------------------
                                        # Ejemplo de info01[0]: AT+CMGS=38\r\n
                                        # Ejemplo de info01[1]: >
                                        # Comprobamos que el módulo esté listo para mandar el mensaje
                                        for i in info01:
                                                if i.startswith('>'):
                                                        info02 = self.sendAT(str(pdu.pdu) + ascii.ctrl('z'))   # Mensaje de texto terminado en Ctrl+z
                                                        break
                                                elif i.startswith('ERROR'):
                                                        self.successfulSending = False
                                                        break
                                                        
                                        for i in info02:
                                                if i.startswith('OK'):
                                                        self.successfulSending = True
                                                        break
                                                elif i.startswith('ERROR'):
                                                        self.successfulSending = False
                                                        break

                                        # Esperamos respuesta de la red si es que no la hubo
                                        while self.successfulSending is None and timeCounter < 15:
                                                time.sleep(1)
                                                timeCounter += 1
                                        # Agregamos la respuesta de la red a la lista
                                        self.successfulList.append(self.successfulSending)
                                        if self.successfulSending:
                                                if (amount > 1):
                                                        logger.write('DEBUG', '[SMS] Mensaje ' + str(index)+ '/' + str(amount) + ' enviado a ' + str(telephoneNumber) + '.')
                                                        index += 1
                                        else:
                                                break

                        if False in self.successfulList:
                                if isInstance:
                                        logger.write('WARNING', '[GSM] No se pudo enviar la instancia de mensaje a %s.' % str(telephoneNumber))
                                else:
                                        logger.write('WARNING', '[GSM] No se pudo enviar el mensaje a %s.' % str(telephoneNumber))
                                return False
                        else:
                                logger.write('INFO', '[GSM] Mensaje de texto enviado a %s.' % str(telephoneNumber))
                                # Borramos el mensaje enviado almacenado en la memoria
                                self.removeAllSms() #DEBUG: Es necesario?
                                return True

                except:
                        print traceback.format_exc()
                        logger.write('ERROR', '[GSM] Error al enviar el mensaje de texto a %s.' % str(telephoneNumber))
                        return False

        def sendVoiceCall(self, telephoneNumber):
                try:
                        self.sendAT('ATD' + str(telephoneNumber) + ';') # Numero al cual se quiere llamar
                        logger.write('INFO', '[GSM] Llamando al número %s...' % str(telephoneNumber))
                        return True
                except:
                        logger.write('ERROR', '[GSM] Se produjo un error al intentar realizar la llamada!')
                        return False

        def answerVoiceCall(self):
                try:
                        self.sendAT('ATA') # Atiende la llamada entrante
                        logger.write('INFO', '[GSM] Conectado con el número %s.' % self.callerID)
                        return True
                except:
                        return False

        def hangUpVoiceCall(self):
                try:
                        self.sendAT('ATH') # Cuelga la llamada en curso
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

        def removeAllSms(self):
                try:
                        self.sendAT('AT+CMGD=1,4') # Elimina todos los mensajes en memoria
                        return True
                except:
                        return False

        def getSmsIndex(self, atOutput):
                # Ejemplo de 'atOutput' (para un mensaje enviado) : +CMGS: 17
                # Ejemplo de 'atOutput' (para un mensaje recibido): +CMGL: 2
                # Quitamos el comando AT, dejando solamente el índice del mensaje en memoria
                if atOutput.startswith('+CMGS'):
                        atOutput = atOutput.replace('+CMGS: ', '')
                elif atOutput.startswith('+CMGL'):
                        atOutput = atOutput.replace('+CMGL: ', '')
                smsIndex = int(atOutput)
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
