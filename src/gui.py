import customtkinter as ctk
import os
import threading
import json
import asyncio
import sys
from profile_manager import GoogleDriveProfileManager
from custom_dialogs import ask_string, show_info, show_error, ask_yes_no
from console_widget import CTkConsole, redirect_output_to_console
from google_drive_gui import GoogleDriveGUIWrapper
import tkinter as tk
from tkinter import filedialog

# Add scraper profiles to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'scraper_profiles'))
from chaseBus_monthly import login, csv_d
from playwright.async_api import async_playwright
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

ctk.set_appearance_mode("dark")

class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("1800x1000")
        self.title("Bank Drive Pipe - Google Drive Integration")
        
        # Configure main grid - 3 column layout: Left(40%) | Middle(30%) | Right(30%)
        self.grid_columnconfigure(0, weight=2)  # Left column 40% width
        self.grid_columnconfigure(1, weight=3)  # Middle column 30% width  
        self.grid_columnconfigure(2, weight=3)  # Right column 30% width
        self.grid_rowconfigure(0, weight=1)     # Top row
        self.grid_rowconfigure(1, weight=1)     # Bottom row
        
        # Left Full Column - Controls (Google Drive & Upload) - spans both rows
        self.controls_frame = ctk.CTkFrame(self, corner_radius=10)
        self.controls_frame.grid(row=0, column=0, rowspan=2, padx=(10, 5), pady=10, sticky="nsew")
        
        # Top Middle - Bank Scraper
        self.scraper_frame = ctk.CTkFrame(self, corner_radius=10)
        self.scraper_frame.grid(row=0, column=1, padx=5, pady=(10, 5), sticky="nsew")
        
        # Top Right - Account Status
        self.account_status_frame = ctk.CTkFrame(self, corner_radius=10)
        self.account_status_frame.grid(row=0, column=2, padx=(5, 10), pady=(10, 5), sticky="nsew")
        
        # Bottom Middle & Right - Console (spans both middle and right columns)
        self.console_frame = ctk.CTkFrame(self, corner_radius=10)
        self.console_frame.grid(row=1, column=1, columnspan=2, padx=(5, 10), pady=(5, 10), sticky="nsew")
        
        # Initialize components
        self.setup_controls()
        self.setup_scraper()
        self.setup_account_status()
        self.setup_console()
        
        # Initialize Google Drive wrapper
        self.drive_wrapper = GoogleDriveGUIWrapper(console_print=self.console.print)
        
        # Handle window close event
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_controls(self):
        """Setup the left side control panel"""
        self.controls_frame.grid_columnconfigure(0, weight=1)
        
        # Title
        title = ctk.CTkLabel(
            self.controls_frame, 
            text="Bank Drive Pipe", 
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        
        # Profile Management Section
        self.profile_section = ProfileSection(self.controls_frame, self)
        self.profile_section.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        
        # Google Drive Operations Section
        self.drive_section = GoogleDriveSection(self.controls_frame, self)
        self.drive_section.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        
        # Upload Operations Section
        self.upload_section = UploadSection(self.controls_frame, self)
        self.upload_section.grid(row=3, column=0, padx=10, pady=5, sticky="ew")

    def setup_scraper(self):
        """Setup the scraper section in top right"""
        self.scraper_frame.grid_columnconfigure(0, weight=1)
        
        # Scraper Section
        self.scraper_section = ScraperSection(self.scraper_frame, self)
        self.scraper_section.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

    def setup_account_status(self):
        """Setup the account status section"""
        self.account_status_frame.grid_columnconfigure(0, weight=1)
        
        # Account Status Section
        self.account_section = AccountStatusSection(self.account_status_frame, self)
        self.account_section.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

    def setup_console(self):
        """Setup the bottom console (spans middle and right columns)"""
        self.console_frame.grid_columnconfigure(0, weight=1)
        self.console_frame.grid_rowconfigure(1, weight=1)
        
        # Console title and controls
        console_header = ctk.CTkFrame(self.console_frame)
        console_header.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        console_header.grid_columnconfigure(0, weight=1)
        
        console_title = ctk.CTkLabel(
            console_header, 
            text="Console Output", 
            font=ctk.CTkFont(size=16, weight="bold")
        )
        console_title.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        clear_btn = ctk.CTkButton(
            console_header,
            text="Clear",
            command=self.clear_console,
            width=80,
            height=28
        )
        clear_btn.grid(row=0, column=1, padx=10, pady=5)
        
        # Console widget
        self.console = CTkConsole(self.console_frame, height=400)
        self.console.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        
        # Redirect print statements to console
        redirect_output_to_console(self.console)
        
        # Welcome message
        self.console.print_info("Welcome to Bank Drive Pipe!")
        self.console.print("Ready to integrate with Google Drive...")

    def clear_console(self):
        """Clear the console output"""
        self.console.clear()
    
    def on_closing(self):
        """Handle application closing - cleanup browser resources"""
        print("🔴 Application closing - cleaning up browser resources...")
        
        # Close browser if it's open
        if hasattr(self, 'scraper_section') and self.scraper_section:
            self.scraper_section.close_browser_sync()
            
        # Destroy the application
        self.destroy()

class ProfileSection(ctk.CTkFrame):
    """Profile management section"""
    
    def __init__(self, parent, main_app):
        super().__init__(parent, corner_radius=8)
        self.main_app = main_app
        self.profile_manager = GoogleDriveProfileManager()
        self.widgets = {}
        
        self.grid_columnconfigure(0, weight=1)
        
        # Section title
        title = ctk.CTkLabel(self, text="Profile Management", font=ctk.CTkFont(size=16, weight="bold"))
        title.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        
        # Profile dropdown
        profile_names = self.profile_manager.get_profile_names()
        if not profile_names:
            profile_names = ["No profiles saved"]
        
        self.widgets['profile_dropdown'] = ctk.CTkComboBox(
            self, 
            values=profile_names,
            command=self.load_selected_profile
        )
        self.widgets['profile_dropdown'].grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        
        # Form fields
        self.create_form_fields()
        
        # Buttons
        self.create_buttons()
    
    def create_form_fields(self):
        """Create the profile form fields"""
        # Root Directory
        root_label = ctk.CTkLabel(self, text="Root Directory:")
        root_label.grid(row=2, column=0, padx=10, pady=(10, 2), sticky="w")
        self.widgets['gdrive_root'] = ctk.CTkEntry(self, placeholder_text='e.g., "Financial Records"')
        self.widgets['gdrive_root'].grid(row=3, column=0, padx=10, pady=(0, 5), sticky="ew")
        
        # Target Directory
        target_label = ctk.CTkLabel(self, text="Target Directory:")
        target_label.grid(row=4, column=0, padx=10, pady=(5, 2), sticky="w")
        self.widgets['gdrive_target'] = ctk.CTkEntry(self, placeholder_text='e.g., "2025 Statements"')
        self.widgets['gdrive_target'].grid(row=5, column=0, padx=10, pady=(0, 5), sticky="ew")
        
        # API Client ID
        api_id_label = ctk.CTkLabel(self, text="API Client ID:")
        api_id_label.grid(row=6, column=0, padx=10, pady=(5, 2), sticky="w")
        self.widgets['gdrive_api_id'] = ctk.CTkEntry(self, placeholder_text="Client ID", show="*")
        self.widgets['gdrive_api_id'].grid(row=7, column=0, padx=10, pady=(0, 5), sticky="ew")
        
        # API Client Secret
        api_secret_label = ctk.CTkLabel(self, text="API Client Secret:")
        api_secret_label.grid(row=8, column=0, padx=10, pady=(5, 2), sticky="w")
        self.widgets['gdrive_api_secret'] = ctk.CTkEntry(self, placeholder_text="Client Secret", show="*")
        self.widgets['gdrive_api_secret'].grid(row=9, column=0, padx=10, pady=(0, 10), sticky="ew")
    
    def create_buttons(self):
        """Create profile management buttons"""
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=10, column=0, padx=10, pady=(0, 10), sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)
        
        save_btn = ctk.CTkButton(button_frame, text="Save Profile", command=self.save_profile)
        save_btn.grid(row=0, column=0, padx=(0, 5), pady=5, sticky="ew")
        
        load_btn = ctk.CTkButton(button_frame, text="Apply Profile", command=self.apply_profile)
        load_btn.grid(row=0, column=1, padx=(5, 0), pady=5, sticky="ew")
    
    def load_selected_profile(self, profile_name: str = None):
        """Load the selected profile into the form fields"""
        if not profile_name or profile_name == "No profiles saved":
            return
            
        profile_data = self.profile_manager.get_profile(profile_name)
        if profile_data:
            # Clear existing values
            for widget in self.widgets.values():
                if hasattr(widget, 'delete') and hasattr(widget, 'insert'):
                    widget.delete(0, 'end')
            
            # Load profile data into widgets
            if 'gdrive_root' in profile_data:
                self.widgets['gdrive_root'].insert(0, profile_data['gdrive_root'])
            if 'gdrive_target' in profile_data:
                self.widgets['gdrive_target'].insert(0, profile_data['gdrive_target'])
            if 'gdrive_api_id' in profile_data:
                self.widgets['gdrive_api_id'].insert(0, profile_data['gdrive_api_id'])
            if 'gdrive_api_secret' in profile_data:
                self.widgets['gdrive_api_secret'].insert(0, profile_data['gdrive_api_secret'])
                
            self.main_app.console.print_success(f"Loaded profile: {profile_name}")
    
    def save_profile(self):
        """Save current form data as a new profile"""
        profile_name = ask_string(self, "Save Profile", "Enter profile name:")
        
        if not profile_name:
            return
            
        # Check if profile exists
        if self.profile_manager.profile_exists(profile_name):
            result = ask_yes_no(
                self,
                "Profile Exists",
                f"Profile '{profile_name}' already exists.\\n\\nDo you want to overwrite it?"
            )
            if not result:
                return
        
        # Get current form data
        profile_data = {
            'gdrive_root': self.widgets['gdrive_root'].get(),
            'gdrive_target': self.widgets['gdrive_target'].get(),
            'gdrive_api_id': self.widgets['gdrive_api_id'].get(),
            'gdrive_api_secret': self.widgets['gdrive_api_secret'].get(),
        }
        
        # Save profile
        if self.profile_manager.save_profile(profile_name, profile_data):
            # Update dropdown with new profile
            profile_names = self.profile_manager.get_profile_names()
            self.widgets['profile_dropdown'].configure(values=profile_names)
            self.widgets['profile_dropdown'].set(profile_name)
            
            self.main_app.console.print_success(f"Profile '{profile_name}' saved successfully!")
            show_info(self, "Success", f"Profile '{profile_name}' saved successfully!")
        else:
            self.main_app.console.print_error(f"Failed to save profile '{profile_name}'")
            show_error(self, "Error", f"Failed to save profile '{profile_name}'")
    
    def apply_profile(self):
        """Apply the current profile settings"""
        profile_data = self.get_current_values()
        self.main_app.console.print_info("Applied current profile settings")
        return profile_data
    
    def get_current_values(self):
        """Get current form values"""
        return {
            'gdrive_root': self.widgets['gdrive_root'].get(),
            'gdrive_target': self.widgets['gdrive_target'].get(),
            'gdrive_api_id': self.widgets['gdrive_api_id'].get(),
            'gdrive_api_secret': self.widgets['gdrive_api_secret'].get(),
        }

