from typing import Optional

from blinker import signal

from . import network, speech


async def on_selected_on_front_changed(sender, **kwargs):
	path = kwargs["path"]
	data = kwargs["data"]
	if path in network.instance.cache and network.instance.cache[path] == data:
		return
	properties: list[str] = ["Name", "EffectName", "DeviceName"]
	name: Optional[str] = network.instance.get_name(path, properties)
	if data:
		if name is None:
			speech.speak("Unknown device selected")
		else:
			speech.speak(f"{name} selected")
	network.instance.cache[path] = data

async def on_48_v_changed(sender, **kwargs):
	path = kwargs["path"]
	data = kwargs["data"]
	if path in network.instance.cache and network.instance.cache[path] == data:
		return
	properties: list[str] = ["Name", "EffectName", "DeviceName"]
	name: Optional[str] = network.instance.get_name(path, properties)
	speech.speak(f"{name} 48V {"on" if data else "off"}")
	network.instance.cache[path] = data

async def on_cr_monitor_level_changed(sender, **kwargs):
	path = kwargs["path"]
	data = kwargs["data"]
	if path in network.instance.cache and network.instance.cache[path] == data:
		return
	properties: list[str] = ["Name", "EffectName", "DeviceName"]
	name: Optional[str] = network.instance.get_name(path, properties)
	speech.speak(f"{name} level {data}")
	network.instance.cache[path] = data

async def on_device_name_changed(sender, **kwargs):
	path = kwargs["path"]
	data = kwargs["data"]
	if path in network.instance.cache and network.instance.cache[path] == data:
		return
	speech.speak(f"Device name changed to {data}")
	network.instance.cache[path] = data

async def on_dim_on_changed(sender, **kwargs):
	path = kwargs["path"]
	data = kwargs["data"]
	if path in network.instance.cache and network.instance.cache[path] == data:
		return
	properties: list[str] = ["Name", "EffectName", "DeviceName"]
	name: Optional[str] = network.instance.get_name(path, properties)
	speech.speak(f"{name} dim {"on" if data else "off"}")
	network.instance.cache[path] = data

async def on_gain_changed(sender, **kwargs):
	path = kwargs["path"]
	data = kwargs["data"]
	if path in network.instance.cache and network.instance.cache[path] == data:
		return
	properties: list[str] = ["Name", "EffectName", "DeviceName"]
	name: Optional[str] = network.instance.get_name(path, properties)
	speech.speak(f"{name} gain {data:.1F}")
	network.instance.cache[path] = data

async def on_hi_z_changed(sender, **kwargs):
	path = kwargs["path"]
	data = kwargs["data"]
	if path in network.instance.cache and network.instance.cache[path] == data:
		return
	properties: list[str] = ["Name", "EffectName", "DeviceName"]
	name: Optional[str] = network.instance.get_name(path, properties)
	speech.speak(f"{name} Hi Z {"on" if data else "off"}")
	network.instance.cache[path] = data

async def on_io_type_changed(sender, **kwargs):
	path = kwargs["path"]
	data = kwargs["data"]
	if path in network.instance.cache and network.instance.cache[path] == data:
		return
	properties: list[str] = ["Name", "EffectName", "DeviceName"]
	name: Optional[str] = network.instance.get_name(path, properties)
	speech.speak(f"{name} IO type {data}")
	network.instance.cache[path] = data

async def on_low_cut_changed(sender, **kwargs):
	path = kwargs["path"]
	data = kwargs["data"]
	if path in network.instance.cache and network.instance.cache[path] == data:
		return
	properties: list[str] = ["Name", "EffectName", "DeviceName"]
	name: Optional[str] = network.instance.get_name(path, properties)
	speech.speak(f"{name} low cut {"on" if data else "off"}")
	network.instance.cache[path] = data

