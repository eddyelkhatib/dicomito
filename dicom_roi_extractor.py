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
            messagebox.showerror("Dicom not found", "No Dicom file was found in the selected folder")
            self.last_dir = folder_path
            folder_path = self.file_dialog()
                          
        if folder_path != () and folder_path != "":
            self.last_dir = folder_path
            OpenCvWindow(folder_path, self).run()
    
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
        self.read_dicoms()
        
    def normalize(self, pixel_array, value_couple=None):
        flat = np.unique(pixel_array.flatten())
        if value_couple == None:
            max_value = np.amax(pixel_array)
            min_value = flat[0]
        else :
            min_value, max_value = value_couple
            
        divider = max_value - min_value
        if divider == 0:
            divider = 1
        return (pixel_array - min_value) / divider
    
    def read_dicoms(self):
        self.files_names = sorted(os.listdir(self.dir_path))
        self.files_names = [s for s in self.files_names if s.lower().endswith('.dcm')]
        for file in self.files_names :
            dicom = pydicom.dcmread(self.dir_path+file, force=True)
            self.dicoms.append(dicom)
            
    def gen_pixel_arrays(self):
        return np.array([dcm.pixel_array.copy() for dcm in self.dicoms])
    
    def gen_normalized_pixel_arrays(self,value_couple=None):
        return [self.normalize(pxl_arr, value_couple) for pxl_arr in self.gen_pixel_arrays()]
    
    def copy_files(self, path, first_slice, last_slice):
        new_dicoms_pathes = []
        for i in range(last_slice - first_slice + 1):
            new_path = shutil.copy(self.dir_path+self.files_names[first_slice + i], path)
            new_dicoms_pathes.append(new_path)
        return new_dicoms_pathes
            
    
    def crop_and_save(self, path, center, size, first_slice, last_slice):
        x,y = center
        if not os.path.exists(path):
            os.mkdir(path)
        new_dicoms_pathes = self.copy_files(path, first_slice, last_slice)
        for new_dicom_path in new_dicoms_pathes :
            dc = pydicom.dcmread(new_dicom_path, force=True)
            cropped_array = dc.pixel_array[y-size:y+size+1, x-size:x+size+1]
            dc.PixelData = cropped_array.tostring()
            dc.Rows, dc.Columns = cropped_array.shape
            dc.save_as(new_dicom_path)
        messagebox.showinfo("Saved !", "The cropped dicom files have been successfully saved")
        
class OpenCvWindow:
    def __init__(self, dir_path, tk_window):
        self.tk_window = tk_window
        self.dicom_controller = DicomController(dir_path)
        self.window_name = self.dicom_controller.ipp
        self.pixel_arrays = self.dicom_controller.gen_normalized_pixel_arrays(None)
        self.first_slice = 0
        self.last_slice = len(self.pixel_arrays) - 1
        self.contrast_array = []
        self.rectangle_center = (0,0)
        self.size = 20
        self.window_min = 0
        self.window_max = 0
        self.generate_elements()
        self.configure_elements()
        self.index = 0
        self.first_slice = 0
    
    def generate_elements(self):
        cv2.namedWindow(self.window_name, cv2.WINDOW_AUTOSIZE | cv2.WINDOW_GUI_NORMAL)
        cv2.createTrackbar('slices', self.window_name, self.first_slice, self.last_slice, self.slice_tbcb)
        cv2.createTrackbar('first', self.window_name, self.first_slice, self.last_slice, self.first_slice_tbcb)
        cv2.createTrackbar('last', self.window_name, self.first_slice, self.last_slice, self.last_slice_tbcb)
        cv2.createTrackbar('size', self.window_name, 1, 100, self.size_tbcb)
        self.contrast_array = np.unique(self.dicom_controller.gen_pixel_arrays().flatten())
        cv2.createTrackbar('window_min', self.window_name, 0, len(self.contrast_array) - 1, self.change_window_first)
        cv2.createTrackbar('window_max', self.window_name, 0, len(self.contrast_array) - 1, self.change_window_last)
        cv2.setTrackbarPos('window_max', self.window_name, len(self.contrast_array) - 1)
    
    def change_window_first(self, x):
        if x >= self.window_max:
            x = self.window_max - 1
            cv2.setTrackbarPos('window_min', self.window_name, x)
        self.window_min = x
        self.pixel_arrays = self.dicom_controller.gen_normalized_pixel_arrays((self.contrast_array[self.window_min], self.contrast_array[self.window_max]))
        
    def change_window_last(self, x):
        if x <= self.window_min:
            x = self.window_min + 1
            cv2.setTrackbarPos('window_max', self.window_name, x)
        self.window_max = x
        self.pixel_arrays = self.dicom_controller.gen_normalized_pixel_arrays((self.contrast_array[self.window_min], self.contrast_array[self.window_max]))
        
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
        cv2.setTrackbarPos('size', self.window_name, self.size)
        cv2.setTrackbarPos('last', self.window_name, self.last_slice)
        cv2.setTrackbarPos('slices', self.window_name, 0)
        
    def generate_crop_rectangles(self):
        x, y = self.rectangle_center
        self.pixel_arrays = self.dicom_controller.gen_normalized_pixel_arrays((self.contrast_array[self.window_min], self.contrast_array[self.window_max]))
        for pxl_arr in self.pixel_arrays:
             cv2.rectangle(pxl_arr, (x-self.size, y-self.size), (x+self.size, y+self.size),(0,255,0),1)
    
    def run(self):
        while True:
            cv2.imshow(self.window_name, self.pixel_arrays[self.index])
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

        cv2.destroyAllWindows()

pouet = DicomMain()
pouet.mainloop()
