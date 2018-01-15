#Módulo de Comunicación

Este módulo resulta una extensión del proyecto original. El mismo tiene capacidades para trabajar en LAN y WLAN, con tecnologías Ethernet y WiFi respectivamente; en WAN con tecnologías GSM/GPRS; y en WPAN con tecnología Bluetooth. Para las redes LAN, WLAN y WAN utiliza la pila TCP/IP como transporte de datos, y la pila BlueZ para WPAN. 

Soporta los servicios de correo electrónico y FTP(aprovechando el stack TCP/IP), además de utilizar la red móvil para SMS, llamadas telefónicas e Internet móvil. Se agrega el soporte de varios dispositivos de hardware, entre ellos una placa de desarrollo Telit, y un teléfono celular con Android; con el primero es posible implementar un contestador de llamadas, que utiliza una API de Google para convertir el audio en texto plano, y viceversa. 

##Requisitos del módulo

	- Python 2.7

	- Pip para la instalación de algunas librerias (sudo apt-get install pip)
	  En caso de problemas de dependencias con pip (sudo apt-get install python python-dev libatlas-base-dev gcc gfortran g++)

	- Librería PyBluez (sudo pip install pybluez)
	  En caso de problemas de dependencias con pip (sudo apt-get install libbluetooth-dev)

	- Librería PySerial (sudo pip install pyserial)
	
	- Librería pexpect (sudo pip install pexpect)
	
	- Librería python-messaging ([GitHub]{github.com/pmarti/python-messaging})
	
	- Librería SpeechRecognition (sudo pip install SpeechRecognition)
	
	- Librería gtts (sudo pip install gTTS)	
	

##Configuración del módulo

	- Completar la lista de contactos con los usuarios con los que se planea la comunicación (contactList.py).

	- Configurar el módulo mediante el archivo de configuración (config.json).
	  Los parámetros del mismo se explican a continuación.

	{
	# --------- CONFIGURACIÓN DEL COMUNICADOR ---------
	"COMMUNICATOR":
	{
		"NAME"                : "Client01", # Nombre del Comunicador.
		"RECEPTION_FILTER"    : 0,          # Habilita o deshabilita el filtrado de mensajes (0/1).
		"TRANSMISSION_QSIZE"  : 25,         # Cantidad máxima de elementos para la cola de transmissión.
		"RECEPTION_QSIZE"     : 25,         # Cantidad máxima de elementos para la cola de recepción.
		"RETRY_TIME"          : 15,         # Tiempo entre reintentos de envío (en segundos).
		"REFRESH_TIME"        : 5           # Tiempo entre comprobaciones de hardware (en segundos).
		"TIME_TO_LIVE"        : 3600        # Tiempo de vida de los mensajes.
		},
	# --------- CONFIGURACIÓN TCP/IP ---------
	"NETWORK":
		{
		"TCP_PORT"    : 5000, # Puerto TCP [1024 - 49151].
		"UDP_PORT"    : 5010, # PUerto UDP [1024 - 49151].
		"BUFFER_SIZE" : 4096, # Tamaño del buffer.
		"CONNECTIONS" : 5     # Cantidad máxima de conexiones simultáneas.
	 	},
	# --------- CONFIGURACIÓN BLUETOOTH ---------
	"BLUETOOTH":
		{
		"SERVICE"  : "BLUETOOTH-Client01",                  # Nombre del servicio.
		"UUID"     : "94f39d29-7d6d-437d-973b-fba39e49d4ee" # ID del servicio.
		},
	# --------- CONFIGURACIÓN DE EMAIL ---------
	"EMAIL":
		{
		"ACCOUNT"     : "client01.datalogger@gmail.com", # Cuenta de gmail.
		"PASSWORD"    : "client01dl",                    # Contraseña de la cuenta.
		"SUBJECT"     : "Módulo de Comunicación",        # Asunto para los mails enviados.
		"SMTP_SERVER" : "smtp.gmail.com",                # Servidor SMTP para envío.
		"IMAP_SERVER" : "imap.gmail.com",                # Servidor IMAP para recepción.
		"SMTP_PORT"   : 587,                             # Puerto SMTP.
		"IMAP_PORT"   : 993                              # Puerto IMAP.
		},
	# ------------ CONFIGURACIÓN FTP ------------
	"FTP":
		{
		"FTP_SERVER"	: "181.28.14.195",	# Dirección IP del servidor.
		"FTP_PORT"	: 21,			# Puerto donde se realiza la conexión.
		"USER"		: "client01dl",		# Usuario del servidor.
		"PASSWORD"	: "client01dl",		# Contraseña del servidor.
		"DIRECTORY"	: "volume9",		# Directorio inicial dentro del servidor.
		"TIMEOUT"	: 5			# Tiempo de espera a una respuesta.
		},
	# --------- CONFIGURACIÓN DEL MÓDEM ---------
	"MODEM":
		{
		"TIME_OUT"  : 1.5,  # Tiempo de respuesta.
		"BAUD_RATE" : 19200 # Velocidad en baudios.
		},
	# --------- PRIORIDAD DE TECNOLOGIAS ---------
		# 0 --> Inhabilitado
	"PRIORITY_LEVELS":
		{
		"VOZ"	    : 1,
		"SMS"       : 5,
		"GPRS"      : 6,
		"WIFI"      : 7,
		"ETHERNET"  : 8,
		"BLUETOOTH" : 4,
		"EMAIL"     : 3,
		"FTP"	    : 2
		},
	# ------- CONFIGURACIÓN DE AUDIO -------
	"AUDIO":
		{
		"LANGUAGE"	: "es",	# Idioma para la detección de audio.
		"RECORD_SECS"	: 30	# Longitud máxima de los mensajes a grabar, en segundos.
		},
	# --------- LOGGER DE EVENTOS ---------
		# DEBUG    --> Depuración
		# INFO     --> Información
		# WARNING  --> Advertencia
		# ERROR    --> Error
		# CRITICAL --> Situación crítica
	"LOGGER":
		{
		"FILE_LOG"              : "events.log", # Nombre del archivo de logueo.
		"FILE_LOGGING_LEVEL"    : "DEBUG",      # Nivel para los eventos del archivo de logueo.
		"CONSOLE_LOGGING_LEVEL" : "DEBUG"       # Nivel para los eventos de la salida estándar.
		}
		
	}

##Funciones del módulo

Para importar el módulo en otro proyecto, se debe hacer un "import communicator". Si se va a utilizar un módem GSM/GPRS, la aplicación se debe correr como root.

Las funciones que proporciona el Comunicador son:

###communicator.open()

	Configura todos los componentes del sistema.

###communicator.send()

	Envio de textoPlano/archivo: **communicator.send(plainText/filePath, receiver, media)**
		Este último campo se puede obviar, y será el comunicador quién elija la tecnología. Ejemplo: communicator.send(plainText/filePath, receiver)

	Envio de instancia de mensaje: **communicator.send(messageInstance, media = userPreference)**
		El mensaje debe ser una instancia "Message" (messageClass.py). El último campo también se puede obviar, donde la tecnología se elegirá automáticamente. Ejemplo: communicator.send(messageInstance)

###communicator.recieve()

	Obtiene el mensaje de mayor prioridad desde la cola de recepción.

###communicator.close()

	Elimina todos los componentes creados en la apertura.

###communicator.lenght()

	Devuelve la cantidad de elementos de la cola de recepción.

Existe un módulo de prueba creado para probar todas las funcionalidades del Comunicador (example.py).
