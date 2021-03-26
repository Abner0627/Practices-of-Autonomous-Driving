# -*- coding: utf-8 -*-
"""
Created on Fri Mar 19 16:38:45 2021

@author: Lab
"""
import numpy as np
import matplotlib.pyplot as plt
import cv2
import os

#%% Load video
P = './data'
V = 'solidWhiteRight.mp4'
sV = 'Lane_' + V
vc = cv2.VideoCapture(os.path.join(P, V))
fps = vc.get(cv2.CAP_PROP_FPS)
frame_count = int(vc.get(cv2.CAP_PROP_FRAME_COUNT))
video = []

#%% Video process
for idx in range(frame_count):   
    vc.set(1, idx)
    ret, frame = vc.read()
    if frame is not None:
        img = frame
        # img = img[:,:,[2,1,0]]
#%% Transform
        src = np.float32(
                    [[153, 540],  # Bottom left
                    [300, 430],  # Top left
                    [692, 430],  # Top right
                    [872, 540]]) # Bottom right

        dst = np.float32(
                    [[153, 540],  # Bottom left
                    [153, 0],  # Top left
                    [872, 0],  # Top right
                    [872, 540]]) # Bottom right 

        img_size = (img.shape[1], img.shape[0])
        M = cv2.getPerspectiveTransform(src, dst)
        M_inv = cv2.getPerspectiveTransform(dst, src)
        img_warped = cv2.warpPerspective(img, M, img_size) 

#%% Binary
        gray_img =cv2.cvtColor(img_warped, cv2.COLOR_BGR2GRAY)
        sobelx = cv2.Sobel(gray_img, cv2.CV_64F, 1, 0)
        abs_sobelx = np.absolute(sobelx)
        # Scale result to 0-255
        scaled_sobel = np.uint8(255*abs_sobelx/np.max(abs_sobelx))

        fig_0 = plt.figure(0)
        plt.imshow(scaled_sobel)

        sx_binary = np.zeros_like(scaled_sobel)
        # Keep only derivative values that are in the margin of interest
        sx_binary[(scaled_sobel >= 30) & (scaled_sobel <= 255)] = 1
        # Detect pixels that are white in the grayscale image
        white_binary = np.zeros_like(gray_img)
        white_binary[(gray_img > 150) & (gray_img <= 255)] = 1
        # Combine all pixels detected above
        binary_warped = cv2.bitwise_or(sx_binary, white_binary)

#%% Histogram & laneBase
        # Take a histogram of the bottom half of the image
        histogram = np.sum(binary_warped, axis=0)

        midpoint = int(histogram.shape[0]//2)
        leftx_base = np.argmax(histogram[:midpoint])
        rightx_base = np.argmax(histogram[midpoint:]) + midpoint
        laneBase = [leftx_base, rightx_base]

#%% Window
        nwindows = 9
        margin = 40
        minpixel = 50

        out_img = np.dstack((binary_warped, binary_warped, binary_warped))*255
        window_img = np.zeros_like(out_img)
        line_img = np.zeros_like(out_img)
        laneLine_y = np.linspace(0, binary_warped.shape[0]-1, binary_warped.shape[0])
        laneLine_x = np.zeros([2, binary_warped.shape[0]])
        for n_lane in range(len(laneBase)): 
            window_height = int(binary_warped.shape[0]//nwindows)
            x_point = []
            y_point = []
            laneCurrent = laneBase[n_lane]
            for n_window in range(nwindows):
                x_range_L = laneCurrent - margin
                x_range_R = laneCurrent + margin
                if x_range_L < 0:
                    x_range_L = 0
                if x_range_R >= binary_warped.shape[1]:
                    x_range_R = binary_warped.shape[1] - 1

                y_range_B = binary_warped.shape[0] - (n_window+1)*window_height
                y_range_T = binary_warped.shape[0] - n_window*window_height

                window = binary_warped[y_range_B:y_range_T, x_range_L:x_range_R]

                y_Nz, x_Nz = np.nonzero(window)
                x_Nz = x_Nz + x_range_L
                y_Nz = y_Nz + y_range_B

                if np.count_nonzero(window) > minpixel:
                    x_point.extend(x_Nz)
                    y_point.extend(y_Nz)
                    laneCurrent = int(np.mean(x_Nz, axis=0))
                    
                # 擬合二次曲線
                if len(y_point) > 0:     
                    fit = np.polyfit(y_point, x_point, 2)
                    # 轉換為點
                    laneLine_x[n_lane, :] = fit[0] * laneLine_y**2 + fit[1] * laneLine_y + fit[2]

#%% Line
        width = 7
        threshold = 60
        for line_x in laneLine_x:
            if np.abs(line_x[-1]-line_x[0]) > threshold:
                continue
            if np.abs(line_x[-1] - line_x[len(line_x)//2]) > threshold:
                continue
            if np.abs(line_x[0] - line_x[len(line_x)//2]) > threshold:
                continue

            # 線段左邊界
            lineWindow1 = np.expand_dims(np.vstack([line_x - width, laneLine_y]).T, axis=0)
            # 線段右邊界
            lineWindow2 = np.expand_dims(np.flipud(np.vstack([line_x + width, laneLine_y]).T), axis=0)
            linePts = np.hstack((lineWindow1, lineWindow2))

            # 使用 openCV 填上曲線間區域
            cv2.fillPoly(line_img, np.int32([linePts]), (0, 0, 255))

#%% Result
        weight = cv2.warpPerspective(line_img, M_inv, (img.shape[1], img.shape[0]))
        result = cv2.addWeighted(img, 1, weight, 1, 0)

        height, width, layers = result.shape
        size = (width, height)
        video.append(result)
vc.release()

#%% Save video
out = cv2.VideoWriter(os.path.join(P, sV), cv2.VideoWriter_fourcc(*'DIVX'), fps, size)
for i in range(len(video)):
    out.write(video[i])
out.release()