class GoogleDriveSection(ctk.CTkFrame):
    """Google Drive operations section"""
    
    def __init__(self, parent, main_app):
        super().__init__(parent, corner_radius=8)
        self.main_app = main_app
        self.current_folder_id = None
        
        self.grid_columnconfigure(0, weight=1)
        
        # Section title
        title = ctk.CTkLabel(self, text="Google Drive Operations", font=ctk.CTkFont(size=16, weight="bold"))
        title.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        
        # Reset connection button
        self.reset_btn = ctk.CTkButton(self, text="🔄 Reset Connection", command=self.reset_connection, fg_color="gray", hover_color="darkgray")
        self.reset_btn.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        
        # Browse folder button
        self.browse_btn = ctk.CTkButton(self, text="📂 Browse Root Folder", command=self.browse_root_folder)
        self.browse_btn.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        
        # Navigate to target button
        self.navigate_btn = ctk.CTkButton(self, text="🧭 Navigate to Target", command=self.navigate_to_target)
        self.navigate_btn.grid(row=3, column=0, padx=10, pady=5, sticky="ew")
        
        # Browse target folder button
        self.browse_target_btn = ctk.CTkButton(self, text="📂 Browse Target Folder", command=self.browse_target_folder)
        self.browse_target_btn.grid(row=4, column=0, padx=10, pady=(5, 10), sticky="ew")
    
    def browse_root_folder(self):
        """Browse the root folder"""
        profile_data = self.main_app.profile_section.get_current_values()
        root_folder = profile_data.get('gdrive_root')
        
        if not root_folder:
            self.main_app.console.print_error("Please specify a root directory in your profile")
            return
        
        self.main_app.drive_wrapper.search_folder(root_folder, self.on_folder_found)
    
    def on_folder_found(self, folder_id):
        """Handle folder found callback"""
        if folder_id:
            self.current_folder_id = folder_id
            self.main_app.drive_wrapper.browse_folder(folder_id)
    
    def navigate_to_target(self):
        """Navigate to the target directory"""
        profile_data = self.main_app.profile_section.get_current_values()
        root_folder = profile_data.get('gdrive_root')
        target_path = profile_data.get('gdrive_target')
        
        if not root_folder or not target_path:
            self.main_app.console.print_error("Please specify both root and target directories")
            return
        
        # Split target path into parts
        path_parts = [part.strip() for part in target_path.split('/') if part.strip()]
        
        self.main_app.drive_wrapper.navigate_to_path(root_folder, path_parts, self.on_target_found)
    
    def on_target_found(self, folder_id):
        """Handle target folder found callback"""
        if folder_id:
            self.current_folder_id = folder_id
            self.main_app.upload_section.set_target_folder(folder_id)
    
    def browse_target_folder(self):
        """Browse target folder with full path display"""
        profile_data = self.main_app.profile_section.get_current_values()
        root_folder = profile_data.get('gdrive_root')
        target_path = profile_data.get('gdrive_target')
        
        if not root_folder or not target_path:
            self.main_app.console.print_error("Please specify both root and target directories")
            return
        
        # Split target path into parts
        path_parts = [part.strip() for part in target_path.split('/') if part.strip()]
        
        self.main_app.drive_wrapper.browse_target_folder(root_folder, path_parts, self.on_target_browsed)
    
    def on_target_browsed(self, folder_id, contents):
        """Handle target folder browsed callback"""
        if folder_id:
            self.current_folder_id = folder_id
            self.main_app.upload_section.set_target_folder(folder_id)
    
    def reset_connection(self):
        """Reset the Google Drive connection"""
        self.main_app.drive_wrapper.reset_connection()

