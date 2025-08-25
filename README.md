# bank_drive_pipe

A tool to grab CSVs of periodic bank activities and upload them to Google Drive.
Automation of Profit/Loss statements and custom dashboard in Google Sheets.

Need to setup Google Cloud services API for program to utilize.

# Files

## scraper_profiles/chaseBus_monthly.py
Main automation script for Chase Business accounts. As each bank is most likely going to have different website elements, would need to make a custom script for each one instead of a universal one. All scraper profiles are stored in the `scraper_profiles/` directory.

## google_conn.py
The code interacting with the Google Drive API, performing authentication, data retrieval, and file uploading.

### google_drive_gui.py
GUI wrapper for the Google API code.

## gui.py
The graphical interface for the program using custom tkinter.

### custom_dialogs.py
Creates a custom pop-up window for the gui as the normal pop up window looks like its from 1997.

### console_widget.py
Creates a console/terminal view of the code for some of the operations so the user knows whats going on. Primarily used to show the file navigation outputs.