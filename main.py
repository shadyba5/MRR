import tkinter as tk
import time
import threading
from pynput.mouse import Listener, Controller
from pynput import keyboard
from tkinter import messagebox

class MouseRecorderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MRR")
        self.root.geometry("300x300")

        self.prog_status = tk.StringVar()
        self.prog_status.set("Idle")
        self.status_label = tk.Label(root, textvariable=self.prog_status, font=("Arial", 12))
        self.status_label.pack(pady=10)

        self.start_record_button = tk.Button(root, text="Start Recording (CTRL+SHIFT+R)", command=self.start_recording)
        self.start_record_button.pack(pady=5)

        self.stop_record_button = tk.Button(root, text="Stop Recording (CTRL+SHIFT+X)", command=self.stop_recording)
        self.stop_record_button.pack(pady=5)
        self.stop_record_button.config(state=tk.DISABLED)

        self.start_play_button = tk.Button(root, text="Start Playing (CTRL+SHIFT+P)", command=self.start_playing)
        self.start_play_button.pack(pady=5)
        self.start_play_button.config(state=tk.DISABLED)

        self.stop_play_button = tk.Button(root, text="Stop Playing (CTRL+SHIFT+S)", command=self.stop_playing)
        self.stop_play_button.pack(pady=5)
        self.stop_play_button.config(state=tk.DISABLED)

        self.replay_count_label = tk.Label(root, text="Replay Count:")
        self.replay_count_label.pack(pady=5)
        self.replay_count_entry = tk.Entry(root)
        self.replay_count_entry.pack(pady=5)

        self.mouse = Controller()
        self.replay_count = 0
        self.is_recording = False
        self.is_playing = False
        self.recorded_events = []
        self.is_playing_or_recording = False
        self.stop_recording_event = threading.Event()

        # Variables to track mouse movement
        self.prev_x, self.prev_y = 0, 0

        # Keybinds with Shift added to each hotkey
        self.listener_keybinds = keyboard.GlobalHotKeys({
            '<shift>+<ctrl>+r': self.start_recording,
            '<shift>+<ctrl>+x': self.stop_recording,
            '<shift>+<ctrl>+p': self.start_playing,
            '<shift>+<ctrl>+s': self.stop_playing
        })

        # Start the mouse listener in a separate thread
        self.mouse_listener_thread = threading.Thread(target=self.start_mouse_listener)
        self.mouse_listener_thread.daemon = True
        self.mouse_listener_thread.start()

    def on_click(self, x, y, button, pressed):
        if self.is_recording:
            event_type = "pressed" if pressed else "released"
            timestamp = time.time()
            self.recorded_events.append((x, y, button, event_type, timestamp))

    def on_move(self, x, y):
        if self.is_recording:
            if x != self.prev_x or y != self.prev_y:
                timestamp = time.time()
                self.recorded_events.append((x, y, None, "moved", timestamp))
                self.prev_x, self.prev_y = x, y

    def start_mouse_listener(self):
        # Start the mouse listener
        with Listener(on_click=self.on_click, on_move=self.on_move) as self.mouse_listener:
            self.mouse_listener.join()

    def start_recording(self):
        if self.is_playing_or_recording:
            return

        self.is_playing_or_recording = True
        self.is_recording = True
        self.prog_status.set("Recording")
        self.start_record_button.config(state=tk.DISABLED)
        self.stop_record_button.config(state=tk.NORMAL)
        self.start_play_button.config(state=tk.DISABLED)
        self.stop_play_button.config(state=tk.DISABLED)
        self.recorded_events = []
        self.prev_x, self.prev_y = self.mouse.position

    def stop_recording(self):
        self.is_recording = False
        self.is_playing_or_recording = False
        self.prog_status.set("Idle")
        self.start_record_button.config(state=tk.NORMAL)
        self.stop_record_button.config(state=tk.DISABLED)
        if self.recorded_events:
            self.start_play_button.config(state=tk.NORMAL)

        # Set the event to signal the recording thread to stop
        self.stop_recording_event.set()

    def start_playing(self):
        if self.is_playing_or_recording or not self.recorded_events:
            return

        replay_count_input = self.replay_count_entry.get()
        if not replay_count_input.isdigit():
            # Display an error message if the input is not a valid integer
            messagebox.showerror("Error", "Please enter a valid replay count (a positive integer).")
            return

        self.is_playing_or_recording = True
        self.replay_count = int(replay_count_input)
        self.is_playing = True
        self.prog_status.set("Playing")
        self.start_record_button.config(state=tk.DISABLED)
        self.stop_record_button.config(state=tk.DISABLED)
        self.start_play_button.config(state=tk.DISABLED)
        self.stop_play_button.config(state=tk.NORMAL)

        play_thread = threading.Thread(target=self.play_events)
        play_thread.start()

    def stop_playing(self):
        self.is_playing = False
        self.is_playing_or_recording = False
        self.prog_status.set("Idle")
        self.start_record_button.config(state=tk.NORMAL)
        self.stop_play_button.config(state=tk.DISABLED)

    def play_events(self):
        try:
            for _ in range(self.replay_count):
                prev_timestamp = None
                for event in self.recorded_events:
                    if not self.is_playing:
                        break

                    x, y, button, event_type, timestamp = event

                    if prev_timestamp:
                        # Calculate the time difference between the current and previous events
                        delay = timestamp - prev_timestamp
                        time.sleep(delay)

                    prev_timestamp = timestamp

                    self.mouse.position = (x, y)
                    if event_type == "pressed":
                        self.mouse.press(button)
                    elif event_type == "released":
                        self.mouse.release(button)

                if not self.is_playing:
                    break

            self.is_playing = False
            self.is_playing_or_recording = False
            self.prog_status.set("Idle")
            self.start_record_button.config(state=tk.NORMAL)
            self.start_play_button.config(state=tk.NORMAL)
            self.stop_play_button.config(state=tk.DISABLED)

            # Clear the event after stopping the recording
            self.stop_recording_event.clear()

        except Exception as e:
            # Display an error message if an exception occurs during playing
            messagebox.showerror("Error", f"An error occurred during playing: {e}")
            self.is_playing = False
            self.is_playing_or_recording = False
            self.prog_status.set("Idle")
            self.start_record_button.config(state=tk.NORMAL)
            self.start_play_button.config(state=tk.NORMAL)
            self.stop_play_button.config(state=tk.DISABLED)

            # Clear the event after stopping the recording
            self.stop_recording_event.clear()

    def run(self):
        self.listener_keybinds.start()
        self.root.protocol("WM_DELETE_WINDOW", self.stop)  # Bind close event to stop method
        self.root.mainloop()

    def stop(self):
        self.mouse_listener.stop()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = MouseRecorderApp(root)
    app.run()
