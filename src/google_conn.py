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


def authenticate_drive():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'tools/auto_files_cred.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    service = build('drive', 'v3', credentials=creds)
    return service

def get_folder(service, folder_name):
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
        print(f'No folder found with name: {folder_name}')
        return None
    else:
        print(f'Found folder: {items[0]["name"]} with ID: {items[0]["id"]}')
        return items[0]["id"] 

def get_subfolder_id(service, folder_name, parent_id):
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
        print(f'No subfolder found with name: {folder_name} in parent ID: {parent_id}')
        return None
    elif len(folders) > 1:
        print(f'Multiple subfolders found with name: {folder_name} in parent ID: {parent_id}')
    
    folder = folders[0]
    print(f'Found subfolder: {folder["name"]} with ID: {folder["id"]} in parent ID: {parent_id}')
    return folder['id']

def get_nested_folder_id(service, path_parts, root_folder_id):
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
            print(f'No folder found with name: {name} in parent ID: {current_folder_id}')
            return None
        current_folder_id = folders[0]['id']
        print(f'Found folder: {folders[0]["name"]} with ID: {current_folder_id} in parent ID: {current_folder_id}')
    return current_folder_id

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

def file_match(folder_path, month, year):
    matched_files = []
    for file in os.listdir(folder_path):
        if str(file.split("__")[1][:-4]) == f"{year}_{month}":
            matched_files.append(file)
    return matched_files

def file_match_upload(folder_path, destination_id, month, year):
    matched_files = []
    for file in os.listdir(folder_path):
        if str(file.split("__")[1][:-4]) == f"{year}_{month}":
            matched_files.append(file)
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
            case "exit":
                status = False