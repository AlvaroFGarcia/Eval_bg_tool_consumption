"""
UI Components Module for Vehicle Log Channel Appender
Contains reusable UI components and widgets.
"""

import customtkinter as ctk
import tkinter as tk


class ModernAutocompleteCombobox(ctk.CTkComboBox):
    """A modern ComboBox with autocompletion support."""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._completion_list = []
        self.bind('<KeyRelease>', self.handle_keyrelease)
    
    def set_completion_list(self, completion_list):
        """Set the list of values for autocompletion."""
        self._completion_list = sorted(completion_list, key=str.lower)
        self.configure(values=self._completion_list)
    
    def handle_keyrelease(self, event):
        """Handle key release events for autocompletion."""
        if event.keysym in ['Up', 'Down', 'Left', 'Right', 'Return', 'Tab']:
            return
        
        current_text = self.get().lower()
        if not current_text:
            self.configure(values=self._completion_list)
            return
        
        # Filter matching items
        matches = [item for item in self._completion_list 
                  if item.lower().startswith(current_text)]
        
        if matches:
            self.configure(values=matches)


class ModernProgressDialog:
    """Modern progress dialog with loading animation."""
    
    def __init__(self, parent, title="Processing", message="Please wait..."):
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x150")
        self.dialog.resizable(False, False)
        
        # Center the dialog
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Create modern layout
        main_frame = ctk.CTkFrame(self.dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Message label
        self.message_label = ctk.CTkLabel(
            main_frame, 
            text=message,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.message_label.pack(pady=(0, 15))
        
        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(main_frame)
        self.progress_bar.pack(fill="x", padx=20, pady=(0, 10))
        self.progress_bar.set(0)
        
        # Status label
        self.status_label = ctk.CTkLabel(
            main_frame,
            text="Initializing...",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.pack()
        
    def update_progress(self, value, status=""):
        """Update progress bar and status."""
        self.progress_bar.set(value)
        if status:
            self.status_label.configure(text=status)
        self.dialog.update_idletasks()
    
    def close(self):
        """Close the dialog."""
        self.dialog.destroy()