async def on_mix_to_mono_changed(sender, **kwargs):
	path = kwargs["path"]
	data = kwargs["data"]
	if path in network.instance.cache and network.instance.cache[path] == data:
		return
	properties: list[str] = ["Name", "EffectName", "DeviceName"]
	name: Optional[str] = network.instance.get_name(path, properties)
	speech.speak(f"{name} sum {"on" if data else "off"}")
	network.instance.cache[path] = data

async def on_mute_changed(sender, **kwargs):
	path = kwargs["path"]
	data = kwargs["data"]
	if path in network.instance.cache and network.instance.cache[path] == data:
		return
	properties: list[str] = ["Name", "EffectName", "DeviceName"]
	name: Optional[str] = network.instance.get_name(path, properties)
	speech.speak(f"{name} mute {"on" if data else "off"}")
	network.instance.cache[path] = data

async def on_pad_changed(sender, **kwargs):
	path = kwargs["path"]
	data = kwargs["data"]
	if path in network.instance.cache and network.instance.cache[path] == data:
		return
	properties: list[str] = ["Name", "EffectName", "DeviceName"]
	name: Optional[str] = network.instance.get_name(path, properties)
	speech.speak(f"{name} pad {"on" if data else "off"}")
	network.instance.cache[path] = data

async def on_stereo_changed(sender, **kwargs):
	path = kwargs["path"]
	data = kwargs["data"]
	if path in network.instance.cache and network.instance.cache[path] == data:
		return
	properties: list[str] = ["Name", "EffectName", "DeviceName"]
	name: Optional[str] = network.instance.get_name(path, properties)
	speech.speak(f"{name} stereo link {"on" if data else"off"}")
	network.instance.cache[path] = data

async def on_talkback_on_changed(sender, **kwargs):
	path = kwargs["path"]
	data = kwargs["data"]
	if path in network.instance.cache and network.instance.cache[path] == data:
		return
	speech.speak(f"Talkback {"on" if data else "off"}")
	network.instance.cache[path] = data

async def on_device_online_changed(sender, **kwargs):
	path = kwargs["path"]
	data = kwargs["data"]
	if path in network.instance.cache and network.instance.cache[path] == data:
		return
	properties: list[str] = ["Name", "EffectName", "DeviceName"]
	name: Optional[str] = network.instance.get_name(path, properties)
	speech.speak(f"{name} {"on" if data else "off"}")
	network.instance.cache[path] = data

async def on_ua_access_initialized(sender, *args, **kwargs):
	speech.speak("UA Access is ready")

async def on_phase_changed(sender, **kwargs):
	path = kwargs["path"]
	data = kwargs["data"]
	if path in network.instance.cache and network.instance.cache[path] == data:
		return
	properties: list[str] = ["Name", "EffectName", "DeviceName"]
	name: Optional[str] = network.instance.get_name(path, properties)
	speech.speak(f"{name} phase {"on" if data else "off"}")
	network.instance.cache[path] = data

def register_events():
	signal("SelectedOnFront").connect(on_selected_on_front_changed)
	signal("48V").connect(on_48_v_changed)
	signal("CRMonitorLevel").connect(on_cr_monitor_level_changed)
	signal("DeviceName").connect(on_device_name_changed)
	signal("DimOn").connect(on_dim_on_changed)
	signal("Gain").connect(on_gain_changed)
	signal("HiZ").connect(on_hi_z_changed)
	signal("IOType").connect(on_io_type_changed)
	signal("LowCut").connect(on_low_cut_changed)
	signal("MixToMono").connect(on_mix_to_mono_changed)
	signal("Mute").connect(on_mute_changed)
	signal("Pad").connect(on_pad_changed)
	signal("Stereo").connect(on_stereo_changed)
	signal("TalkbackOn").connect(on_talkback_on_changed)
	signal("DeviceOnline").connect(on_device_online_changed)
	signal("UAAccessInitialized").connect(on_ua_access_initialized)
	signal("Phase").connect(on_phase_changed)
