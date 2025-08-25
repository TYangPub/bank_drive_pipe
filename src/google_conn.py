from __future__ import print_function
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

import ast
import os
import pickle

SCOPES = ['https://www.googleapis.com/auth/drive']

def get_project_root():
    """Get the project root directory"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # If we're in src/, go up one level
    if os.path.basename(current_dir) == 'src':
        return os.path.dirname(current_dir)
    return current_dir

def get_creds_path():
    """Get the credentials directory path"""
    project_root = get_project_root()
    return os.path.join(project_root, 'src', 'creds')

def get_token_path():
    """Get the token file path"""
    return os.path.join(get_creds_path(), 'token.pickle')

def get_client_secrets_path():
    """Get the client secrets file path"""
    return os.path.join(get_creds_path(), 'auto_files_cred.json')

def authenticate_drive():
    creds = None
    token_path = get_token_path()
    
    # Load existing token if it exists
    if os.path.exists(token_path):
        try:
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        except Exception as e:
            print(f"Error loading token: {e}")
            # If token is corrupted, delete it and start fresh
            try:
                os.remove(token_path)
            except:
                pass
            creds = None
    
    # Check if we need to authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                print("Token refreshed successfully")
            except Exception as e:
                print(f"Token refresh failed: {e}")
                creds = None
        
        if not creds:
            # Need to do full authentication
            client_secrets_path = get_client_secrets_path()
            if not os.path.exists(client_secrets_path):
                raise FileNotFoundError(f"Client secrets file not found: {client_secrets_path}")
            
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_path, SCOPES)
            creds = flow.run_local_server(port=0)
            print("New authentication completed")
        
        # Save the credentials
        try:
            os.makedirs(os.path.dirname(token_path), exist_ok=True)
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
            print(f"Token saved to: {token_path}")
        except Exception as e:
            print(f"Error saving token: {e}")
    
    service = build('drive', 'v3', credentials=creds)
    return service

def get_folder(service, folder_name, silent=False):
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    # results = service.files().list(q=query, fields="files(id, name)").execute()
    results = service.files().list(
        q=query,
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
        fields="nextPageToken, files(id, name, mimeType, parents)"
    ).execute()
    items = results.get('files', [])

    if not items:
        if not silent:
            print(f'No folder found with name: {folder_name}')
        return None
    else:
        if not silent:
            print(f'Found folder: {items[0]["name"]} with ID: {items[0]["id"]}')
        return items[0]["id"] 

def get_subfolder_id(service, folder_name, parent_id, silent=False):
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false and '{parent_id}' in parents"

    results = service.files().list(
        q=query,
        spaces='drive',
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
        fields="nextPageToken, files(id, name, mimeType)"
    ).execute()

    folders = results.get('files', [])
    if not folders:
        if not silent:
            print(f'No subfolder found with name: {folder_name} in parent ID: {parent_id}')
        return None
    elif len(folders) > 1:
        if not silent:
            print(f'Multiple subfolders found with name: {folder_name} in parent ID: {parent_id}')
    
    folder = folders[0]
    if not silent:
        print(f'Found subfolder: {folder["name"]} with ID: {folder["id"]} in parent ID: {parent_id}')
    return folder['id']

def get_nested_folder_id(service, path_parts, root_folder_id, silent=False):
    current_folder_id = root_folder_id

    for name in path_parts:
        query = (
            f"name = '{name}' and '{current_folder_id}' in parents "
            "and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        )

        results = service.files().list(
            q=query,
            spaces='drive',
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            fields="nextPageToken, files(id, name, mimeType)",
            pageSize=1
        ).execute()

        folders = results.get('files', [])
        if not folders:
            if not silent:
                print(f'No folder found with name: {name} in parent ID: {current_folder_id}')
            return None
        current_folder_id = folders[0]['id']
        if not silent:
            print(f'Found folder: {folders[0]["name"]} with ID: {current_folder_id} in parent ID: {current_folder_id}')
    return current_folder_id

def get_folder_path_and_contents(service, root_folder_name, path_parts, silent=False):
    """
    Get the full path from root to target folder and show target folder contents.
    Returns a tuple of (path_array, target_folder_id, contents)
    """
    try:
        # Get root folder
        root_id = get_folder(service, root_folder_name)
        if not root_id:
            if not silent:
                print(f'Root folder not found: {root_folder_name}')
            return None, None, None
        
        # Build path array starting with root
        path_array = [root_folder_name]
        current_folder_id = root_id
        
        # Navigate through each path part
        for part in path_parts:
            path_array.append(part)
            
            query = (
                f"name = '{part}' and '{current_folder_id}' in parents "
                "and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            )
            
            results = service.files().list(
                q=query,
                spaces='drive',
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                fields="nextPageToken, files(id, name, mimeType)",
                pageSize=1
            ).execute()
            
            folders = results.get('files', [])
            if not folders:
                if not silent:
                    print(f'Folder not found: {part} in path {"/".join(path_array)}')
                return path_array, None, None
            
            current_folder_id = folders[0]['id']
        
        # Get contents of target folder
        contents_result = service.files().list(
            q=f"'{current_folder_id}' in parents and trashed=false",
            pageSize=1000,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            fields="nextPageToken, files(id, name, mimeType, parents, modifiedTime)",
        ).execute()
        
        contents = contents_result.get('files', [])
        
        # Display the full path and contents (only if not silent)
        if not silent:
            print(f'\nFull path traversal:')
            for i, folder in enumerate(path_array):
                indent = "  " * i
                if i == 0:
                    print(f'{indent}📁 {folder} (Root)')
                elif i == len(path_array) - 1:
                    print(f'{indent}└── 📁 {folder} (Target) - ID: {current_folder_id}')
                else:
                    print(f'{indent}└── 📁 {folder}')
            
            print(f'\nTarget folder contents ({len(contents)} items):')
            if not contents:
                print('  📂 Folder is empty')
            else:
                # Separate folders and files
                folders = [item for item in contents if item['mimeType'] == 'application/vnd.google-apps.folder']
                files = [item for item in contents if item['mimeType'] != 'application/vnd.google-apps.folder']
                
                # Display folders first
                for folder in folders:
                    print(f'  📁 {folder["name"]}')
                
                # Then display files
                for file in files:
                    file_type = '📊' if 'csv' in file.get('name', '').lower() else '📄'
                    print(f'  {file_type} {file["name"]}')
        
        return path_array, current_folder_id, contents
        
    except Exception as e:
        if not silent:
            print(f'Error getting folder path and contents: {str(e)}')
        return None, None, None

def upload_file(service, file_path, folder_id):
    file_metadata = {
        'name': os.path.basename(file_path),
        'parents': [folder_id]
    }
    media = MediaFileUpload(file_path)
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id',
        supportsAllDrives=True
        ).execute()
    print(f'File ID: {file.get("id")} uploaded to folder ID: {folder_id}')
    return

def list_drive_files(service, folder_id):
    results = service.files().list(
        q=f"'{folder_id}' in parents and trashed=false",
        pageSize=1000,
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
        fields="nextPageToken, files(id, name, mimeType, parents)",
    ).execute()

    items = results.get('files', [])
    for item in items:
        # parent = item.get('parents', ['root'])[0]
        print(f"File ID: {item['id']}, Name: {item['name']}, Type: {item['mimeType']}")
    return

def file_match(folder_path, month, year, debug=False):
    matched_files = []
    
    # Debug: Check if folder exists and what's in it
    if debug:
        print(f"DEBUG: Looking in folder: {folder_path}")
        print(f"DEBUG: Folder exists: {os.path.exists(folder_path)}")
        if os.path.exists(folder_path):
            all_files = os.listdir(folder_path)
            print(f"DEBUG: Found {len(all_files)} total files: {all_files}")
        print(f"DEBUG: Looking for pattern: *__{year}_{month}.csv")
    
    if not os.path.exists(folder_path):
        if debug:
            print(f"DEBUG: Folder {folder_path} does not exist!")
        return matched_files
    
    for file in os.listdir(folder_path):
        try:
            if debug:
                print(f"DEBUG: Checking file: {file}")
            
            # Skip files that don't match the expected pattern
            if "__" not in file:
                if debug:
                    print(f"DEBUG: Skipping {file} - no '__' found")
                continue
                
            if not file.endswith('.csv'):
                if debug:
                    print(f"DEBUG: Skipping {file} - not a .csv file")
                continue
            
            # Split filename and check pattern: ACCOUNT__YEAR_MONTH.csv
            parts = file.split("__")
            if len(parts) >= 2:
                date_part = parts[1][:-4]  # Remove .csv extension
                if debug:
                    print(f"DEBUG: File {file} has date part: '{date_part}', looking for: '{year}_{month}'")
                
                if date_part == f"{year}_{month}":
                    matched_files.append(file)
                    if debug:
                        print(f"DEBUG: MATCH! Added {file}")
                else:
                    if debug:
                        print(f"DEBUG: No match for {file}")
            else:
                if debug:
                    print(f"DEBUG: Skipping {file} - not enough parts after splitting by '__'")
        except (IndexError, ValueError) as e:
            if debug:
                print(f"DEBUG: Error processing {file}: {e}")
            continue
    
    if debug:
        print(f"DEBUG: Final matched files: {matched_files}")
    
    return matched_files

def file_match_upload(folder_path, destination_id, month, year):
    matched_files = []
    for file in os.listdir(folder_path):
        try:
            # Skip files that don't match the expected pattern
            if "__" not in file or not file.endswith('.csv'):
                continue
            
            # Split filename and check pattern: ACCOUNT__YEAR_MONTH.csv
            parts = file.split("__")
            if len(parts) >= 2:
                date_part = parts[1][:-4]  # Remove .csv extension
                if date_part == f"{year}_{month}":
                    matched_files.append(file)
        except (IndexError, ValueError):
            # Skip files that don't match the expected pattern
            continue
    return matched_files

if __name__ == '__main__':
    service = authenticate_drive()

    status = True
    while status == True:
        user_input = input("Enter a command: ")
        match user_input:
            case "get":
                folder_name_inp = input("Enter folder name: ")
                get_folder(service, folder_name_inp)
            case "nested":
                path = input("Enter nested folder path: ")
                root = get_folder(service, "P&L Reports")
                final = get_nested_folder_id(service, ast.literal_eval(path), root)
                print(f"FINAL: {final}")
            case "upload":
                test_path = 'downloads/200 OLD PALISADE RD__2025_1.csv'
                test_drive_path = ['2025 PnL', 'test']
                test_drive_root = get_folder(service, "P&L Reports")
                upload_file(service, test_path, get_nested_folder_id(service, test_drive_path, test_drive_root))
            case "list":
                folder_id = get_folder(service, input("Enter folder name: "))
                list_drive_files(service, folder_id)
            case "filter":
                root = get_folder(service, "P&L Reports")
                file_match("downloads", "04", 2025)
            case "batch_upload":
                test_drive_path = ["2025 PnL", "test"]
                test_drive_root = get_folder(service, "P&L Reports")
                grab_these = file_match("downloads", "01", 2025)
                destination = get_nested_folder_id(service, test_drive_path, test_drive_root)
                for file in grab_these:
                    file_path = f"downloads/{file}"
                    upload_file(service, file_path, destination)
            case "browse_target":
                root_name = input("Enter root folder name: ")
                target_path = input("Enter target path (e.g., '2025 PnL/January'): ")
                path_parts = [part.strip() for part in target_path.split('/') if part.strip()]
                path_array, folder_id, contents = get_folder_path_and_contents(service, root_name, path_parts)
            case "exit":
                status = False