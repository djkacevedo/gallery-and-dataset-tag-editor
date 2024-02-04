# gallery-and-dataset-tag-editor

This Image Gallery Application is a Python-based tool for organizing and viewing images with features like tag management, sorting, and filtering.

## Installation

To install and run the Image Gallery Application, follow these steps:

1. **Clone or download the repository**:
   - If you have `git` installed, you can clone the repository using:
     ```
     git clone [repository-url]
     ```
   - Alternatively, download the ZIP file and extract it.

2. **Install dependencies**:
   - Navigate to the project directory in your terminal or command prompt.
   - Install the required Python packages using:
     ```
     pip install -r requirements.txt
     ```

## Usage

To use the Image Gallery Application, follow these instructions:

1. **Starting the application**:
   - Run the script using Python:
     ```
     python app.py
     ```

2. **Loading images**:
   - Use the 'Open' option in the 'File' menu to load images from a folder.

3. **Viewing images**:
   - Click on any image thumbnail to view a larger preview.

## Features

- **Tag Management**:
  - Add, sort, and remove tags for images.
  - Sorting is done by danbooru tags.  
  - Context menu for quick tag operations.

- **Image Filtering**:
  - Filter images based on positive and negative tag filters.

- **Dark Mode**:
  - Toggle dark mode from the 'File' menu for a different visual experience.

- **Keyboard Navigation**:
  - Use arrow keys for navigating through images.

## Credits

I snatched the csv and yaml files used for coloring and sorting from [a1111-sd-webui-tagcomplete](https://github.com/DominikDoom/a1111-sd-webui-tagcomplete) and [sd-webui-prompt-all-in-one](https://github.com/Physton/sd-webui-prompt-all-in-one).

Warning! Those seem to be straight rips from the booru, so there are a lot of NSFW words in there.

Also. I used copilot and chatgpt for a lot of this. So credit to them. I'm still adding features, and it desperately needs to be refactored. I'm using this myself, so as I think of useful stuff, or get suggestions that I'll find useful, I'll add things.

Also! Main reason for this is that I like [stable-diffusion-webui-dataset-tag-editor](https://github.com/toshiaki1729/stable-diffusion-webui-dataset-tag-editor), but it's kinda buggy, and kinda slow. So I'm mostly pulling from there for ideas on what features to add.