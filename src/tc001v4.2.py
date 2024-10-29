#!/usr/bin/env python3
'''
Les Wright 21 June 2023
https://youtube.com/leslaboratory
A Python program to read, parse and display thermal data from the Topdon TC001 Thermal camera!
'''
from http.client import responses

from numpy.core.multiarray import unravel_index

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
			 ('Parula', cv2.COLORMAP_PARULA)]

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

def findHighest(data):
	linear_max = data[...].argmax()
	row, col = unravel_index(linear_max, data.shape)
	return (col, row, data[row, col])

def findLowest(data):
	linear_max = data[...].argmin()
	row, col = unravel_index(linear_max, data.shape)
	return (col, row, data[row, col])

def findAverage(data):
	return round(data[...].mean(), 2)

def applyColorMap(colormap_index):
	colormap_title, colormap = colormaps[colormap_index]
	heatmap = cv2.applyColorMap(bgr, colormap)
	return colormap_title, heatmap

def getBounds(bottom, top, left, right):
	return th_data[bottom:top, left:right]


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

while cap.isOpened():
	# Capture frame-by-frame
	ret, frame = cap.read()

	if ret:
		im_data,raw_th_data = np.array_split(frame, 2)
		th_data = convertRawToCelcius(raw_th_data)

		temp = th_data[96, 128]

		mrow, mcol, maxtemp = findHighest(th_data)
		lrow, lcol, mintemp = findLowest(th_data)

		avg_temp = findAverage(th_data)

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

		#gui.draw_crosshair(image, temp, scaled_width, scaled_height)
		#gui.draw_menu(hud, image, avg_temp, threshold, cmapText, rad, scale, alpha, snaptime, recording, elapsed)
		gui.draw_dot(image, mrow, mcol, scale, (0, 0, 255), maxtemp)
		gui.draw_dot(image, lrow, lcol, scale, (255, 0, 0), mintemp)

		zone1 = getBounds(0, 64, 0, 64)

		z_l_row, z_l_col, z_min_temp = findLowest(zone1)
		z_m_row, z_m_col, z_max_temp = findHighest(zone1)

		gui.draw_dot(image, z_l_row, z_l_col, scale, (0, 255, 0), z_min_temp)
		gui.draw_dot(image, z_m_row, z_m_col, scale, (0, 255, 0), z_max_temp)

		#display image
		cv2.imshow('Thermal', image)

		
		keyPress = cv2.waitKey(1)

		if keyPress == ord('q'): #enable fullscreen
			dispFullscreen = True
			cv2.namedWindow('Thermal',cv2.WND_PROP_FULLSCREEN)
			cv2.setWindowProperty('Thermal',cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)

		if keyPress == ord('h'):
			hud = not hud

		if keyPress == ord('m'): #m to cycle through color maps
			colormap_index += 1
			if colormap_index == 11:
				colormap_index = 0

		if keyPress == ord('q'):
			break
			capture.release()
			cv2.destroyAllWindows()