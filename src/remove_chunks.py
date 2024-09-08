import os


def remove(folder_path):
    list_of_files = os.listdir(folder_path)
    for file_name in list_of_files:
        if 'chunks' in file_name:
            os.remove(os.path.join(folder_path, file_name))