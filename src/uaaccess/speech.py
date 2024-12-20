import sys
if sys.platform == "win32":
	from cytolk import tolk
elif sys.platform == "darwin":
	from . import nsss

synth = None

def init():
	global synth
	if sys.platform == "win32":
		tolk.load()
	elif sys.platform == "darwin":
		synth = nsss.NSSS()

def speak(text, interrupt = False):
	if sys.platform == "win32":
		tolk.speak(text, interrupt)
	elif sys.platform == "darwin":
	  synth.speak(text, interrupt)

def is_loaded():
	if sys.platform == "win32":
		return tolk.is_loaded()
	elif sys.platform == "darwin":
		return synth is not None

def deinit():
	if sys.platform == "win32":
		tolk.unload()
