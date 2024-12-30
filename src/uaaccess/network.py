import asyncio
import platform
import sys

if sys.platform == "darwin" and platform.machine() == "x86_64":
	import json
else:
	from cysimdjson import JSONParser
import time
from ipaddress import IPv4Address, IPv6Address
from typing import Any, Optional, Union

from blinker import signal


class NetworkManager:
	def __init__(self):
		self.writer = None
		self.reader = None
		self.tree = {}
		self.cache = {}
		self.friendly_prop_map = {
			"CRMonitorLevel": "Level",
			"DimOn": "Dim",
			"FaderLevel": "Volume",
			"IOType": "Type",
			"LowCut": "Low Cut",
			"MixToMono": "Sum",
			"MixInSource": "Source",
			"MirrorsToDigital": "Mirrors to Digital",
			"RecordPreEffects": "Record Effects",
			"SendPostFader": "Pre/Post"
		}
		if sys.platform != "darwin" or platform.machine() != "x86_64":
			self.json_parser = JSONParser()
		self.handle_events_normally = asyncio.Event()
		if sys.executable.find("python") != -1:
			self.packet_log = []

	def get_name(self, path: str, properties: list[str]) -> Optional[str]:
		if properties is None:
			raise RuntimeError("Properties were not specified in self.get_name")
		components: list[str] = path.strip('/').split('/')[:-2]
		value: Optional[str] = None
		while len(components) > 0:
			new_path: str = '/'.join(components)
			for prop in properties:
				value = self.get(f"{new_path}/{prop}/value")
				if value is not None:
					break
			if value is not None:
				break
			components.pop()
		return value

	def prop_display_name(self, name: str) -> str:
		return self.friendly_prop_map.get(name, name)

	def get_inputs(self, device: int) -> dict[str, Any]:
		inputs: dict[str, Any] = self.get(f"/devices/{device}/inputs")
		inputs = inputs["children"]
		return inputs

	def get_outputs(self, device: int) -> dict[str, Any]:
		outputs: dict[str, Any] = self.get(f"/devices/{device}/outputs")
		outputs = outputs["children"]
		return outputs

	def get_auxs(self, device: int) -> dict[str, Any]:
		auxs: dict[str, Any] = self.get(f"/devices/{device}/auxs")
		auxs= auxs["children"]
		return auxs

	def get_input(self, device: int, input: int) -> dict[str, Any]:
		inp = self.get(f"/devices/{device}/inputs/{input}")
		return inp

	def get_output(self, device: int, output: int) -> dict[str, Any]:
		outp = self.get(f"/devices/{device}/outputs/{output}")
		return outp

	def get_aux(self, device: int, aux: int) -> dict[str, Any]:
		auxp = self.get(f"/devices/{device}/auxs/{aux}")
		return auxp

	def get_preamp(self, device: int, input: int, preamp: int) -> dict[str, Any]:
		amp = self.get(f"/devices/{device}/inputs/{input}/preamps/{preamp}")
		return amp

	def get_all_input_sends(self, device: int, input: int) -> dict[str, Any]:
		sends = self.get(f"/devices/{device}/inputs/{input}/sends")
		sends= sends["children"]
		return sends

	def get_all_aux_sends(self, device: int, aux: int) -> dict[str, Any]:
		sends = self.get(f"/devices/{device}/auxs/{aux}/sends")
		sends= sends["children"]
		return sends

	def get_all_preamp_effects(self, device: int, input: int)->Optional[dict[str, Any]]:
		effects = self.get(f"/devices/{device}/inputs/{input}/preamps/0/effects")
		return None if effects is None else effects["children"]

	def get_all_plugins(self) -> Optional[dict[str, Any]]:
		plugins = self.get("/plugins")
		return None if plugins is None else plugins["children"]

	def get_all_preamp_effect_parameters(self, device: int, input: int) -> Optional[dict[str, Any]]:
		parameters = self.get(f"/devices/{device}/inputs/{input}/preamps/0/effects/0/parameters")
		return None if parameters is None else parameters["children"]

	def get(self, path: str) -> Optional[Union[dict[str, Any], bool, int, str, float]]:
		parts: list[str] = path.strip('/').split('/')
		current: Any = self.tree['data']
		for i, part in enumerate(parts):
			if 'properties' in current and part[0].isupper():
				if part in current['properties']:
					current = current['properties'][part]
				else:
					return None	 # Part not found in properties
			elif 'children' in current:
				if part in current['children']:
					current = current['children'][part]
				else:
					return None	 # Part not found in children
			else:
				# If neither 'properties' nor 'children' can handle it, check for direct key access
				if part in current:
					current = current[part]
				else:
					return None	 # Direct key not found

			if current is None:
				return None	 # Check if navigation resulted in None

		return current

	def set(self, path: str, value: Union[bool, int, str, float]):
		parts: list[str] = path.strip('/').split('/')
		current: Any = self.tree['data']
		last_part: str = parts[-1]
		for part in parts:
			if 'properties' in current and part in current['properties']:
				current = current['properties'][part]
				break
			elif 'children' in current and part in current['children']:
				current = current['children'][part]
			elif 'commands' in current and part in current['commands']:
				break
		current[last_part] = value

	async def preload_tree(self, ipaddr: Union[IPv4Address, IPv6Address]):
		self.loop = asyncio.get_running_loop()
		await self.connect_to_server(ipaddr, 4710)
		await self.send_request("get /?recursive=1")
		await self.safe_recv()
		await self.send_request("subscribe /?recursive=1")
		await self.send_request("get /uaaccess_is_ready?handle_events_normally=1")
		self.loop.create_task(self.handle_responses_continuously())

	async def safe_recv(self):
		"""Accumulate data from the socket and yield complete messages."""
		data_buffer: bytearray = bytearray()
		tmp_buffer: bytearray = await self.reader.readuntil(b'\x00')
		data_buffer.extend(tmp_buffer)
		while b'\x00' not in data_buffer:
			tmp_buffer = await self.reader.readuntil(b'\x00')
			data_buffer.extend(tmp_buffer)
		while b'\x00' in data_buffer:
			message, _, data_buffer = data_buffer.partition(b'\x00')
			if sys.executable.find("python") != -1:
				self.packet_log.append({"time": time.time(), "type": "recv", "message": message.decode()})
				await signal("NewPacket").send_async(self, packet=self.packet_log[-1])
			await self.process_message(bytes(message))

	async def send_request(self,  request: str):
		"""Sends a request to the server, ensuring it ends with '\x00'."""
		if sys.executable.find("python") != -1:
			self.packet_log.append({"time": time.time(), "type": "send", "message": request})
			await signal("NewPacket").send_async(self, packet=self.packet_log[-1])
		if not request.endswith('\x00'):
			request += '\x00'
		request = request.encode()
		self.writer.write(request)
		await self.writer.drain()

	async def connect_to_server(self, address: Union[IPv4Address, IPv6Address], port: int):
		self.reader, self.writer = await asyncio.open_connection(str(address), 4710, limit=2**32)
		if sys.executable.find("python") != -1:
			self.packet_log.append({"time": time.time(), "type": "conn", "message": None})

	async def process_message(self, message: bytes):
		resp: dict[str, Any] = {}
		if sys.platform == "darwin" and platform.machine() == "x86_64":
			resp = json.loads(message.decode())
		else:
			resp = self.json_parser.loads(message.decode()).export()
		if "path" in resp and resp["path"] == "/uaaccess_is_ready" and "parameters" in resp and "handle_events_normally" in resp["parameters"]:
			self.handle_events_normally.set()
			await signal("UAAccessInitialized").send_async(self)
			return
		if "error" in resp:
			print (f"Warning: {resp["path"]}: {resp["error"]}")
			return
		if "data" not in resp or "path" not in resp:
			print(f"Warning: received invalid response: {message}")
			return
		data: Union[dict[str, Any], int, float, bool] = resp['data']
		path: str = resp['path']
		if not isinstance(data, dict) or "children" not in data or "properties" not in data:
			self.set(path, data)
			if not self.handle_events_normally.is_set():
				return
			components: list[str] = path.strip('/').split('/')
			propname: Optional[str] = None
			if components[-1] == "value":
				propname = components[-2]
			else:
				propname = components[-1]
			sig = signal(propname)
			await sig.send_async(self, path=path, data=data)
		else:
			self.tree = resp

	async def handle_responses_continuously(self):
		while True:
			await self.safe_recv()

instance: Optional[NetworkManager] = None