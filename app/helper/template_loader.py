# !

import os

def create_template_files_dict(directory="../app/template_strings"):
    """
    Reads all .txt files in the specified directory and creates a dictionary
    with file names as keys and their paths as values.
    
    :param directory: The path to the directory containing the template files.
    :return: A dictionary with template names and file paths.
    """
    template_files = {}
    # List all files in the given directory
    for filename in os.listdir(directory):
        if filename.endswith('.txt'):
            # Remove the file extension for the key
            file_key = os.path.splitext(filename)[0]
            # Create a relative path from the directory to the file
            file_path = os.path.join(directory, filename)
            # Correct path separators if needed (for Windows compatibility)
            file_path = file_path.replace(os.sep, '/')
            # Add to dictionary
            template_files[file_key] = file_path
    return template_files
 
 

def get_template_by_type(layout_type):
    """Fetches and returns the content of a template file based on the layout type."""
    template_files=create_template_files_dict();
    if layout_type in template_files:
        file_path = template_files[layout_type]
        try:
            with open(file_path, 'r') as file:
                return file.read()
        except FileNotFoundError:
            print(f"Error: The file for {layout_type} does not exist.")
            return None
    else:
        print("Error: Layout type not recognized.")
        return None