import serial
import matplotlib.pyplot as plt
import numpy as np
import time

# Configure the serial connection
SERIAL_PORT = '/dev/ttyACM0'  # Replace with your Arduino's port
BAUD_RATE = 115200
arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)

# Circular progress bar configuration
beats_per_breath = 6
progress = 0
beat_times = []
beat_marker_angles = []
INTERPOLATION_STEPS = 50

# Initialize the plot
fig, ax = plt.subplots(figsize=(6, 6), subplot_kw={'projection': 'polar'})
fig.patch.set_facecolor('black')
ax.set_facecolor('black')
ax.set_theta_direction(-1)
ax.set_theta_offset(np.pi / 2)
ax.set_ylim(0, 1)
ax.axis('off')
progress_bar, = ax.plot([], [], lw=15, color='lightblue')
beat_points, = ax.plot([], [], 'ro', markersize=85)
beat_rings = []

# Screen params
screen_refresh_rate = 30 # Hz
screen_refresh_period = 1.0 / screen_refresh_rate

# Heart beat info
beat_record_len = 128 # How many beat to record
bpm_window_len = 16 # How many beats avg for bpm calculation
min_beat_interval = 0.5  # Minimum time between beats to avoid false positives
init_time = time.time()
last_frame_time = 0

def progress_to_radius(progress, breath_beat):
    radius = progress if breath_beat <= 3 else 1 - progress
    radius *= 2
    return radius

# Function to update the expanding and contracting circle and beat markers
def update_progress(progress, beat_progress_marks, breath_beat, beat_frame):
    radius = progress_to_radius(progress, breath_beat)
    theta = np.linspace(0, 2 * np.pi, 100)
    r = np.ones(100) * radius
    progress_bar.set_data(theta, r)
    if(beat_frame):
        progress_bar.set_color('red')
        r *= 1.1
    else:
        progress_bar.set_color('lightblue')

    ## Update beat markers as static lighter rings
    for ring in beat_rings:
        ring.remove()
    beat_rings.clear()
    for hist_progress, hist_breath_beat in beat_progress_marks:
        ring, = ax.plot(theta, np.ones(100) * progress_to_radius(hist_progress, hist_breath_beat), lw=2, color='red')
        beat_rings.append(ring)

    plt.draw()
    plt.pause(0.01)

# Tracks what beat we are on in the current breath
breath_beat = 1
beat_progress_marks = []
beat_frame = False

# Weighting for the bpm calculation
lin = np.linspace(0, 1, bpm_window_len+1)[-bpm_window_len:]
beat_period_weights = lin / np.sum(lin)
print('Weighting: ', beat_period_weights)

# Guess the starting beat period
bpm_init = 61.5
beat_period = 1.0 / (bpm_init / 60)
beat_times.append(0)

# Main loop
try:
    plt.ion()
    plt.show()

    while True:
        current_time = time.time() - init_time

        # Estimate the extrapolated progress bar progress
        min_prog = max(0, breath_beat-1) / beats_per_breath
        max_prog = breath_beat / beats_per_breath
        progress = ((current_time - beat_times[-1]) / beat_period) * (max_prog - min_prog) + min_prog
        # Read from the serial port
        if arduino.in_waiting > 0:
            line = arduino.readline().decode('utf-8').strip()
            if line == 'BEAT':
                if len(beat_times) == 0 or (current_time - beat_times[-1]) > min_beat_interval:
                    beat_times.append(current_time)
                    beat_progress_marks += [(progress, breath_beat)]
                    beat_frame = True
                    # Increment the beat
                    breath_beat += 1
                    # Reset the breath beat 
                    if breath_beat > beats_per_breath:
                        breath_beat = 1
                        beat_progress_marks = [(progress, breath_beat)]

                    # Remove the earliest beat if the circular array is full
                    if len(beat_times) > beat_record_len:
                        beat_times.pop(0)

                    # Calculate beat metrics
                    if len(beat_times) > bpm_window_len:
                        time_diffs = np.diff(beat_times)
                        beat_period = np.sum(beat_period_weights * time_diffs[-bpm_window_len:])
                        bpm = 60.0 / beat_period
                    else:
                        bpm = bpm_init
                        print('Using default beat period.')
                    print('Beat Count: {0}\tBeat Period: {1:2.1f}\tBPM: {2:2.1f}\tNumBeatMarks: {3}'.format(breath_beat, beat_period, bpm, len(beat_progress_marks), beat_progress_marks))


        # Refresh the screen
        if (current_time - last_frame_time) > screen_refresh_period:
            last_frame_time = current_time

            update_progress(progress, beat_progress_marks, breath_beat, beat_frame)
            beat_frame = False

except KeyboardInterrupt:
    print("Exiting program.")
finally:
    arduino.close()
    plt.close()

