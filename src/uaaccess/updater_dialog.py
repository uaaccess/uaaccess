import asyncio
import subprocess
import sys

import aiofiles
import aiohttp
import toga
from github import GitReleaseAsset
from toga.style import Pack
from toga.style.pack import COLUMN


class UpdaterDialog(toga.Window):
	def __init__(self, asset: GitReleaseAsset):
		super().__init__(title="Downloading update", size=(400, 200))
		self.content = toga.Box(style=Pack(direction=COLUMN, padding=10))
		self.content.add(toga.Label("Please wait while the update is downloaded"))
		self.update_progress = toga.ProgressBar()
		self.content.add(self.update_progress)
		self.cancel_button = toga.Button("Cancel", on_press=self.cancel_download)
		self.content.add(self.cancel_button)
		self.download_task = self.app.loop.create_task(self.download_update(asset))

	async def download_update(self, asset: GitReleaseAsset):
		self.update_progress.start()
		destination = self.app.paths.cache/asset.name
		try:
			async with aiohttp.ClientSession() as client, client.get(asset.browser_download_url) as resp:
				resp.raise_for_status()
				total_size = resp.headers.get('Content-Length')
				if total_size is None:
					total_size = asset.size
				async with aiofiles.open(destination, "wb") as f:
					downloaded = 0
					chunk_size = 1024
					async for chunk in resp.content.iter_chunked(chunk_size):
						if chunk:
							await f.write(chunk)
							downloaded += len(chunk)
							if total_size > 0:
								progress = downloaded / total_size * 100
								self.update_progress.value = progress
			self.update_progress.stop()
			await self.app.dialog(toga.InfoDialog("Done", "The update has been downloaded and is ready to be installed. Click okay to proceed with the installation."))
			if sys.platform == "win32":
				subprocess.Popen(f"msiexec {destination!s}")
			else:
				subprocess.Popen(f"open {destination!s}")
			self.app.request_exit()
		except asyncio.CancelledError:
			self.update_progress.stop()
			if destination.exists():
				await aiofiles.os.remove(destination)
			return
		except Exception as e:
			await self.app.dialog(toga.ErrorDialog("Error", f"Update download failed: {e!s}"))
			return

	async def cancel_download(self):
		self.download_task.cancel()
