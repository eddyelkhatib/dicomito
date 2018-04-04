import pydicom
import os
import cv2
import numpy as np

folder = '/home/orious/Bureau/test/178036_cropped/'
files = sorted(os.listdir(folder))
normalized_dicoms = []
normalized_dicoms_unmodified = []

for file in files:
    pxls = pydicom.dcmread(folder+file).pixel_array
    normalized = (pxls - np.amin(pxls)) / (np.amax(pxls) - np.amin(pxls))
    normalized_dicoms.append(normalized)
    
normalized_dicoms = np.array(normalized_dicoms)  
normalized_dicoms_unmodified = normalized_dicoms.copy()

size = 20
rectangle_center = (0,0)
first_image = 0
last_image = len(normalized_dicoms) - 1

def mouse_callback(event, x, y, flags, param):
    global rectangle_center
    if event == cv2.EVENT_LBUTTONDBLCLK:
        rectangle_center = (x,y)
        generate_rectangles()
        
def change_image(x):
    global index
    index = x

def change_size(x):
    global size
    size = x
    generate_rectangles()
    
def change_first(x):
    global first_image, last_image, index
    if x >= last_image:
        x = last_image - 1
        cv2.setTrackbarPos('first', 'window', x)
    index = x
    first_image = x
    cv2.setTrackbarMin('coupes', 'window', x)
    cv2.setTrackbarPos('coupes', 'window', x)
        
def change_last(x):
    global first_image, last_image, index
    if  x <= first_image:
        x = first_image + 1
        cv2.setTrackbarPos('last', 'window', x)
    last_image = x
    index = x
    cv2.setTrackbarMax('coupes', 'window', x)
    cv2.setTrackbarPos('coupes', 'window', x)


def call_back_button(state, pointer):
    print("ok ta mère")
    
def generate_rectangles():
    global normalized_dicoms, normalized_dicoms_unmodified, rectangle_center, size
    x, y = rectangle_center
    normalized_dicoms = normalized_dicoms_unmodified.copy()
    for img in normalized_dicoms:
        cv2.rectangle(img, (x-size, y-size), (x+size, y+size),(0,255,0),1)

cv2.namedWindow('window', cv2.WINDOW_AUTOSIZE | cv2.WINDOW_GUI_NORMAL)
cv2.setMouseCallback('window', mouse_callback)
cv2.createTrackbar('coupes', 'window', first_image, last_image, change_image)
cv2.createTrackbar('first', 'window', first_image, last_image, change_first)
cv2.createTrackbar('last', 'window', first_image, last_image, change_last)
cv2.setTrackbarPos('last', 'window', last_image)
cv2.createTrackbar('taille', 'window', 1, 100, change_size)
cv2.setTrackbarMin('taille','window', 1)
cv2.setTrackbarPos('taille', 'window', size)
cv2.createButton('save_button', call_back_button, cv2.QT_NEW_BUTTONBAR, 0)


index = 0
cv2.setTrackbarPos('coupes', 'window', 0)

while True:
    cv2.imshow('window', normalized_dicoms[index])
    key = cv2.waitKey(1)
    if key == ord('q'):
        break
    else :
        if key == ord('+'):
            size += 1
            generate_rectangles()
            cv2.setTrackbarPos('taille', 'window', size)
        elif key == ord('-'):
            if size - 1 >= 1:
                size -= 1
                generate_rectangles()
                cv2.setTrackbarPos('taille', 'window', size)
        elif key == ord('s'):
            folder_name = folder[:-1]
            folder_name = folder_name[folder_name.rfind('/')+1:]
            new_folder = folder+'../'+folder_name+"_cropped"
            os.mkdir(new_folder)
            for i in range(last_image - first_image + 1):
                index = first_image + i
                dc = pydicom.dcmread(folder+files[index])
                x,y = rectangle_center
                new_data = dc.pixel_array[x-size:x+size+1, y-size:y+size+1]
                dc.PixelData = new_data.tostring()
                dc.Rows, dc.Columns = new_data.shape
                dc.save_as(new_folder+'/'+files[index])
                
            print("done")

cv2.destroyAllWindows()

