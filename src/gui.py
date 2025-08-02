import customtkinter as ctk
import google_conn

ctk.set_appearance_mode("dark")

class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("1600x900")
        self.title("Google Drive Uploader")

        # Left frame
        self.dir_frame = ctk.CTkFrame(master=self, width=300)
        self.dir_frame.pack(side="left", fill="y", padx=20, pady=20)

        self.entries = {}
        for row, label_text in enumerate(["Root Directory", "Destination Directory"]):
            label = ctk.CTkLabel(self.dir_frame, text=label_text+" :")
            label.grid(row=row, column = 0, sticky="e", pady=20)
            entry = ctk.CTkEntry(self.dir_frame, width=180)
            entry.grid(row=row, column=1, sticky="w", padx=20, pady=20)
            self.entries[label_text] = entry

        def text_input_handler(self):
            for label_entry in self.entries.items():
                print(f"{label}: {entry.get()}")

        self.dir_frame_btn = ctk.CTkButton(self.dir_frame, text="Submit", command=text_input_handler)
        self.dir_frame_btn.grid(row=row+1, column=0, columnspan=2, pady=10)

        # Northeast/Upper Right Frame
        self.upload_frame = Upload(master=self)
        self.upload_frame.place(relx=1, rely=0, anchor="ne", x=-20, y=20)


class Upload(ctk.CTkFrame):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, width=600, height=110, border_width=2, border_color="grey", **kwargs)
        ctk.CTkLabel(self, text="Upload Frame").pack(padx=10, pady=100, fill="x")

if __name__=="__main__":
    app = MainApp()
    app.mainloop()
    