import threading
import os
from typing import Optional, List, Dict, Callable
from google_conn import (
    authenticate_drive, get_folder, get_subfolder_id, 
    get_nested_folder_id, upload_file, list_drive_files, 
    file_match, get_token_path, get_folder_path_and_contents
)

class GoogleDriveGUIWrapper:
    """Simplified wrapper for Google Drive operations with GUI integration"""
    
    def __init__(self, console_print: Callable[[str], None] = print):
        self.console_print = console_print
        self._service = None
        self._authenticated_user = None
        
    def get_service(self):
        """Get Google Drive service with caching to avoid re-authentication"""
        # Return cached service if available
        if self._service is not None:
            try:
                # Test that the cached service still works
                about = self._service.about().get(fields='user').execute()
                return self._service
            except Exception as e:
                self.console_print(f"Cached service expired: {str(e)}")
                self._service = None
                self._authenticated_user = None
        
        # Need to authenticate
        try:
            self.console_print("🔑 Connecting to Google Drive...")
            service = authenticate_drive()
            
            if service is not None:
                # Test the connection with a simple API call
                try:
                    about = service.about().get(fields='user').execute()
                    user_email = about.get('user', {}).get('emailAddress', 'Unknown')
                    self.console_print(f"✓ Connected to Google Drive as: {user_email}")
                    
                    # Cache the service and user info
                    self._service = service
                    self._authenticated_user = user_email
                    return service
                except Exception as test_error:
                    self.console_print(f"✗ Connection test failed: {str(test_error)}")
                    return None
            else:
                self.console_print("✗ authenticate_drive() returned None")
                return None
                
        except Exception as e:
            self.console_print(f"✗ Failed to connect to Google Drive: {str(e)}")
            return None
    
    def reset_connection(self):
        """Reset the connection by removing token file and clearing cache"""
        try:
            # Clear cached service
            self._service = None
            self._authenticated_user = None
            
            # Remove token file
            token_path = get_token_path()
            if os.path.exists(token_path):
                os.remove(token_path)
                self.console_print("🔄 Token file removed - will re-authenticate on next operation")
            else:
                self.console_print("🔄 No token file found to remove")
                
            self.console_print("🔄 Connection cache cleared")
        except Exception as e:
            self.console_print(f"✗ Error resetting connection: {str(e)}")
    
    def search_folder(self, folder_name: str, callback: Optional[Callable[[Optional[str]], None]] = None):
        """Search for a folder by name"""
        def _search():
            service = self.get_service()
            if not service:
                self.console_print("✗ No Google Drive connection available")
                if callback:
                    callback(None)
                return
            
            try:
                self.console_print(f"🔍 Searching for folder: '{folder_name}'...")
                folder_id = get_folder(service, folder_name, silent=True)
                
                if folder_id:
                    self.console_print(f"✓ Found folder: {folder_name}")
                    self.console_print(f"  └── ID: {folder_id}")
                else:
                    self.console_print(f"✗ Folder not found: {folder_name}")
                
                if callback:
                    callback(folder_id)
                    
            except Exception as e:
                self.console_print(f"✗ Error searching folder: {str(e)}")
                if callback:
                    callback(None)
        
        thread = threading.Thread(target=_search, daemon=True)
        thread.start()
    
    def browse_folder(self, folder_id: str, callback: Optional[Callable[[List[Dict]], None]] = None):
        """Browse contents of a folder"""
        def _browse():
            service = self.get_service()
            if not service:
                self.console_print("✗ No Google Drive connection available")
                if callback:
                    callback([])
                return
            
            try:
                self.console_print(f"📂 Browsing folder contents...")
                
                # Get folder contents
                results = service.files().list(
                    q=f"'{folder_id}' in parents and trashed=false",
                    pageSize=1000,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                    fields="nextPageToken, files(id, name, mimeType, parents, modifiedTime)",
                ).execute()
                
                items = results.get('files', [])
                
                if not items:
                    self.console_print("📂 Folder is empty")
                else:
                    self.console_print(f"📂 Found {len(items)} items:")
                    
                    # Separate folders and files
                    folders = [item for item in items if item['mimeType'] == 'application/vnd.google-apps.folder']
                    files = [item for item in items if item['mimeType'] != 'application/vnd.google-apps.folder']
                    
                    # Display folders first
                    for folder in folders:
                        self.console_print(f"  📁 {folder['name']}")
                    
                    # Then display files
                    for file in files:
                        file_type = self._get_file_type_icon(file['mimeType'])
                        self.console_print(f"  {file_type} {file['name']}")
                
                if callback:
                    callback(items)
                    
            except Exception as e:
                self.console_print(f"✗ Error browsing folder: {str(e)}")
                if callback:
                    callback([])
        
        thread = threading.Thread(target=_browse, daemon=True)
        thread.start()
    
    def navigate_to_path(self, root_folder_name: str, path_parts: List[str], 
                        callback: Optional[Callable[[Optional[str]], None]] = None):
        """Navigate to a nested folder path"""
        def _navigate():
            service = self.get_service()
            if not service:
                self.console_print("✗ No Google Drive connection available")
                if callback:
                    callback(None)
                return
            
            try:
                self.console_print(f"🧭 Navigating to path...")
                self.console_print(f"  📁 Root: {root_folder_name}")
                
                # Get root folder (silent mode)
                root_id = get_folder(service, root_folder_name, silent=True)
                if not root_id:
                    self.console_print(f"✗ Root folder not found: {root_folder_name}")
                    if callback:
                        callback(None)
                    return
                
                self.console_print(f"✓ Found root folder: {root_folder_name}")
                
                # Navigate through path with hierarchical indentation
                current_path = root_folder_name
                for i, part in enumerate(path_parts):
                    indent = "  " * (i + 1)  # Each level gets one more indent
                    self.console_print(f"{indent}└── {part}")
                    current_path = f"{current_path}/{part}"
                
                final_id = get_nested_folder_id(service, path_parts, root_id, silent=True)
                
                if final_id:
                    self.console_print(f"✓ Successfully navigated to: {current_path}")
                    self.console_print(f"🎯 Target folder ready for uploads")
                else:
                    self.console_print(f"✗ Failed to navigate to: {current_path}")
                
                if callback:
                    callback(final_id)
                    
            except Exception as e:
                self.console_print(f"✗ Error navigating: {str(e)}")
                if callback:
                    callback(None)
        
        thread = threading.Thread(target=_navigate, daemon=True)
        thread.start()
    
    def upload_files(self, file_paths: List[str], destination_folder_id: str,
                    callback: Optional[Callable[[List[bool]], None]] = None):
        """Upload multiple files to a destination folder"""
        def _upload():
            service = self.get_service()
            if not service:
                self.console_print("✗ No Google Drive connection available")
                if callback:
                    callback([])
                return
            
            results = []
            total_files = len(file_paths)
            
            self.console_print(f"📤 Uploading {total_files} file{'s' if total_files != 1 else ''}...")
            
            for i, file_path in enumerate(file_paths, 1):
                try:
                    if not os.path.exists(file_path):
                        self.console_print(f"✗ File not found: {file_path}")
                        results.append(False)
                        continue
                    
                    filename = os.path.basename(file_path)
                    self.console_print(f"📤 ({i}/{total_files}) Uploading: {filename}")
                    
                    upload_file(service, file_path, destination_folder_id)
                    
                    self.console_print(f"✓ Upload complete: {filename}")
                    results.append(True)
                    
                except Exception as e:
                    self.console_print(f"✗ Upload failed for {os.path.basename(file_path)}: {str(e)}")
                    results.append(False)
            
            successful = sum(results)
            if successful == total_files:
                self.console_print(f"✅ All {total_files} files uploaded successfully!")
            elif successful > 0:
                self.console_print(f"⚠️ {successful}/{total_files} files uploaded successfully")
            else:
                self.console_print(f"❌ No files were uploaded successfully")
            
            if callback:
                callback(results)
        
        thread = threading.Thread(target=_upload, daemon=True)
        thread.start()
    
    def batch_upload_by_pattern(self, local_folder: str, month: str, year: int, 
                               destination_folder_id: str,
                               callback: Optional[Callable[[List[str]], None]] = None):
        """Upload files matching a pattern (month/year)"""
        def _batch_upload():
            service = self.get_service()
            if not service:
                self.console_print("✗ No Google Drive connection available")
                if callback:
                    callback([])
                return
            
            try:
                self.console_print(f"🔍 Finding files for {month}/{year} in {local_folder}")
                
                # Show all files in folder first (human readable)
                if os.path.exists(local_folder):
                    all_files = os.listdir(local_folder)
                    self.console_print(f"📁 Found {len(all_files)} files in {local_folder}:")
                    if all_files:
                        for file in all_files:
                            self.console_print(f"  📄 {file}")
                    else:
                        self.console_print("  (folder is empty)")
                else:
                    self.console_print(f"❌ Folder '{local_folder}' does not exist!")
                    if callback:
                        callback([])
                    return
                
                # Find matching files (with debug output)
                self.console_print(f"🔍 Looking for pattern: *__{year}_{month}.csv")
                matched_files = file_match(local_folder, month, year, debug=False)
                
                # Show matching logic for each file
                self.console_print(f"🔍 Checking each file against pattern:")
                for file in all_files:
                    if "__" not in file:
                        self.console_print(f"  ❌ {file} - missing '__'")
                    elif not file.endswith('.csv'):
                        self.console_print(f"  ❌ {file} - not a .csv file")
                    else:
                        parts = file.split("__")
                        if len(parts) >= 2:
                            date_part = parts[1][:-4]  # Remove .csv extension
                            expected = f"{year}_{month}"
                            if date_part == expected:
                                self.console_print(f"  ✅ {file} - MATCH! ({date_part})")
                            else:
                                self.console_print(f"  ❌ {file} - date mismatch (got '{date_part}', need '{expected}')")
                        else:
                            self.console_print(f"  ❌ {file} - not enough parts after '__' split")
                
                if not matched_files:
                    self.console_print(f"ℹ️ No files found matching pattern for {month}/{year}")
                    if callback:
                        callback([])
                    return
                
                self.console_print(f"🔍 Found {len(matched_files)} files for {month}/{year}")
                if len(matched_files) <= 5:
                    for file in matched_files:
                        self.console_print(f"  📄 {file}")
                else:
                    for file in matched_files[:3]:
                        self.console_print(f"  📄 {file}")
                    self.console_print(f"  ... and {len(matched_files) - 3} more files")
                
                # Upload each file
                file_paths = [os.path.join(local_folder, file) for file in matched_files]
                self.upload_files(file_paths, destination_folder_id, callback)
                
            except Exception as e:
                self.console_print(f"✗ Error in batch upload: {str(e)}")
                if callback:
                    callback([])
        
        thread = threading.Thread(target=_batch_upload, daemon=True)
        thread.start()
    
    def browse_target_folder(self, root_folder_name: str, path_parts: List[str], 
                            callback: Optional[Callable[[Optional[str], List[Dict]], None]] = None):
        """Browse target folder with full path display from root to target"""
        def _browse_target():
            service = self.get_service()
            if not service:
                self.console_print("✗ No Google Drive connection available")
                if callback:
                    callback(None, [])
                return
            
            try:
                self.console_print(f"🔍 Browsing target folder with full path...")
                
                # Get path and contents using the new function (silent mode)
                path_array, target_folder_id, contents = get_folder_path_and_contents(
                    service, root_folder_name, path_parts, silent=True
                )
                
                # Display user-friendly path info
                if path_array and target_folder_id:
                    self.console_print(f"📂 Path: {' → '.join(path_array)}")
                    
                    if contents:
                        folders = [item for item in contents if item['mimeType'] == 'application/vnd.google-apps.folder']
                        files = [item for item in contents if item['mimeType'] != 'application/vnd.google-apps.folder']
                        
                        self.console_print(f"📊 Contents: {len(folders)} folders, {len(files)} files")
                        
                        # Display folders first
                        if folders:
                            self.console_print("📁 Folders:")
                            for folder in folders:
                                self.console_print(f"  📁 {folder['name']}")
                        
                        # Then display files
                        if files:
                            self.console_print("📄 Files:")
                            for file in files:
                                file_icon = self._get_file_type_icon(file['mimeType'])
                                file_type_name = self._get_file_type_name(file['mimeType'], file.get('name', ''))
                                self.console_print(f"  {file_icon} {file['name']} ({file_type_name})")
                    else:
                        self.console_print(f"📂 Target folder is empty")
                    
                    self.console_print(f"✓ Successfully browsed target folder")
                else:
                    self.console_print(f"✗ Failed to browse target folder")
                
                if callback:
                    callback(target_folder_id, contents or [])
                    
            except Exception as e:
                self.console_print(f"✗ Error browsing target folder: {str(e)}")
                if callback:
                    callback(None, [])
        
        thread = threading.Thread(target=_browse_target, daemon=True)
        thread.start()
    
    def _get_file_type_icon(self, mime_type: str) -> str:
        """Get an icon for the file type"""
        if 'folder' in mime_type:
            return '📁'
        elif 'spreadsheet' in mime_type or 'csv' in mime_type:
            return '📊'
        elif 'document' in mime_type:
            return '📄'
        elif 'image' in mime_type:
            return '🖼️'
        elif 'pdf' in mime_type:
            return '📕'
        elif 'presentation' in mime_type:
            return '📊'
        elif 'video' in mime_type:
            return '🎥'
        elif 'audio' in mime_type:
            return '🎵'
        elif 'zip' in mime_type or 'archive' in mime_type:
            return '📦'
        else:
            return '📄'
    
    def _get_file_type_name(self, mime_type: str, filename: str = '') -> str:
        """Get a human-readable file type name"""
        # Check file extension first for more specific types
        if filename:
            ext = filename.lower().split('.')[-1] if '.' in filename else ''
            if ext in ['csv']:
                return 'CSV File'
            elif ext in ['xlsx', 'xls']:
                return 'Excel File'
            elif ext in ['pdf']:
                return 'PDF File'
            elif ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp']:
                return f'{ext.upper()} Image'
            elif ext in ['mp4', 'avi', 'mov', 'wmv']:
                return f'{ext.upper()} Video'
            elif ext in ['mp3', 'wav', 'flac']:
                return f'{ext.upper()} Audio'
            elif ext in ['zip', 'rar', '7z']:
                return f'{ext.upper()} Archive'
            elif ext in ['txt']:
                return 'Text File'
            elif ext in ['doc', 'docx']:
                return 'Word Document'
            elif ext in ['ppt', 'pptx']:
                return 'PowerPoint'
        
        # Fall back to MIME type
        if 'vnd.google-apps.spreadsheet' in mime_type:
            return 'Google Sheets'
        elif 'vnd.google-apps.document' in mime_type:
            return 'Google Docs'
        elif 'vnd.google-apps.presentation' in mime_type:
            return 'Google Slides'
        elif 'vnd.google-apps.folder' in mime_type:
            return 'Folder'
        elif 'text/csv' in mime_type:
            return 'CSV File'
        elif 'application/pdf' in mime_type:
            return 'PDF File'
        elif 'image/' in mime_type:
            return 'Image'
        elif 'video/' in mime_type:
            return 'Video'
        elif 'audio/' in mime_type:
            return 'Audio'
        elif 'text/' in mime_type:
            return 'Text File'
        else:
            # Extract the subtype from mime_type as last resort
            if '/' in mime_type:
                subtype = mime_type.split('/')[-1]
                return subtype.replace('-', ' ').title()
            return 'File'