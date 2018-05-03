import tkinter
from tkinter import filedialog
from tkinter import messagebox
from tkinter import *
import numpy as np
import pydicom
import os
import cv2
import shutil

class DicomMain:
    def __init__(self):
        self.root = Tk()
        self.root.title("DICOM ROI EXTRACTOR")
        self.root.geometry("500x100")
        self.root.resizable(width=False, height=False)
        self.menubar = Menu(self.root)
        self.filemenu = Menu(self.menubar, tearoff=0)
        self.filemenu.add_command(label="Open folder", command=self.launch)
        self.filemenu.add_command(label="Exit", command=self.quit_everything)
        self.menubar.add_cascade(label="File", menu=self.filemenu)
        self.root.config(menu=self.menubar)
        label = Label(self.root, text="\nVersion 0.9")
        label2 = Label(self.root, text="Author : Eddy El Khatib")
        label.pack()
        label2.pack()
        self.last_dir = '.'
        
    def mainloop(self):
        self.root.mainloop()
        
    def launch(self):
        folder_path = self.file_dialog()
        check_suffix = lambda ss : any(s.lower().endswith('.dcm') for s in ss)
        while folder_path != () and folder_path != "" and not check_suffix(os.listdir(folder_path)):
            messagebox.showerror("Dicom not found", 
                                 "No Dicom file found in the folder")
            self.last_dir = folder_path
            folder_path = self.file_dialog()
                          
        if folder_path != () and folder_path != "":
            self.last_dir = folder_path
            obj = OpenCvWindow(folder_path, self).run()
            del obj
        
    
    def file_dialog(self):
        return filedialog.askdirectory(initialdir=self.last_dir)
    
    def quit_everything(self):
        self.root.quit()

class DicomController:
    def __init__(self, dir_path):
        self.dicoms = []
        if dir_path[-1] == '/':    
            self.ipp = dir_path[:-1]
            self.dir_path = dir_path
        else:
            self.ipp = dir_path
            self.dir_path = dir_path+'/'
        self.ipp = self.ipp[self.ipp.rfind('/')+1:]
        self.files_names = []
        self.slices = self.load_scan(dir_path)
    
    def get_pixels_hu(self):
        # copied from https://www.kaggle.com/gzuidhof/full-preprocessing-tutorial
        image = np.stack([s.pixel_array for s in self.slices])
        # Convert to int16 (from sometimes int16), 
        # should be possible as values should always be low enough (<32k)
        image = image.astype(np.int16)
    
        # Set outside-of-scan pixels to 0
        # The intercept is usually -1024, so air is approximately 0
        image[image == -2000] = 0
        
        # Convert to Hounsfield units (HU)
        for slice_nb in range(len(self.slices)):
            
            intercept = self.slices[slice_nb].RescaleIntercept
            slope = self.slices[slice_nb].RescaleSlope
            
            if slope != 1:
                image[slice_nb] = slope * image[slice_nb].astype(np.float64)
                image[slice_nb] = image[slice_nb].astype(np.int16)
                
            image[slice_nb] += np.int16(intercept)
        
        return np.array(image, dtype=np.int16)

    def load_scan(self, path):
        files_names = sorted(os.listdir(path))
        files_names = [s for s in files_names if s.lower().endswith('.dcm')]
        self.files_names = files_names
        slices = []
        for file_name in files_names :
            s = pydicom.dcmread(self.dir_path+file_name, force=True)
            slices.append(s)
            
        try:
            slice_thickness = np.abs(slices[0].ImagePositionPatient[2] - 
                                     slices[1].ImagePositionPatient[2])
        except:
            slice_thickness = np.abs(slices[0].SliceLocation - 
                                     slices[1].SliceLocation)
            
        for s in slices:
            s.SliceThickness = slice_thickness
            
        return slices
    
    def copy_files(self, path, fst_slice, lst_slice):
        ndicoms_pathes = []
        for i in range(lst_slice - fst_slice + 1):
            new_path = shutil.copy(self.dir_path + 
                                   self.files_names[fst_slice + i], path)
            ndicoms_pathes.append(new_path)
        return ndicoms_pathes       
    
    def crop_and_save(self, path, center, size, first_slice, last_slice):
        x,y = center
        if not os.path.exists(path):
            os.mkdir(path)
        ndcm_pathes = self.copy_files(path, first_slice, last_slice)
        for ndcm_path in ndcm_pathes :
            dc = pydicom.dcmread(ndcm_path, force=True)
            cropped_array = dc.pixel_array[y-size:y+size+1, x-size:x+size+1]
            dc.PixelData = cropped_array.tostring()
            dc.Rows, dc.Columns = cropped_array.shape
            dc.save_as(ndcm_path)
        messagebox.showinfo("Saved !", 
                            "Dicom files have been successfully saved")

