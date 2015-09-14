 # coding=utf-8
"""Modulo para encargarse de las funciones de logging, es decir la escritura
	de los eventos del sistema.
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Abril de 2015 """

import sys
import logging
import commentjson
import configReader

JSON_FILE = 'config.json'
JSON_CONFIG = commentjson.load(open(JSON_FILE))

CONSOLE_FORMAT = '[%(levelname)s] %(message)s'
FILE_FORMAT = '[%(asctime)s][%(levelname)s] %(message)s'
FILE_LOG = 'HistoricalEvents.log'

LOGGING_LEVELS = {'DEBUG' : logging.DEBUG,
                  'INFO' : logging.INFO,
                  'WARNING' : logging.WARNING,
                  'ERROR' : logging.ERROR,
                  'CRITICAL' : logging.CRITICAL}

logger = logging.getLogger(__name__) # Creamos el objeto Logger

def set():
	"""Se configura el logger, los manejadores (junto con los niveles de mensajes) 
	y los formatos de los mismos.
	@param name: Nombre del objeto logger
	@type name: str
	"""
	global logger
	logger.setLevel(LOGGING_LEVELS['DEBUG'])

	fileFormatter = logging.Formatter(FILE_FORMAT)          # Creamos el 'formatter' para la consola
	fileHandler = logging.FileHandler(FILE_LOG)             # Creamos el 'handler' para el archivo LOG
	fileHandler.setLevel(JSON_CONFIG["FILE_LOGGING_LEVEL"]) # Establecemos el nivel para almacenar los mensajes
	fileHandler.setFormatter(fileFormatter)                 # Establecemos el formato de los mensajes
	logger.addHandler(fileHandler)                          # Añadimos el 'handler' al objeto Logger

	consoleFormatter = logging.Formatter(CONSOLE_FORMAT)          # Creamos el 'formatter' para la consola
	consoleHandler = logging.StreamHandler(sys.stdout)            # Creamos el 'handler para la consola
	consoleHandler.setLevel(JSON_CONFIG["CONSOLE_LOGGING_LEVEL"]) # Establecemos el nivel para mostrar los mensajes
	consoleHandler.setFormatter(consoleFormatter)                 # Establecemos el formato de los mensajes
	logger.addHandler(consoleHandler)                             # Añadimos el 'handler' al objeto Logger

def write(logType, message):
	"""Se añade un mensaje al logger si es correcto el tipo de mensaje, el mensaje
	es añadido tanto al archivo logger como mostrado en consola dependiendo de los
	niveles que se hayan definido.
	@param logType: Tipo de mensaje Log
	@type logType: str
	@param message: Mensaje para logger.
	@type message: str"""
	if logType is 'DEBUG': logger.debug(message)
	elif logType is 'INFO': logger.info(message)
	elif logType is 'WARNING': logger.warn(message)
	elif logType is 'ERROR': logger.error(message)
	elif logType is 'CRITICAL': logger.critical(message)
	else: logger.error('Intento de escribir en Log erroneo no se designo un tipo de log correcto')