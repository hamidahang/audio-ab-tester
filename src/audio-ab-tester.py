import sys, os
import tkinter as tk
from tkinter import filedialog, messagebox, Scale
from pydub import AudioSegment
from mutagen import File as MutagenFile
import simpleaudio as sa
from PIL import Image, ImageTk
import os
import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "icons")

# === Color Configuration ===
# Default color scheme - can be customized
COLOR_SCHEME = {
    "background": "#5599b0",       # Main background color
    "panel_bg": "#232323",         # Panel background color (set to black to match image)
    "info_text_bg": "#232323",     # Background color for info text area
    "info_text_fg": "#5599b0",     # Text color for info text area
    "waveform_bg": "#232323",      # Background color for waveform
    "waveform_line": "#ffffff",    # Waveform line color
    "progress_line": "#5599b0",    # Progress indicator color
    "button_bg": "#232323",        # Button background color
    "button_fg": "#232323",          # Button text color
    "meter_green": "#00FF00",      # LED meter green color
    "meter_yellow": "#FFFF00",     # LED meter yellow color
    "meter_red": "#FF0000",        # LED meter red color
    "volume_slider_bg": "#232323", # Volume slider background
    "volume_slider_fg": "#5599b0", # Volume slider foreground
}

# === Background Configuration ===
USE_BACKGROUND_IMAGE = True
BACKGROUND_COLOR = COLOR_SCHEME["background"]
BACKGROUND_IMAGE_PATH = os.path.join(ICON_DIR, "player_bg.png")
BACKGROUND_X = 0
BACKGROUND_Y = 0
BACKGROUND_WIDTH = 1000
BACKGROUND_HEIGHT = 750
BACKGROUND_ALPHA = 100

# === Animation Configuration ===
USE_ANIMATED_GIF = False
GIF_PATH = os.path.join(SCRIPT_DIR, "az_cassette_animation4.gif")
GIF_WIDTH = 219
GIF_HEIGHT = 145
GIF_X = 390
GIF_Y = 385

# === Panel Configuration ===
# Updated panel dimensions and positions to fit the black areas
PANEL_WIDTH = 330   # Width to fit inside black panels
PANEL_HEIGHT = 190  # **ADJUSTED: Estimated height for the black rectangle based on discussion**
LEFT_PANEL_X = 45   # X position for left panel (from Photoshop measurement)
LEFT_PANEL_Y = 285  # Y position for left panel (from Photoshop measurement)
RIGHT_PANEL_X = 640 # X position for right panel (from Photoshop measurement)
RIGHT_PANEL_Y = 285 # Y position for right panel (from Photoshop measurement)

# also check (self.info_text) & (self.waveform_fig) for size adjustments

class LEDMeter(tk.Canvas):
    def __init__(self, parent, width=200, height=20, segments=20, **kwargs):
        super().__init__(parent, width=width, height=height, highlightthickness=0, **kwargs)
        self.segments = segments
        self.width = width
        self.height = height

        # Calculate segment width
        self.segment_width = width / segments
        self.segment_padding = 1  # Space between segments

        # Initialize with all segments off
        self.level = 0
        self.draw_segments()

    def draw_segments(self):
        """Draw the meter segments with appropriate colors"""
        self.delete("all")  # Clear the canvas

        for i in range(self.segments):
            # Determine segment color based on position
            if i < self.segments * 0.7:  # First 70% are green
                color = COLOR_SCHEME["meter_green"]
            elif i < self.segments * 0.9:  # Next 20% are yellow
                color = COLOR_SCHEME["meter_yellow"]
            else:  # Last 10% are red
                color = COLOR_SCHEME["meter_red"]

            # Calculate segment position
            x1 = i * self.segment_width
            y1 = 0
            x2 = (i + 1) * self.segment_width - self.segment_padding
            y2 = self.height

            # Draw the segment with lower brightness if not active
            if i < self.level:
                self.create_rectangle(x1, y1, x2, y2, fill=color, outline="")
            else:
                # Create a dimmed version for inactive segments
                dim_color = self.dim_color(color, factor=0.3)
                self.create_rectangle(x1, y1, x2, y2, fill=dim_color, outline="")

    def set_level(self, level_percent):
        """Set the meter level (0-100%)"""
        level = int((self.segments * level_percent) / 100)
        if level != self.level:
            self.level = level
            self.draw_segments()

    @staticmethod
    def dim_color(hex_color, factor=0.3):
        """Dim a hex color by the given factor"""
        # Convert hex to RGB
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)

        # Dim the color
        r = int(r * factor)
        g = int(g * factor)
        b = int(b * factor)

        # Convert back to hex
        return f"#{r:02x}{g:02x}{b:02x}"

