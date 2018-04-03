import pydicom
import os
import cv2
import numpy as np

folder = '/home/orious/Bureau/test/178036/'
files = sorted(os.listdir(folder))
loaded_dicoms = []


for file in files:
    pxls = pydicom.dcmread(folder+file).pixel_array
    #equalized = cv2.equalizeHist(pxls)
    #equalized = limitedEqualize(pxls)
    #normalized = (pxls - np.amax(pxls)) / (np.amax(pxls) - np.amin(pxls))
    loaded_dicoms.append(pxls)
    
    
loaded_dicoms = np.array(loaded_dicoms)

index = 0

def mouse_callback(event, x, y, flags, param):
    global index

    if event == cv2.EVENT_MOUSEWHEEL :
        if flags > 0:
            index += 1
        elif flags < 0:
            index -= 1
        index %= len(loaded_dicoms)

cv2.namedWindow('window', cv2.WINDOW_AUTOSIZE)
cv2.setMouseCallback('window', mouse_callback)

while True:
    cv2.imshow("window", loaded_dicoms[index])
    cv2.setMouseCallback('window', mouse_callback)
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break

cv2.destroyAllWindows()

