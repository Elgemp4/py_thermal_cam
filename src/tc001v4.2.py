#!/usr/bin/env python3
'''
Les Wright 21 June 2023
https://youtube.com/leslaboratory
A Python program to read, parse and display thermal data from the Topdon TC001 Thermal camera!
'''
from http.client import responses

from numpy.core.multiarray import unravel_index

from src.gui import draw_dot

print('Les Wright 21 June 2023')
print('https://youtube.com/leslaboratory')
print('A Python program to read, parse and display thermal data from the Topdon TC001 Thermal camera!')
print('')
print('Tested on Debian all features are working correctly')
print('This will work on the Pi However a number of workarounds are implemented!')
print('Seemingly there are bugs in the compiled version of cv2 that ships with the Pi!')
print('')
print('Key Bindings:')
print('')
print('a z: Increase/Decrease Blur')
print('s x: Floating High and Low Temp Label Threshold')
print('d c: Change Interpolated scale Note: This will not change the window size on the Pi')
print('f v: Contrast')
print('q w: Fullscreen Windowed (note going back to windowed does not seem to work on the Pi!)')
print('r t: Record and Stop')
print('p : Snapshot')
print('m : Cycle through ColorMaps')
print('h : Toggle HUD')

import cv2
import gui
import numpy as np
import argparse
import time
import io

#We need to know if we are running on the Pi, because openCV behaves a little oddly on all the builds!
#https://raspberrypi.stackexchange.com/questions/5100/detect-that-a-python-program-is-running-on-the-pi
def is_raspberrypi():
    try:
        with io.open('/sys/firmware/devicetree/base/model', 'r') as m:
            if 'raspberry pi' in m.read().lower(): return True
    except Exception: pass
    return False

isPi = is_raspberrypi()

parser = argparse.ArgumentParser()
parser.add_argument("--device", type=int, default=0, help="Video Device number e.g. 0, use v4l2-ctl --list-devices")
args = parser.parse_args()
	
if args.device:
	dev = args.device
else:
	dev = 0
	
#init video
cap = cv2.VideoCapture('/dev/video'+str(dev), cv2.CAP_V4L)
#cap = cv2.VideoCapture(0)
#pull in the video but do NOT automatically convert to RGB, else it breaks the temperature data!
#https://stackoverflow.com/questions/63108721/opencv-setting-videocap-property-to-cap-prop-convert-rgb-generates-weird-boolean
if isPi == True:
	cap.set(cv2.CAP_PROP_CONVERT_RGB, 0.0)
else:
	cap.set(cv2.CAP_PROP_CONVERT_RGB, 0.0)

#256x192 General settings
width = 256 #Sensor width
height = 192 #sensor height
scale = 3 #scale multiplier
scaled_width = width * scale
scaled_height = height * scale
alpha = 1.0 # Contrast control (1.0-3.0)
colormap_index = 0
font=cv2.FONT_HERSHEY_SIMPLEX
dispFullscreen = False
cv2.namedWindow('Thermal',cv2.WINDOW_GUI_NORMAL)
cv2.resizeWindow('Thermal', scaled_width, scaled_height)
rad = 0 #blur radius
threshold = 2
hud = True
recording = False
elapsed = "00:00:00"
snaptime = "None"

colormaps = [('Jet', cv2.COLORMAP_JET),
			 ('Hot', cv2.COLORMAP_HOT),
			 ('Magma', cv2.COLORMAP_MAGMA),
			 ('Inferno', cv2.COLORMAP_INFERNO),
			 ('Plasma', cv2.COLORMAP_PLASMA),
			 ('Bone', cv2.COLORMAP_BONE),
			 ('Spring', cv2.COLORMAP_SPRING),
			 ('Autumn', cv2.COLORMAP_AUTUMN),
			 ('Viridis', cv2.COLORMAP_VIRIDIS),
			 ('Parula', cv2.COLORMAP_PARULA),
			 ('Inv Rainbow', cv2.COLORMAP_RAINBOW)]

def rec():
	now = time.strftime("%Y%m%d--%H%M%S")
	#do NOT use mp4 here, it is flakey!
	videoOut = cv2.VideoWriter(now +'output.avi', cv2.VideoWriter_fourcc(*'XVID'), 25, (scaled_width, scaled_height))
	return(videoOut)

def snapshot(heatmap):
	#I would put colons in here, but it Win throws a fit if you try and open them!
	now = time.strftime("%Y%m%d-%H%M%S") 
	snaptime = time.strftime("%H:%M:%S")
	cv2.imwrite("TC001"+now+".png", heatmap)
	return snaptime

def findHighest():
	linear_max = th_data[...].argmax()
	row, col = unravel_index(linear_max, (192, 256))
	return (col, row, th_data[row, col])

def findLowest():
	linear_max = th_data[...].argmin()
	row, col = unravel_index(linear_max, (192, 256))
	return (col, row, th_data[row, col])

def findAverage():
	return round(th_data[...].mean(), 2)


def applyColorMap(colormap_index):
	colormap_title, colormap = colormaps[colormap_index]
	heatmap = cv2.applyColorMap(bgr, colormap)
	return colormap_title, heatmap

