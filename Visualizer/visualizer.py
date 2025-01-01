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
ax.set_theta_direction(-1)
ax.set_theta_offset(np.pi / 2)
ax.set_ylim(0, 1)
ax.axis('off')
background_circle, = ax.plot([], [], lw=85, color='lightgrey')
progress_bar, = ax.plot([], [], lw=85, color='blue')
beat_points, = ax.plot([], [], 'ro', markersize=85)

# Screen params
screen_refresh_rate = 30 # Hz
screen_refresh_period = 1.0 / screen_refresh_rate

# Heart beat info
beat_record_len = 128 # How many beat to record
bpm_window_len = 16 # How many beats avg for bpm calculation

# Draw background circle
theta = np.linspace(0, 2 * np.pi, 100)
r = np.ones(100)
background_circle.set_data(theta, r)

init_time = time.time()
last_frame_time = 0

# Function to update the progress bar and beat markers
def update_progress(progress, beat_angles):
    theta = np.linspace(0, 2 * np.pi * progress, 100)
    r = np.ones(100)
    progress_bar.set_data(theta, r)

    # Update beat markers
    if beat_angles:
        beat_points.set_data(beat_angles, np.ones(len(beat_angles)))
    else:
        beat_points.set_data([], [])

    plt.draw()
    plt.pause(0.01)

# Tracks what beat we are on in the current breath
breath_beat = 1

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
        # Read from the serial port
        if arduino.in_waiting > 0:
            line = arduino.readline().decode('utf-8').strip()
            if line == 'BEAT':
                beat_times.append(current_time)
                print('Received beat at {0:2.1f}s with {1} beats'.format(current_time, len(beat_times)))
                # Increment the beat
                breath_beat += 1
                # Reset the breath beat 
                if(breath_beat > beats_per_breath):
                    breath_beat = 1

                # Calculate angles for the beat markers
                beat_marker_angles = [2 * np.pi * (i / beats_per_breath) for i in range(breath_beat)]
                print('Angles: ', beat_marker_angles)

                # Remove the earliest beat if the circular array is full
                if len(beat_times) > beat_record_len:
                    beat_times.pop(0)

                # Calculate beat metrics
                if(len(beat_times) > bpm_window_len):
                    time_diffs = np.diff(beat_times)
                    beat_period = np.sum(beat_period_weights * time_diffs[-bpm_window_len:])
                    bpm = 60.0/beat_period
                else:
                    bpm = bpm_init
                    print('Using default beat period.')
                print('Beat Count: {0}\tBeat Period: {1:2.1f}\tBPM: {2:2.1f}'.format(breath_beat, beat_period, bpm))


        # Refresh the screen
        if((current_time - last_frame_time) > screen_refresh_period):
            last_frame_time = current_time

            # Estimate the extrapolated progress bar progress
            # Update progress bar with smooth interpolation
            min_prog = max(0, breath_beat-1)/beats_per_breath
            max_prog = (breath_beat)/beats_per_breath
            progress = ((current_time - beat_times[-1]) / (beat_period)) * (max_prog - min_prog) + min_prog
            #print(min_prog, max_prog, '\tProgress: ', progress)
            update_progress(progress, beat_marker_angles)

            



except KeyboardInterrupt:
    print("Exiting program.")
finally:
    arduino.close()
    plt.close()

