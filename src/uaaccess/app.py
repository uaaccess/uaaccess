# SPDX-License-Identifier: GPL-3.0-or-later

import asyncio
import cProfile
import json
import os
import sys
import time
import traceback
import zipfile
from ipaddress import IPv4Address, IPv6Address
from typing import Optional, Union

import aiofiles
import aioping
import clipboard
import toga
from blinker import signal
from github import Github, GithubException
from packaging import version
from packaging.version import InvalidVersion
from toga.style import Pack
from toga.style.pack import COLUMN

from . import events, network, speech
from .connection_requester import ConnectionRequester
from .dialogs import PreampEffectsDialog, SendsDialog, SendsType

if sys.platform == "win32":
	import io
	from ctypes import byref, c_int32, c_ulong, create_unicode_buffer

	from win32more.Windows.Win32.Foundation import (
		ERROR_NO_MORE_ITEMS,
		ERROR_SUCCESS,
	)
	from win32more.Windows.Win32.System.ApplicationInstallationAndServicing import (
		INSTALLPROPERTY_INSTALLEDPRODUCTNAME,
		INSTALLSTATE_DEFAULT,
		MSIINSTALLCONTEXT_MACHINE,
		MSIINSTALLCONTEXT_USERMANAGED,
		MSIINSTALLCONTEXT_USERUNMANAGED,
		MsiEnumProductsEx,
		MsiGetProductInfoEx,
		MsiQueryProductState,
	)
else:
	import plistlib
import socket

from .updater_dialog import UpdaterDialog


