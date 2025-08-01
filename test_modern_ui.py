"""
Test script for the modernized Vehicle Log Channel Appender UI
This version removes heavy dependencies to test the interface design
"""

import tkinter as tk
from tkinter import ttk


class AutocompleteCombobox(ttk.Combobox):
    """A Combobox with autocompletion support."""
    def set_completion_list(self, completion_list):
        self._completion_list = sorted(completion_list, key=str.lower)
        self._hits = []
        self._hit_index = 0
        self.position = 0
        self['values'] = self._completion_list
        self.bind('<KeyRelease>', self.handle_keyrelease)

    def autocomplete(self, delta=0):
        if delta:
            self.delete(self.position, tk.END)
        else:
            self.position = len(self.get())

        _hits = []
        for element in self._completion_list:
            if element.lower().startswith(self.get().lower()):
                _hits.append(element)

        if _hits != self._hits:
            self._hit_index = 0
            self._hits = _hits

        if self._hits:
            self.delete(0, tk.END)
            self.insert(0, self._hits[self._hit_index])
            self.select_range(self.position, tk.END)

    def handle_keyrelease(self, event):
        if event.keysym == "BackSpace":
            self.position = self.index(tk.END)
        if event.keysym == "Left":
            self.position -= 1
        if event.keysym == "Right":
            self.position = self.index(tk.END)
        if len(event.keysym) == 1:
            self.autocomplete()