class UploadSection(ctk.CTkFrame):
    """Upload operations section"""
    
    def __init__(self, parent, main_app):
        super().__init__(parent, corner_radius=8)
        self.main_app = main_app
        self.selected_files = []
        self.target_folder_id = None
        
        self.grid_columnconfigure(0, weight=1)
        
        # Section title
        title = ctk.CTkLabel(self, text="Upload Operations", font=ctk.CTkFont(size=16, weight="bold"))
        title.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        
        # File selection
        self.select_files_btn = ctk.CTkButton(self, text="📁 Select Files", command=self.select_files)
        self.select_files_btn.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        
        # Date Filter Label
        date_filter_label = ctk.CTkLabel(self, text="Date Filter for Downloads folder", font=ctk.CTkFont(size=12, weight="bold"))
        date_filter_label.grid(row=2, column=0, padx=10, pady=(10, 2), sticky="ew")
        
        # Month/Year selection for batch upload
        month_year_frame = ctk.CTkFrame(self, fg_color="transparent")
        month_year_frame.grid(row=3, column=0, padx=10, pady=5, sticky="ew")
        month_year_frame.grid_columnconfigure(0, weight=1)
        month_year_frame.grid_columnconfigure(1, weight=1)
        
        self.month_var = ctk.StringVar(value="01")
        month_menu = ctk.CTkOptionMenu(month_year_frame, variable=self.month_var,
                                      values=["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"])
        month_menu.grid(row=0, column=0, padx=(0, 5), pady=2, sticky="ew")
        
        self.year_var = ctk.StringVar(value="2025")
        year_entry = ctk.CTkEntry(month_year_frame, textvariable=self.year_var, placeholder_text="Year")
        year_entry.grid(row=0, column=1, padx=(5, 0), pady=2, sticky="ew")
        
        # Upload buttons
        self.upload_selected_btn = ctk.CTkButton(self, text="📤 Upload Selected", command=self.upload_selected_files)
        self.upload_selected_btn.grid(row=4, column=0, padx=10, pady=5, sticky="ew")
        
        self.batch_upload_btn = ctk.CTkButton(self, text="📤 Batch Upload", command=self.batch_upload_by_pattern)
        self.batch_upload_btn.grid(row=5, column=0, padx=10, pady=(5, 10), sticky="ew")
    
    def set_target_folder(self, folder_id: str):
        """Set the target folder ID for uploads"""
        self.target_folder_id = folder_id
        self.main_app.console.print_success(f"Target folder set for uploads: {folder_id}")
    
    def select_files(self):
        """Select files for upload"""
        file_paths = filedialog.askopenfilenames(
            title="Select files to upload",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if file_paths:
            self.selected_files = list(file_paths)
            self.main_app.console.print_info(f"Selected {len(self.selected_files)} files:")
            for file_path in self.selected_files:
                self.main_app.console.print_path(os.path.basename(file_path), "  📄")
    
    def upload_selected_files(self):
        """Upload the selected files"""
        if not self.selected_files:
            self.main_app.console.print_error("No files selected for upload")
            return
        
        if not self.target_folder_id:
            self.main_app.console.print_error("Please navigate to target folder first")
            return
        
        self.main_app.drive_wrapper.upload_files(self.selected_files, self.target_folder_id)
    
    def batch_upload_by_pattern(self):
        """Upload files matching month/year pattern"""
        month = self.month_var.get()
        year = int(self.year_var.get())
        
        # Use downloads directory by default
        local_folder = "downloads"
        
        if not os.path.exists(local_folder):
            self.main_app.console.print_error(f"Local folder not found: {local_folder}")
            return
        
        if not self.target_folder_id:
            self.main_app.console.print_error("Please navigate to target folder first")
            return
        
        self.main_app.drive_wrapper.batch_upload_by_pattern(local_folder, month, year, self.target_folder_id)

class ScraperSection(ctk.CTkFrame):
    """Bank scraper operations section"""
    
    def __init__(self, parent, main_app):
        super().__init__(parent, corner_radius=8)
        self.main_app = main_app
        self.selected_scraper = None
        self.playwright = None
        self.browser_context = None
        self.page = None
        self.login_instance = None
        self.csv_instance = None
        self.is_running = False
        
        self.grid_columnconfigure(0, weight=1)
        
        # Section title
        title = ctk.CTkLabel(self, text="Bank Scraper", font=ctk.CTkFont(size=16, weight="bold"))
        title.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        
        # Scraper profile dropdown
        profile_label = ctk.CTkLabel(self, text="Scraper Profile:")
        profile_label.grid(row=1, column=0, padx=10, pady=(10, 2), sticky="w")
        
        # Get available scraper profiles
        scraper_profiles = self.get_available_scrapers()
        
        self.scraper_dropdown = ctk.CTkComboBox(
            self, 
            values=scraper_profiles,
            command=self.on_scraper_selected,
            state="readonly"
        )
        self.scraper_dropdown.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="ew")
        
        # Set default selection if available
        if scraper_profiles and scraper_profiles[0] != "No scrapers found":
            self.scraper_dropdown.set(scraper_profiles[0])
            self.selected_scraper = scraper_profiles[0]
        
        # Date selection for scraper
        date_label = ctk.CTkLabel(self, text="Scraper Date Range:")
        date_label.grid(row=3, column=0, padx=10, pady=(10, 2), sticky="w")
        
        # Month/Year selection frame
        scraper_date_frame = ctk.CTkFrame(self, fg_color="transparent")
        scraper_date_frame.grid(row=4, column=0, padx=10, pady=5, sticky="ew")
        scraper_date_frame.grid_columnconfigure(0, weight=1)
        scraper_date_frame.grid_columnconfigure(1, weight=1)
        
        self.scraper_month_var = ctk.StringVar(value="01")
        month_menu = ctk.CTkOptionMenu(scraper_date_frame, variable=self.scraper_month_var,
                                      values=["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"])
        month_menu.grid(row=0, column=0, padx=(0, 5), pady=2, sticky="ew")
        
        self.scraper_year_var = ctk.StringVar(value="2025")
        year_entry = ctk.CTkEntry(scraper_date_frame, textvariable=self.scraper_year_var, placeholder_text="Year")
        year_entry.grid(row=0, column=1, padx=(5, 0), pady=2, sticky="ew")
        
        # Scraper status
        self.status_label = ctk.CTkLabel(self, text="Ready to run scraper", text_color="gray")
        self.status_label.grid(row=5, column=0, padx=10, pady=5, sticky="ew")
        
        # Individual function buttons
        functions_label = ctk.CTkLabel(self, text="Individual Functions:", font=ctk.CTkFont(size=12, weight="bold"))
        functions_label.grid(row=6, column=0, padx=10, pady=(10, 2), sticky="w")
        
        # Function buttons frame
        func_buttons_frame = ctk.CTkFrame(self, fg_color="transparent")
        func_buttons_frame.grid(row=7, column=0, padx=10, pady=5, sticky="ew")
        func_buttons_frame.grid_columnconfigure(0, weight=1)
        func_buttons_frame.grid_columnconfigure(1, weight=1)
        
        # First row of buttons
        self.launch_browser_btn = ctk.CTkButton(func_buttons_frame, text="🌐 Launch", command=self.run_launch_browser, width=70)
        self.launch_browser_btn.grid(row=0, column=0, padx=2, pady=2, sticky="ew")
        
        self.login_btn = ctk.CTkButton(func_buttons_frame, text="🔑 Login", command=self.run_login, width=70)
        self.login_btn.grid(row=0, column=1, padx=2, pady=2, sticky="ew")
        
        # Second row of buttons  
        self.init_download_btn = ctk.CTkButton(func_buttons_frame, text="📥 Initial", command=self.run_init_download, width=70)
        self.init_download_btn.grid(row=1, column=0, padx=2, pady=2, sticky="ew")
        
        self.norm_download_btn = ctk.CTkButton(func_buttons_frame, text="📊 Download", command=self.run_norm_download, width=70)
        self.norm_download_btn.grid(row=1, column=1, padx=2, pady=2, sticky="ew")
        
        # Full workflow buttons
        workflow_label = ctk.CTkLabel(self, text="Full Workflow:", font=ctk.CTkFont(size=12, weight="bold"))
        workflow_label.grid(row=8, column=0, padx=10, pady=(10, 2), sticky="w")
        
        # Run scraper button (full workflow)
        self.run_btn = ctk.CTkButton(self, text="🏦 Run Full Scraper", command=self.run_scraper)
        self.run_btn.grid(row=9, column=0, padx=10, pady=5, sticky="ew")
        
        # Control buttons frame
        control_buttons_frame = ctk.CTkFrame(self, fg_color="transparent")
        control_buttons_frame.grid(row=10, column=0, padx=10, pady=(5, 10), sticky="ew")
        control_buttons_frame.grid_columnconfigure(0, weight=1)
        control_buttons_frame.grid_columnconfigure(1, weight=1)
        
        # Stop scraper button
        self.stop_btn = ctk.CTkButton(control_buttons_frame, text="🛑 Stop", command=self.stop_scraper, state="disabled")
        self.stop_btn.grid(row=0, column=0, padx=2, pady=2, sticky="ew")
        
        # Close browser button
        self.close_browser_btn = ctk.CTkButton(control_buttons_frame, text="🔴 Close", command=self.close_browser_sync)
        self.close_browser_btn.grid(row=0, column=1, padx=2, pady=2, sticky="ew")
    
    def get_available_scrapers(self, debug=False):
        """Get list of available scraper profiles"""
        # Get the project root directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        scraper_dir = os.path.join(current_dir, "scraper_profiles")
        
        # Debug: Print paths for troubleshooting
        debug = True
        if debug:
            print(f"DEBUG: Current file: {__file__}")
            print(f"DEBUG: Project root: {current_dir}")
            print(f"DEBUG: Scraper dir: {scraper_dir}")
            print(f"DEBUG: Scraper dir exists: {os.path.exists(scraper_dir)}")
        
        if not os.path.exists(scraper_dir):
            return ["No scrapers found"]
        
        if debug:
            scrapers = []
            all_files = os.listdir(scraper_dir)
            print(f"DEBUG: Files in scraper_profiles: {all_files}")
            for file in all_files:
                print(f"DEBUG: Checking file: {file}")
                if file.endswith('.py') and not file.startswith('__'):
                    # Remove .py extension and format name
                    scraper_name = file[:-3].replace('_', ' ').title()
                    scrapers.append(scraper_name)
                    print(f"DEBUG: Added scraper: {scraper_name}")
            
            print(f"DEBUG: Final scrapers list: {scrapers}")
        return scrapers if scrapers else ["No scrapers found"]
    
    def on_scraper_selected(self, selection):
        """Handle scraper profile selection"""
        # Close existing browser when switching profiles
        if self.selected_scraper != selection and (self.browser_context or self.playwright):
            self.main_app.console.print_info("🔄 Switching scraper profile - closing existing browser...")
            self.close_browser_sync()
            
        self.selected_scraper = selection
        self.main_app.console.print_info(f"Selected scraper: {selection}")
        self.status_label.configure(text=f"Ready to run: {selection}")
    
    def run_launch_browser(self):
        """Launch browser and navigate to site only (no login)"""
        if not self.selected_scraper or self.selected_scraper == "No scrapers found":
            self.main_app.console.print_error("No valid scraper selected")
            return
        
        if self.is_running:
            self.main_app.console.print_warning("Scraper is already running")
            return
        
        self.main_app.console.print_info(f"🌐 Launching browser for: {self.selected_scraper}")
        self.status_label.configure(text="Launching browser...", text_color="orange")
        
        # Run browser launch in separate thread
        threading.Thread(target=self._run_launch_browser_async, daemon=True).start()

    def run_login(self):
        """Run only the login function"""
        if not self.selected_scraper or self.selected_scraper == "No scrapers found":
            self.main_app.console.print_error("No valid scraper selected")
            return
        
        if self.is_running:
            self.main_app.console.print_warning("Scraper is already running")
            return
        
        self.main_app.console.print_info(f"🔑 Running login for: {self.selected_scraper}")
        self.status_label.configure(text="Running login...", text_color="orange")
        
        # Run login in separate thread
        threading.Thread(target=self._run_login_async, daemon=True).start()

    def run_init_download(self):
        """Run only the init_download function"""
        if not self.selected_scraper or self.selected_scraper == "No scrapers found":
            self.main_app.console.print_error("No valid scraper selected")
            return
        
        if self.is_running:
            self.main_app.console.print_warning("Scraper is already running")
            return
        
        month = self.scraper_month_var.get()
        year = self.scraper_year_var.get()
        
        self.main_app.console.print_info(f"📥 Running initial download setup for: {self.selected_scraper}")
        self.main_app.console.print_info(f"📅 Date: {month}/{year}")
        self.status_label.configure(text="Running initial download...", text_color="orange")
        
        # Run init_download in separate thread
        threading.Thread(target=self._run_init_download_async, args=(int(month), int(year)), daemon=True).start()

    def run_norm_download(self):
        """Run only the norm_download function"""
        if not self.selected_scraper or self.selected_scraper == "No scrapers found":
            self.main_app.console.print_error("No valid scraper selected")
            return
        
        if self.is_running:
            self.main_app.console.print_warning("Scraper is already running")
            return
        
        month = self.scraper_month_var.get()
        year = self.scraper_year_var.get()
        
        self.main_app.console.print_info(f"📊 Running batch download for all accounts: {self.selected_scraper}")
        self.main_app.console.print_info(f"📅 Date: {month}/{year}")
        self.status_label.configure(text="Running batch download...", text_color="orange")
        
        # Run norm_download in separate thread
        threading.Thread(target=self._run_norm_download_async, args=(int(month), int(year)), daemon=True).start()
    
    def run_scraper(self):
        """Run the full scraper workflow (login -> init_download -> norm_download)"""
        if not self.selected_scraper or self.selected_scraper == "No scrapers found":
            self.main_app.console.print_error("No valid scraper selected")
            return
        
        month = self.scraper_month_var.get()
        year = self.scraper_year_var.get()
        
        self.main_app.console.print_info(f"🏦 Starting full scraper workflow: {self.selected_scraper}")
        self.main_app.console.print_info(f"📅 Date range: {month}/{year}")
        self.main_app.console.print_info(f"🔄 Workflow: Login → Init Download → Norm Download")
        self.status_label.configure(text="Full scraper running...", text_color="orange")
        
        # Disable run button, enable stop button
        self.run_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        
        # TODO: Implement actual scraper execution with full workflow
        self.main_app.console.print_warning("Full scraper execution not yet implemented")
        self.main_app.console.print_info(f"Would run: 1) Login 2) Init Download 3) Norm Download for {month}/{year}")
    
    def stop_scraper(self):
        """Stop the running scraper"""
        self.main_app.console.print_info("🛑 Stopping scraper...")
        self.status_label.configure(text=f"Ready to run: {self.selected_scraper}", text_color="gray")
        
        # Re-enable run button, disable stop button
        self.run_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        
        # Stop running operations
        self.is_running = False
        self.main_app.console.print_success("Scraper stopped")
    
    def _run_launch_browser_async(self):
        """Async wrapper for browser launch and navigation only"""
        import os
        user_data_dir = os.getenv("user_data_dir")
        
        async def run_launch():
            try:
                self.is_running = True
                
                # Close existing browser if any
                await self._close_browser()
                
                # Start new Playwright instance (keep it persistent)
                self.playwright = await async_playwright().start()
                self.browser_context = await self.playwright.chromium.launch_persistent_context(
                    user_data_dir,
                    headless=False,
                    slow_mo=1000,
                    viewport={"width": 1920, "height": 1040},
                    accept_downloads=True
                )
                self.page = await self.browser_context.new_page()
                
                # Initialize login instance
                self.login_instance = login(self.page)
                
                # Only launch and navigate (no login)
                await self.login_instance.launch_and_navigate()
                
                self.main_app.console.print_success("✅ Browser launched and navigated to Chase Business!")
                self.status_label.configure(text="Browser ready", text_color="green")
                
            except Exception as e:
                self.main_app.console.print_error(f"❌ Browser launch failed: {str(e)}")
                self.status_label.configure(text="Browser launch failed", text_color="red")
                await self._close_browser()
            finally:
                self.is_running = False
        
        # Run the async function
        asyncio.run(run_launch())
    
    def _run_login_async(self):
        """Async wrapper for login function"""
        
        async def run_login():
            try:
                self.is_running = True
                
                # Check if browser is already launched
                if not self.page or not self.login_instance:
                    self.main_app.console.print_error("❌ Browser not initialized. Please run 'Launch Browser' first.")
                    return
                
                # Execute login (navigate to sign in and fill credentials)
                self.main_app.console.print_info("🔐 Starting login process...")
                await self.login_instance.gotosite()  # Navigate to sign in page
                await asyncio.sleep(3)
                await self.login_instance.fill_credentials_only("chaseBus")  # Fill credentials
                await asyncio.sleep(1)  
                await self.login_instance.submit_login("chaseBus")  # Submit login
                
                self.main_app.console.print_success("✅ Login completed successfully!")
                self.status_label.configure(text="Login completed", text_color="green")
                
            except Exception as e:
                self.main_app.console.print_error(f"❌ Login failed: {str(e)}")
                self.status_label.configure(text="Login failed", text_color="red")
            finally:
                self.is_running = False
        
        # Run the async function
        asyncio.run(run_login())
    
    def _run_init_download_async(self, month, year):
        """Async wrapper for init_download function"""
        
        async def run_init():
            try:
                self.is_running = True
                
                if not self.page or not self.login_instance:
                    self.main_app.console.print_error("❌ Browser not initialized. Please run login first.")
                    return
                
                if not self.csv_instance:
                    self.csv_instance = csv_d(self.page)
                
                # Load bank accounts
                try:
                    with open('src/bank_acct_profiles/bank_accts.json', 'r') as file:
                        bank_accts = json.load(file)
                except FileNotFoundError:
                    with open('bank_acct_profiles/bank_accts.json', 'r') as file:
                        bank_accts = json.load(file)
                
                if not bank_accts:
                    self.main_app.console.print_error("❌ No bank accounts found in configuration")
                    return
                
                # Use first account for init_download
                first_account = bank_accts[0]
                account_name = first_account['name']
                account_num = first_account['num']
                
                self.main_app.console.print_info(f"📥 Starting init_download for: {account_name}")
                
                # Update current account in status section
                if hasattr(self.main_app, 'account_status'):
                    self.main_app.account_status.set_current_account(account_name, account_num)
                
                # Execute init_download for first account
                await self.csv_instance.init_download(account_name, account_num, month, year)
                
                self.main_app.console.print_success(f"✅ Initial download setup completed for {account_name}!")
                self.status_label.configure(text="Initial download completed", text_color="green")
                
            except Exception as e:
                self.main_app.console.print_error(f"❌ Initial download failed: {str(e)}")
                self.status_label.configure(text="Initial download failed", text_color="red")
            finally:
                self.is_running = False
        
        # Run the async function
        asyncio.run(run_init())
    
    def _run_norm_download_async(self, month, year):
        """Async wrapper for norm_download function"""
        
        async def run_norm():
            try:
                self.is_running = True
                
                if not self.page or not self.login_instance:
                    self.main_app.console.print_error("❌ Browser not initialized. Please run Launch and Login first.")
                    return
                
                if not self.csv_instance:
                    self.main_app.console.print_info("📥 Initializing CSV instance...")
                    self.csv_instance = csv_d(self.page)
                
                # Load bank accounts
                try:
                    with open('src/bank_acct_profiles/bank_accts.json', 'r') as file:
                        bank_accts = json.load(file)
                except FileNotFoundError:
                    with open('bank_acct_profiles/bank_accts.json', 'r') as file:
                        bank_accts = json.load(file)
                
                if not bank_accts:
                    self.main_app.console.print_error("❌ No bank accounts found in configuration")
                    return
                
                # Run norm_download for all accounts
                self.main_app.console.print_info(f"📊 Starting norm_download for {len(bank_accts)} accounts...")
                
                for i, account in enumerate(bank_accts):
                    account_name = account['name']
                    account_num = account['num']
                    
                    self.main_app.console.print_info(f"📊 Processing account {i+1}/{len(bank_accts)}: {account_name}")
                    
                    # Update current account in status section
                    if hasattr(self.main_app, 'account_status'):
                        self.main_app.account_status.set_current_account(account_name, account_num)
                    
                    try:
                        await self.csv_instance.norm_download(account_name, account_num, month, year)
                        self.main_app.console.print_success(f"✅ Downloaded {account_name} for {month}/{year}")
                    except Exception as e:
                        self.main_app.console.print_error(f"❌ Failed to download {account_name}: {str(e)}")
                        continue
                
                self.main_app.console.print_success("✅ Batch download completed for all accounts!")
                self.status_label.configure(text="Batch download completed", text_color="green")
                
            except Exception as e:
                self.main_app.console.print_error(f"❌ Batch download failed: {str(e)}")
                self.status_label.configure(text="Batch download failed", text_color="red")
            finally:
                self.is_running = False
        
        # Run the async function
        asyncio.run(run_norm())
    
    async def _close_browser(self):
        """Close browser and cleanup resources"""
        try:
            if self.browser_context:
                await self.browser_context.close()
                self.browser_context = None
                self.page = None
                self.login_instance = None
                self.csv_instance = None
                
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
                
        except Exception as e:
            self.main_app.console.print_error(f"Error closing browser: {str(e)}")
    
    def close_browser_sync(self):
        """Synchronous wrapper for closing browser"""
        if self.browser_context or self.playwright:
            asyncio.run(self._close_browser())
            self.main_app.console.print_info("🔴 Browser closed")

