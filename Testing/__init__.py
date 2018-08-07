import unittest
from mock import MagicMock, PropertyMock, patch, mock_open, call
import mock
import os
import sys

os.chdir("..")
	
sys.path.append(os.getcwd())
sys.path.append(os.path.abspath('Email/'))
sys.path.append(os.path.abspath('Modem/'))
sys.path.append(os.path.abspath('Network/'))
sys.path.append(os.path.abspath('Bluetooth/'))
sys.path.append(os.path.abspath('File Transfer/'))
sys.path.append(os.path.abspath('Audio/'))