class VolumeControl(tk.Frame):
    def __init__(self, parent, **kwargs):
        bg_color = kwargs.pop('bg', COLOR_SCHEME["background"])
        super().__init__(parent, bg=bg_color, **kwargs)

        # Volume slider - adjusted width for new panel size
        self.volume_slider = Scale(
            self,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            length=250,  # Increased for wider panels
            sliderlength=20,
            showvalue=False,
            bg=COLOR_SCHEME["volume_slider_bg"],
            fg=COLOR_SCHEME["volume_slider_fg"],
            troughcolor=COLOR_SCHEME["volume_slider_bg"],
            highlightthickness=0,
            command=self.update_volume
        )
        self.volume_slider.set(80)  # Default to 80%

        # Volume icon (you might want to use an icon here)
        try:
            self.icon_volume = ImageTk.PhotoImage(
                Image.open(os.path.join(SCRIPT_DIR, "icon_volume.png")).resize((24, 24))
            )
            self.volume_label = tk.Label(
                self,
                image=self.icon_volume,
                bg=bg_color
            )
        except:
            # Fallback if icon is not available
            self.volume_label = tk.Label(
                self,
                text="🔊",
                font=("NimbusSansNarrow-Bold", 8), # Adjusted font size for fallback
                bg=bg_color,
                fg="white"
            )

        # Volume value label
        self.volume_value = tk.Label(
            self,
            text="80%",
            width=4,
            bg=bg_color,
            fg="white",
            font=("NimbusSansNarrow-Bold", 8) # Adjusted font size
        )

        # Pack widgets
        self.volume_label.pack(side=tk.LEFT, padx=(0, 5))
        self.volume_slider.pack(side=tk.LEFT)
        self.volume_value.pack(side=tk.LEFT, padx=(5, 0))

        # Current volume level (0.0 to 1.0)
        self.volume = 0.8

    def update_volume(self, val):
        """Update volume when slider is moved"""
        vol = int(float(val))
        self.volume = vol / 100.0
        self.volume_value.config(text=f"{vol}%")

    def get_volume(self):
        """Return current volume (0.0 to 1.0)"""
        return self.volume

