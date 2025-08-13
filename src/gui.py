import customtkinter as ctk
import google_conn
import os

ctk.set_appearance_mode("dark")

class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("1600x900")
        self.title("Google Drive Uploader")

        # Left frame
        self.dir_frame = DirInfo(master=self)
        self.dir_frame.pack(side="left", fill="y", padx=10, pady=10)

        # Northeast/Upper Right Frame
        self.upload_frame = Upload(master=self)
        self.upload_frame.pack(side="top", anchor="ne", padx=10, pady=10)
    
class DirInfo(ctk.CTkFrame):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, width=600, height=110, border_width=2, border_color="grey", **kwargs)
        
        self.entries = {}

        self.gDrive_label = ctk.CTkLabel(self, text="Google Drive Info").grid(row=0, column=0, columnspan=2,padx=10, pady=10)
        for row, label_text in enumerate(["Root Directory", "Destination Directory"]):
            label = ctk.CTkLabel(self, text=label_text+" :")
            label.grid(row=row+1, column = 0, sticky="e", padx=10, pady=20)
            entry = ctk.CTkEntry(self, width=180)
            entry.grid(row=row+1, column=1, sticky="w", padx=10, pady=20)
            self.entries[label_text] = entry

        self.dir_frame_btn = ctk.CTkButton(self, text="Submit", command=self.text_input_handler)
        self.dir_frame_btn.grid(row=row+2, column=0, columnspan=2, pady=10)


    def text_input_handler(self):
            for label, entry in self.entries.items():
                print(f"{label}: {entry.get()}")

class Scraper(ctk.CTkFrame):
    def __init__(self, master=None, base_dir="src/photos", **kwargs):
        super().__init__(master, width=600, height= 300, border_width=2, border_color="grey", **kwargs)
        self.base_dir = base_dir

        self.update_folders()

        ctk.CTkLabel(self, text="Data Scraper for Chase").grid(row=0, column=0, columnspan=2, padx=10, pady=10)

        # Dropdown
        self.combobox = ctk.CTkComboBox(self, values=self.folders).grid(row=1, column=0, padx=10, pady=10)

        self.new_folder_entry = ctk.CTkEntry(self, placeholder_text="New Folder Name").grid(row=2, column=0, padx=10, pady=10)

        self.add_button = ctk.CTkButton(self, text="Create New Folder", command=self.add_folder).grid(row=2, column=1, padx=10, pady=5)

    def update_folders(self):
        try:
            self.folders = [f for f in os.listdir(self.base_dir) if os.path.isdir(os.path.join(self.base_dir, f))]
        except Exception as e:
            self.folders = []
        if hasattr(self, "combobox"):
            self.combobox.configure(values=self.folders)
    
    def add_folder(self):
        new_folder_name = self.new_folder_entry.get().strip()
        
        if new_folder_name:
            full_path = os.path.join(self.base_dir, new_folder_name)
            if not os.path.exists(full_path):
                os.makedirs(full_path)
                self.update_folders()
                self.combobox.set(new_folder_name)
                self.new_folder_entry.delete(0, "end")
            else:
                self.combobox.set(new_folder_name)
        else:
            pass

class input_info(ctk.CTkFrame):
    def __init__(self, master=None, photos_dir="src/photos", **kwargs):
        self.photos_dir = photos_dir

        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)

        # Drive Info
        gdrive_title = ctk.CTkLabel(self, text="Google Drive")
        gdrive_title.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        gdrive_

        month_label = ctk.CTkLabel(self, text="Month: ")
        month_label.grid(row=1, column=0, sticky="e", padx=5)
        month_menu = ctk.CTkOptionMenu(self, values=["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"])
        month_menu.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        year_label = ctk.CTkLabel(self, text="Year: ")
        year_label.grid(row=2, column=0, sticky="e", padx=5)
        year_entry = ctk.CTkEntry(self, placeholder_text="Year: XXXX")
        year_entry.grid(row=2, column=1, padx=10, pady=10, sticky="ew")

class Upload(ctk.CTkFrame):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, border_width=2, border_color="grey", **kwargs)
        # ctk.CTkLabel(self, text="Upload Frame").grid(row=0, column=0, columnspan=2, padx=10, pady=10)

        # month_label = ctk.CTkLabel(self, text="Month: ").grid(row=1, column=0)
        # month = ctk.CTkOptionMenu(self, values=["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]).grid(row=1, column=1, padx=10, pady=10)
        # year_label = ctk.CTkLabel(self, text="Year: ").grid(row=2, column=0)
        # year = ctk.CTkEntry(self,placeholder_text="Year: XXXX").grid(row=2, column=1, padx=10,pady=10)

        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2) # input fields to stretch

        title_label = ctk.CTkLabel(self, text="Upload Frame")
        title_label.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        month_label = ctk.CTkLabel(self, text="Month: ")
        month_label.grid(row=1, column=0, sticky="e", padx=5)
        month_menu = ctk.CTkOptionMenu(self, values=["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"])
        month_menu.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        year_label = ctk.CTkLabel(self, text="Year: ")
        year_label.grid(row=2, column=0, sticky="e", padx=5)
        year_entry = ctk.CTkEntry(self, placeholder_text="Year: XXXX")
        year_entry.grid(row=2, column=1, padx=10, pady=10, sticky="ew")


if __name__=="__main__":
    app = MainApp()
    app.mainloop()

    