def writeText(text, x, y):
	cv2.putText(image, text, (x, y), font, 0.5, (0, 255, 255), 1, cv2.LINE_AA)

# Converting the raw values to celsius
# https://www.eevblog.com/forum/thermal-imaging/infiray-and-their-p2-pro-discussion/200/
# Huge props to LeoDJ for figuring out how the data is stored and how to compute temp from it.
# Basically the temperatures are stored on 14 bits in kelvin multiplied by 16
# As the data is stored on two different bytes they need to be recombined in a single 16 bits unsigned integer
# So the formula is (raw_temp >> 2) / 16 to get the temperature in Kelvin
# Then we substract 273.15 to convert Lelvin in Celcius
# Simplified the equation become : raw_temp / 64 - 273.15
# The data is then rounded for ease of use
def convertRawToCelcius(raw_temp):
	return np.round(((raw_th_data[..., 1].astype(np.uint16) << 8) + raw_th_data[..., 0].astype(np.uint16)) / 64 - 273.15, 2)

while(cap.isOpened()):
	# Capture frame-by-frame
	ret, frame = cap.read()

	if ret == True:
		im_data,raw_th_data = np.array_split(frame, 2)
		th_data = convertRawToCelcius(raw_th_data)

		temp = th_data[96, 128]

		mrow, mcol, maxtemp = findHighest()
		lrow, lcol, mintemp = findLowest()

		avg_temp = findAverage()

		# Convert the real image to RGB
		bgr = cv2.cvtColor(im_data, cv2.COLOR_YUV2BGR_YUYV)

		#Contrast
		bgr = cv2.convertScaleAbs(bgr, alpha=alpha)#Contrast

		#bicubic interpolate, upscale and blur
		bgr = cv2.resize(bgr, (scaled_width, scaled_height), interpolation=cv2.INTER_CUBIC)#Scale up!
		if rad>0:
			bgr = cv2.blur(bgr,(rad,rad))


		#apply colormap
		cmapText, image = applyColorMap(colormap_index)

		if(colormap_index == 10):
			image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

		gui.draw_crosshair(image, temp, scaled_width, scaled_height)

		gui.draw_menu(hud, image, avg_temp, threshold, cmapText, rad, scale, alpha, snaptime, recording, elapsed)

		gui.draw_dot(image, mrow, mcol, scale, (0, 0, 255), maxtemp)

		gui.draw_dot(image, lrow, lcol, scale, (255, 0, 0), mintemp)

		#display image
		cv2.imshow('Thermal', image)

		if recording == True:
			elapsed = (time.time() - start)
			elapsed = time.strftime("%H:%M:%S", time.gmtime(elapsed))
			videoOut.write(image)
		
		keyPress = cv2.waitKey(1)
		if keyPress == ord('a'): #Increase blur radius
			rad += 1
		if keyPress == ord('z'): #Decrease blur radius
			rad -= 1
			if rad <= 0:
				rad = 0

		if keyPress == ord('s'): #Increase threshold
			threshold += 1
		if keyPress == ord('x'): #Decrease threashold
			threshold -= 1
			if threshold <= 0:
				threshold = 0

		if keyPress == ord('d'): #Increase scale
			scale += 1
			if scale >=5:
				scale = 5
			scaled_width = width * scale
			scaled_height = height * scale
			if dispFullscreen == False and isPi == False:
				cv2.resizeWindow('Thermal', scaled_width, scaled_height)
		if keyPress == ord('c'): #Decrease scale
			scale -= 1
			if scale <= 1:
				scale = 1
			scaled_width = width * scale
			scaled_height = height * scale
			if dispFullscreen == False and isPi == False:
				cv2.resizeWindow('Thermal', scaled_width, scaled_height)

		if keyPress == ord('q'): #enable fullscreen
			dispFullscreen = True
			cv2.namedWindow('Thermal',cv2.WND_PROP_FULLSCREEN)
			cv2.setWindowProperty('Thermal',cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)
		if keyPress == ord('w'): #disable fullscreen
			dispFullscreen = False
			cv2.namedWindow('Thermal',cv2.WINDOW_GUI_NORMAL)
			cv2.setWindowProperty('Thermal',cv2.WND_PROP_AUTOSIZE,cv2.WINDOW_GUI_NORMAL)
			cv2.resizeWindow('Thermal', scaled_width, scaled_height)

		if keyPress == ord('f'): #contrast+
			alpha += 0.1
			alpha = round(alpha,1)#fix round error
			if alpha >= 3.0:
				alpha=3.0
		if keyPress == ord('v'): #contrast-
			alpha -= 0.1
			alpha = round(alpha,1)#fix round error
			if alpha<=0:
				alpha = 0.0


		if keyPress == ord('h'):
			hud = not hud

		if keyPress == ord('m'): #m to cycle through color maps
			colormap_index += 1
			if colormap_index == 11:
				colormap_index = 0

		if keyPress == ord('r') and recording == False: #r to start reording
			videoOut = rec()
			recording = True
			start = time.time()
		if keyPress == ord('t'): #f to finish reording
			recording = False
			elapsed = "00:00:00"

		if keyPress == ord('p'): #f to finish reording
			snaptime = snapshot(image)

		if keyPress == ord('q'):
			break
			capture.release()
			cv2.destroyAllWindows()
		