class AccountStatusSection(ctk.CTkFrame):
    """Account status display section"""
    
    def __init__(self, parent, main_app):
        super().__init__(parent, corner_radius=8)
        self.main_app = main_app
        self.current_account = None
        self.accounts_list = []
        
        self.grid_columnconfigure(0, weight=1)
        
        # Section title
        title = ctk.CTkLabel(self, text="Account Status", font=ctk.CTkFont(size=16, weight="bold"))
        title.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        
        # Current account info
        current_label = ctk.CTkLabel(self, text="Current Account:")
        current_label.grid(row=1, column=0, padx=10, pady=(10, 2), sticky="w")
        
        self.current_account_label = ctk.CTkLabel(self, text="None", font=ctk.CTkFont(size=14, weight="bold"))
        self.current_account_label.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="ew")
        
        # Accounts list
        accounts_label = ctk.CTkLabel(self, text="All Accounts:")
        accounts_label.grid(row=3, column=0, padx=10, pady=(10, 2), sticky="w")
        
        # Scrollable account list
        self.accounts_text = ctk.CTkTextbox(self, height=200, font=ctk.CTkFont(size=11))
        self.accounts_text.grid(row=4, column=0, padx=10, pady=(0, 10), sticky="nsew")
        
        # Load accounts button
        self.load_accounts_btn = ctk.CTkButton(self, text="🔄 Load Accounts", command=self.load_accounts)
        self.load_accounts_btn.grid(row=5, column=0, padx=10, pady=(0, 10), sticky="ew")
        
        # Auto-load accounts on startup
        self.after(1000, self.load_accounts)  # Load after 1 second
    
    def load_accounts(self):
        """Load accounts from bank_accts.json"""
        try:
            import json
            import os
            
            # Try multiple paths for bank_accts.json
            possible_paths = [
                'src/bank_acct_profiles/bank_accts.json',
                'bank_acct_profiles/bank_accts.json',
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src', 'bank_acct_profiles', 'bank_accts.json')
            ]
            
            bank_accts = None
            for path in possible_paths:
                if os.path.exists(path):
                    with open(path, 'r') as file:
                        bank_accts = json.load(file)
                    break
            
            if bank_accts:
                self.accounts_list = bank_accts
                self.update_accounts_display()
                self.main_app.console.print_success(f"✅ Loaded {len(bank_accts)} accounts")
            else:
                self.main_app.console.print_error("❌ Could not find bank_accts.json")
                self.accounts_text.delete("1.0", "end")
                self.accounts_text.insert("1.0", "❌ No accounts file found\n\nExpected locations:\n• src/bank_acct_profiles/bank_accts.json\n• bank_acct_profiles/bank_accts.json")
                
        except Exception as e:
            self.main_app.console.print_error(f"Error loading accounts: {str(e)}")
            self.accounts_text.delete("1.0", "end")
            self.accounts_text.insert("1.0", f"❌ Error loading accounts:\n{str(e)}")
    
    def update_accounts_display(self):
        """Update the accounts display"""
        self.accounts_text.delete("1.0", "end")
        
        if not self.accounts_list:
            self.accounts_text.insert("1.0", "No accounts loaded")
            return
        
        accounts_text = f"📊 Total Accounts: {len(self.accounts_list)}\n\n"
        for i, account in enumerate(self.accounts_list, 1):
            name = account.get('name', 'Unknown')
            num = account.get('num', 'N/A')
            status = "🔄 Pending" if i > 1 else "👆 Current" if self.current_account else "⏳ Ready"
            
            accounts_text += f"{i:2d}. {name}\n"
            accounts_text += f"     Account: ...{num}\n"
            accounts_text += f"     Status: {status}\n\n"
        
        self.accounts_text.insert("1.0", accounts_text)
    
    def set_current_account(self, account_name, account_num):
        """Set the current account being processed"""
        self.current_account = {"name": account_name, "num": account_num}
        self.current_account_label.configure(text=f"{account_name} (...{account_num})")
        self.update_accounts_display()
        self.main_app.console.print_info(f"📍 Processing: {account_name}")
    
    def clear_current_account(self):
        """Clear the current account"""
        self.current_account = None
        self.current_account_label.configure(text="None")
        self.update_accounts_display()

if __name__ == "__main__":
    app = MainApp()
    app.mainloop()