class OpenCvWindow:
    def __init__(self, dir_path, tk_window):
        self.tk_window = tk_window
        self.dicom_controller = DicomController(dir_path)
        self.window_name = self.dicom_controller.ipp
        self.pixel_arrays = self.dicom_controller.get_pixels_hu()
        self.original = self.pixel_arrays.copy()
        self.first_slice = 0
        self.last_slice = len(self.pixel_arrays) - 1
        self.rectangle_center = (0,0)
        self.size = 20
        self.contrast_window_min = 0
        self.contrast_window_max = 1000
        self.generate_elements()
        self.configure_elements()
        self.index = 0
        self.first_slice = 0
        
    
    def generate_elements(self):
        cv2.namedWindow(self.window_name, cv2.WINDOW_AUTOSIZE | cv2.WINDOW_GUI_NORMAL)
        cv2.createTrackbar('slices', self.window_name, self.first_slice, self.last_slice, self.slice_tbcb)
        cv2.createTrackbar('first', self.window_name, self.first_slice, self.last_slice, self.first_slice_tbcb)
        cv2.createTrackbar('last', self.window_name, self.first_slice, self.last_slice, self.last_slice_tbcb)
        cv2.createTrackbar('size', self.window_name, 1, 20, self.size_tbcb)
        cv2.createTrackbar('contrast_window_min', self.window_name, 0, 1000, self.change_window_first)
        cv2.createTrackbar('contrast_window_max', self.window_name, 0, 1000, self.change_window_last)
        cv2.setTrackbarPos('contrast_window_max', self.window_name, 1000)
    
    def change_window_first(self, x):
        x = x
        if x >= self.contrast_window_max:
            x = self.contrast_window_max - 1
            cv2.setTrackbarPos('contrast_window_min', self.window_name, x)
        self.contrast_window_min = x
        
    def change_window_last(self, x):
        x = x
        if x <= self.contrast_window_min:
            x = self.contrast_window_min + 1
            cv2.setTrackbarPos('contrast_window_max', self.window_name, x)
        self.contrast_window_max = x
        
    def slice_tbcb(self, x):
        self.index = x 
    
    def size_tbcb(self, x):
        self.size = x * 10
        self.generate_crop_rectangles()
    
    def first_slice_tbcb(self, x):
        if x >= self.last_slice:
            x = self.last_slice - 1
            cv2.setTrackbarPos('first', self.window_name, x)
        self.first_slice = x
        cv2.setTrackbarMin('slices', self.window_name, x)
        cv2.setTrackbarPos('slices', self.window_name, x)
        
    def last_slice_tbcb(self, x):
        if x <= self.first_slice:
            x = self.first_slice + 1
            cv2.setTrackbarPos('last', self.window_name, x)
        self.last_slice = x
        cv2.setTrackbarMax('slices', self.window_name, x)
        cv2.setTrackbarPos('slices', self.window_name, x)
    
    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDBLCLK:
            self.rectangle_center = (x,y)
            self.generate_crop_rectangles()
        
    def configure_elements(self):
        cv2.setMouseCallback(self.window_name, self.mouse_callback)
        cv2.setTrackbarMin('size', self.window_name, 1)
        cv2.setTrackbarPos('size', self.window_name, 1)
        cv2.setTrackbarPos('last', self.window_name, self.last_slice)
        cv2.setTrackbarPos('slices', self.window_name, 0)
        
    def generate_crop_rectangles(self):
        self.pixel_arrays = self.original.copy()
        x, y = self.rectangle_center
        for pxl_arr in self.pixel_arrays:
             cv2.rectangle(pxl_arr, (x-self.size, y-self.size), (x+self.size, y+self.size),(255,255,255),1)
    
    def run(self):
        while True:
            cv2.imshow(self.window_name, (self.pixel_arrays[self.index] - self.contrast_window_min) / (self.contrast_window_max - self.contrast_window_min) + 1)
            key = cv2.waitKey(1)
            if key == ord('q'):
                break
            elif key == ord('s'):
                path = self.tk_window.file_dialog()
                if path != () and path != "" :
                    path+='/'
                    self.dicom_controller.crop_and_save(path,
                                                        self.rectangle_center,
                                                        self.size,
                                                        self.first_slice,
                                                        self.last_slice)
        del self.original
        del self.pixel_arrays
        cv2.destroyAllWindows()

pouet = DicomMain()
pouet.mainloop()