class AudioPanel:
    def __init__(self, parent, label_text):
        # Updated panel size to fit the black areas, no border, and black background
        self.frame = tk.Frame(parent, width=PANEL_WIDTH, height=PANEL_HEIGHT,
                             relief=tk.FLAT, borderwidth=0, bg=COLOR_SCHEME["info_text_bg"]) # Changed relief, borderwidth, and bg

        self.label = tk.Label(self.frame, text=label_text, font=("NimbusSansNarrow-Bold", 8), # Adjusted font size
                             bg=COLOR_SCHEME["info_text_bg"], fg="white") # Changed bg here too
        self.label.pack(pady=2) # Reduced pady

        # Load icons
        self.icon_load = ImageTk.PhotoImage(Image.open(os.path.join(ICON_DIR, "icon_eject.png")).resize((33, 40)))
        self.icon_play = ImageTk.PhotoImage(Image.open(os.path.join(ICON_DIR, "icon_play.png")).resize((33, 40)))
        self.icon_pause = ImageTk.PhotoImage(Image.open(os.path.join(ICON_DIR, "icon_pause.png")).resize((33, 40)))
        self.icon_stop = ImageTk.PhotoImage(Image.open(os.path.join(ICON_DIR, "icon_stop.png")).resize((33, 40)))

        self.load_button = tk.Button(self.frame, bg=COLOR_SCHEME["button_bg"], text="", image=self.icon_load,
                                   compound=tk.LEFT, command=self.load_audio, bd=0, highlightthickness=0)
        self.load_button.pack(pady=2) # Reduced pady

        self.controls_frame = tk.Frame(self.frame, bg=COLOR_SCHEME["info_text_bg"]) # Changed bg here
        self.controls_frame.pack(pady=2) # Reduced pady

        self.play_button = tk.Button(self.controls_frame, bg=COLOR_SCHEME["button_bg"], text="", image=self.icon_play,
                                   compound=tk.LEFT, state=tk.DISABLED, command=self.play_audio, bd=0, highlightthickness=0)
        self.play_button.pack(side=tk.LEFT, padx=5)

        self.pause_button = tk.Button(self.controls_frame, bg=COLOR_SCHEME["button_bg"], text="", image=self.icon_pause,
                                    compound=tk.LEFT, state=tk.DISABLED, command=self.pause_audio, bd=0, highlightthickness=0)
        self.pause_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = tk.Button(self.controls_frame, bg=COLOR_SCHEME["button_bg"], text="", image=self.icon_stop,
                                   compound=tk.LEFT, state=tk.DISABLED, command=self.stop_audio, bd=0, highlightthickness=0)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        # Info text with custom background and text colors - adjusted size
        self.info_text = tk.Text(self.frame, height=11, width=30, bg=COLOR_SCHEME["info_text_bg"], # Drastically reduced height
                               fg=COLOR_SCHEME["info_text_fg"], font=("NimbusSansNarrow-Bold", 8)) # Adjusted font size
        self.info_text.pack(pady=2) # Reduced pady

        # Configure waveform plot with custom background - adjusted size
        # Set figsize to a reasonable aspect ratio, but primarily control size via the canvas widget's width/height
        self.waveform_fig, self.waveform_ax = plt.subplots(figsize=(3, 1)) # Smaller figsize, but height config is key
        self.waveform_fig.patch.set_facecolor(COLOR_SCHEME["waveform_bg"])
        self.waveform_ax.set_facecolor(COLOR_SCHEME["waveform_bg"])
        # self.waveform_ax.tick_params(colors=COLOR_SCHEME["info_text_fg"])
        self.waveform_ax.tick_params(axis='y', colors=COLOR_SCHEME["info_text_fg"], labelsize=6) # Added labelsize for y-axis ticks
        for spine in self.waveform_ax.spines.values():
            spine.set_color(COLOR_SCHEME["info_text_fg"])
        self.waveform_ax.xaxis.label.set_color(COLOR_SCHEME["info_text_fg"])
        self.waveform_ax.yaxis.label.set_color(COLOR_SCHEME["info_text_fg"])
        self.waveform_ax.title.set_color(COLOR_SCHEME["info_text_fg"]) # This was the old line
        # self.waveform_ax.set_title('Waveform') # Removed this line

        self.canvas = FigureCanvasTkAgg(self.waveform_fig, master=self.frame)
        # Explicitly set the pixel width and height of the Tkinter canvas widget
        # This is critical for controlling the exact size.
        self.canvas.get_tk_widget().config(width=PANEL_WIDTH - 20, height=100) # **CRITICAL: Drastically reduced height**
        self.canvas.get_tk_widget().pack(pady=2) # Reduced pady

        # Add volume control
        self.volume_control = VolumeControl(self.frame, bg=COLOR_SCHEME["info_text_bg"]) # Changed bg here
        self.volume_control.pack(pady=2) # Reduced pady

        # Add LED meter - adjusted width for new panel size
        self.led_meter = LEDMeter(self.frame, width=300, height=20, bg=COLOR_SCHEME["info_text_bg"]) # Changed bg here
        self.led_meter.pack(pady=2) # Reduced pady

        # Audio state
        self.audio = None
        self.play_obj = None
        self.is_paused = False
        self.stop_flag = False
        self.pause_position = 0
        self.play_start_time = None
        self.progress_line = None
        self.samples = None

        # Initialize LED meter animation
        self.meter_update_id = None
        self.progress_update_id = None # New: Store the after ID for progress
        self.led_meter.set_level(0)  # Start with 0 level

    def load_audio(self):
        file_path = filedialog.askopenfilename(filetypes=[("Audio Files", "*.mp3 *.wav")])
        if not file_path:
            return
        try:
            self.audio = AudioSegment.from_file(file_path)
            metadata = MutagenFile(file_path, easy=True)
            self.display_info(file_path, metadata)
            self.draw_waveform()
            self.play_button.config(state=tk.NORMAL)
            self.pause_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.NORMAL)
            self.pause_position = 0
            self.led_meter.set_level(0)  # Reset meter
        except Exception as e:
            messagebox.showerror("Error", f"Could not load file:\n{e}")

    def display_info(self, file_path, metadata):
        self.info_text.delete(1.0, tk.END)
        info = f"File: {os.path.basename(file_path)}\n"
        info += f"Format: {self.audio.format if hasattr(self.audio, 'format') else os.path.splitext(file_path)[1][1:]}\n"
        info += f"Duration: {round(len(self.audio)/1000, 2)} sec\n"
        info += f"Sample Rate: {self.audio.frame_rate} Hz\n"
        info += f"Channels: {self.audio.channels}\n"
        if metadata:
            for key, value in metadata.items():
                info += f"{key.capitalize()}: {value}\n"
        self.info_text.insert(tk.END, info)

    def draw_waveform(self):
        try:
            self.samples = np.array(self.audio.get_array_of_samples())
            if self.audio.channels == 2:
                self.samples = self.samples.reshape((-1, 2))
                self.samples = self.samples.mean(axis=1)

            self.waveform_ax.clear()
            self.waveform_ax.plot(self.samples, color=COLOR_SCHEME["waveform_line"])
            # self.waveform_ax.set_title('Waveform') # Removed this line to remove the title
            self.waveform_ax.set_xlabel('Samples', fontsize=8) # Set font size here
            self.waveform_ax.set_ylabel('Amplitude', fontsize=8) # Set font size here

            # Restore colors after clearing
            self.waveform_ax.set_facecolor(COLOR_SCHEME["waveform_bg"])
            self.waveform_ax.tick_params(colors=COLOR_SCHEME["info_text_fg"])
            for spine in self.waveform_ax.spines.values():
                spine.set_color(COLOR_SCHEME["info_text_fg"])
            self.waveform_ax.xaxis.label.set_color(COLOR_SCHEME["info_text_fg"])
            self.waveform_ax.yaxis.label.set_color(COLOR_SCHEME["info_text_fg"])
            self.waveform_ax.title.set_color(COLOR_SCHEME["info_text_fg"])

            self.progress_line = self.waveform_ax.axvline(x=0, color=COLOR_SCHEME["progress_line"])
            self.canvas.draw()
        except Exception as e:
            self.waveform_ax.clear()
            # self.waveform_ax.set_title("Waveform unavailable") # Removed this line as well

            # Restore colors after clearing
            self.waveform_ax.set_facecolor(COLOR_SCHEME["waveform_bg"])
            self.waveform_ax.title.set_color(COLOR_SCHEME["info_text_fg"])

            self.canvas.draw()

    def play_audio(self):
        if not self.audio:
            return
        if self.play_obj and self.play_obj.is_playing():
            self.play_obj.stop()

        # Apply volume adjustment by creating a new segment
        segment = self.audio[self.pause_position:]

        # Apply volume adjustment
        volume_factor = self.volume_control.get_volume()
        if volume_factor != 1.0:
            segment = segment.apply_gain(20 * np.log10(volume_factor) if volume_factor > 0 else -100)

        self.play_obj = sa.play_buffer(
            segment.raw_data,
            num_channels=segment.channels,
            bytes_per_sample=segment.sample_width,
            sample_rate=segment.frame_rate
        )

        self.play_start_time = time.time()
        self.stop_flag = False
        self.is_paused = False
        self.update_progress_line()
        self.animate_led_meter()

    def update_progress_line(self):
        if not self.play_obj or self.is_paused or self.stop_flag:
            if self.progress_update_id:
                self.frame.after_cancel(self.progress_update_id)
                self.progress_update_id = None
            return

        elapsed = time.time() - self.play_start_time
        current_ms = self.pause_position + int(elapsed * 1000)

        if current_ms >= len(self.audio):
            self.progress_line.set_xdata([0])
            self.canvas.draw()
            return

        sample_index = int(current_ms * self.audio.frame_rate / 1000)
        self.progress_line.set_xdata([sample_index])
        self.canvas.draw()
        self.progress_update_id = self.frame.after(100, self.update_progress_line) # Store the ID here

    def animate_led_meter(self):
        """Animate the LED meter during playback"""
        if not self.play_obj or self.is_paused or self.stop_flag:
            if self.meter_update_id:
                self.frame.after_cancel(self.meter_update_id)
                self.meter_update_id = None
            self.led_meter.set_level(0)
            return

        # Calculate current position in audio
        elapsed = time.time() - self.play_start_time
        current_ms = self.pause_position + int(elapsed * 1000)

        if current_ms >= len(self.audio):
            self.led_meter.set_level(0)
            return

        # Calculate sample index range for current time window
        window_ms = 100  # 100ms window for amplitude calculation
        sample_rate = self.audio.frame_rate
        start_sample = int((current_ms - window_ms if current_ms > window_ms else 0) * sample_rate / 1000)
        end_sample = int(current_ms * sample_rate / 1000)

        # Get amplitude from samples if available
        level = 0
        if self.samples is not None and start_sample < len(self.samples) and end_sample <= len(self.samples):
            window_samples = self.samples[start_sample:end_sample]
            if len(window_samples) > 0:
                # Normalize to 0-100 range - adjust these values based on your audio dynamics
                max_amp = np.max(np.abs(window_samples))
                normalized_amp = min(100, max_amp / 32768 * 100)  # Assuming 16-bit audio

                # Apply some smoothing
                level = normalized_amp

        # Add some randomness for visual effect if level is too low
        if level < 5 and self.play_obj.is_playing():
            level = np.random.randint(5, 15)

        # Set the meter level
        self.led_meter.set_level(level)

        # Schedule next update
        self.meter_update_id = self.frame.after(50, self.animate_led_meter)

    def pause_audio(self):
        if self.play_obj and self.play_obj.is_playing():
            self.play_obj.stop()
            elapsed = time.time() - self.play_start_time
            self.pause_position += int(elapsed * 1000)
            self.is_paused = True
            if self.meter_update_id:
                self.frame.after_cancel(self.meter_update_id)
                self.meter_update_id = None
            if self.progress_update_id:
                self.frame.after_cancel(self.progress_update_id)
                self.progress_update_id = None


    def stop_audio(self):
        self.stop_flag = True
        if self.play_obj and self.play_obj.is_playing():
            self.play_obj.stop()
        self.pause_position = 0
        self.is_paused = False
        if self.progress_line:
            self.progress_line.set_xdata([0])
            self.canvas.draw()
        self.led_meter.set_level(0)
        if self.meter_update_id:
            self.frame.after_cancel(self.meter_update_id)
            self.meter_update_id = None
        if self.progress_update_id: # Cancel on stop
            self.frame.after_cancel(self.progress_update_id)
            self.progress_update_id = None


