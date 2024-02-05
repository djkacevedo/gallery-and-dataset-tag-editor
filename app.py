import os
import tkinter as tk
from tkinter import filedialog, Canvas, Frame
from tkinter import ttk  # Import ttk for the progress bar
from tkinter import Menu
from PIL import Image, ImageTk, ImageOps
import threading
import json
import yaml
import csv
import subprocess
import tkinter.font as font

class ImageGalleryApp:
    color_mapping = {
        "danbooru": {
            "-1": ["red", "maroon"],
            "0": ["lightblue", "dodgerblue"],
            "1": ["indianred", "firebrick"],
            "3": ["violet", "darkorchid"],
            "4": ["lightgreen", "darkgreen"],
            "5": ["orange", "darkorange"]
        },
        "e621": {
            "-1": ["red", "maroon"],
            "0": ["lightblue", "dodgerblue"],
            "1": ["gold", "goldenrod"],
            "3": ["violet", "darkorchid"],
            "4": ["lightgreen", "darkgreen"],
            "5": ["tomato", "darksalmon"],
            "6": ["red", "maroon"],
            "7": ["whitesmoke", "black"],
            "8": ["seagreen", "darkseagreen"]
        }
    }
    def __init__(self, root):
        self.root = root
        self.root.title("Image Gallery")

        self.create_menu_bar()
        self.initialize_variables()
        self.setup_main_frames()
        self.setup_grid_canvas()
        self.setup_right_frame()
        self.setup_key_bindings()
        self.setup_filter_and_tag_options()
        self.initialize_color_schemes()

        settings = self.load_settings()
        self.apply_initial_settings(settings)

    def create_menu_bar(self):
        self.menu_bar = tk.Menu(self.root)
        self.root.config(menu=self.menu_bar)
        self.create_file_menu()
        self.create_tools_menu()

    def create_file_menu(self):
        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.file_menu.add_command(label="Open", command=self.load_folder)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Quit", command=self.root.quit)
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)

    def create_tools_menu(self):
        self.tools_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.add_tools_menu_commands()
        self.menu_bar.add_cascade(label="Tools", menu=self.tools_menu)
    
    def add_tools_menu_commands(self):
        self.tools_menu.add_command(label="Remove Duplicate tags in Visible Images", command=self.remove_duplicates_visible)
        self.tools_menu.add_command(label="Remove Duplicate tags All Images", command=self.remove_duplicates_all)
        self.tools_menu.add_command(label="Remove Duplicate tags Selected Image", command=self.remove_duplicate_selected)
        self.tools_menu.add_command(label="Sort Tags for Selected Image", command=self.sort_tags_selected)
        self.tools_menu.add_command(label="Sort Tags for Visible Images", command=self.sort_tags_visible)
        self.tools_menu.add_command(label="Sort Tags for All Images", command=self.sort_tags_all)
    
    def initialize_variables(self):
        self.image_labels = []
        self.tag_freq = {}
        self.tag_colors = {}
        self.selected_label = None
        self.selection_lock = threading.Lock()
        self.selection_debounce = None
        self.tag_map = {}
        self.color_schemes = {}  # Initialize color_schemes
    
    def setup_main_frames(self):
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill="both", expand=True)
    
    def setup_grid_canvas(self):
        self.grid_canvas = Canvas(self.main_frame, borderwidth=0, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.main_frame, orient="vertical", command=self.grid_canvas.yview)
        self.scrollable_frame = Frame(self.grid_canvas, borderwidth=0)
        self.grid_canvas.config(width=300)
        self.grid_canvas.pack_propagate(False)
        self.scrollable_frame.config(width=300)
        self.scrollable_frame.pack_propagate(False)
        self.scrollable_frame.bind("<Configure>", lambda e: self.grid_canvas.configure(scrollregion=self.grid_canvas.bbox("all")))
        self.grid_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.grid_canvas.configure(yscrollcommand=self.scrollbar.set)
        self.grid_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.grid_canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="left", fill="y")
    
    def setup_right_frame(self):
        self.right_frame = tk.Frame(self.main_frame)
        self.right_frame.pack(side="right", fill="both", expand=True)
        self.setup_preview_frame()
        self.setup_tags_frame()
    
    def setup_preview_frame(self):
        self.preview_frame = tk.Frame(self.right_frame, width=512, height=512)
        self.preview_frame.pack_propagate(False)
        self.preview_frame.pack(side="top", fill="both", expand=False)
        self.preview_image_label = tk.Label(self.preview_frame)
        self.preview_image_label.pack(fill="both", expand=True)
    
    def setup_tags_frame(self):
        self.tags_frame = tk.Frame(self.right_frame)
        self.tags_frame.pack(side="bottom", fill="both", expand=True)
        self.tags_text = tk.Text(self.tags_frame, wrap='word', height=3, borderwidth=0, cursor="", bg='SystemButtonFace')
        self.tags_text.pack(side="left", fill="both", expand=True)
        self.tags_text.bind("<1>", lambda e: "break")
        self.tags_text.bind("<B1-Motion>", lambda e: "break")
    
    def setup_key_bindings(self):
        self.root.bind("<Left>", lambda e: self.move_focus("left"))
        self.root.bind("<Right>", lambda e: self.move_focus("right"))
        self.root.bind("<Up>", lambda e: self.move_focus("up"))
        self.root.bind("<Down>", lambda e: self.move_focus("down"))
        self.root.bind("<Control-MouseWheel>", self.ctrl_mouse_wheel)
        self.root.bind("<Tab>", self.handle_tab_press)
        self.root.bind("<Return>", self.handle_return_press)
        self.root.bind("<Delete>", self.handle_delete_press)
        self.progress_bar = ttk.Progressbar(self.grid_canvas, orient="horizontal", mode="determinate")
        self.progress_bar.pack(side="top", fill="x")
        self.progress_bar.pack_forget()

    def handle_delete_press(self, event):
        focused_widget = self.root.focus_get()
        # Check if the focused widget is not a text box
        if not isinstance(focused_widget, (tk.Entry, tk.Text)):
            if self.selected_label:
                self.delete_image(self.selected_label)

    def handle_return_press(self, event):
        focused_widget = self.root.focus_get()

        # Check which widget is focused and perform the relevant action
        if focused_widget == self.pos_filter_entry or focused_widget == self.neg_filter_entry:
            self.apply_filters()
        elif focused_widget == self.tag_entry:
            self.add_tag()
        elif focused_widget == self.remove_tag_entry:
            self.remove_tag()

    def setup_filter_and_tag_options(self):
        self.pos_filter_option = tk.IntVar(value=1)
        self.neg_filter_option = tk.IntVar(value=1)
        self.hide_non_filtered_tags = tk.BooleanVar(value=False)
        self.dark_mode_enabled = tk.BooleanVar()
        self.add_filter_boxes()
        self.add_tag_entry()
        self.file_menu.add_checkbutton(label="Dark Mode", onvalue=True, offvalue=False, variable=self.dark_mode_enabled, command=self.toggle_dark_mode)
    
    def apply_initial_settings(self, settings):
        self.dark_mode_enabled.set(settings.get('dark_mode_enabled', False))
        last_folder = settings.get('last_opened_folder')
        last_color_scheme = settings.get('last_color_scheme', 'None')
        if self.dark_mode_enabled.get():
            self.apply_dark_mode()
        if last_folder and os.path.isdir(last_folder):
            self.display_images(last_folder)
        if last_color_scheme in self.color_schemes:
            self.change_color_scheme(last_color_scheme)

    def initialize_color_schemes(self):
        self.color_schemes = {"None": None}  # Default option
        self.load_color_schemes()  # Load available color schemes

    def clear_text_focus(self):
        self.root.focus_set()

    def load_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.display_images(folder_path)
            self.tag_map = {}  # Reset the tag map for the new folder
            # Update last opened folder in settings
            settings = self.load_settings()
            settings['last_opened_folder'] = folder_path
            self.save_settings(settings)

    def show_progress_bar(self):
        self.progress_bar.pack(side="top", fill="x")
    
    def hide_progress_bar(self):
        self.progress_bar.pack_forget()

    def replace_underscores(self, image_path, tag):
        if self.selected_label in self.tag_map:
            tags = self.tag_map[self.selected_label]
            updated_tags = [t.replace('_', ' ') if t == tag else t for t in tags]

            # Update the tag map
            self.tag_map[self.selected_label] = updated_tags

            # Update the tags file for the image
            caption_path = image_path.rsplit('.', 1)[0] + '.txt'
            if os.path.exists(caption_path):
                with open(caption_path, 'w') as file:
                    file.write(', '.join(updated_tags))

            # Update the tags display
            self.display_tags(image_path, self.count_tag_frequencies())

    def create_context_menu(self, label):
        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="Clear Filters", command=lambda: self.clear_filters())
        context_menu.add_command(label="Delete Image", command=lambda: self.delete_image(label))
        context_menu.add_command(label="Sort Tags", command=lambda: self.sort_tags_selected())
        context_menu.add_command(label="Open Image", command=lambda: self.open_in_default_app(label.image_path))
        context_menu.add_command(label="Open Caption File", command=lambda: self.open_caption_file(label.image_path))
        context_menu.add_command(label="Open Containing Folder", command=lambda: self.open_folder_in_default_app(label.image_path))

        return context_menu

    def delete_image(self, label_to_delete):
        # Get current index of the label to delete
        if not self.image_labels:
            return

        visible_labels = [label for label in self.image_labels if label.winfo_ismapped()]

        if not visible_labels:
            return

        current_index = visible_labels.index(label_to_delete) if label_to_delete in visible_labels else -1

        # Delete the image and caption files
        image_path = label_to_delete.image_path
        caption_path = image_path.rsplit('.', 1)[0] + '.txt'
        if os.path.exists(image_path):
            os.remove(image_path)
        if os.path.exists(caption_path):
            os.remove(caption_path)

        # Remove the label and rearrange the remaining labels
        label_to_delete.grid_forget()
        label_to_delete.destroy()
        self.image_labels.remove(label_to_delete)
        self.rearrange_labels()

        # Select the next image
        # self.select_next_image_after_deletion(current_index)
        next_index = current_index + 1 if current_index < len(visible_labels) - 1 else current_index - 1
        self.select_image(None, visible_labels[next_index])
        self.apply_filters()

    def rearrange_labels(self):
        # Rearrange the remaining labels to fill in the gap
        row, col = 0, 0
        for label in self.image_labels:
            label.grid(row=row, column=col, padx=2, pady=2)
            col += 1
            if col >= 3:  # Assuming 3 columns, adjust as needed
                col = 0
                row += 1

    def open_folder_in_default_app(self, path):
        if os.path.exists(path):
            os.startfile(os.path.dirname(path))

    def open_in_default_app(self, path):
        if os.path.exists(path):
            os.startfile(path)

    def open_caption_file(self, image_path):
        caption_path = image_path.rsplit('.', 1)[0] + '.txt'
        if os.path.exists(caption_path):
            os.startfile(caption_path)

    def display_images_threaded(self, folder_path):
        self.scrollable_frame.after(0, self.show_progress_bar)
        self.image_labels.clear()
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        images = [f for f in os.listdir(folder_path) if f.endswith(('.png', '.jpg', '.jpeg'))]
        total_images = len(images)
        
        def update_progress(value):
            self.progress_bar["value"] = value
            self.progress_bar["maximum"] = total_images
            self.progress_bar.update_idletasks()

        def add_image_label(i, img, image_path, row, col):
            label = tk.Label(self.scrollable_frame, image=img, borderwidth=2, relief="flat", highlightthickness=2, highlightbackground="black")
            label.image = img
            label.image_path = image_path
            label.grid(row=row, column=col, padx=2, pady=2)
            label.bind("<Button-1>", lambda e, path=image_path: self.select_image(e, path))

            # Bind the context menu
            context_menu = self.create_context_menu(label)
            label.bind("<Button-3>", lambda e: context_menu.tk_popup(e.x_root, e.y_root))

            self.image_labels.append(label)

            # Read tags and store in the tag map
            tags = self.read_tags(image_path)
            self.tag_map[label] = tags

        row, col = 0, 0
        for i, image_file in enumerate(images):
            image_path = os.path.join(folder_path, image_file)
            img = Image.open(image_path)
            img.thumbnail((120, 120))
            img = ImageTk.PhotoImage(img)

            self.scrollable_frame.after(0, lambda i=i, img=img, image_path=image_path, row=row, col=col: add_image_label(i, img, image_path, row, col))
            self.scrollable_frame.after(0, lambda idx=i: update_progress(idx + 1))

            col += 1
            if col >= 3:
                col = 0
                row += 1

        self.scrollable_frame.after(0, self.hide_progress_bar)
    
    def load_image(self, folder_path, image_file, row, col, current_index, total_images):
        image_path = os.path.join(folder_path, image_file)
        img = Image.open(image_path)
        img.thumbnail((100, 100))  # Set thumbnail size
        img = ImageTk.PhotoImage(img)
    
        def add_image_label():
            label = tk.Label(self.scrollable_frame, image=img, borderwidth=2, relief="flat")
            label.image = img  # Keep a reference
            label.image_path = image_path  # Store the image path
            label.grid(row=row, column=col, padx=5, pady=5, sticky='nsew')
    
            label.bind("<Button-1>", lambda e, path=image_path: self.select_image(e, path))
            self.image_labels.append(label)
    
        self.scrollable_frame.after(0, add_image_label)

    def display_images(self, folder_path):
        # Start the threaded image loading
        threading.Thread(target=self.display_images_threaded, args=(folder_path,), daemon=True).start()
    
        # Calculate the number of rows based on the number of images and columns
        images = [f for f in os.listdir(folder_path) if f.endswith(('.png', '.jpg', '.jpeg'))]
        num_rows = (len(images) + 2) // 3  # Assuming 3 columns, adjust '+ 2' for rounding up
    
        # Configure grid columns and rows to not resize
        for i in range(3):  # Assuming 3 columns
            self.scrollable_frame.grid_columnconfigure(i, weight=0, uniform="col")
        for i in range(num_rows):
            self.scrollable_frame.grid_rowconfigure(i, weight=0, uniform="row")

    def _on_mousewheel(self, event):
        if not (event.state & 0x0004):  # Check if Control key is not pressed
            self.grid_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def handle_tab_press(self, event):
        # Prevent default Tab behavior
        event.widget.tk_focusNext().focus()
        return "break"  # This stops the event from propagating further

        # You can also add logic here to perform actions similar to image selection,
        # depending on the requirements of your application

    def ctrl_mouse_wheel(self, event):
        # This method will be called regardless of which widget is focused
        if event.delta > 0:
            # Mouse wheel scrolled up, move to the previous image
            self.move_focus("left")
        else:
            # Mouse wheel scrolled down, move to the next image
            self.move_focus("right")

    def move_focus(self, direction):
        # Check if the currently focused widget is a text box
        if isinstance(self.root.focus_get(), tk.Entry) or isinstance(self.root.focus_get(), tk.Text):
            return  # Do nothing if a text box is focused

        if not self.image_labels:
            return

        visible_labels = [label for label in self.image_labels if label.winfo_ismapped()]

        if not visible_labels:
            return

        current_index = visible_labels.index(self.selected_label) if self.selected_label in visible_labels else -1
        row_length = 3  # Adjust based on your column configuration

        new_index = current_index
        while True:
            if direction == "left" and new_index > 0:
                new_index -= 1
            elif direction == "right" and new_index < len(visible_labels) - 1:
                new_index += 1
            elif direction == "up" and new_index >= row_length:
                new_index -= row_length
            elif direction == "down" and new_index + row_length < len(visible_labels):
                new_index += row_length
            else:
                break  # Stop if no more images in the direction or at the edges

            # Check if the new index points to a visible image
            if visible_labels[new_index].winfo_ismapped():
                break

        if new_index != current_index:
            self.select_image(None, visible_labels[new_index])

            # After updating the selection:
            self.scroll_to_label(self.selected_label)

    def scroll_to_label(self, label):
        self.scrollable_frame.update_idletasks()  # Update layout
        if not label.winfo_ismapped():
            return  # Skip if the label is not visible
        self.scrollable_frame.update_idletasks()  # Update layout
        label_x, label_y = label.winfo_x(), label.winfo_y()  # Get label position within frame
        label_width, label_height = label.winfo_width(), label.winfo_height()  # Get label size
    
        # Get the visible area of the canvas
        canvas_x1 = self.grid_canvas.canvasx(0)
        canvas_y1 = self.grid_canvas.canvasy(0)
        canvas_x2 = canvas_x1 + self.grid_canvas.winfo_width()
        canvas_y2 = canvas_y1 + self.grid_canvas.winfo_height()
    
        # Determine if scrolling is needed
        scroll_x, scroll_y = None, None
        if label_x < canvas_x1:
            scroll_x = label_x
        elif label_x + label_width > canvas_x2:
            scroll_x = label_x + label_width - self.grid_canvas.winfo_width()
    
        if label_y < canvas_y1:
            scroll_y = label_y
        elif label_y + label_height > canvas_y2:
            scroll_y = label_y + label_height - self.grid_canvas.winfo_height()
    
        # Perform the scrolling if needed
        if scroll_x is not None:
            self.grid_canvas.xview_moveto(scroll_x / self.scrollable_frame.winfo_width())
        if scroll_y is not None:
            self.grid_canvas.yview_moveto(scroll_y / self.scrollable_frame.winfo_height())


    def select_image(self, event, image_or_path):
        self.clear_text_focus()

        # Clear the highlight from the previously selected image
        if self.selected_label and self.selected_label in self.image_labels:
            self.selected_label.config(highlightthickness=2, highlightbackground="black")
        
        # Determine the new selected label and image path
        if event:
            new_selected_label = event.widget
            image_path = event.widget.image_path
        elif isinstance(image_or_path, tk.Label):
            new_selected_label = image_or_path
            image_path = image_or_path.image_path
        else:
            return
        
        # Check if the new selected label is valid and exists in the image_labels list
        if new_selected_label in self.image_labels:
            self.selected_label = new_selected_label
            # Highlight the newly selected label
            self.selected_label.config(highlightthickness=2, highlightbackground="yellow")
    
            # Resize and display the selected image
            large_img = Image.open(image_path)
            large_img.thumbnail((512, 512), Image.Resampling.LANCZOS)
            large_img = ImageTk.PhotoImage(large_img)
            self.preview_image_label.config(image=large_img)
            self.preview_image_label.image = large_img
        
            # Bind the context menu to the preview image
            context_menu = self.create_context_menu(self.selected_label)
            self.preview_image_label.bind("<Button-3>", lambda e: context_menu.tk_popup(e.x_root, e.y_root))

            # Update the tags display
            self.display_tags(image_path, self.count_tag_frequencies())
        else:
            # The selected label is no longer valid, likely due to new folder loading
            self.selected_label = None

    def process_selection(self, event, image_or_path):
        with self.selection_lock:
            # Clear the border from the previously selected image
            if self.selected_label is not None:
                self.selected_label.config(borderwidth=0, relief="flat")
    
            # Determine the new selected label and image path
            if event:
                self.selected_label = event.widget
                image_path = event.widget.image_path
            elif isinstance(image_or_path, tk.Label):
                self.selected_label = image_or_path
                image_path = image_or_path.image_path
            else:
                return
    
            # Highlight the newly selected label
            if self.selected_label:
                self.selected_label.config(borderwidth=5, relief="solid", highlightbackground="yellow")
    
            # Resize and display the selected image
            large_img = Image.open(image_path)
            large_img.thumbnail((512, 512), Image.Resampling.LANCZOS)
            large_img = ImageTk.PhotoImage(large_img)
            self.preview_image_label.config(image=large_img)
            self.preview_image_label.image = large_img
    
            # Update the tags display
            self.display_tags(image_path, self.count_tag_frequencies())

    def clear_tags_frame(self):
        self.tags_text.config(state='normal')  # Enable editing to clear
        self.tags_text.delete('1.0', 'end')  # Delete all contents

    def remove_tag_from_tags_frame(self, image_path, tag_to_remove):
        if self.selected_label in self.tag_map:
            tags = self.tag_map[self.selected_label]
            tags = [tag for tag in tags if tag != tag_to_remove]
            self.tag_map[self.selected_label] = tags
            
            caption_path = image_path.rsplit('.', 1)[0] + '.txt'
            if os.path.exists(caption_path):
                with open(caption_path, 'w') as file:
                    file.write(', '.join(tags))
            self.display_tags(image_path, self.count_tag_frequencies())

    def read_tags(self, image_path):
        caption_path = image_path.rsplit('.', 1)[0] + '.txt'
        if os.path.exists(caption_path):
            with open(caption_path, 'r') as file:
                return [tag.strip() for tag in file.read().split(',')]
        return []

    def display_tags(self, image_path, tag_freq):
        pos_filter_tags = set(self.pos_filter_entry.get().split(','))
        
        tags = self.tag_map.get(self.selected_label, [])
        self.clear_tags_frame()

        tag_labels = []  # Store labels for delayed binding
        for tag in tags:
            if self.hide_non_filtered_tags.get():
                pos_filters = [tag.strip() for tag in self.pos_filter_entry.get().split(',') if tag.strip()]
                neg_filters = [tag.strip() for tag in self.neg_filter_entry.get().split(',') if tag.strip()]
                if (pos_filters and tag not in pos_filters) or (neg_filters and tag in neg_filters):
                    continue

            normalized_tag = tag.replace('_', ' ')
            freq = tag_freq.get(normalized_tag, 0)
            tag_color = self.tag_colors.get(normalized_tag, "black")
            btn_fg = "white" if self.dark_mode_enabled.get() and tag_color == "black" else tag_color
            btn_bg = "gray25" if self.dark_mode_enabled.get() else "SystemButtonFace"

            # Define a bold font
            bold_font = font.Font(weight="bold", size=12)
            regular_font = font.Font(size=10)
            tag_font = bold_font if tag in pos_filter_tags else regular_font

            # Create a frame and label for each tag
            tag_frame = tk.Frame(self.tags_text, bg=btn_bg)
            tag_label = tk.Label(tag_frame, text=f"{tag} ({freq})", fg=btn_fg, bg=btn_bg, font=tag_font)
            tag_label.pack(side="left", padx=2)
            tag_frame.pack(side="left")

            tag_labels.append((tag_label, tag))

            self.tags_text.window_create("end", window=tag_frame)
            self.tags_text.insert("end", " ")

        self.tags_text.config(state='disabled')

        # Schedule delayed binding
        self.root.after(250, lambda: self.delayed_tag_binding(image_path, tag_labels))

    def sort_tags_by_danbooru_group(self, tags):
        tag_groups = {
            "indianred": [],
            "violet": [],
            "lightgreen": [],
            "lightblue": [],
            "score": [],
            "source": [],
            "by": [],
            "other": []
        }

        for tag in tags:
            color = self.tag_colors.get(tag, "other")
            if tag.startswith("score_"):
                tag_groups["score"].append(tag)
            elif tag.startswith("source_"):
                tag_groups["source"].append(tag)
            elif tag.startswith("by ") and tag not in self.tag_colors:
                tag_groups["by"].append(tag)
            else:
                if color not in tag_groups:
                    color = "other"
                tag_groups[color].append(tag)

        sorted_tags = []
        sorted_tags.extend(sorted(tag_groups["score"], reverse=True))  # Sort "score_" tags in reverse order

        for group in ["source", "by", "indianred", "violet", "lightgreen", "lightblue", "other"]:
            sorted_tags.extend(sorted(tag_groups[group]))

        return sorted_tags

    def sort_tags_selected(self):
        if self.selected_label:
            self.sort_tags(self.selected_label)

    def sort_tags_visible(self):
        for label in self.image_labels:
            if label.winfo_ismapped():
                self.sort_tags(label)

    def sort_tags_all(self):
        for label in self.image_labels:
            self.sort_tags(label)

    def sort_tags(self, label):
        if label in self.tag_map:
            tags = self.tag_map[label]
            sorted_tags = self.sort_tags_by_danbooru_group(tags)

            # Update the tag map
            self.tag_map[label] = sorted_tags

            # Update the tags file for the image
            image_path = label.image_path
            caption_path = image_path.rsplit('.', 1)[0] + '.txt'
            if os.path.exists(caption_path):
                with open(caption_path, 'w') as file:
                    file.write(', '.join(sorted_tags))

            # Update the tags display if the selected image's tags were changed
            if label == self.selected_label:
                self.display_tags(image_path, self.count_tag_frequencies())

    def delayed_tag_binding(self, image_path, tags):
        if self.selected_label and self.selected_label.image_path == image_path:
            for tag_label, tag in tags:
                if tag_label.winfo_ismapped():  # Check if tag label still exists
                    tag_label.bind("<Button-3>", lambda e, t=tag: self.tag_right_click_menu(e, t))
                    tag_label.bind("<Button-1>", lambda e, t=tag: self.add_tag_to_filter_and_apply(t))
                    hover_color = "blue"  # Color to show on mouse hover

                    # Add mouse-over and mouse-leave bindings
                    tag_label.bind("<Enter>", lambda e, lbl=tag_label, t=tag: lbl.config(fg=hover_color))
                    tag_label.bind("<Leave>", lambda e, lbl=tag_label, t=tag: lbl.config(fg=self.get_tag_original_color(t)))

    def get_tag_original_color(self, tag):
        # Determine the original color of the tag based on dark mode setting
        original_color = self.tag_colors.get(tag, "black")
        if self.dark_mode_enabled.get() and original_color == "black":
            return "white"  # White color in dark mode for better visibility
        return original_color

    def add_tag_to_filter_and_apply(self, tag):
        current_filter = self.pos_filter_entry.get()
        if current_filter:
            new_filter = f"{current_filter}, {tag}"
        else:
            new_filter = tag
        self.pos_filter_entry.delete(0, tk.END)
        self.pos_filter_entry.insert(0, new_filter)
        self.pos_filter_entry.xview_moveto(1)  # Auto-scroll to the right
        self.apply_filters()

    def tag_right_click_menu(self, event, tag):
        # Create a context menu for tag options
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Remove from Positive Filter", command=lambda: self.remove_tag_from_filter_and_apply(tag, self.pos_filter_entry))
        menu.add_command(label="Remove from Negative Filter", command=lambda: self.remove_tag_from_filter_and_apply(tag, self.neg_filter_entry))
        menu.add_separator()
        menu.add_command(label="Add to Positive Filter", command=lambda: self.add_to_filter_and_apply(tag, self.pos_filter_entry))
        menu.add_command(label="Add to Negative Filter", command=lambda: self.add_to_filter_and_apply(tag, self.neg_filter_entry))
        menu.add_separator()
        menu.add_command(label="Remove Tag From Image", command=lambda: self.remove_tag_from_tags_frame(self.selected_label.image_path, tag))
        menu.add_command(label="Replace Underscores with Spaces", command=lambda: self.replace_underscores(self.selected_label.image_path, tag))
        menu.add_separator()
        menu.add_command(label="Add to Add Tag Box", command=lambda: self.add_to_add_tag_entry(tag))
        menu.add_command(label="Add to Remove Tag Box", command=lambda: self.add_to_remove_tag_entry(tag))
        menu.add_separator()
        menu.add_command(label="Copy to Clipboard", command=lambda: self.copy_to_clipboard(tag))


        # Display the menu at the cursor's position
        menu.tk_popup(event.x_root, event.y_root)

    def remove_tag_from_filter_and_apply(self, tag, filter_entry):
        # Get the current filter content
        current_filter = filter_entry.get()
        # Remove the tag from the filter
        filter_tags = [t.strip() for t in current_filter.split(',') if t.strip()]
        if tag in filter_tags:
            filter_tags.remove(tag)
            # Update the filter entry
            new_filter = ', '.join(filter_tags)
            filter_entry.delete(0, tk.END)
            filter_entry.insert(0, new_filter)
        self.apply_filters()
        filter_entry.xview_moveto(1)  # Auto-scroll to the right

    def add_to_add_tag_entry(self, tag):
        current_text = self.tag_entry.get()
        if current_text:
            new_text = f"{current_text}, {tag}"
        else:
            new_text = tag
        self.tag_entry.delete(0, tk.END)
        self.tag_entry.insert(0, new_text)

    def add_to_remove_tag_entry(self, tag):
        current_text = self.remove_tag_entry.get()
        if current_text:
            new_text = f"{current_text}, {tag}"
        else:
            new_text = tag
        self.remove_tag_entry.delete(0, tk.END)
        self.remove_tag_entry.insert(0, new_text)

    def add_to_filter_and_apply(self, tag, filter_entry):
        current_filter = filter_entry.get()
        if current_filter:
            new_filter = f"{current_filter}, {tag}"
        else:
            new_filter = tag
        filter_entry.delete(0, tk.END)
        filter_entry.insert(0, new_filter)
        self.apply_filters()

    def open_tag_menu(self, tag):
        # This function will be triggered when clicking on a tag
        menu = Menu(self.root, tearoff=0)
        menu.add_command(label="Option 1")  # Placeholder for real options
        menu.add_command(label="Option 2")
        # More options can be added here
        menu.post(self.root.winfo_pointerx(), self.root.winfo_pointery())  # Display the menu

        
    def count_tag_frequencies(self):
        tag_freq = {}
        for tags in self.tag_map.values():
            for tag in tags:
                tag_freq[tag] = tag_freq.get(tag, 0) + 1
        return tag_freq

    def add_filter_boxes(self):
        # Create a frame for filter boxes
        self.filter_frame = tk.Frame(self.right_frame)
        self.filter_frame.pack(side="bottom", fill="x", padx=5, pady=5)

        # Positive filter
        self.pos_filter_label = tk.Label(self.filter_frame, text="Positive Filter:")
        self.pos_filter_label.pack(side="left")
        self.pos_filter_entry = tk.Entry(self.filter_frame)
        self.pos_filter_entry.pack(side="left", fill="x", expand=True)

        # Positive filter options (AND/OR) with command binding
        pos_and_radio = tk.Radiobutton(self.filter_frame, text="AND", variable=self.pos_filter_option, value=0, command=self.apply_filters)
        pos_and_radio.pack(side="left")
        pos_or_radio = tk.Radiobutton(self.filter_frame, text="OR", variable=self.pos_filter_option, value=1, command=self.apply_filters)
        pos_or_radio.pack(side="left")

        # Negative filter
        self.neg_filter_label = tk.Label(self.filter_frame, text="Negative Filter:")
        self.neg_filter_label.pack(side="left")
        self.neg_filter_entry = tk.Entry(self.filter_frame)
        self.neg_filter_entry.pack(side="left", fill="x", expand=True)

        # Negative filter options (AND/OR) with command binding
        neg_and_radio = tk.Radiobutton(self.filter_frame, text="AND", variable=self.neg_filter_option, value=0, command=self.apply_filters)
        neg_and_radio.pack(side="left")
        neg_or_radio = tk.Radiobutton(self.filter_frame, text="OR", variable=self.neg_filter_option, value=1, command=self.apply_filters)
        neg_or_radio.pack(side="left")

        # Add mouse-over and mouse-leave bindings for the filter labels
        hover_color = "blue"  # Color to show on mouse hover

        self.pos_filter_label.bind("<Enter>", lambda e: self.pos_filter_label.config(fg=hover_color))
        self.pos_filter_label.bind("<Leave>", lambda e: self.pos_filter_label.config(fg=self.get_filter_label_color()))

        self.neg_filter_label.bind("<Enter>", lambda e: self.neg_filter_label.config(fg=hover_color))
        self.neg_filter_label.bind("<Leave>", lambda e: self.neg_filter_label.config(fg=self.get_filter_label_color()))

        # Filter button
        self.filter_button = tk.Button(self.filter_frame, text="Apply Filter", command=self.apply_filters)
        self.filter_button.pack(side="left", padx=5)

        # Clear filter button
        self.clear_filter_button = tk.Button(self.filter_frame, text="Clear Filter", command=self.clear_filters)
        self.clear_filter_button.pack(side="left", padx=5)

        # Checkbox for hiding non-filtered tags
        hide_tags_checkbox = tk.Checkbutton(self.filter_frame, text="Hide non-filtered tags", 
                                            variable=self.hide_non_filtered_tags, 
                                            command=self.update_tag_visibility)
        hide_tags_checkbox.pack(side="left")

        # Add Remove Tag Frame
        self.remove_tag_frame = tk.Frame(self.right_frame)
        self.remove_tag_frame.pack(side="bottom", fill="x", padx=5, pady=5)

        # Remove Tag Entry Box
        self.remove_tag_entry = tk.Entry(self.remove_tag_frame)
        self.remove_tag_entry.pack(side="left", fill="x", expand=True)

        # Dropdown for selecting the scope of tag removal
        self.remove_tag_options = ["Current Image", "Visible Images", "All Images"]
        self.remove_tag_scope = tk.StringVar(value=self.remove_tag_options[0])
        self.remove_tag_dropdown = tk.OptionMenu(self.remove_tag_frame, self.remove_tag_scope, *self.remove_tag_options)
        self.remove_tag_dropdown.pack(side="left", padx=5)

        # Remove tag button
        self.remove_tag_button = tk.Button(self.remove_tag_frame, text="Remove Tag", command=self.remove_tag)
        self.remove_tag_button.pack(side="left", padx=5)

        # Make filter labels clickable
        self.pos_filter_label.bind("<Button-1>", self.show_filter_edit_popup)
        self.neg_filter_label.bind("<Button-1>", self.show_filter_edit_popup)
    
        self.pos_filter_label.bind("<Button-3>", self.show_pos_filter_context_menu)

        # Underline filter labels
        self.pos_filter_label.config(font=('TkDefaultFont', 10, 'underline'))
        self.neg_filter_label.config(font=('TkDefaultFont', 10, 'underline'))

    # Method to find common tags
    def find_common_tags(self):
        common_tags = set(self.tag_map[next(iter(self.tag_map))]) if self.tag_map else set()
        for tags in self.tag_map.values():
            common_tags.intersection_update(tags)
        return common_tags

    # Method to create and display the context menu for positive filter
    def show_pos_filter_context_menu(self, event):
        common_tags = self.find_common_tags()
        context_menu = tk.Menu(self.root, tearoff=0)

        if common_tags:
            context_menu.add_command(label="Filter by Common Tags",
                                    command=lambda: self.apply_common_tags_filter(common_tags))
        else:
            context_menu.add_command(label="No Common Tags", state="disabled")

        context_menu.tk_popup(event.x_root, event.y_root)

    # Method to apply common tags filter
    def apply_common_tags_filter(self, common_tags):
        self.pos_filter_entry.delete(0, tk.END)
        self.pos_filter_entry.insert(0, ', '.join(common_tags))
        self.pos_filter_option.set(0)  # Set to AND
        self.apply_filters()

    def show_filter_edit_popup(self, event):
        # Get the current mouse position
        x, y = self.root.winfo_pointerxy()

        # Determine which filter label was clicked
        filter_entry = self.pos_filter_entry if event.widget == self.pos_filter_label else self.neg_filter_entry

        # Create a top-level window for editing
        edit_popup = tk.Toplevel(self.root)
        edit_popup.wm_title("Edit Filter")
        edit_popup.geometry(f"+{x+10}+{y+10}")  # Place the window near the mouse

        # Create a text widget in the popup window
        edit_text = tk.Text(edit_popup, width=50, height=10)  # Adjust width and height as needed
        edit_text.insert('1.0', filter_entry.get())
        edit_text.pack()

        # Set focus to the text widget
        edit_text.focus_set()

        # Function to call when Apply is clicked or Enter is pressed
        def apply_changes():
            self.apply_filter_edit(filter_entry, edit_text.get('1.0', 'end-1c'), edit_popup)

        # Button to apply changes
        apply_button = tk.Button(edit_popup, text="Apply", command=apply_changes)
        apply_button.pack()

        # Bind the Enter key to the apply_changes function
        edit_popup.bind('<Return>', lambda e: apply_changes())

    def apply_filter_edit(self, filter_entry, new_value, popup_window):
        filter_entry.delete(0, tk.END)
        filter_entry.insert(0, new_value)
        popup_window.destroy()
        self.apply_filters()

    def get_filter_label_color(self):
        # Determine the label color based on dark mode setting
        return "white" if self.dark_mode_enabled.get() else "black"

    def edit_filter_in_popup(self, filter_entry, filter_name):
        popup = tk.Toplevel(self.root)
        popup.title(filter_name)
        popup.geometry("400x200")  # Adjust size as needed

        large_text = tk.Text(popup, width=40, height=10)  # A 2D text box
        large_text.insert("1.0", filter_entry.get())
        large_text.pack(pady=20)

        save_button = tk.Button(popup, text="Save", command=lambda: self.save_filter_from_popup(large_text.get("1.0", "end-1c"), filter_entry, popup))
        save_button.pack()

    def save_filter_from_popup(self, new_filter_text, filter_entry, popup_window):
        filter_entry.delete(0, tk.END)
        filter_entry.insert(0, new_filter_text.strip())
        popup_window.destroy()
        self.apply_filters()

    def update_tag_visibility(self):
        if self.selected_label:
            image_path = self.selected_label.image_path
            self.display_tags(image_path, self.count_tag_frequencies())

    def remove_tag(self):
        tags_to_remove = [tag.strip() for tag in self.remove_tag_entry.get().split(',') if tag.strip()]
        if not tags_to_remove:
            return  # Do nothing if no tags are entered

        scope = self.remove_tag_scope.get()
        if scope == "Current Image":
            self.remove_tags_from_image(self.selected_label, tags_to_remove)
        elif scope == "Visible Images":
            for label in [lbl for lbl in self.image_labels if lbl.winfo_ismapped()]:
                self.remove_tags_from_image(label, tags_to_remove)
        elif scope == "All Images":
            for label in self.image_labels:
                self.remove_tags_from_image(label, tags_to_remove)

        self.remove_tag_entry.delete(0, 'end')  # Clear the entry box

    def remove_tags_from_image(self, label, tags):
        if label:
            image_tags = self.tag_map.get(label, [])
            updated = False
            for tag_to_remove in tags:
                if tag_to_remove in image_tags:
                    image_tags.remove(tag_to_remove)
                    updated = True

            if updated:
                # Update the tag map
                self.tag_map[label] = image_tags

                # Update the tags file for the image
                image_path = label.image_path
                caption_path = image_path.rsplit('.', 1)[0] + '.txt'
                with open(caption_path, 'w') as file:
                    file.write(', '.join(image_tags))

                # Update the tags display if the selected image's tags were changed
                if label == self.selected_label:
                    self.display_tags(image_path, self.count_tag_frequencies())

    def clear_filters(self):
        # Clear the filter entries
        self.pos_filter_entry.delete(0, 'end')
        self.neg_filter_entry.delete(0, 'end')

        # Update the gallery view to show all images
        self.update_gallery_view([], [], self.pos_filter_option.get(), self.neg_filter_option.get())

    def apply_filters(self):
        pos_filters = [tag.strip() for tag in self.pos_filter_entry.get().split(',') if tag.strip()]
        neg_filters = [tag.strip() for tag in self.neg_filter_entry.get().split(',') if tag.strip()]

        # Update the gallery view based on filters
        self.update_gallery_view(pos_filters, neg_filters, self.pos_filter_option.get(), self.neg_filter_option.get())

    def update_gallery_view(self, pos_filters, neg_filters, pos_option, neg_option):
        visible_labels = []  # List to keep track of labels that will be visible
        selected_visible = False  # Flag to check if selected label is visible

        for label in self.image_labels:
            image_tags = self.tag_map[label]

            # Apply AND/OR logic for positive and negative filters
            show_image = True
            if pos_filters:
                show_image = show_image and (all(tag in image_tags for tag in pos_filters) if pos_option == 0 else any(tag in image_tags for tag in pos_filters))
            if neg_filters:
                show_image = show_image and (all(tag not in image_tags for tag in neg_filters) if neg_option == 0 else any(tag not in image_tags for tag in neg_filters))

            if show_image:
                visible_labels.append(label)
                if label == self.selected_label:
                    selected_visible = True

        # Rearrange visible labels in the grid
        row, col = 0, 0
        for label in visible_labels:
            label.grid(row=row, column=col, padx=2, pady=2)
            col += 1
            if col >= 3:  # Assuming 3 columns, adjust as needed
                col = 0
                row += 1

        # Hide other labels
        for label in set(self.image_labels) - set(visible_labels):
            label.grid_remove()

        # Scroll to keep the selected image in view or select the first visible image
        if selected_visible:
            self.scroll_to_label(self.selected_label)
        elif visible_labels:
            self.select_image(None, visible_labels[0])
            self.scroll_to_label(visible_labels[0])


    def add_tag_entry(self):
        # Create a frame for tag entry and options
        self.tag_entry_frame = tk.Frame(self.right_frame)
        self.tag_entry_frame.pack(side="bottom", fill="x", padx=5, pady=5)

        # Tag entry box
        self.tag_entry = tk.Entry(self.tag_entry_frame)
        self.tag_entry.pack(side="left", fill="x", expand=True)

        # Dropdown for selecting the scope of tag addition
        self.tag_add_options = ["Current Image", "Visible Images", "All Images"]
        self.tag_add_scope = tk.StringVar(value=self.tag_add_options[0])
        self.tag_add_dropdown = tk.OptionMenu(self.tag_entry_frame, self.tag_add_scope, *self.tag_add_options)
        self.tag_add_dropdown.pack(side="left", padx=5)

        # Add tag button
        self.add_tag_button = tk.Button(self.tag_entry_frame, text="Add Tag", command=self.add_tag)
        self.add_tag_button.pack(side="left", padx=5)

    def add_tag(self):
        tags_to_add = [tag.strip() for tag in self.tag_entry.get().split(',') if tag.strip()]
        if not tags_to_add:
            return  # Do nothing if no tags are entered

        scope = self.tag_add_scope.get()
        if scope == "Current Image":
            self.add_tags_to_image(self.selected_label, tags_to_add)
        elif scope == "Visible Images":
            for label in [lbl for lbl in self.image_labels if lbl.winfo_ismapped()]:
                self.add_tags_to_image(label, tags_to_add)
        elif scope == "All Images":
            for label in self.image_labels:
                self.add_tags_to_image(label, tags_to_add)

        self.tag_entry.delete(0, 'end')  # Clear the entry box

    def add_tags_to_image(self, label, tags):
        if label:
            image_tags = self.tag_map.get(label, [])
            updated = False
            for new_tag in tags:
                if new_tag and new_tag not in image_tags:
                    image_tags.append(new_tag)
                    updated = True

            if updated:
                # Update the tag map
                self.tag_map[label] = image_tags

                # Update the tags file for the image
                image_path = label.image_path
                caption_path = image_path.rsplit('.', 1)[0] + '.txt'
                with open(caption_path, 'w') as file:
                    file.write(', '.join(image_tags))

                # Update the tags display if the selected image's tags were changed
                if label == self.selected_label:
                    self.display_tags(image_path, self.count_tag_frequencies())

    def save_settings(self, settings):
        with open('settings/app_settings.json', 'w') as f:
            json.dump(settings, f)

    def load_settings(self):
        if os.path.exists('settings/app_settings.json'):
            with open('settings/app_settings.json', 'r') as f:
                return json.load(f)
        return {}

    def rgba_to_hex(self, rgba_color):
        # Parse the RGBA string to integers
        rgba = rgba_color.strip('rgba()').split(',')
        r, g, b = [int(x) for x in rgba[:3]]  # Convert RGB values to integers
        # Convert to hexadecimal
        return f'#{r:02x}{g:02x}{b:02x}'

    def load_color_schemes(self):
        self.color_schemes = {"None": None}  # Default option
        color_scheme_dir = 'tags'  # Directory where color schemes are stored
        try:
            for file in os.listdir(color_scheme_dir):
                if file.endswith(('.yaml', '.csv')):
                    scheme_name = file.rsplit('.', 1)[0]
                    self.color_schemes[scheme_name] = os.path.join(color_scheme_dir, file)
        except FileNotFoundError:
            print(f"Color scheme directory '{color_scheme_dir}' not found.")

    def change_color_scheme(self, scheme_name):
        selected_scheme = self.color_schemes[scheme_name]
        if selected_scheme:
            self.load_tag_colors(selected_scheme)
        else:
            self.tag_colors = {}  # Reset to no color coding

        # Update last color scheme in settings
        settings = self.load_settings()
        settings['last_color_scheme'] = scheme_name
        self.save_settings(settings)

        if self.selected_label:
            image_path = self.selected_label.image_path
            self.display_tags(image_path, self.count_tag_frequencies())

    def load_tag_colors(self, file_path):
        try:
            if file_path.endswith('.yaml'):
                with open(file_path, 'r', encoding='utf-8') as file:
                    data = yaml.safe_load(file)
                for category in data:
                    for group in category['groups']:
                        rgba_color = group.get('color', 'rgba(0, 0, 0, 1)')
                        color = self.rgba_to_hex(rgba_color)
                        for tag in group['tags']:
                            normalized_tag = tag.replace('_', ' ')
                            self.tag_colors[normalized_tag] = color
            elif file_path.endswith('.csv'):
                with open(file_path, newline='', encoding='utf-8') as csvfile:
                    reader = csv.reader(csvfile)
                    for row in reader:
                        tag, group_number, _, alt_tags = row
                        scheme = 'danbooru' if 'danbooru' in file_path else 'e621'
                        color = self.color_mapping[scheme].get(group_number, ["black"])[0]
                        normalized_tag = tag.replace('_', ' ')
                        self.tag_colors[normalized_tag] = color
                        # Process alternate tags
                        if alt_tags:
                            for alt_tag in alt_tags.strip('\"').split(','):
                                normalized_alt_tag = alt_tag.replace('_', ' ')
                                self.tag_colors[normalized_alt_tag] = color
        except FileNotFoundError:
            print(f"File '{file_path}' not found.")
        except Exception as e:
            print(f"Error loading file '{file_path}': {e}")

    def copy_to_clipboard(self, tag):
        self.root.clipboard_clear()
        self.root.clipboard_append(tag)
        self.root.update() 

    def toggle_dark_mode(self):
        if self.dark_mode_enabled.get():
            self.apply_dark_mode()
        else:
            self.apply_light_mode()
        settings = self.load_settings()
        settings['dark_mode'] = self.dark_mode_enabled.get()
        self.save_settings(settings)
        if self.selected_label:
            image_path = self.selected_label.image_path
            self.display_tags(image_path, self.count_tag_frequencies())

    def apply_dark_mode(self):
        dark_bg = 'gray20'
        dark_fg = 'white'
        dark_canvas = 'gray30'
        dark_text_bg = 'gray25'
        dark_bar = 'gray30'  # Dark mode color for progress bar

        style = ttk.Style(self.root)
        style.theme_use('clam')
        style.configure("Horizontal.TProgressbar", troughcolor=dark_bg, background=dark_bar, bordercolor=dark_bg, lightcolor=dark_bar, darkcolor=dark_bar)

        self.root.configure(bg=dark_bg)
        self.main_frame.configure(bg=dark_bg)
        self.grid_canvas.configure(bg=dark_canvas, highlightbackground=dark_bg)
        self.scrollable_frame.configure(bg=dark_bg)
        self.right_frame.configure(bg=dark_bg)
        self.preview_frame.configure(bg=dark_bg)
        self.tags_frame.configure(bg=dark_bg)
        self.tags_text.configure(bg=dark_text_bg, fg=dark_fg)
        self.filter_frame.configure(bg=dark_bg)
        self.tag_entry_frame.configure(bg=dark_bg)
        self.preview_image_label.configure(bg=dark_bg, fg=dark_fg)
        self.scrollbar.configure(bg=dark_bg)
        self.pos_filter_entry.configure(bg=dark_text_bg, fg=dark_fg)
        self.neg_filter_entry.configure(bg=dark_text_bg, fg=dark_fg)
        self.pos_filter_label.configure(bg=dark_text_bg, fg=dark_fg)
        self.neg_filter_label.configure(bg=dark_text_bg, fg=dark_fg)
        self.filter_button.configure(bg=dark_bg, fg=dark_fg)
        self.tag_entry.configure(bg=dark_text_bg, fg=dark_fg)
        self.add_tag_button.configure(bg=dark_bg, fg=dark_fg)
        self.clear_filter_button.configure(bg=dark_bg, fg=dark_fg)
        self.tag_entry.configure(bg=dark_bg, fg=dark_fg)
        self.tag_add_dropdown.configure(bg=dark_bg, fg=dark_fg)
        self.add_tag_button.configure(bg=dark_bg, fg=dark_fg)
        self.remove_tag_entry.configure(bg=dark_bg, fg=dark_fg)
        self.remove_tag_dropdown.configure(bg=dark_bg, fg=dark_fg)
        self.remove_tag_button.configure(bg=dark_bg, fg=dark_fg)
        self.remove_tag_frame.configure(bg=dark_bg)

        if self.selected_label:
            image_path = self.selected_label.image_path
            self.display_tags(image_path, self.count_tag_frequencies())

    def apply_light_mode(self):
        light_bg = 'SystemButtonFace'
        light_fg = 'black'
        light_canvas = 'white'
        light_text_bg = 'white'
        light_bar = 'SystemButtonFace'  # Light mode color for progress bar

        style = ttk.Style(self.root)
        style.theme_use('clam')
        style.configure("Horizontal.TProgressbar", troughcolor=light_bg, background=light_bar, bordercolor=light_bg, lightcolor=light_bar, darkcolor=light_bar)

        self.root.configure(bg=light_bg)
        self.main_frame.configure(bg=light_bg)
        self.grid_canvas.configure(bg=light_canvas, highlightbackground=light_bg)
        self.scrollable_frame.configure(bg=light_bg)
        self.right_frame.configure(bg=light_bg)
        self.preview_frame.configure(bg=light_bg)
        self.tags_frame.configure(bg=light_bg)
        self.tags_text.configure(bg=light_text_bg, fg=light_fg)
        self.filter_frame.configure(bg=light_bg)
        self.tag_entry_frame.configure(bg=light_bg)
        self.preview_image_label.configure(bg=light_bg, fg=light_fg)
        self.scrollbar.configure(bg=light_bg)
        self.pos_filter_entry.configure(bg=light_text_bg, fg=light_fg)
        self.neg_filter_entry.configure(bg=light_text_bg, fg=light_fg)
        self.pos_filter_label.configure(bg=light_text_bg, fg=light_fg)
        self.neg_filter_label.configure(bg=light_text_bg, fg=light_fg)
        self.filter_button.configure(bg=light_bg, fg=light_fg)
        self.tag_entry.configure(bg=light_bg, fg=light_fg)
        self.add_tag_button.configure(bg=light_bg, fg=light_fg)
        self.clear_filter_button.configure(bg=light_bg, fg=light_fg)
        self.tag_entry.configure(bg=light_bg, fg=light_fg)
        self.tag_add_dropdown.configure(bg=light_bg, fg=light_fg)
        self.add_tag_button.configure(bg=light_bg, fg=light_fg)
        self.remove_tag_entry .configure(bg=light_bg, fg=light_fg)
        self.remove_tag_dropdown .configure(bg=light_bg, fg=light_fg)
        self.remove_tag_button .configure(bg=light_bg, fg=light_fg)
        self.remove_tag_frame.configure(bg=light_bg)

        if self.selected_label:
            image_path = self.selected_label.image_path
            self.display_tags(image_path, self.count_tag_frequencies())

    def remove_duplicates_visible(self):
        for label in self.image_labels:
            if label.winfo_ismapped():  # Checks if the label (image) is currently visible
                self._remove_duplicate_tags(label)

    def remove_duplicates_all(self):
        for label in self.image_labels:
            self._remove_duplicate_tags(label)

    def remove_duplicate_selected(self):
        if self.selected_label:
            self._remove_duplicate_tags(self.selected_label)

    def _remove_duplicate_tags(self, label):
        image_path = label.image_path
        tags = self.tag_map.get(label, [])
        unique_tags = list(set(tags))  # Remove duplicates

        if len(unique_tags) != len(tags):
            self.tag_map[label] = unique_tags

            # Update the tags file for the image
            caption_path = image_path.rsplit('.', 1)[0] + '.txt'
            with open(caption_path, 'w') as file:
                file.write(', '.join(unique_tags))

            if label == self.selected_label:
                # Update the tags display if the selected image's tags were changed
                self.display_tags(image_path, self.count_tag_frequencies())

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1440x1024")  # Adjust initial window size
    app = ImageGalleryApp(root)

    root.mainloop()