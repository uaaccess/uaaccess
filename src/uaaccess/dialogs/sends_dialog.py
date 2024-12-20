import toga
from blinker import signal
from .. import network
from enum import Enum

class SendsType (Enum):
	INPUT = 0
	AUX = 1

class SendsDialog(toga.Window):
	def __init__(self, device_id: int, sends_type: SendsType, id: int):
		assert isinstance(sends_type, SendsType), "Invalid sends type argument!"
		if sends_type == SendsType.INPUT:
			super().__init__(title=f"Edit Sends for {network.instance.get(f"/devices/{device_id}/inputs/{id}/Name/value")}", size=(400, 200))
		else:
			super().__init__(title=f"Edit Sends for {network.instance.get(f"/devices/{device_id}/auxs/{id}/Name/value")}", size=(400, 200))
		signal("Gain").connect(self.on_send_gain_changed)
		self.sends_content = toga.Box()
		self.type_id = id
		self.device = device_id
		self.instance = network.instance
		self.content = self.sends_content
		self.sends_type = sends_type

	def build(self):
		sends = None
		if self.sends_type == SendsType.INPUT:
			sends = self.instance.get_all_input_sends(self.device, self.type_id)
		else:
			sends = self.instance.get_all_aux_sends(self.device, self.type_id)
		for id, send in sends.items():
			if self.sends_type == SendsType.INPUT:
				path = f"/devices/{self.device}/inputs/{self.type_id}/sends/{id}/Gain/value"
			else:
				path = f"/devices/{self.device}/auxs/{self.type_id}/sends/{id}/Gain/value"
			sendname = send["properties"]["Name"]["value"]
			val = send["properties"]["Gain"]["value"] if "value" in send["properties"]["Gain"] else None
			default = send["properties"]["Gain"]["default"]
			min = send["properties"]["Gain"]["min"]
			max = send["properties"]["Gain"]["max"]
			label = toga.Label(f"{sendname} Gain")
			edit = toga.NumberInput(id=path, step=1.0, min=min, max = max, value = val if val is not None else default, on_change=self.on_prop_float_change)
			self.sends_content.add(label)
			self.sends_content.add(edit)
		self.sends_content.add(toga.Button("&Close", on_press=self.close_window))

	async def on_send_gain_changed(self, sender, **kwargs):
		path = kwargs["path"]
		data = kwargs["data"]
		for send_widget in self.sends_content.children:
			if send_widget.id == path:
				handler = send_widget.on_change
				send_widget.on_change = None
				send_widget.value = data
				send_widget.on_change = handler

	async def on_prop_float_change(self, widget, *args, **kwargs):
		await self.instance.send_request(f"set {self.uuid_map[widget.id]} {widget.value}")

	def close_window(self, widget, *args, **kwargs):
		self.close()