class UAAccess(toga.App):
	def startup(self):
		if sys.executable.find("python") != -1:
			self.profiler = cProfile.Profile()
			self.profiler.enable()
		speech.init()
		self.loop.create_task(self.do_update_check())
		self.ui_required_input_props = ["FaderLevel", "IOType", "Mute", "RecordPreEffects", "Solo"]
		self.ui_required_output_props = ["MixToMono", "MixInSource", "Pad", "AltMonTrim", "AltMonEnabled", "Mute", "CRMonitorLevel", "MirrorsToDigital", "DimOn"]
		self.ui_required_aux_props = ["Gain", "Mute", "FaderLevel", "MixToMono", "Isolate", "SendPostFader"]
		self.ui_required_preamp_props = ["Gain", "48V", "LowCut", "Pad", "Phase"]
		self.currently_selected_input, self.currently_selected_output, self.currently_selected_aux = 0, 0, 0
		self.on_exit = self.handle_exit
		self.loop.set_exception_handler(self.handle_exception)
		self.main_window = toga.MainWindow(title=f"{self.formal_name} [Loading]")
		self.input_details_box = toga.Box()
		self.output_details_box = toga.Box()
		self.aux_details_box = toga.Box()
		self.tab_container = toga.OptionContainer()
		self.main_container = toga.Box(style=Pack(direction=COLUMN, padding=10))
		self.main_window.content = self.main_container
		self.loop.create_task(self.try_connecting_locally())
		self.main_window.show()
		self.commands.add(toga.Command(self.export_tree, "Export schema tree", group=toga.Group("Debugging")))
		if sys.executable.find("python") != -1:
			self.commands.add(toga.Command(self.enable_packet_logging, "Enable logging of packets", group=toga.Group("Debugging")))
		self.log_file = None

	async def close_app(self, widget, **kwargs):
		self.exit()

	def build_input_widgets(self, inp: int) -> Optional[toga.Box]:
		input = self.instance.get_input(0, inp)
		if "Active" in input["properties"] and not input["properties"]["Active"]["value"]:
			return None
		if input is None:
			return None
		box = toga.Box(style=Pack(direction = COLUMN, padding=5))
		props = input["properties"]
		inputname = props["Name"]["value"]
		for name, prop in props.items():
			if name not in self.ui_required_input_props or "value" not in prop:
				continue
			path = f"/devices/0/inputs/{inp}/{name}/value"
			match prop["type"]:
				case "bool":
					toggle = toga.Switch(f"{inputname} {self.instance.prop_display_name(name)}", id=path, value=prop.get("value", False), enabled = not prop["readonly"] if "readonly" in prop else True, on_change=self.on_prop_bool_toggle)
					box.add(toggle)
				case "string":
					label = toga.Label(f"{inputname} {self.instance.prop_display_name(name)}")
					edit = None
					if "values" in prop:
						edit = toga.Selection(id=path, items=prop["values"], value=prop.get("value", None), on_change=self.on_prop_string_enum_change, enabled=not prop.get("readonly", False))
					else:
						edit = toga.TextInput(id=path, value=prop.get("value", None), readonly = prop.get("readonly", True), on_confirm=self.on_prop_string_change)
					box.add(label)
					box.add(edit)
				case "float":
					label = toga.Label(f"{inputname} {self.instance.prop_display_name(name)}")
					edit = None
					if "values" in prop:
						edit = toga.Selection(id=path, items=[f"{v:.1F}" for v in prop["values"]], value=prop.get("value", None), on_change=self.on_prop_int_enum_change, enabled=not prop.get("readonly", False))
					else:
						edit = toga.NumberInput(id=path, value=prop.get("value", None), readonly = prop.get("readonly", False), on_change=self.on_prop_int_change, min=prop.get("min", None), max=prop.get("max", None), step=1.0)
					box.add(label)
					box.add(edit)
				case "int" | "int64" | "pointer":
					label = toga.Label(f"{inputname} {self.instance.prop_display_name(name)}")
					edit = None
					if "values" in prop:
						edit = toga.Selection(id=path, items=[str(v) for v in prop["values"]], value=prop.get("value", None), on_change=self.on_prop_int_enum_change, enabled=not prop.get("readonly", False))
					else:
						edit = toga.NumberInput(id=path, value=prop.get("value", None), readonly = prop.get("readonly", False), on_change=self.on_prop_int_change, min=prop.get("min", None), max=prop.get("max", None), step=1.0)
					box.add(label)
					box.add(edit)
		preamp = self.instance.get_preamp(0, inp, 0)
		if preamp is None:
			box.add(toga.Button("&Sends", on_press=self.open_input_sends))
			return box
		props = preamp["properties"]
		for name, prop in props.items():
			if name not in self.ui_required_preamp_props:
				continue
			path = f"/devices/0/inputs/{inp}/preamps/0/{name}/value"
			match prop["type"]:
				case "bool":
					toggle = toga.Switch(f"{inputname} Preamp {self.instance.prop_display_name(name)}", id=path, value=prop.get("value", False), enabled = not prop["readonly"] if "readonly" in prop else True, on_change=self.on_prop_bool_toggle)
					box.add(toggle)
				case "string":
					label = toga.Label(f"{inputname} Preamp {self.instance.prop_display_name(name)}")
					edit = None
					if "values" in prop:
						edit = toga.Selection(id=path, items=prop["values"], value=prop.get("value", None), on_change=self.on_prop_string_enum_change, enabled=not prop.get("readonly", False))
					else:
						edit = toga.TextInput(id=path, value=prop.get("value", None), readonly = prop.get("readonly", True), on_confirm=self.on_prop_string_change)
					box.add(label)
					box.add(edit)
				case "float":
					label = toga.Label(f"{inputname} Preamp {self.instance.prop_display_name(name)}")
					edit = None
					if "values" in prop:
						edit = toga.Selection(id=path, items=[f"{v:.1F}" for v in prop["values"]], value=prop.get("value", None), on_change=self.on_prop_int_enum_change, enabled=not prop.get("readonly", False))
					else:
						edit = toga.NumberInput(id=path, value=prop.get("value", None), readonly = prop.get("readonly", False), on_change=self.on_prop_int_change, min=prop.get("min", None), max=prop.get("max", None), step=1.0)
					box.add(label)
					box.add(edit)
				case "int" | "int64" | "pointer":
					label = toga.Label(f"{inputname} Preamp {self.instance.prop_display_name(name)}")
					edit = None
					if "values" in prop:
						edit = toga.Selection(id=path, items=[str(v) for v in prop["values"]], value=prop.get("value", None), on_change=self.on_prop_int_enum_change, enabled=not prop.get("readonly", False))
					else:
						edit = toga.NumberInput(id=path, value=prop.get("value", None), readonly = prop.get("readonly", False), on_change=self.on_prop_int_change, min=prop.get("min", None), max=prop.get("max", None), step=1.0)
					box.add(label)
					box.add(edit)
		box.add(toga.Button(f"{inputname} &Sends", on_press=self.open_input_sends))
		if sys.executable.find("python") != -1:
			box.add(toga.Button("&Preamp Effects", on_press=self.open_preamp_effects_dialog))
		return box

	def build_output_widgets(self, outp: int) -> Optional[toga.Box]:
		output = self.instance.get_output(0, outp)
		if "Active" in output["properties"] and not output["properties"]["Active"]["value"]:
			return None
		if output is None:
			return None
		box = toga.Box(style=Pack(direction = COLUMN, padding=5))
		props = output["properties"]
		outputname = props["Name"]["value"]
		for name, prop in props.items():
			if name not in self.ui_required_output_props or "value" not in prop:
				continue
			path = f"/devices/0/outputs/{outp}/{name}/value"
			match prop["type"]:
				case "bool":
					toggle = toga.Switch(f"{outputname} {self.instance.prop_display_name(name)}", id=path, value=prop.get("value", False), enabled = not prop["readonly"] if "readonly" in prop else True, on_change=self.on_prop_bool_toggle)
					box.add(toggle)
				case "string":
					label = toga.Label(f"{outputname} {self.instance.prop_display_name(name)}")
					edit = None
					if "values" in prop:
						edit = toga.Selection(id=path, items=prop["values"], value=prop.get("value", None), on_change=self.on_prop_string_enum_change, enabled=not prop.get("readonly", False))
					else:
						edit = toga.TextInput(id=path, value=prop.get("value", None), readonly = prop.get("readonly", True), on_confirm=self.on_prop_string_change)
					box.add(label)
					box.add(edit)
				case "float":
					label = toga.Label(f"{outputname} {self.instance.prop_display_name(name)}")
					edit = None
					if "values" in prop:
						edit = toga.Selection(id=path, items=[f"{v:.1F}" for v in prop["values"]], value=prop.get("value", None), on_change=self.on_prop_int_enum_change, enabled=not prop.get("readonly", False))
					else:
						edit = toga.NumberInput(id=path, value=prop.get("value", None), readonly = prop.get("readonly", False), on_change=self.on_prop_int_change, min=prop.get("min", None), max=prop.get("max", None), step=1.0)
					box.add(label)
					box.add(edit)
				case "int" | "int64" | "pointer":
					label = toga.Label(f"{outputname} {self.instance.prop_display_name(name)}")
					edit = None
					if "values" in prop:
						edit = toga.Selection(id=path, items=[str(v) for v in prop["values"]], value=prop.get("value", None), on_change=self.on_prop_int_enum_change, enabled=not prop.get("readonly", False))
					else:
						edit = toga.NumberInput(id=path, value=prop.get("value", None), readonly = prop.get("readonly", False), on_change=self.on_prop_int_change, min=prop.get("min", None), max=prop.get("max", None), step=1.0)
					box.add(label)
					box.add(edit)
		return box

	def build_aux_widgets(self, auxp: int) -> Optional[toga.Box]:
		aux = self.instance.get_aux(0, auxp)
		if "Active" in aux["properties"] and not aux["properties"]["Active"]["value"]:
			return None
		if aux is None:
			return None
		box = toga.Box(style=Pack(direction = COLUMN, padding=5))
		props = aux["properties"]
		auxname = props["Name"]["value"]
		for name, prop in props.items():
			if name not in self.ui_required_aux_props or "value" not in prop:
				continue
			path = f"/devices/0/auxs/{auxp}/{name}/value"
			match prop["type"]:
				case "bool":
					toggle = toga.Switch(f"{auxname} {self.instance.prop_display_name(name)}", id=path, value=prop.get("value", False), enabled = not prop["readonly"] if "readonly" in prop else True, on_change=self.on_prop_bool_toggle)
					box.add(toggle)
				case "string":
					label = toga.Label(f"{auxname} {self.instance.prop_display_name(name)}")
					edit = None
					if "values" in prop:
						edit = toga.Selection(id=path, items=prop["values"], value=prop.get("value", None), on_change=self.on_prop_string_enum_change, enabled=not prop.get("readonly", False))
					else:
						edit = toga.TextInput(id=path, value=prop.get("value", None), readonly = prop.get("readonly", True), on_confirm=self.on_prop_string_change)
					box.add(label)
					box.add(edit)
				case "float":
					label = toga.Label(f"{auxname} {self.instance.prop_display_name(name)}")
					edit = None
					if "values" in prop:
						edit = toga.Selection(id=path, items=[f"{v:.1F}" for v in prop["values"]], value=prop.get("value", None), on_change=self.on_prop_int_enum_change, enabled=not prop.get("readonly", False))
					else:
						edit = toga.NumberInput(id=path, value=prop.get("value", None), readonly = prop.get("readonly", False), on_change=self.on_prop_int_change, min=prop.get("min", None), max=prop.get("max", None), step=1.0)
					box.add(label)
					box.add(edit)
				case "int" | "int64" | "pointer":
					label = toga.Label(f"{auxname} {self.instance.prop_display_name(name)}")
					edit = None
					if "values" in prop:
						edit = toga.Selection(id=path, items=[str(v) for v in prop["values"]], value=prop.get("value", None), on_change=self.on_prop_int_enum_change, enabled=not prop.get("readonly", False))
					else:
						edit = toga.NumberInput(id=path, value=prop.get("value", None), readonly = prop.get("readonly", False), on_change=self.on_prop_int_change, min=prop.get("min", None), max=prop.get("max", None), step=1.0)
					box.add(label)
					box.add(edit)
		box.add(toga.Button(f"{auxname} &Sends", on_press=self.open_aux_sends, id=str(auxp)))
		return box

	async def try_connecting_locally(self):
		try:
			network.instance = network.NetworkManager()
			self.instance = network.instance
			await self.instance.preload_tree("127.0.0.1")
			await self.initialize()
		except Exception:
			if await self.main_window.dialog(toga.QuestionDialog("Alert", "It does not appear that the UA console is running on this system. Would you like to connect to a remote UA console?")):
				try:
					self.connection_dialog = ConnectionRequester(self.handle_connection_selection)
					self.connection_dialog.show()
				except Exception as e:
					await self.main_window.dialog(toga.ErrorDialog("Error", f"No connection to the remote UA console could be established. Reason: {str(e)}"))
					self.exit()
			else:
				self.exit()

	async def handle_connection_selection(self, ipaddr: Union[IPv4Address, IPv6Address]):
		try:
			network.instance = network.NetworkManager()
			self.instance = network.instance
			await self.instance.preload_tree(ipaddr)
			await self.initialize()
		except Exception as e:
			await self.main_window.dialog(toga.ErrorDialog("Error", f"No connection to the remote UA console could be established. Reason: {str(e)}"))
			self.exit()


	async def initialize(self):
		self.main_window.title = f"{self.formal_name} [{self.instance.get('/devices/0/DeviceName/value')}]"
		events.register_events()
		self.ui_inputs_label = toga.Label("Inputs", style=Pack(padding=5))
		self.ui_inputs_list = toga.Selection(style=Pack(padding=5), on_change=self.on_input_selected, accessor="name")
		self.ui_inputs_box = toga.Box()
		self.build_inputs_list()
		self.ui_inputs_box.add(self.ui_inputs_label)
		self.ui_inputs_box.add(self.ui_inputs_list)
		self.input_details_box = toga.Box()
		self.ui_inputs_box.add(self.input_details_box)
		self.tab_container.content.append("Inputs", self.ui_inputs_box)
		self.ui_outputs_list_label = toga.Label("Outputs")
		self.ui_outputs_list = toga.Selection(on_change=self.on_output_selected, accessor="name")
		self.build_outputs_list()
		self.ui_outputs_box = toga.Box()
		self.ui_outputs_box.add(self.ui_outputs_list_label)
		self.ui_outputs_box.add(self.ui_outputs_list)
		self.output_details_box = toga.Box()
		self.ui_outputs_box.add(self.output_details_box)
		self.tab_container.content.append("Outputs", self.ui_outputs_box)
		self.ui_auxs_list_label = toga.Label("AUXs")
		self.ui_auxs_list = toga.Selection(on_change=self.on_aux_selected, accessor="name")
		self.build_auxs_list()
		self.ui_auxs_box = toga.Box()
		self.ui_auxs_box.add(self.ui_auxs_list_label)
		self.ui_auxs_box.add(self.ui_auxs_list)
		self.aux_details_box = toga.Box()
		self.ui_auxs_box.add(self.aux_details_box)
		self.tab_container.content.append("AUXs", self.ui_auxs_box)
		self.main_container.add(self.tab_container)
		for prop in self.ui_required_input_props:
			signal(prop).connect(self.on_ui_required_input_prop_changed)
		for prop in self.ui_required_preamp_props:
			signal(prop).connect(self.on_ui_required_input_preamp_prop_changed)
		for prop in self.ui_required_output_props:
			signal(prop).connect(self.on_ui_required_output_prop_changed)
		for prop in self.ui_required_aux_props:
			signal(prop).connect(self.on_ui_required_aux_prop_changed)

	async def on_ui_required_input_prop_changed(self, sender, **kwargs):
		path = kwargs["path"]
		data = kwargs["data"]
		widget = None
		if len(self.input_details_box.children) > 0:
			for b in self.input_details_box.children:
				for w in b.children:
					if w.id == path:
						widget = w
						break
		if widget is None:
			return
		handler = widget.on_change
		widget.on_change = None
		widget.value = data
		widget.on_change = handler

	async def on_ui_required_input_preamp_prop_changed(self, sender, **kwargs):
		path = kwargs["path"]
		data = kwargs["data"]
		widget = None
		if len(self.input_details_box.children) > 0:
			for b in self.input_details_box.children:
				for w in b.children:
					if w.id == path:
						widget = w
						break
		if widget is None:
			return
		handler = widget.on_change
		widget.on_change = None
		widget.value = data
		widget.on_change = handler

	async def on_ui_required_output_prop_changed(self, sender, **kwargs):
		path = kwargs["path"]
		data = kwargs["data"]
		widget = None
		if len(self.output_details_box.children) > 0:
			for b in self.output_details_box.children:
				for w in b.children:
					if w.id == path:
						widget = w
						break
		if widget is None:
			return
		handler = widget.on_change
		widget.on_change = None
		widget.value = data
		widget.on_change = handler

	async def on_ui_required_aux_prop_changed(self, sender, **kwargs):
		path = kwargs["path"]
		data = kwargs["data"]
		widget = None
		if len(self.aux_details_box.children) > 0:
			for b in self.aux_details_box.children:
				for w in b.children:
					if w.id == path:
						widget = w
						break
		if widget is None:
			return
		handler = widget.on_change
		widget.on_change = None
		widget.value = data
		widget.on_change = handler

	def build_inputs_list(self):
		inputs = self.instance.get_inputs(0)
		data = []
		for id, input in inputs.items():
			if "Active" in input["properties"] and not input["properties"]["Active"]["value"]:
				continue
			data.append({"name": input["properties"]["Name"]["value"], "input_id": id})
		self.ui_inputs_list.items = data
		self.ui_inputs_list.value = self.ui_inputs_list.items[0]

	def build_outputs_list(self):
		outputs = self.instance.get_outputs(0)
		data = []
		for id, output in outputs.items():
			if "Active" in output["properties"] and not output["properties"]["Active"]["value"]:
				continue
			data.append({"name": output["properties"]["Name"]["value"], "output_id": id})
		self.ui_outputs_list.items = data
		self.ui_outputs_list.value = self.ui_outputs_list.items[0]

	def build_auxs_list(self):
		auxs = self.instance.get_auxs(0)
		data = []
		for id, aux in auxs.items():
			if "Active" in aux["properties"] and not aux["properties"]["Active"]["value"]:
				continue
			data.append({"name": aux["properties"]["Name"]["value"], "aux_id": id})
		self.ui_auxs_list.items = data
		self.ui_auxs_list.value = self.ui_auxs_list.items[0]

	async def on_prop_bool_toggle(self, widget, *args, **kwargs):
		await self.instance.send_request(f"set {widget.id} {str(widget.value).lower()}")

	async def on_prop_string_enum_change(self, widget, *args, **kwargs):
		await self.instance.send_request(f"set {widget.id} {widget.value}")

	async def on_prop_string_change(self, widget, *args, **kwargs):
		await self.instance.send_request(f"set {widget.id} {widget.value}")

	async def on_prop_int_enum_change(self, widget, *args, **kwargs):
		await self.instance.send_request(f"set {widget.id} {widget.value}")

	async def on_prop_int_change(self, widget, *args, **kwargs):
		await self.instance.send_request(f"set {widget.id} {widget.value}")

	async def on_prop_float_change(self, widget, *args, **kwargs):
		await self.instance.send_request(f"set {widget.id} {widget.value}")

	def on_input_selected(self, widget, *args, **kwargs):
		if widget.value is None:
			return
		self.input_details_box.clear()
		self.currently_selected_input = widget.value.input_id
		box = self.build_input_widgets(int(widget.value.input_id))
		if box is None:
			return
		self.input_details_box.add(box)

	def on_output_selected(self, widget, *args, **kwargs):
		if widget.value is None:
			return
		self.output_details_box.clear()
		self.currently_selected_output = widget.value.output_id
		box = self.build_output_widgets(int(widget.value.output_id))
		if box is None:
			return
		self.output_details_box.add(box)

	def on_aux_selected(self, widget, *args, **kwargs):
		if widget.value is None:
			return
		self.aux_details_box.clear()
		self.currently_selected_aux = widget.value.aux_id
		box = self.build_aux_widgets(int(widget.value.aux_id))
		if box is None:
			return
		self.aux_details_box.add(box)

	def open_input_sends(self, widget, *args, **kwargs):
		dialog = SendsDialog(0, SendsType.INPUT, self.currently_selected_input)
		dialog.build()
		dialog.show()

	def open_aux_sends(self, widget, *args, **kwargs):
		dialog = SendsDialog(0, SendsType.AUX, self.currently_selected_aux)
		dialog.build()
		dialog.show()

	def open_preamp_effects_dialog(self, widget, *args, **kwargs):
		dialog = PreampEffectsDialog(0, self.currently_selected_input)
		dialog.show()

	async def handle_exit(self, app, **kwargs):
		speech.deinit()
		if self.log_file is not None and not self.log_file.closed:
			await self.log_file.close()
			signal("NewPacket").disconnect(self.on_new_packet)
		if self.profiler is not None:
			self.profiler.disable()
			self.profiler.print_stats()
		return True

	async def export_tree(self, command, **kwargs):
		if self.instance is None:
			await self.main_window.dialog(toga.ErrorDialog("Error", "UAAccess is not connected to a device!"))
			return
		fname = await self.main_window.dialog(toga.SaveFileDialog("Specify schema file name", "schema.zip", ["zip"]))
		if fname is None:
			await self.main_window.dialog(toga.ErrorDialog("Error", "Please specify a file name for schema export."))
			return
		with zipfile.ZipFile(fname, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9, allowZip64=True) as zipf:
			await self.add_properties_to_zip(zipf, self.instance.tree["data"]["properties"], '')
			await self.add_commands_to_zip(zipf, self.instance.tree["data"]["commands"], '')
			if "children" in self.instance.tree["data"]:
				await self.recurse_children(zipf, self.instance.tree["data"]["children"], '')
			await self.main_window.dialog(toga.InfoDialog("Done", f"Schema exported to {fname}. Please visit https://github.com/uaaccess/uaaccess/issues, click 'New issue', select 'Schema Dump', enter all requested details, and attach the dump, then click submit."))

	async def enable_packet_logging(self, command, **kwargs):
		fname = await self.main_window.dialog(toga.SaveFileDialog("Specify packet log file", "packets.log", ["log", "txt"]))
		if fname is None:
			await self.main_window.dialog(self.ErrorDialog("Error", "Please specify a file name for schema export."))
			return
		try:
			if self.log_file is not None and not self.log_file.closed:
				await self.log_file.close()
			self.log_file = await aiofiles.open(fname, "w")
			for packet in self.instance.packet_log:
				json.dump(packet, self.log_file, indent=4)
				await self.log_file.write('\n')
			self.instance.packet_log.clear()
			signal("NewPacket").connect(self.on_new_packet)
		except OSError as e:
			await self.main_window.dialog(toga.ErrorDialog("Error", f"Could not open file for writing: {str(e)}"))

	async def on_new_packet(self, sender, *args, **kwargs):
		packet = kwargs["packet"]
		if self.log_file is not None and not self.log_file.closed:
			json.dump(packet, self.log_file, indent=4)
			await self.log_file.write('\n')
			self.instance.packet_log.clear()

	async def add_properties_to_zip(self, zipf, properties, path):
		json_data = json.dumps(properties, indent=4)
		zipf.writestr(os.path.join(path, "properties.json"), json_data)

	async def add_commands_to_zip(self, zipf, properties, path):
		json_data = json.dumps(properties, indent=4)
		zipf.writestr(os.path.join(path, "commands.json"), json_data)

	async def recurse_children(self, zipf, children, base_path):
		for child_name, child_data in children.items():
			child_path = os.path.normpath(os.path.join(base_path, child_name))
			zipf.writestr(child_path + '/', '')
			if "properties" in child_data:
				await self.add_properties_to_zip(zipf, child_data["properties"], child_path)
			if "commands" in child_data:
				await self.add_commands_to_zip(zipf, child_data["commands"], child_path)
			if "children" in child_data:
				await self.recurse_children(zipf, child_data["children"], child_path)

	def handle_exception(self, loop, context):
		asyncio.create_task(self.handle_exception_async(loop, context))

	async def handle_exception_async(self, loop, context):
		await self.main_window.dialog(toga.ErrorDialog("Critical error", "A critical error occurred and UAAccess has crashed. The error and any associated context will be copied to your clipboard when you close this dialog. Please open an issue on the UAAccess issue tracker and include this information in your bug report to assist us in fixing this problem."))
		ctx = []
		ctx.append(f"Time: {time.ctime()} ({time.time()}, {time.time_ns()})")
		ctx.append(f"Loop: {loop}")
		ctx.append("Context:")
		for key, value in context.items():
			ctx.append(f"{key}: {value}")
		ctx.append("Traceback:")
		ctx.append(''.join(traceback.format_exception(context["exception"])))
		clipboard.copy(os.linesep.join(ctx))
		self.exit()

	async def is_internet_available(self) -> bool:
		try:
			await aioping.ping("google.com")
			return True
		except socket.error:
			return False
		except NotImplementedError:
			try:
				reader, writer = await asyncio.wait_for(asyncio.open_connection("google.com", 80, limit=2**32), 1)
				_ = await reader.read()
				writer.close()
				await writer.wait_closed()
				return True
			except (socket.error, TimeoutError):
				return False

	async def is_installed(self)->bool:
		is_installed = False
		if sys.platform == "win32":
			guid = create_unicode_buffer(39)
			product_name = create_unicode_buffer(io.DEFAULT_BUFFER_SIZE)
			context=c_int32(0)
			buf_size = c_ulong(io.DEFAULT_BUFFER_SIZE)
			i = 0
			while True:
				buf_size = c_ulong(io.DEFAULT_BUFFER_SIZE)
				res = MsiEnumProductsEx(None, None, MSIINSTALLCONTEXT_USERMANAGED | MSIINSTALLCONTEXT_USERUNMANAGED | MSIINSTALLCONTEXT_MACHINE, i, guid, byref(context), None, None)
				if res == ERROR_NO_MORE_ITEMS:
					break
				if res != ERROR_SUCCESS:
					# todo: log the error here
					continue
				res = MsiGetProductInfoEx(guid, None, context, INSTALLPROPERTY_INSTALLEDPRODUCTNAME, product_name, byref(buf_size))
				if res != ERROR_SUCCESS:
					# Todo: log the error here
					continue
				state = MsiQueryProductState(guid)
				if product_name.value == self.formal_name and state.value == INSTALLSTATE_DEFAULT:
					is_installed = True
					break
				i += 1
		else:
			try:
				async with aiofiles.open(f"/var/db/receipts/{self.app_id}.uaaccess.plist", "rb") as f:
					data = await f.read()
					plist = plistlib.loads(data)
					if plist and "packageVersion" in plist and plist["packageVersion"] == self.app.version:
						is_installed = True
			except (FileNotFoundError, plistlib.InvalidFileException):
				pass
		return is_installed

	async def get_required_asset(self, assets, is_installed):
		asset_criteria = {
			("win32", True): ".msi",
			("win32", False): ".zip",
			("darwin", True): ".pkg",
			("darwin", False): ".dmg",
		}
		platform = sys.platform
		desired_extension = asset_criteria.get((platform, is_installed))
		if not desired_extension:
			return None
		return next((asset for asset in assets if asset.name.lower().endswith(desired_extension)), None)

	async def do_update_check(self):
		if not await self.is_internet_available():
			return
		g = Github()
		repo = g.get_repo("uaaccess/uaaccess")
		try:
			latest_release = repo.get_latest_release()
			tag_name = latest_release.tag_name.lstrip('vV')
			parsed_version = version.parse(tag_name)
			current_version = version.parse(self.app.version.lstrip('vV'))
			if parsed_version > current_version:
				is_installed = await self.is_installed()
				if not is_installed:
					await self.dialog(toga.InfoDialog("Update available", f"UAAccess {parsed_version!s} is available! Please visit https://uaaccess.org to download it."))
					return
				perform_update = await self.dialog(toga.QuestionDialog("Update available", "An update to UAAccess is available. Would you like to upgrade now?"))
				if perform_update:
					try:
						assets = latest_release.get_assets()
						required_asset = await self.get_required_asset(assets, is_installed)
						dialog = UpdaterDialog(required_asset)
						dialog.show()
					except GithubException:
						await self.dialog(toga.ErrorDialog("Error", "The update package could not be acquired. Please try again later."))
						return
		except (GithubException, InvalidVersion):
			return

def main():
	return UAAccess()