class AnimatedGIF:
    def __init__(self, parent, gif_path, canvas=None, x=0, y=0, width=None, height=None):
        self.parent = parent
        self.gif_path = gif_path
        self.canvas = canvas
        self.x = x
        self.y = y
        self.width = width
        self.height = height

        self.frames = []
        self.frame_index = 0
        self.canvas_item = None
        self.is_running = False
        self.after_id = None # New: Store the after ID

        try:
            # Load the GIF and prepare frames
            self.load_gif()
        except Exception as e:
            messagebox.showwarning("GIF Warning", f"Could not load GIF: {e}")
            # Create placeholder if GIF can't be loaded
            self.create_placeholder()

    def load_gif(self):
        """Load the GIF and convert frames to PhotoImage objects"""
        if not os.path.exists(self.gif_path):
            self.create_placeholder()
            return

        # Open the GIF file
        gif = Image.open(self.gif_path)
        self.delay = gif.info.get('duration', 100)  # Default to 100ms if not specified

        try:
            # Process all frames
            frame_count = 0
            while True:
                # Resize if dimensions are provided
                if self.width and self.height:
                    frame = gif.copy().resize((self.width, self.height), Image.LANCZOS)
                else:
                    frame = gif.copy()

                # Convert to PhotoImage
                photo_frame = ImageTk.PhotoImage(frame)
                self.frames.append(photo_frame)

                # Move to next frame
                frame_count += 1
                gif.seek(frame_count)
        except EOFError:
            # End of frames
            pass

        # If we have frames, start the animation
        if self.frames:
            # Create or place the image on canvas
            if self.canvas:
                self.canvas_item = self.canvas.create_image(
                    self.x, self.y, image=self.frames[0], anchor=tk.NW)
            else:
                # Create a label to display the GIF if no canvas
                self.label = tk.Label(self.parent, image=self.frames[0],
                                     borderwidth=0, highlightthickness=0)
                self.label.place(x=self.x, y=self.y)

            # Start animation
            self.is_running = True
            self.animate()

    def create_placeholder(self):
        """Create a placeholder if GIF can't be loaded"""
        # Create a placeholder frame
        w = self.width or 200
        h = self.height or 100
        placeholder = Image.new('RGB', (w, h), color='#dddddd')

        # Add text
        try:
            from PIL import ImageDraw, ImageFont
            draw = ImageDraw.Draw(placeholder)
            font = ImageFont.load_default()
            text = "Animated GIF\nPlaceholder"

            # Center the text
            text_width, text_height = draw.text.textsize(text, font=font) # Corrected syntax here
            position = ((w - text_width) / 2, (h - text_height) / 2)

            # Draw the text
            draw.text(position, text, fill='black', font=font)
        except Exception:
            # If text placement fails, just use the gray box
            pass

        # Convert to PhotoImage
        photo = ImageTk.PhotoImage(placeholder)
        self.frames = [photo]

        # Place the placeholder
        if self.canvas:
            self.canvas_item = self.canvas.create_image(
                self.x, self.y, image=photo, anchor=tk.NW)
        else:
            self.label = tk.Label(self.parent, image=photo,
                                 borderwidth=0, highlightthickness=0)
            self.label.place(x=self.x, y=self.y)

    def animate(self):
        """Cycle through the frames to create animation"""
        if not self.is_running:
            return

        # Move to next frame
        self.frame_index = (self.frame_index + 1) % len(self.frames)
        current_frame = self.frames[self.frame_index]

        # Update the image
        if self.canvas and self.canvas_item:
            self.canvas.itemconfig(self.canvas_item, image=current_frame)
        else:
            self.label.configure(image=current_frame)

        # Schedule the next frame
        self.after_id = self.parent.after(self.delay, self.animate) # Store the ID here

    def stop(self):
        """Stop the animation"""
        self.is_running = False
        if self.after_id: # Cancel the scheduled call if it exists
            self.parent.after_cancel(self.after_id)
            self.after_id = None

    def start(self):
        """Start or restart the animation"""
        if not self.is_running:
            self.is_running = True
            self.animate()


