# SPDX-License-Identifier: GPL-3.0-or-later

import platform

import toga
from blinker import signal
from pedalboard import load_plugin

from .. import network


class EffectParametersDialog(toga.Window):
	def __init__(self, device: int, input: int, effect: int, plugin: int, for_preamp: bool = True, preamp: int=0):
		plugindata = network.instance.get(f"/plugins/{plugin}")
		pname = plugindata["properties"]["Name"]["value"]
		pcat = plugindata["properties"]["Categories"]["value"].split(',')[0].replace('&', "and")
		signal("NormalizedValue").connect(self.on_remote_parameter_changed)
		self.instance = network.instance
		super().__init__(title=f"Effect parameters editor: {pname}")
		common_path = ""
		match platform.system():
			case "Windows":
				common_path = r"C:\Program Files\Common Files\VST3\Universal Audio"
				self.plugin_instance = load_plugin(rf"{common_path}\{pcat}\{pname}.vst3\Contents\x86_64-win\{pname}.vst3")
			case "Darwin":
				common_path = "/Library/Audio/Plug-Ins/VST3/Universal Audio"
				self.plugin_instance = load_plugin(rf"{common_path}/{pcat}/{pname}.vst3/Contents/MacOS/{pname}")
			case _:
				return
		self.params = list(self.plugin_instance.parameters.keys())
		if self.params.index("master_bypass") != -1:
			self.params.pop(self.params.index("master_bypass"))
			presets = ["None"]
		data = self.instance.get(f"/plugins/{plugin}/Preset/values")
		results = []
		top_level_values = data
		stack = [(item, "") for item in top_level_values]
		while stack:
			current, parent_value = stack.pop()
			if current.get("type") == "file":
				if parent_value:
					results.append(f"{parent_value}: {current['value']}")
				else:
					results.append(current['value'])
			elif current.get("type") == "folder":
				current_value = current.get("value", "")
				if "children" in current:
					for child in current["children"]:
						stack.append((child, current_value))
			else:
				results.append(current_value)
		results.reverse()
		presets.extend(results)
		cur_preset = None
		if for_preamp:
			cur_preset = self.instance.get(f"/devices/{device}/inputs/{input}/preamps/{preamp}/effects/{effect}/Preset/value")
		else:
			cur_preset = self.instance.get(f"/devices/{device}/inputs/{input}/effects/{effect}/Preset/value")
		self.box = toga.Box()
		self.preset_label = toga.Label("Preset")
		self.preset = None
		if for_preamp:
			self.preset = toga.Selection(id=f"/devices/{device}/inputs/{input}/preamps/{preamp}/effects/{effect}/Preset", items=presets, value=cur_preset if len(cur_preset) > 0 else "Default" if "Default" in presets else "None", on_change=self.set_preset)
		else:
			self.preset = toga.Selection(id=f"/devices/{device}/inputs/{input}/effects/{effect}/Preset", items=presets, value=cur_preset if len(cur_preset) > 0 else "Default" if "Default" in presets else "None", on_change=self.set_preset)
		self.box.add(self.preset_label)
		self.box.add(self.preset)
		self.actual_params = {}
		for param_python_name in self.params:
			param = self.plugin_instance.parameters[param_python_name]
			param_strings = []
			for value in param.valid_values:
				setattr(self.plugin_instance, param.python_name, value)
				param_strings.append(param.string_value)
			self.plugin_instance.reset()
			if param.type is bool:
				if for_preamp:
					self.actual_params[param_python_name] = toga.Switch(f"{param.name}{f" ({param.units})" if param.units is not None else ""}", on_change=self.on_param_bool_toggle, id=f"/devices/{device}/inputs/{input}/preamps/{preamp}/effects/{effect}/parameters/{self.params.index(param_python_name)}")
				else:
					self.actual_params[param_python_name] = toga.Switch(f"{param.name}{f" ({param.units})" if param.units is not None else ""}", on_change=self.on_param_bool_toggle, id=f"/devices/{device}/inputs/{input}/effects/{effect}/parameters/{self.params.index(param_python_name)}")
				self.box.add(self.actual_params[param_python_name])
			elif param.type is str or param.type is float:
				self.actual_params[f"{param_python_name}_label"] = toga.Label(f"{param.name}{f" ({param.units})" if param.units is not None else ""}")
				if for_preamp:
					self.actual_params[param_python_name] = toga.Selection(items=param_strings, on_change=self.on_choice_param_change, id=f"/devices/{device}/inputs/{input}/preamps/{preamp}/effects/{effect}/parameters/{self.params.index(param_python_name)}")
				else:
					self.actual_params[param_python_name] = toga.Selection(items=param_strings, on_change=self.on_choice_param_change, id=f"/devices/{device}/inputs/{input}/effects/{effect}/parameters/{self.params.index(param_python_name)}")
				self.box.add(self.actual_params[f"{param_python_name}_label"])
				self.box.add(self.actual_params[param_python_name])
			else:
				print(f"Warning: type {param.type} is unknown")
		self.box.add(toga.Button("Close", on_press=self.close_editor))
		self.content = self.box
		self.app.loop.create_task(self.instance.send_request(f"subscribe /devices/{device}/inputs/{input}/effects/{effect}/parameters?recursive=1"))

	async def on_remote_parameter_changed(self, sender, *args, **kwargs):
		path = kwargs["path"]
		data = kwargs["data"]
		components = path.strip("/").split("/")
		param_name = self.params[int(components[components.index("parameters")+1])]
		self.plugin_instance.parameters[param_name].raw_value = float(data)
		handler = self.actual_params[param_name].on_change
		self.actual_params[param_name].on_change = None
		if self.plugin_instance.parameters[param_name].type is bool:
			self.actual_params[param_name].value = bool(self.plugin_instance.parameters[param_name].raw_value)
		else:
			self.actual_params[param_name].value = self.plugin_instance.parameters[param_name].string_value
		self.actual_params[param_name].on_change = handler
		self.plugin_instance.reset()

	async def on_param_bool_toggle(self, widget, *args, **kwargs):
		components = widget.id.strip("/").split("/")
		param_name = self.params[int(components[components.index("parameters")+1])]
		normalized_value = self.plugin_instance.parameters[param_name].get_raw_value_for(widget.value)
		await self.instance.send_request(f"set {widget.id}/NormalizedValue {normalized_value}")

	async def on_choice_param_change(self, widget, *args, **kwargs):
		components = widget.id.strip("/").split("/")
		param_name = self.params[int(components[components.index("parameters")+1])]
		normalized_value = self.plugin_instance.parameters[param_name].get_raw_value_for(widget.value)
		await self.instance.send_request(f"set {widget.id}/NormalizedValue {normalized_value}")

	async def set_preset(self, widget, *args, **kwargs):
		if widget.value == "None":
			await self.instance.send_request(f"set {widget.id} \"\"")
			return
		preset = widget.value
		if widget.value.find(": ") != -1:
			preset = preset.split(": ")[-1]
		await self.instance.send_request(f"set {widget.id} \"{preset}\"")

	def close_editor(self, widget, *args, **kwargs):
		del self.plugin_instance
		signal("NormalizedValue").disconnect(self.on_remote_parameter_changed)
		self.close()
