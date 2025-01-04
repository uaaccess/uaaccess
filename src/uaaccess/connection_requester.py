# SPDX-License-Identifier: GPL-3.0-or-later

import inspect
from ipaddress import ip_address

import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW


class ConnectionRequester(toga.Window):
	def __init__(self, on_submit):
		super().__init__(title="Enter connection information", size=(400, 200))
		self.on_submit = on_submit

		self.content = toga.Box(style=Pack(direction=COLUMN, padding=10))
		self.content.add(toga.Label("Enter connection information"))

		self.ipaddr = toga.TextInput(on_confirm =self.connect)
		self.content.add(toga.Label('Enter IP address:'))
		self.content.add(self.ipaddr)
		self.ipaddr.focus()

		button_box = toga.Box(style=Pack(direction=ROW, padding_top=15))
		btn_connect = toga.Button('Connect', on_press=self.connect, style=Pack(flex=1))
		button_box.add(btn_connect)
		self.content.add(button_box)

	def connect(self, widget):
		try:
			addr = ip_address(self.ipaddr.value)
			if inspect.iscoroutinefunction(self.on_submit):
				self.app.loop.create_task(self.on_submit(addr))
			else:
				self.on_submit(addr)
			self.close()
		except ValueError as e:
			self.error_dialog("Error", str(e))