class VehicleLogChannelAppenderTest:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Vehicle Log Channel Appender - Multi-Channel Tool")
        
        # Set modern styling and responsive window sizing
        self.setup_modern_styling()
        self.setup_responsive_window()
        
        # Data storage (simplified for testing)
        self.vehicle_file_path = None
        self.custom_channels = []
        
        # Search and filter variables
        self.search_var = tk.StringVar()
        self.filter_vars = {}
        
        self.setup_ui()
        self.log_status("🚀 Application started. Please select a vehicle file and configure custom channels.")
    
    def setup_modern_styling(self):
        """Setup modern color scheme and styling"""
        # Modern color palette
        self.colors = {
            'primary': '#2E86AB',      # Blue
            'secondary': '#A23B72',    # Purple  
            'success': '#43AA8B',      # Green
            'warning': '#F18F01',      # Orange
            'danger': '#C73E1D',       # Red
            'light': '#F8F9FA',        # Light gray
            'dark': '#343A40',         # Dark gray
            'white': '#FFFFFF',
            'background': '#F5F5F5',   # Light background
            'card': '#FFFFFF',         # Card background
            'border': '#DEE2E6'        # Border color
        }
        
        # Configure ttk styles for modern look
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure modern notebook style
        style.configure('Modern.TNotebook', background=self.colors['background'])
        style.configure('Modern.TNotebook.Tab', 
                       padding=[20, 12], 
                       font=('Segoe UI', 11, 'bold'))
        
        # Configure modern frame style
        style.configure('Modern.TFrame', background=self.colors['card'])
        
        # Set root window styling
        self.root.configure(bg=self.colors['background'])
    
    def setup_responsive_window(self):
        """Setup responsive window with proper constraints"""
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Calculate responsive window size (80% of screen, but with limits)
        min_width, min_height = 1000, 700
        max_width, max_height = 1600, 1200
        
        window_width = max(min_width, min(max_width, int(screen_width * 0.8)))
        window_height = max(min_height, min(max_height, int(screen_height * 0.8)))
        
        # Center window on screen
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.minsize(min_width, min_height)
        self.root.maxsize(max_width, max_height)
        
        # Allow window to be resizable
        self.root.resizable(True, True)
        
        # Configure grid weight for responsive behavior
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
    def setup_ui(self):
        """Setup the user interface with modern tabbed layout"""
        
        # Create main container with padding
        main_container = tk.Frame(self.root, bg=self.colors['background'])
        main_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Modern title with better styling
        title_frame = tk.Frame(main_container, bg=self.colors['background'])
        title_frame.pack(fill="x", pady=(0, 20))
        
        title_label = tk.Label(title_frame, 
                              text="🚗 Vehicle Log Channel Appender", 
                              font=("Segoe UI", 20, "bold"),
                              fg=self.colors['dark'],
                              bg=self.colors['background'])
        title_label.pack()
        
        subtitle_label = tk.Label(title_frame, 
                                 text="Multi-Channel Analysis Tool with Surface Table Interpolation", 
                                 font=("Segoe UI", 11),
                                 fg=self.colors['secondary'],
                                 bg=self.colors['background'])
        subtitle_label.pack(pady=(5, 0))
        
        # Create modern notebook for tabs
        self.notebook = ttk.Notebook(main_container, style='Modern.TNotebook')
        self.notebook.pack(fill="both", expand=True, pady=(0, 15))
        
        # Setup tabs
        self.setup_processing_tab()
        self.setup_custom_channels_tab()
        
        # Modern Status/Log area
        log_frame = tk.LabelFrame(main_container, 
                                 text="📊 Status Log", 
                                 font=("Segoe UI", 12, "bold"),
                                 fg=self.colors['dark'],
                                 bg=self.colors['background'],
                                 bd=2,
                                 relief="groove")
        log_frame.pack(fill="x", pady=(0, 15))
        
        # Create scrollable text widget with modern styling
        text_frame = tk.Frame(log_frame, bg=self.colors['card'])
        text_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.log_text = tk.Text(text_frame, 
                               height=6, 
                               wrap=tk.WORD,
                               font=("Segoe UI", 10),
                               bg=self.colors['white'],
                               fg=self.colors['dark'],
                               bd=1,
                               relief="solid",
                               selectbackground=self.colors['primary'],
                               selectforeground=self.colors['white'])
        scrollbar = tk.Scrollbar(text_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Modern Settings section
        settings_frame = tk.Frame(main_container, bg=self.colors['background'])
        settings_frame.pack(fill="x", pady=(0, 10))
        
        # Create card-style container for settings
        settings_card = tk.Frame(settings_frame, 
                                bg=self.colors['card'],
                                bd=1,
                                relief="solid")
        settings_card.pack(fill="x", padx=5, pady=5)
        
        # Auto-save status with modern styling
        status_frame = tk.Frame(settings_card, bg=self.colors['card'])
        status_frame.pack(side="left", fill="x", expand=True, padx=15, pady=10)
        
        tk.Label(status_frame, 
                text="🔄 Auto-save: ON", 
                font=("Segoe UI", 10, "bold"), 
                fg=self.colors['success'],
                bg=self.colors['card']).pack(side="left", padx=5)
        tk.Label(status_frame, 
                text="●", 
                font=("Segoe UI", 14), 
                fg=self.colors['success'],
                bg=self.colors['card']).pack(side="left")
        
        # Main settings buttons with modern styling
        main_settings_frame = tk.Frame(settings_card, bg=self.colors['card'])
        main_settings_frame.pack(side="right", padx=15, pady=10)
        
        self.create_modern_button(main_settings_frame, 
                                 "💾 Save Settings As...", 
                                 self.dummy_action, 
                                 self.colors['success']).pack(side="left", padx=3)
        self.create_modern_button(main_settings_frame, 
                                 "📁 Load Settings From...", 
                                 self.dummy_action, 
                                 self.colors['primary']).pack(side="left", padx=3)
        
        # Reset button with modern styling
        self.create_modern_button(main_settings_frame, 
                                 "🔄 Reset", 
                                 self.dummy_action, 
                                 self.colors['warning']).pack(side="left", padx=3)

    def create_modern_button(self, parent, text, command, bg_color, width=None, height=None):
        """Create a modern styled button"""
        return tk.Button(parent,
                        text=text,
                        command=command,
                        bg=bg_color,
                        fg=self.colors['white'],
                        font=("Segoe UI", 10, "bold"),
                        relief="flat",
                        bd=0,
                        padx=15,
                        pady=8,
                        cursor="hand2",
                        activebackground=self.darken_color(bg_color),
                        activeforeground=self.colors['white'],
                        width=width,
                        height=height)
    
    def darken_color(self, color):
        """Darken a hex color by 20% for hover effects"""
        # Simple darkening - remove the # and convert to RGB
        if color.startswith('#'):
            color = color[1:]
        
        # Convert hex to RGB
        r = int(color[0:2], 16)
        g = int(color[2:4], 16) 
        b = int(color[4:6], 16)
        
        # Darken by 20%
        r = int(r * 0.8)
        g = int(g * 0.8)
        b = int(b * 0.8)
        
        # Convert back to hex
        return f"#{r:02x}{g:02x}{b:02x}"

    def setup_processing_tab(self):
        """Setup the main processing tab with modern styling"""
        self.processing_frame = ttk.Frame(self.notebook, style='Modern.TFrame')
        self.notebook.add(self.processing_frame, text="🔧 Processing")
        
        # Create scrollable container for the processing tab
        canvas = tk.Canvas(self.processing_frame, bg=self.colors['background'])
        scrollbar = ttk.Scrollbar(self.processing_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.colors['background'])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Vehicle file selection with modern card design
        file_card = tk.LabelFrame(scrollable_frame, 
                                 text="📁 Vehicle Log File", 
                                 font=("Segoe UI", 14, "bold"),
                                 fg=self.colors['dark'],
                                 bg=self.colors['card'],
                                 bd=2,
                                 relief="groove")
        file_card.pack(fill="x", padx=25, pady=15)
        
        vehicle_btn_frame = tk.Frame(file_card, bg=self.colors['card'])
        vehicle_btn_frame.pack(fill="x", padx=20, pady=20)
        
        # Modern file selection button
        self.vehicle_btn = self.create_modern_button(vehicle_btn_frame, 
                                                    "📂 Select Vehicle File (MDF/MF4/DAT/CSV)", 
                                                    self.dummy_action, 
                                                    self.colors['primary'],
                                                    width=35)
        self.vehicle_btn.pack(anchor="w")
        
        # Status label with modern styling
        status_frame = tk.Frame(vehicle_btn_frame, bg=self.colors['card'])
        status_frame.pack(fill="x", pady=(15, 0))
        
        self.vehicle_status = tk.Label(status_frame, 
                                      text="❌ No vehicle file selected", 
                                      fg=self.colors['danger'],
                                      bg=self.colors['card'],
                                      font=("Segoe UI", 11))
        self.vehicle_status.pack(anchor="w")
        
        # Modern Processing options
        options_card = tk.LabelFrame(scrollable_frame, 
                                   text="⚙️ Processing Options", 
                                   font=("Segoe UI", 14, "bold"),
                                   fg=self.colors['dark'],
                                   bg=self.colors['card'],
                                   bd=2,
                                   relief="groove")
        options_card.pack(fill="x", padx=25, pady=15)
        
        # Output format selection with modern styling
        format_container = tk.Frame(options_card, bg=self.colors['card'])
        format_container.pack(fill="x", padx=20, pady=20)
        
        format_title = tk.Label(format_container, 
                               text="📊 Output Format:", 
                               font=("Segoe UI", 12, "bold"),
                               fg=self.colors['dark'],
                               bg=self.colors['card'])
        format_title.pack(anchor="w", pady=(0, 10))
        
        self.output_format = tk.StringVar(value="mf4")
        
        # Modern radio buttons
        format_frame = tk.Frame(format_container, bg=self.colors['card'])
        format_frame.pack(fill="x", padx=20)
        
        mf4_radio = tk.Radiobutton(format_frame, 
                                  text="🔧 MF4 (Recommended for calculated channels)", 
                                  variable=self.output_format, 
                                  value="mf4",
                                  font=("Segoe UI", 11),
                                  bg=self.colors['card'],
                                  fg=self.colors['dark'],
                                  selectcolor=self.colors['primary'],
                                  activebackground=self.colors['card'])
        mf4_radio.pack(anchor="w", pady=3)
        
        csv_radio = tk.Radiobutton(format_frame, 
                                  text="📈 CSV (For data analysis)", 
                                  variable=self.output_format, 
                                  value="csv",
                                  font=("Segoe UI", 11),
                                  bg=self.colors['card'],
                                  fg=self.colors['dark'],
                                  selectcolor=self.colors['primary'],
                                  activebackground=self.colors['card'])
        csv_radio.pack(anchor="w", pady=3)
        
        # Modern Processing section
        process_card = tk.LabelFrame(scrollable_frame, 
                                   text="🚀 Process Channels", 
                                   font=("Segoe UI", 14, "bold"),
                                   fg=self.colors['dark'],
                                   bg=self.colors['card'],
                                   bd=2,
                                   relief="groove")
        process_card.pack(fill="x", padx=25, pady=15)
        
        info_container = tk.Frame(process_card, bg=self.colors['card'])
        info_container.pack(fill="x", padx=20, pady=20)
        
        # Modern info section with icon
        info_text = ("💡 Configure custom channels in the 'Custom Channels' tab, then process them here.\n"
                    "🔄 The tool will create calculated channels based on surface table interpolation.")
        info_label = tk.Label(info_container, 
                             text=info_text, 
                             font=("Segoe UI", 11), 
                             fg=self.colors['primary'],
                             bg=self.colors['card'],
                             justify="left",
                             wraplength=600)
        info_label.pack(anchor="w", pady=(0, 20))
        
        # Modern process button
        process_btn_frame = tk.Frame(info_container, bg=self.colors['card'])
        process_btn_frame.pack(fill="x")
        
        self.process_btn = self.create_modern_button(process_btn_frame, 
                                                    "🚀 Process All Custom Channels", 
                                                    self.dummy_action, 
                                                    self.colors['warning'],
                                                    width=30,
                                                    height=2)
        self.process_btn.pack(pady=10)

    def setup_custom_channels_tab(self):
        """Setup the custom channels tab with modern design"""
        self.custom_channels_frame = ttk.Frame(self.notebook, style='Modern.TFrame')
        self.notebook.add(self.custom_channels_frame, text="⚙️ Custom Channels")
        
        # Create scrollable container for the custom channels tab
        canvas2 = tk.Canvas(self.custom_channels_frame, bg=self.colors['background'])
        scrollbar2 = ttk.Scrollbar(self.custom_channels_frame, orient="vertical", command=canvas2.yview)
        scrollable_frame2 = tk.Frame(canvas2, bg=self.colors['background'])
        
        scrollable_frame2.bind(
            "<Configure>",
            lambda e: canvas2.configure(scrollregion=canvas2.bbox("all"))
        )
        
        canvas2.create_window((0, 0), window=scrollable_frame2, anchor="nw")
        canvas2.configure(yscrollcommand=scrollbar2.set)
        
        canvas2.pack(side="left", fill="both", expand=True)
        scrollbar2.pack(side="right", fill="y")
        
        # Modern title section
        title_container = tk.Frame(scrollable_frame2, bg=self.colors['background'])
        title_container.pack(fill="x", padx=25, pady=(15, 0))
        
        title_label = tk.Label(title_container, 
                              text="⚙️ Custom Channel Management", 
                              font=("Segoe UI", 18, "bold"),
                              fg=self.colors['dark'],
                              bg=self.colors['background'])
        title_label.pack()
        
        subtitle_label = tk.Label(title_container,
                                 text="Create and manage custom calculated channels with surface table interpolation",
                                 font=("Segoe UI", 11),
                                 fg=self.colors['secondary'],
                                 bg=self.colors['background'])
        subtitle_label.pack(pady=(5, 15))
        
        # Modern Add new channel section
        add_card = tk.LabelFrame(scrollable_frame2, 
                                text="➕ Add New Custom Channel", 
                                font=("Segoe UI", 14, "bold"),
                                fg=self.colors['dark'],
                                bg=self.colors['card'],
                                bd=2,
                                relief="groove")
        add_card.pack(fill="x", padx=25, pady=15)
        
        # Main form container
        form_container = tk.Frame(add_card, bg=self.colors['card'])
        form_container.pack(fill="x", padx=20, pady=20)
        
        # Modern Channel name field
        name_frame = tk.Frame(form_container, bg=self.colors['card'])
        name_frame.pack(fill="x", pady=8)
        tk.Label(name_frame, 
                text="📝 Channel Name:", 
                width=20, 
                anchor="w",
                font=("Segoe UI", 11, "bold"),
                fg=self.colors['dark'],
                bg=self.colors['card']).pack(side="left")
        self.new_custom_name = tk.Entry(name_frame, 
                                       width=30,
                                       font=("Segoe UI", 11),
                                       bd=1,
                                       relief="solid")
        self.new_custom_name.pack(side="left", padx=10)
        
        # Add a modern add button
        add_btn_frame = tk.Frame(form_container, bg=self.colors['card'])
        add_btn_frame.pack(fill="x", pady=20)
        
        add_btn = self.create_modern_button(add_btn_frame, 
                                           "➕ Add Custom Channel", 
                                           self.dummy_action,
                                           self.colors['success'],
                                           width=20)
        add_btn.pack()

    def log_status(self, message):
        """Add a status message to the log"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)

    def dummy_action(self):
        """Dummy action for testing buttons"""
        self.log_status("✅ Button clicked - UI test successful!")

    def run(self):
        """Start the application"""
        self.root.mainloop()


if __name__ == "__main__":
    app = VehicleLogChannelAppenderTest()
    app.run()