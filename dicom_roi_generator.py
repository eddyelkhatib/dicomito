import numpy as np
import pydicom
import os
import cv2
import shutil

class DicomController:
    def __init__(self, dir_path):
        print(dir_path)
        self.dir_path = dir_path
        self.dicoms = []
        if dir_path[-1] == '/':    
            self.ipp = dir_path[:-1]
        self.ipp = self.ipp[self.ipp.rfind('/')+1:]
        self.files_names = []
        self.read_dicoms()
        
    def normalize(self, pixel_array):
        max_value = np.amax(pixel_array)
        min_value = np.unique(pixel_array.flatten())[3]
        return (pixel_array - min_value) / (max_value - min_value)
    
    def read_dicoms(self):
        self.files_names = sorted(os.listdir(self.dir_path))
        for file in self.files_names :
            dicom = pydicom.dcmread(self.dir_path+file)
            self.dicoms.append(dicom)
            
    def gen_pixel_arrays(self):
        return np.array([dcm.pixel_array for dcm in self.dicoms])
    
    def gen_normalized_pixel_arrays(self):
        return [self.normalize(pxl_arr) for pxl_arr in self.gen_pixel_arrays()]
    
    def copy_files(self, path, first_slice, last_slice):
        new_dicoms_pathes = []
        for i in range(last_slice - first_slice + 1):
            new_path = shutil.copy(self.dir_path+self.files_names[i], path)
            new_dicoms_pathes.append(new_path)
        return new_dicoms_pathes
            
    
    def crop_and_save(self, path, center, size, first_slice, last_slice):
        os.mkdir(path)
        x,y = center
        new_dicoms_pathes = self.copy_files(path, first_slice, last_slice)
        for new_dicom_path in new_dicoms_pathes :
            dc = pydicom.dcmread(new_dicom_path)
            cropped_array = dc.pixel_array[y-size:y+size+1, x-size:x+size+1]
            dc.PixelData = cropped_array.tostring()
            dc.Rows, dc.Columns = cropped_array.shape
            dc.save_as(new_dicom_path)
            
            

class OpenCvWindow:
    def __init__(self, dir_path):
        self.dicom_controller = DicomController(dir_path)
        self.window_name = self.dicom_controller.ipp
        self.pixel_arrays = self.dicom_controller.gen_normalized_pixel_arrays()
        self.first_slice = 0
        self.last_slice = len(self.pixel_arrays) - 1
        self.rectangle_center = (0,0)
        self.size = 20
        self.generate_elements()
        self.configure_elements()
        self.index = 0
        self.first_slice = 0
    
    def generate_elements(self):
        cv2.namedWindow(self.window_name, cv2.WINDOW_AUTOSIZE | cv2.WINDOW_GUI_NORMAL)
        cv2.createTrackbar('coupes', self.window_name, self.first_slice, self.last_slice, self.slice_tbcb)
        cv2.createTrackbar('first', self.window_name, self.first_slice, self.last_slice, self.first_slice_tbcb)
        cv2.createTrackbar('last', self.window_name, self.first_slice, self.last_slice, self.last_slice_tbcb)
        cv2.createTrackbar('taille', self.window_name, 1, 100, self.size_tbcb)
    
    def slice_tbcb(self, x):
        self.index = x
    
    def size_tbcb(self, x):
        self.size = x
        self.generate_crop_rectangles()
    
    def first_slice_tbcb(self, x):
        if x >= self.last_slice:
            x = self.last_slice - 1
            cv2.setTrackbarPos('first', self.window_name, x)
        self.first_slice = x
        cv2.setTrackbarMin('coupes', self.window_name, x)
        cv2.setTrackbarPos('coupes', self.window_name, x)
        
    def last_slice_tbcb(self, x):
        if x <= self.first_slice:
            x = self.first_slice + 1
            cv2.setTrackbarPos('last', self.window_name, x)
        self.last_slice = x
        cv2.setTrackbarMax('coupes', self.window_name, x)
        cv2.setTrackbarPos('coupes', self.window_name, x)
    
    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDBLCLK:
            self.rectangle_center = (x,y)
            self.generate_crop_rectangles()
        
    def configure_elements(self):
        cv2.setMouseCallback(self.window_name, self.mouse_callback)
        cv2.setTrackbarMin('taille', self.window_name, 1)
        cv2.setTrackbarPos('taille', self.window_name, self.size)
        cv2.setTrackbarPos('last', self.window_name, self.last_slice)
        cv2.setTrackbarPos('coupes', self.window_name, 0)

    
    def generate_crop_rectangles(self):
        x, y = self.rectangle_center
        self.pixel_arrays = self.dicom_controller.gen_normalized_pixel_arrays()
        for pxl_arr in self.pixel_arrays:
             cv2.rectangle(pxl_arr, (x-self.size, y-self.size), (x+self.size, y+self.size),(0,255,0),1)
    
    def run(self):
        while True:
            cv2.imshow(self.window_name, self.pixel_arrays[self.index])
            key = cv2.waitKey(1)
            if key == ord('q'):
                break
            else :
                if key == ord('+'):
                    cv2.setTrackbarPos('taille', self.window_name, self.size + 1)
                elif key == ord('-'):
                    if self.size - 1 >= 1:
                        cv2.setTrackbarPos('taille', self.window_name, self.size - 1)
                elif key == ord('s'):
                    self.dicom_controller.crop_and_save(self.dicom_controller.dir_path+"../"+self.window_name+"-cropped",
                                                        self.rectangle_center,
                                                        self.size,
                                                        self.first_slice,
                                                        self.last_slice)
                    self.dicom_controller.read_dicoms()
                    self.pixel_arrays = self.dicom_controller.gen_normalized_pixel_arrays()
                    

        cv2.destroyAllWindows()

w = OpenCvWindow('/home/orious/Bureau/test/178036-cropped/')
w.run()
