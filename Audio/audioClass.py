
from gtts import gTTS
from pydub import AudioSegment
import json
import tempfile

import logger
import gsmClass

JSON_FILE = 'config.json'
JSON_CONFIG = json.load(open(JSON_FILE))

class Audio(Object):
	
	language = None
	
	def __init__(self):
		self.language = JSON_FILE['AUDIO']['LANGUAGE']
		if self.language not in gTTS.LANGUAGES:
			logger.write('WARNING', '[AUDIO] El idioma no esta soportado. Revise el archivo de configuracion')
	
	def text_to_audio(self, text):
		tts = gTTS(text= text, lang= self.language)
		f = tempfile.TemporaryFile()
		tts.write_to_fp(f)
		audio = AudioSegment.from_mp3(f)
		audio.export("error.raw", format="raw", bitrate="64k", parameters=["-ar","8000","-ac","1","-acodec","pcm_s8"])
	
	