def setup_background(root):
    """Set up the background - either image or color"""
    # Use the global variable for configuration
    global USE_BACKGROUND_IMAGE

    if USE_BACKGROUND_IMAGE:
        try:
            # Load and process the background image
            bg_img = Image.open(BACKGROUND_IMAGE_PATH)

            # Resize if needed
            if bg_img.width != BACKGROUND_WIDTH or bg_img.height != BACKGROUND_HEIGHT:
                bg_img = bg_img.resize((BACKGROUND_WIDTH, BACKGROUND_HEIGHT))

            # Apply transparency if needed
            if BACKGROUND_ALPHA < 1.0:
                bg_img = bg_img.convert("RGBA")
                data = np.array(bg_img)
                data[..., 3] = data[..., 3] * BACKGROUND_ALPHA
                bg_img = Image.fromarray(data)

            # Convert to PhotoImage for Tkinter
            bg_photo = ImageTk.PhotoImage(bg_img)

            # Create a canvas for the background
            bg_canvas = tk.Canvas(root, width=BACKGROUND_WIDTH, height=BACKGROUND_HEIGHT,
                                 highlightthickness=0)
            bg_canvas.place(x=BACKGROUND_X, y=BACKGROUND_Y)

            # Add the image to the canvas
            bg_canvas.create_image(0, 0, image=bg_photo, anchor=tk.NW)

            # Store a reference to prevent garbage collection
            root.bg_photo = bg_photo
            root.bg_canvas = bg_canvas

            # Set panels to have transparent background
            return bg_canvas

        except Exception as e:
            messagebox.showwarning("Background Warning",
                f"Could not load background image: {e}\nFalling back to color background.")
            # Don't modify the global variable, just proceed with color background

    # If we're here, use color background
    root.configure(bg=BACKGROUND_COLOR)
    return None


