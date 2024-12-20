import toga
from .. import network
from .effect_parameters_dialog import *
import copy

class PreampEffectsDialog(toga.Window):
	def __init__(self, device: int, input: int):
		super().__init__(title=f"Preamp unison effects manager for {network.instance.get(f"/devices/{device}/inputs/{input}/Name/value")}")
		self.instance = network.instance
		self.device = device
		self.input = input
		self.effects = self.instance.get_all_preamp_effects(device, input)
		self.box = toga.Box()
		self.show_authorized_plugins_only_switch = toga.Switch("&Show authorized plug-ins only", on_change=self.rescan_plugins)
		self.plugins = [{"name": "None", "id": -1}]
		self.plugins.extend(self.scan_all_plugins())
		self.plugins_list_label = toga.Label("Select a plug-in")
		self.plugins_list = toga.Selection(items=self.plugins, on_change=self.on_plugin_selected, accessor="name")
		self.current_plugin_selection = None
		self.apply_button = toga.Button("&Apply", on_press=self.apply_plugin, enabled=False)
		self.parameters_button = toga.Button("Parameters", enabled=False, on_press=self.edit_plugin_parameters)
		self.close_button = toga.Button("&Close", on_press=self.close_window)
		if self.effects['0']["properties"]["EffectInstance"]["value"] != 0:
			self.plugins_list.value = [plugin for plugin in self.plugins_list.items if plugin.name == self.effects['0']["properties"]["EffectName"]["value"]][0]
			self.current_plugin_selection = [plugin.id for plugin in self.plugins_list.items if plugin.name == self.effects['0']["properties"]["EffectName"]["value"]][0]
			self.parameters_button.enabled = True
		self.box.add(self.show_authorized_plugins_only_switch)
		self.box.add(self.plugins_list_label)
		self.box.add(self.plugins_list)
		self.box.add(self.apply_button)
		self.box.add(self.parameters_button)
		self.box.add(self.close_button)
		self.content = self.box
		self.show_authorized_plugins_only_switch.focus()

	def scan_all_plugins(self) -> list[str]:
		plugins = self.instance.get_all_plugins()
		ids_to_remove = set()
		if self.show_authorized_plugins_only_switch.value:
			# Filter by plugins that are authorized
			for id, plugin in plugins.items():
				if plugin["properties"]["Status"]["value"].find("Authorized") == -1:
					ids_to_remove.add(id)
		if len(ids_to_remove) > 0:
			for id in ids_to_remove:
				plugins.pop(id)

		ids_to_remove.clear()
		for id, plugin in plugins.items():
			if not plugin["properties"]["Unison"]["value"]:
				ids_to_remove.add(id)

		for id in ids_to_remove:
			plugins.pop(id)

		names = []
		for id, plugin in plugins.items():
			names.append({"name": plugin["properties"]["Name"]["value"], "id": id})

		return names

	def rescan_plugins(self, widget, *args, **kwargs):
		try:
			plugins_list = [{"name": "None", "id": -1}]
			plugins_list.extend(self.scan_all_plugins())
			self.plugins_list.items = plugins_list
		except KeyError:
			self.plugins_list.value = self.plugins_list.items[0]

	def on_plugin_selected(self, widget, *args, **kwargs):
		self.current_plugin_selection = widget.value.id
		self.apply_button.enabled = True

	async def apply_plugin(self, widget, *args, **kwargs):
		if self.current_plugin_selection == -1: # None
			await self.instance.send_request(f"set /devices/{self.device}/inputs/{self.input}/preamps/0/effects/0/EffectName/value \"\"")
			self.parameters_button.enabled = False
			return
		pname=[plugin['name'] for plugin in self.plugins if plugin['id'] == self.current_plugin_selection][0]
		await self.instance.send_request(f"set /devices/{self.device}/inputs/{self.input}/preamps/0/effects/0/EffectName \"{pname}\"")
		self.parameters_button.enabled = True

	async def edit_plugin_parameters(self, widget, *args, **kwargs):
		plugin_id = [plugin['id'] for plugin in self.plugins if plugin['id'] == self.current_plugin_selection][0]
		dialog = EffectParametersDialog(self.device, self.input, 0, plugin_id, True, 0)
		dialog.show()

	def close_window(self, widget, *args, **kwargs):
		self.close()
