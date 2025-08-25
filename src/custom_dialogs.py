import customtkinter as ctk
from typing import Optional

class CTkInputDialog(ctk.CTkToplevel):
    """Custom input dialog that matches CustomTkinter styling"""
    
    def __init__(self, parent, title: str, prompt: str, initial_value: str = ""):
        super().__init__(parent)
        
        self.result = None
        self.parent = parent
        
        # Configure window dimensions
        self.dialog_width = 400
        self.dialog_height = 200
        
        self.title(title)
        self.geometry(f"{self.dialog_width}x{self.dialog_height}")
        self.resizable(False, False)
        
        # Make it modal and center on parent
        self.transient(parent)
        self.grab_set()
        self._center_on_parent()
        
        # Create main frame
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Prompt label
        prompt_label = ctk.CTkLabel(
            main_frame, 
            text=prompt, 
            font=ctk.CTkFont(size=14),
            wraplength=350
        )
        prompt_label.pack(pady=(10, 20))
        
        # Entry field
        self.entry = ctk.CTkEntry(
            main_frame, 
            placeholder_text="Enter profile name...",
            font=ctk.CTkFont(size=12),
            height=35
        )
        self.entry.pack(fill="x", padx=20, pady=(0, 20))
        
        if initial_value:
            self.entry.insert(0, initial_value)
        
        # Button frame
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", padx=20)
        
        # Configure button frame grid
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)
        
        # Cancel button
        cancel_btn = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self._cancel,
            fg_color="gray",
            hover_color="darkgray",
            width=80,
            height=32
        )
        cancel_btn.grid(row=0, column=0, padx=(0, 5), sticky="e")
        
        # Save button
        save_btn = ctk.CTkButton(
            button_frame,
            text="Save",
            command=self._ok,
            width=80,
            height=32
        )
        save_btn.grid(row=0, column=1, padx=(5, 0), sticky="w")
        
        # Bind Enter and Escape keys
        self.bind("<Return>", lambda event: self._ok())
        self.bind("<Escape>", lambda event: self._cancel())
        
        # Focus on entry field
        self.entry.focus()
        
        # Select all text if initial value provided
        if initial_value:
            self.entry.select_range(0, 'end')
    
    def _center_on_parent(self):
        """Center the dialog on the parent window"""
        self.update_idletasks()
        
        # Get parent geometry
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        # Use the manually set dialog dimensions (THIS WAS THE FIX!)
        dialog_width = self.dialog_width
        dialog_height = self.dialog_height
        
        x = parent_x + (parent_width // 2) - (dialog_width // 2)
        y = parent_y + (parent_height // 2) - (dialog_height // 2)
        
        self.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
    
    def _ok(self):
        """Handle OK button click"""
        self.result = self.entry.get().strip()
        self.destroy()
    
    def _cancel(self):
        """Handle Cancel button click"""
        self.result = None
        self.destroy()
    
    def get_result(self) -> Optional[str]:
        """Get the dialog result after it closes"""
        return self.result

class CTkMessageDialog(ctk.CTkToplevel):
    """Custom message dialog that matches CustomTkinter styling"""
    
    def __init__(self, parent, title: str, message: str, dialog_type: str = "info", 
                 buttons: list = None):
        super().__init__(parent)
        
        self.result = None
        self.parent = parent
        
        if buttons is None:
            if dialog_type == "yesno":
                buttons = ["Yes", "No"]
            else:
                buttons = ["OK"]
        
        # Configure window dimensions (CHANGE THESE LINES TO RESIZE)
        self.dialog_width = 400
        self.dialog_height = 200
        
        self.title(title)
        self.geometry(f"{self.dialog_width}x{self.dialog_height}")
        self.resizable(False, False)
        
        # Make it modal and center on parent
        self.transient(parent)
        self.grab_set()
        self._center_on_parent()
        
        # Create main frame
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Icon and message frame
        content_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, pady=(10, 20))
        
        # Message label
        message_label = ctk.CTkLabel(
            content_frame, 
            text=message, 
            font=ctk.CTkFont(size=13),
            wraplength=300,
            justify="left"
        )
        message_label.pack(pady=10)
        
        # Button frame
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x")
        
        # Create buttons
        self._create_buttons(button_frame, buttons, dialog_type)
        
        # Bind Escape key
        self.bind("<Escape>", lambda event: self._close(False))
        
        # Focus on the dialog
        self.focus()
    
    def _center_on_parent(self):
        """Center the dialog on the parent window"""
        self.update_idletasks()
        
        # Get parent geometry
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        # Use the manually set dialog dimensions (THIS WAS THE FIX!)
        dialog_width = self.dialog_width
        dialog_height = self.dialog_height
        
        x = parent_x + (parent_width // 2) - (dialog_width // 2)
        y = parent_y + (parent_height // 2) - (dialog_height // 2)
        
        self.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
    
    def _create_buttons(self, parent_frame, buttons, dialog_type):
        """Create buttons based on dialog type"""
        button_width = 75
        button_height = 32
        
        if len(buttons) == 1:
            # Single button (OK, etc.)
            btn = ctk.CTkButton(
                parent_frame,
                text=buttons[0],
                command=lambda: self._close(True),
                width=button_width,
                height=button_height
            )
            btn.pack()
        elif len(buttons) == 2:
            # Configure grid for two buttons
            parent_frame.grid_columnconfigure(0, weight=1)
            parent_frame.grid_columnconfigure(1, weight=1)
            
            # Left button (usually No/Cancel)
            left_btn = ctk.CTkButton(
                parent_frame,
                text=buttons[1],
                command=lambda: self._close(False),
                fg_color="gray",
                hover_color="darkgray",
                width=button_width,
                height=button_height
            )
            left_btn.grid(row=0, column=0, padx=(0, 5), sticky="e")
            
            # Right button (usually Yes/OK)
            right_btn = ctk.CTkButton(
                parent_frame,
                text=buttons[0],
                command=lambda: self._close(True),
                width=button_width,
                height=button_height
            )
            right_btn.grid(row=0, column=1, padx=(5, 0), sticky="w")
            
            # Bind Enter to right button
            self.bind("<Return>", lambda event: self._close(True))
    
    def _close(self, result):
        """Close dialog with result"""
        self.result = result
        self.destroy()
    
    def get_result(self) -> bool:
        """Get the dialog result after it closes"""
        return self.result if self.result is not None else False

def ask_string(parent, title: str, prompt: str, initial_value: str = "") -> Optional[str]:
    """Show a string input dialog and return the result"""
    dialog = CTkInputDialog(parent, title, prompt, initial_value)
    parent.wait_window(dialog)
    return dialog.get_result()

def show_info(parent, title: str, message: str) -> None:
    """Show an info message dialog"""
    dialog = CTkMessageDialog(parent, title, message, "info")
    parent.wait_window(dialog)

def show_error(parent, title: str, message: str) -> None:
    """Show an error message dialog"""
    dialog = CTkMessageDialog(parent, title, message, "error")
    parent.wait_window(dialog)

def ask_yes_no(parent, title: str, message: str) -> bool:
    """Show a yes/no question dialog and return the result"""
    dialog = CTkMessageDialog(parent, title, message, "yesno")
    parent.wait_window(dialog)
    return dialog.get_result()