def main():
    root = tk.Tk()
    root.title("Audio A/B Tester by Hamid Ahang")
    root.geometry("1000x750")

    # Setup background
    bg_canvas = setup_background(root)

    # Panels with updated positions and sizes
    left_panel = AudioPanel(root if not bg_canvas else bg_canvas, "")
    left_panel.frame.place(x=LEFT_PANEL_X, y=LEFT_PANEL_Y)

    right_panel = AudioPanel(root if not bg_canvas else bg_canvas, "")
    right_panel.frame.place(x=RIGHT_PANEL_X, y=RIGHT_PANEL_Y)

    animated_gif = None # Initialize to None
    # Add animated GIF with updated position to fit in cassette area
    if USE_ANIMATED_GIF:
        if bg_canvas:
            # If we have a canvas, add the GIF to it
            animated_gif = AnimatedGIF(root, GIF_PATH, canvas=bg_canvas,
                                      x=GIF_X, y=GIF_Y,
                                      width=GIF_WIDTH, height=GIF_HEIGHT)
        else:
            # Otherwise add directly to root
            animated_gif = AnimatedGIF(root, GIF_PATH,
                                      x=GIF_X, y=GIF_Y,
                                      width=GIF_WIDTH, height=GIF_HEIGHT)

        # Store a reference to prevent garbage collection
        root.animated_gif = animated_gif

    # --- New Cleanup Function ---
    def on_closing():
        # Stop all audio playback
        left_panel.stop_audio()
        right_panel.stop_audio()

        # Stop GIF animation if it exists
        if animated_gif:
            animated_gif.stop()

        # Destroy the main window
        root.destroy()

    # Bind the cleanup function to the window's close protocol
    root.protocol("WM_DELETE_WINDOW", on_closing)

    root.mainloop()


if __name__ == "__main__":
    main()
