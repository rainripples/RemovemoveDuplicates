import os
import hashlib
import shutil
from pathlib import Path
import logging
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import csv
from gooey import Gooey, GooeyParser

# Configure logging
log_file = "duplicate_log.txt"
logging.basicConfig(filename=log_file, level=logging.INFO, format="%(asctime)s - %(message)s")

# Dictionary to store duplicates info for reporting
duplicate_info = []

# Function to calculate MD5 hash of a file
def calculate_md5(file_path, chunk_size=1024):
    md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                md5.update(chunk)
    except:
        return 'fail'
    
    return md5.hexdigest()

# Function to find duplicates and move them
def find_and_move_duplicates(directory, duplicate_folder):
    file_hashes = {}
    duplicates_folder_path = Path(duplicate_folder)
    duplicates_folder_path.mkdir(exist_ok=True)  # Create duplicates folder if not exist
    
    for root, dirs, files in os.walk(directory):
        for file in files:
        
            file_path = Path(root) / file

            if should_ignore_dir(root):
                logging.info(f"Ignored as directory is on exclude list: {file_path} ")
                print(f"Ignored as directory is on exclude list: {file_path}")   
                continue

            if is_hidden(file):
                logging.info(f"Hidden file ignored: {file_path} ")
                print(f"Hidden file ignored: {file_path}")
                continue

            # exclude certain file extensions (create one filter function at some point)
            exclude_extensions=['ini','rdp','exe','marker','dll','lib','cmd','json','sys','tmp','index','marker']
            file=file.lower()
            if file.endswith(tuple(exclude_extensions)):
                logging.info(f"File ignored due to file extension: {file_path} ")
                print(f"File ignored due to file extension: {file_path}")
                continue
            
            # make sure we can read the file
            try: 
                fp=open(file_path,"rb")
            except:
                logging.info(f"File could not be opened (not gettiing into why): {file_path} ")
                print(f"Error opening file {file_path}")
                continue
    
   
            file_md5 = calculate_md5(file_path)
            if file_md5=="fail":
                logging.info(f"File failed to calc MD5 - :Path:{file_path} ")
                print(f"File failed to calc MD5 - Path:{file_path}")
                continue
            else:
                logging.info(f"File processed - MD5:{file_md5} Path:{file_path} ")
                print(f"File processed - MD5:{file_md5} Path:{file_path}")
        
            if file_md5 in file_hashes:
        
                # Found duplicate, move to duplicates folder
                original_path = file_hashes[file_md5]
                new_path = duplicates_folder_path / file

                # Collect duplicate data for reporting
                duplicate_info.append({
                    "original_path": str(original_path),
                    "duplicate_path": str(file_path),
                    "moved_to": str(new_path),
                    "file_extension": file_path.suffix,
                    "folder_name": file_path.parent.name,
                    "created_date": datetime.fromtimestamp(file_path.stat().st_ctime),
                    "modified_date": datetime.fromtimestamp(file_path.stat().st_mtime)
                })

                # Handle duplicate names in the duplicates folder
                counter = 1
                while new_path.exists():
                    new_path = duplicates_folder_path / f"{new_path.stem}_{counter}{new_path.suffix}"
                    counter += 1
                try:
                    shutil.move(str(file_path), str(new_path))
                except:

                    # Log the failed duplicate move
                    logging.info(f"Duplicate found: {file_path} (Original: {original_path}), failed to Moved to: {new_path}")
                    print(f"Duplicate found: {file_path}, but could not Moved to: {new_path}")
                else:
                    # Log the duplicate move
                    logging.info(f"Duplicate found: {file_path} (Original: {original_path}), Moved to: {new_path}")
                    print(f"Duplicate found: {file_path}, Moved to: {new_path}")
                
            else:
                # Add to the hash dictionary if it's not a duplicate
                file_hashes[file_md5] = file_path

# Function to generate reports
def generate_reports():
    if not duplicate_info:
        print("No duplicates found, no reports to generate.")
        return
    
    df = pd.DataFrame(duplicate_info)

    # Bar graph: Duplicates by file extension
    extension_counts = df['file_extension'].value_counts()
    extension_counts.plot(kind='bar', title='Number of Duplicates by File Extension', figsize=(10, 6))
    plt.ylabel('Number of Duplicates')
    plt.xlabel('File Extension')
    plt.tight_layout()
    plt.savefig("duplicates_by_extension.png")
    #plt.show()

    # Bar graph: Duplicates by folder name and file extension
    folder_extension_counts = df.groupby(['folder_name', 'file_extension']).size().unstack(fill_value=0).sum(axis=1)
    folder_extension_counts.plot(kind='bar', title='Number of Duplicates by Folder and Extension', figsize=(10, 6))
    plt.ylabel('Number of Duplicates')
    plt.xlabel('Folder Name')
    plt.tight_layout()
    plt.savefig("duplicates_by_folder_extension.png")
    #plt.show()

    # Line graph: Number of files by created date and modified date
    df['created_date'].dt.date.value_counts().sort_index().plot(kind='line', title='Files by Created Date', figsize=(10, 6))
    plt.ylabel('Number of Files')
    plt.xlabel('Created Date')
    plt.tight_layout()
    plt.savefig("files_by_created_date.png")
    #plt.show()

    df['modified_date'].dt.date.value_counts().sort_index().plot(kind='line', title='Files by Modified Date', figsize=(10, 6))
    plt.ylabel('Number of Files')
    plt.xlabel('Modified Date')
    plt.tight_layout()
    plt.savefig("files_by_modified_date.png")
    #plt.show()

@Gooey(program_name="Duplicate File Finder", default_size=(600, 400))
def main():
# # # Gooey UI setup

    parser = GooeyParser(description="Find and move duplicate files based on MD5 hash, and generate reports.")

    # Add input for directory
    parser.add_argument('directory', 
                    metavar='Directory', 
                    widget='DirChooser', 
                    help="Select the directory to search for duplicates")

    # Add input for duplicate folder (optional)
    parser.add_argument('duplicate_folder', 
                    metavar='Duplicate Folder', 
                    widget='DirChooser', 
                    help="Select the folder to move duplicates (will be created if it doesn't exist)", 
                    default="duplicates")

    args = parser.parse_args()

    # Run the duplicate finder
    find_and_move_duplicates(args.directory, args.duplicate_folder)

#for debug (comment out prior line and gooey ref.)
# dir=f"C:\\Users\\colin\\OneDrive\\Pictures"
# dups=f"C:\\Users\\colin\\duplicates"
# find_and_move_duplicates(dir,dups)
# Generate reports after processing duplicates
    generate_reports()
    
    # Report completion
    print(f"Process completed. Log saved to {log_file}.")
    print(f"Log file and reports graphs are available at: {Path(log_file).resolve()}")

def should_ignore_dir(directory):
    """Check if the current directory or any of its parents should be ignored."""
    ignore_folders=['Program files','Program files (x86)']
    for ignore_folder in ignore_folders:
        # Compare full path to see if it starts with the ignored folder's path
        #check=os.path.abspath(ignore_folder)
        directory=directory.lower()
        ignore_folder=ignore_folder.lower()

        findval=directory.find(ignore_folder)
        if findval !=-1:
            return True
    return False

def is_hidden(filepath):
    """Check if the file or directory is hidden."""
    exclude_startswith=['.','~','_']
    return any(part.startswith(tuple(exclude_startswith)) for part in filepath.split(os.sep))

if __name__ == "__main__":
    main()
