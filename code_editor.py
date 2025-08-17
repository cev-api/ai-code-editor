import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import json
import openai
from pathlib import Path
import threading
import queue
import datetime

class CodeEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("OpenAI Based Code Editor by CevAPI")
        self.root.geometry("1200x800")
        
        # Configuration
        self.config_file = "config.json"
        self.load_config()
        
        # OpenAI client
        self.client = None
        if self.api_key:
            self.client = openai.OpenAI(api_key=self.api_key)
        
        # Current working directory
        self.current_folder = None
        self.current_file = None
        
        # Message queue for async operations
        self.message_queue = queue.Queue()
        
        # AI conversation history for maintaining context
        self.conversation_history = []
        
        # File history for tracking changes and reverting
        self.file_history = {}  # file_path -> list of (content, timestamp, description)
        self.current_history_index = {}  # file_path -> current position in history
        
        # Token usage tracking
        self.total_tokens_used = 0
        self.total_requests = 0
        self.session_start_time = datetime.datetime.now()
        
        self.setup_ui()
        self.check_queue()
        
        # Add welcome message to debug console
        self.add_debug_log("=== AI Code Editor Debug Console ===", "SYSTEM")
        self.add_debug_log("Application started successfully", "SYSTEM")
        self.add_debug_log("Debug logging enabled - monitor API calls, requests, and system events", "INFO")
        self.add_debug_log("Token usage tracking enabled - monitor costs in real-time", "INFO")
    
    def load_config(self):
        # Load configuration from file
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.api_key = config.get('api_key', '')
                    self.model = config.get('model', 'gpt-4')
                    self.temperature = config.get('temperature', 1.0)
                    self.max_tokens = config.get('max_tokens', 4000)
                    self.max_completion_tokens = config.get('max_completion_tokens', 4000)
                    self.conversation_memory_limit = config.get('conversation_memory_limit', 10)
            except:
                self.api_key = ''
                self.model = 'gpt-4'
                self.temperature = 1.0
                self.max_tokens = 4000
                self.max_completion_tokens = 4000
                self.conversation_memory_limit = 10
        else:
            self.api_key = ''
            self.model = 'gpt-4'
            self.temperature = 1.0
            self.max_tokens = 4000
            self.max_completion_tokens = 4000
            self.conversation_memory_limit = 10
    
    def save_config(self):
        # Save configuration to file
        # Save current configuration to file
        config = {
            'api_key': self.api_key,
            'model': self.model,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
            'max_completion_tokens': self.max_completion_tokens,
            'conversation_memory_limit': self.conversation_memory_limit
        }
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Update status
        self.status_var.set("Configuration saved successfully!")
    
    def show_settings_panel(self):
        # Show the settings panel for model parameters
        settings_window = tk.Toplevel(self.root)
        settings_window.title("AI Model Settings")
        settings_window.geometry("500x400")
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # Main frame
        main_frame = ttk.Frame(settings_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(main_frame, text="AI Model Configuration", font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Temperature setting
        temp_frame = ttk.Frame(main_frame)
        temp_frame.pack(fill=tk.X, pady=5)
        ttk.Label(temp_frame, text="Temperature:", width=20).pack(side=tk.LEFT)
        temp_var = tk.DoubleVar(value=self.temperature)
        temp_scale = ttk.Scale(temp_frame, from_=0.0, to=2.0, variable=temp_var, orient=tk.HORIZONTAL)
        temp_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
        temp_label = ttk.Label(temp_frame, text=f"{self.temperature:.1f}")
        temp_label.pack(side=tk.LEFT, padx=(10, 0))
        
        def update_temp_label(val):
            temp_label.config(text=f"{float(val):.1f}")
        
        temp_scale.config(command=update_temp_label)
        
        # Max tokens setting
        tokens_frame = ttk.Frame(main_frame)
        tokens_frame.pack(fill=tk.X, pady=5)
        ttk.Label(tokens_frame, text="Max Tokens:", width=20).pack(side=tk.LEFT)
        tokens_var = tk.IntVar(value=self.max_tokens)
        tokens_entry = ttk.Entry(tokens_frame, textvariable=tokens_var, width=10)
        tokens_entry.pack(side=tk.LEFT, padx=(10, 0))
        
        # Max completion tokens setting (for GPT-5)
        comp_tokens_frame = ttk.Frame(main_frame)
        comp_tokens_frame.pack(fill=tk.X, pady=5)
        ttk.Label(comp_tokens_frame, text="Max Completion Tokens:", width=20).pack(side=tk.LEFT)
        comp_tokens_var = tk.IntVar(value=self.max_completion_tokens)
        comp_tokens_entry = ttk.Entry(comp_tokens_frame, textvariable=comp_tokens_var, width=10)
        comp_tokens_entry.pack(side=tk.LEFT, padx=(10, 0))
        
        # Conversation memory limit setting
        memory_frame = ttk.Frame(main_frame)
        memory_frame.pack(fill=tk.X, pady=5)
        ttk.Label(memory_frame, text="Conversation Memory:", width=20).pack(side=tk.LEFT)
        memory_var = tk.IntVar(value=self.conversation_memory_limit)
        memory_entry = ttk.Entry(memory_frame, textvariable=memory_var, width=10)
        memory_entry.pack(side=tk.LEFT, padx=(10, 0))
        
        # Help text
        help_text = """Temperature: Controls randomness (0.0 = focused, 2.0 = creative)
Max Tokens: Maximum tokens for most models
Max Completion Tokens: For GPT-5 models only
Conversation Memory: Number of messages to keep for context (higher = more tokens)"""
        help_label = ttk.Label(main_frame, text=help_text, font=('Arial', 9), foreground='gray', justify=tk.LEFT)
        help_label.pack(pady=20)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=20)
        
        def save_settings():
            self.temperature = temp_var.get()
            self.max_tokens = tokens_var.get()
            self.max_completion_tokens = comp_tokens_var.get()
            self.conversation_memory_limit = memory_var.get()
            self.save_config()
            
            # Log the new settings
            self.add_debug_log(f"Settings updated - Temp: {self.temperature}, Max Tokens: {self.max_tokens}, Memory Limit: {self.conversation_memory_limit}", "SYSTEM")
            
            settings_window.destroy()
            messagebox.showinfo("Success", "Settings saved successfully!")
        
        ttk.Button(button_frame, text="Save Settings", command=save_settings).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Cancel", command=settings_window.destroy).pack(side=tk.LEFT)
    
    def show_instructions(self):
        # Show comprehensive instructions and tips
        instructions_window = tk.Toplevel(self.root)
        instructions_window.title("Instructions & Tips")
        instructions_window.geometry("700x600")
        instructions_window.transient(self.root)
        instructions_window.grab_set()
        
        # Main frame
        main_frame = ttk.Frame(instructions_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(main_frame, text="Instructions & Tips", font=('Arial', 16, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Instructions text area
        instructions_frame = ttk.LabelFrame(main_frame, text="How to Use")
        instructions_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        instructions_text = scrolledtext.ScrolledText(instructions_frame, wrap=tk.WORD, font=('Arial', 10))
        instructions_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Comprehensive instructions
        instructions_content = """🚀 AI Code Editor - Complete Guide

📁 FILE MANAGEMENT:
• Select a folder using "Select Folder" button
• Click on files in the left panel to open them
• Use Save button to save changes
• Use History button to view file versions and revert changes

✏️ CODE EDITING:
• Type your request in the "AI Prompt" area
• Press Enter or click "Edit Code" to submit
• AI will modify your code based on your request
• Prompt input automatically clears after successful editing
• Use Shift+Enter for multi-line prompts

💬 AI CHAT:
• Switch to "AI Chat" tab for conversations
• Type your message and press Enter to send
• Check "📎 Include file context" to reference current file
• Chat remembers conversation history for context
• Use Shift+Enter for multi-line messages

⚙️ SETTINGS & CONFIGURATION:
• Click "⚙️ Settings" to configure AI parameters:
  - Temperature: Controls randomness (0.0=focused, 2.0=creative)
  - Max Tokens: Token limits for responses
  - Max Completion Tokens: For GPT-5 models
  - Conversation Memory: Number of messages to keep for context
• Model changes apply immediately (no save needed)
• API key changes apply on focus out
• Click "Save Config" to persist settings to JSON

🐛 DEBUG CONSOLE:
• Switch to "🐛 Debug Console" tab
• Monitor all API calls, requests, and system events
• View response times, token usage, and errors
• Export logs or copy to clipboard for analysis
• Color-coded logs for different event types

💰 TOKEN USAGE TRACKING:
• Real-time token usage in status bar
• Click "💰 Token Usage" button for detailed statistics
• Right-click status bar for quick access menu
• Cost estimates based on current model
• Session duration and tokens per minute
• Reset statistics for new projects

📚 FILE HISTORY:
• Every edit, save, and AI change is tracked
• Access via "History" button in editor toolbar
• Revert to any previous version or original
• Automatic version management (keeps last 20)

⌨️ KEYBOARD SHORTCUTS:
• Enter: Send message/edit code
• Shift+Enter: Add new line
• Ctrl+S: Save file (in code editor)

💡 PRO TIPS:
• For code editing: Use lower temperature (0.0-0.5) for precise changes
• For creative tasks: Use higher temperature (1.0-2.0) for brainstorming
• File context in chat: Only include when needed to save tokens
• Conversation history: AI remembers previous interactions for context
• Model selection: Different models have different capabilities and costs

🔧 TROUBLESHOOTING:
• If API calls fail: Check your API key and model settings
• If file context isn't working: Ensure file is selected and checkbox is checked
• If history isn't showing: Make sure you've made some changes to the file
• For token issues: Use the debug console to monitor usage

📊 COST OPTIMIZATION:
• Uncheck "Include file context" for general questions
• Large files (>10k chars) use significant tokens when included
• Use appropriate token limits for your needs
• Adjust conversation memory limit in Settings (lower = fewer tokens)
• Monitor usage in debug console
• Clear conversation history when starting new topics
• Consider file size when choosing to include context
• Check "💰 Token Usage" button for real-time cost tracking"""
        
        instructions_text.insert(1.0, instructions_content)
        instructions_text.config(state=tk.DISABLED)  # Make read-only
        
        # Close button
        ttk.Button(main_frame, text="Close", command=instructions_window.destroy).pack()
    
    def setup_ui(self):
        # Setup the user interface
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Top control panel
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # API Key entry
        ttk.Label(control_frame, text="OpenAI API Key:").pack(side=tk.LEFT)
        self.api_key_var = tk.StringVar(value=self.api_key)
        api_key_entry = ttk.Entry(control_frame, textvariable=self.api_key_var, width=50, show="*")
        api_key_entry.pack(side=tk.LEFT, padx=(5, 10))
        api_key_entry.bind('<FocusOut>', self.on_api_key_change)
        
        # Model selection
        ttk.Label(control_frame, text="Model:").pack(side=tk.LEFT)
        self.model_var = tk.StringVar(value=self.model)
        model_combo = ttk.Combobox(control_frame, textvariable=self.model_var, 
                                  values=['gpt-5', 'gpt-4.1', 'gpt-4.1-mini', 'gpt-4.1-nano', 
                                         'o3-pro', 'o3-mini', 'o3-mini-high', 'gpt-4', 'gpt-3.5-turbo'], width=15)
        model_combo.pack(side=tk.LEFT, padx=(5, 10))
        model_combo.bind('<<ComboboxSelected>>', self.on_model_change)
        
        # Settings button
        ttk.Button(control_frame, text="⚙️ Settings", 
                  command=self.show_settings_panel).pack(side=tk.LEFT, padx=(0, 10))
        
        # Instructions button
        ttk.Button(control_frame, text="📖 Instructions", 
                  command=self.show_instructions).pack(side=tk.LEFT, padx=(0, 10))
        
        # Save config button
        ttk.Button(control_frame, text="Save Config", 
                  command=self.save_config).pack(side=tk.LEFT, padx=(0, 10))
        
        # Folder selection
        ttk.Button(control_frame, text="Select Folder", 
                  command=self.select_folder).pack(side=tk.LEFT)
        
        # Current folder label
        self.folder_label = ttk.Label(control_frame, text="No folder selected")
        self.folder_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Main content area
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left panel - File browser
        left_panel = ttk.Frame(content_frame, width=300)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False)
        
        ttk.Label(left_panel, text="Files", font=('Arial', 12, 'bold')).pack(pady=(0, 5))
        
        # File tree
        self.file_tree = ttk.Treeview(left_panel, show="tree")
        self.file_tree.pack(fill=tk.BOTH, expand=True)
        self.file_tree.bind('<<TreeviewSelect>>', self.on_file_select)
        
        # Right panel - Tabbed interface for Editor and Chat
        right_panel = ttk.Frame(content_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(right_panel)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Code Editor
        self.editor_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.editor_tab, text="Code Editor")
        
        # Editor area
        editor_frame = ttk.LabelFrame(self.editor_tab, text="Code Editor")
        editor_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Editor toolbar
        editor_toolbar = ttk.Frame(editor_frame)
        editor_toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(editor_toolbar, text="Save", command=self.save_file).pack(side=tk.LEFT)
        ttk.Button(editor_toolbar, text="History", command=self.show_file_history).pack(side=tk.LEFT, padx=(5, 0))
        ttk.Button(editor_toolbar, text="Revert", command=self.revert_file).pack(side=tk.LEFT, padx=(5, 0))
        
        self.file_path_label = ttk.Label(editor_toolbar, text="No file selected")
        self.file_path_label.pack(side=tk.RIGHT)
        
        # Code editor
        self.code_editor = scrolledtext.ScrolledText(editor_frame, wrap=tk.NONE, 
                                                   font=('Consolas', 10))
        self.code_editor.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
        
        # Tab 2: AI Chat
        self.chat_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.chat_tab, text="AI Chat")
        
        # Tab 3: Debug Console
        self.debug_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.debug_tab, text="🐛 Debug Console")
        
        # Chat area
        chat_frame = ttk.LabelFrame(self.chat_tab, text="AI Chat")
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Chat history display
        self.chat_history = scrolledtext.ScrolledText(chat_frame, wrap=tk.WORD, 
                                                    font=('Arial', 10), state=tk.DISABLED)
        self.chat_history.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Chat input area
        chat_input_frame = ttk.Frame(chat_frame)
        chat_input_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        # Attachment checkbox
        self.include_file_context = tk.BooleanVar(value=False)
        attachment_check = ttk.Checkbutton(chat_input_frame, text="📎 Include file context", 
                                         variable=self.include_file_context)
        attachment_check.pack(side=tk.TOP, anchor=tk.W, pady=(0, 5))
        
        # File context indicator
        self.file_context_label = ttk.Label(chat_input_frame, text="", font=('Arial', 8), foreground='gray')
        self.file_context_label.pack(side=tk.TOP, anchor=tk.W, pady=(0, 5))
        
        self.chat_input = scrolledtext.ScrolledText(chat_input_frame, height=3, wrap=tk.WORD)
        self.chat_input.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Chat buttons
        chat_buttons_frame = ttk.Frame(chat_frame)
        chat_buttons_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        ttk.Button(chat_buttons_frame, text="Send", 
                  command=self.send_chat).pack(side=tk.LEFT)
        ttk.Button(chat_buttons_frame, text="Clear Chat", 
                  command=self.clear_chat_history).pack(side=tk.LEFT, padx=(5, 0))
        ttk.Button(chat_buttons_frame, text="Clear History", 
                  command=self.clear_conversation_history).pack(side=tk.LEFT, padx=(5, 0))
        
        # Debug Console area
        debug_frame = ttk.LabelFrame(self.debug_tab, text="Debug Console")
        debug_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Debug controls
        debug_controls = ttk.Frame(debug_frame)
        debug_controls.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(debug_controls, text="Clear Log", 
                  command=self.clear_debug_log).pack(side=tk.LEFT)
        ttk.Button(debug_controls, text="Export Log", 
                  command=self.export_debug_log).pack(side=tk.LEFT, padx=(5, 0))
        ttk.Button(debug_controls, text="Copy to Clipboard", 
                  command=self.copy_debug_log).pack(side=tk.LEFT, padx=(5, 0))
        
        # Debug log display
        self.debug_log = scrolledtext.ScrolledText(debug_frame, wrap=tk.WORD, 
                                                 font=('Consolas', 9), state=tk.DISABLED)
        self.debug_log.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
        
        # Prompt area (for code editing)
        prompt_frame = ttk.LabelFrame(self.editor_tab, text="AI Prompt")
        prompt_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.prompt_text = scrolledtext.ScrolledText(prompt_frame, height=4, wrap=tk.WORD)
        self.prompt_text.pack(fill=tk.X, padx=5, pady=5)
        
        prompt_buttons_frame = ttk.Frame(prompt_frame)
        prompt_buttons_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        ttk.Button(prompt_buttons_frame, text="Edit Code", 
                  command=self.edit_code).pack(side=tk.LEFT)
        ttk.Button(prompt_buttons_frame, text="Clear", 
                  command=lambda: self.prompt_text.delete(1.0, tk.END)).pack(side=tk.LEFT, padx=(5, 0))
        
        # Status bar
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))
        
        # Status label
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(status_frame, textvariable=self.status_var, 
                              relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Bind right-click to status bar for context menu
        status_bar.bind('<Button-3>', self.show_status_context_menu)
        
        # Token usage button
        token_button = ttk.Button(status_frame, text="💰 Token Usage", 
                                 command=self.show_token_usage_details, width=15)
        token_button.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Bind events
        self.prompt_text.bind('<Return>', self.on_edit_enter)
        self.prompt_text.bind('<Shift-Return>', self.on_edit_shift_enter)
        self.chat_input.bind('<Return>', self.on_chat_enter)
        self.chat_input.bind('<Shift-Return>', self.on_chat_shift_enter)
        self.code_editor.bind('<Control-s>', lambda e: self.save_file())
    
    def update_token_usage(self, tokens_used, model_name):
        # Update token usage statistics
        self.total_tokens_used += tokens_used
        self.total_requests += 1
        
        # Log token usage
        self.add_debug_log(f"Token usage: {tokens_used} tokens (Total: {self.total_tokens_used})", "INFO")
        
        # Update status bar with token info
        self.update_token_status()
    
    def calculate_estimated_cost(self):
        # Calculate estimated cost based on current model and token usage
        # Approximate costs per 1K tokens (as of 2024)
        model_costs = {
            'gpt-4': 0.03,      # $0.03 per 1K input, $0.06 per 1K output
            'gpt-4.1': 0.01,    # $0.01 per 1K input, $0.03 per 1K output
            'gpt-4.1-mini': 0.00015,  # $0.00015 per 1K input, $0.0006 per 1K output
            'gpt-4.1-nano': 0.0001,   # $0.0001 per 1K input, $0.0004 per 1K output
            'gpt-5': 0.005,     # $0.005 per 1K input, $0.015 per 1K output
            'o3-pro': 0.015,    # $0.015 per 1K input, $0.06 per 1K output
            'o3-mini': 0.0002,  # $0.0002 per 1K input, $0.0008 per 1K output
            'o3-mini-high': 0.0003,  # $0.0003 per 1K input, $0.0012 per 1K output
            'gpt-3.5-turbo': 0.0005  # $0.0005 per 1K input, $0.0015 per 1K output
        }
        
        current_model = self.model_var.get() if hasattr(self, 'model_var') else self.model
        
        # Get cost for current model (default to gpt-4 if unknown)
        cost_per_1k = model_costs.get(current_model, 0.03)
        
        # Calculate estimated cost (assuming 50/50 input/output split)
        estimated_cost = (self.total_tokens_used / 1000) * cost_per_1k
        
        return estimated_cost, cost_per_1k
    
    def update_token_status(self):
        # Update the status bar with token usage information
        if self.total_tokens_used > 0:
            estimated_cost, cost_per_1k = self.calculate_estimated_cost()
            
            # Format the status with token info
            status_text = f"Tokens: {self.total_tokens_used:,} | Requests: {self.total_requests} | Est. Cost: ${estimated_cost:.4f}"
            self.status_var.set(status_text)
        else:
            self.status_var.set("Ready")
    
    def reset_token_usage(self):
        # Reset token usage statistics for new session
        self.total_tokens_used = 0
        self.total_requests = 0
        self.session_start_time = datetime.datetime.now()
        self.add_debug_log("Token usage reset", "SYSTEM")
        self.update_token_status()
    
    def show_token_usage_details(self):
        # Show detailed token usage information
        if self.total_tokens_used == 0:
            messagebox.showinfo("Token Usage", "No tokens used yet in this session.")
            return
        
        estimated_cost, cost_per_1k = self.calculate_estimated_cost()
        session_duration = datetime.datetime.now() - self.session_start_time
        
        # Calculate tokens per minute
        minutes_elapsed = session_duration.total_seconds() / 60
        tokens_per_minute = self.total_tokens_used / minutes_elapsed if minutes_elapsed > 0 else 0
        
        details = f"""Token Usage Statistics:

📊 Session Summary:
• Total Tokens Used: {self.total_tokens_used:,}
• Total Requests: {self.total_requests:,}
• Session Duration: {session_duration.total_seconds()/60:.1f} minutes
• Tokens per Minute: {tokens_per_minute:.1f}

💰 Cost Information:
• Current Model: {self.model_var.get() if hasattr(self, 'model_var') else self.model}
• Cost per 1K Tokens: ${cost_per_1k:.4f}
• Estimated Total Cost: ${estimated_cost:.4f}

💡 Tips:
• Lower conversation memory = fewer tokens
• Uncheck file context for general questions
• Monitor usage in Debug Console
• Reset stats for new projects"""
        
        # Create details window
        details_window = tk.Toplevel(self.root)
        details_window.title("Token Usage Details")
        details_window.geometry("500x400")
        details_window.transient(self.root)
        details_window.grab_set()
        
        # Main frame
        main_frame = ttk.Frame(details_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(main_frame, text="Token Usage Statistics", font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Details text
        details_text = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, font=('Arial', 10))
        details_text.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        details_text.insert(1.0, details)
        details_text.config(state=tk.DISABLED)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Reset Stats", 
                  command=self.reset_token_usage).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Close", 
                  command=details_window.destroy).pack(side=tk.LEFT)
    
    def add_debug_log(self, message, level="INFO"):
        # Add a message to the debug console
        
        timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        # Color coding for different log levels
        level_colors = {
            "INFO": "black",
            "API": "blue",
            "REQUEST": "green", 
            "RESPONSE": "purple",
            "ERROR": "red",
            "WARNING": "orange",
            "SYSTEM": "gray"
        }
        
        color = level_colors.get(level, "black")
        formatted_message = f"[{timestamp}] {level}: {message}\n"
        
        # Update debug log
        self.debug_log.config(state=tk.NORMAL)
        
        # Insert with color tag
        tag_name = f"level_{level.lower()}"
        self.debug_log.insert(tk.END, formatted_message, tag_name)
        
        # Configure tag color
        self.debug_log.tag_config(tag_name, foreground=color)
        
        # Scroll to bottom
        self.debug_log.see(tk.END)
        self.debug_log.config(state=tk.DISABLED)
    
    def log_api_request(self, model, temperature, max_tokens, message_count, prompt_length):
        # Log API request details
        self.add_debug_log(f"API Request - Model: {model}, Temp: {temperature}, Max Tokens: {max_tokens}", "API")
        self.add_debug_log(f"Request Details - Messages: {message_count}, Prompt Length: {prompt_length} chars", "REQUEST")
    
    def log_api_response(self, response_time, token_usage, model_used):
        # Log API response details
        self.add_debug_log(f"API Response - Time: {response_time:.2f}s, Tokens: {token_usage}, Model: {model_used}", "RESPONSE")
    
    def log_error(self, error_message, context=""):
        # Log error messages
        if context:
            self.add_debug_log(f"ERROR: {error_message} | Context: {context}", "ERROR")
        else:
            self.add_debug_log(f"ERROR: {error_message}", "ERROR")
    
    def clear_debug_log(self):
        # Clear the debug console
        self.debug_log.config(state=tk.NORMAL)
        self.debug_log.delete(1.0, tk.END)
        self.debug_log.config(state=tk.DISABLED)
        self.add_debug_log("Debug log cleared", "SYSTEM")
    
    def export_debug_log(self):
        # Export debug log to file
        try:
            filename = f"debug_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.debug_log.get(1.0, tk.END))
            messagebox.showinfo("Success", f"Debug log exported to {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export debug log: {str(e)}")
    
    def copy_debug_log(self):
        # Copy debug log to clipboard
        try:
            log_content = self.debug_log.get(1.0, tk.END)
            self.root.clipboard_clear()
            self.root.clipboard_append(log_content)
            self.add_debug_log("Debug log copied to clipboard", "SYSTEM")
        except Exception as e:
            self.log_error(f"Failed to copy to clipboard: {str(e)}")
    
    def clear_file_context_indicator(self):
        # Clear the file context indicator in chat area
        if hasattr(self, 'file_context_label'):
            self.file_context_label.config(text="")
    
    def select_folder(self):
        # Select a folder to work with
        folder = filedialog.askdirectory()
        if folder:
            self.current_folder = folder
            self.folder_label.config(text=f"Folder: {os.path.basename(folder)}")
            self.refresh_file_tree()
            self.status_var.set(f"Selected folder: {folder}")
            self.clear_file_context_indicator() # Clear indicator when folder changes
    
    def clear_current_file(self):
        # Clear the current file and update indicators
        self.current_file = None
        self.code_editor.delete(1.0, tk.END)
        self.file_path_label.config(text="No file selected")
        self.clear_file_context_indicator()
        self.status_var.set("No file selected")
    
    def refresh_file_tree(self):
        # Refresh the file tree with current folder contents
        if not self.current_folder:
            return
        
        # Clear current file if it's not in the new folder
        if self.current_file and not self.current_file.startswith(self.current_folder):
            self.clear_current_file()
        
        # Clear existing items
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        
        # Add files recursively
        self.add_files_to_tree("", self.current_folder)
    
    def add_files_to_tree(self, parent, path):
        # Recursively add files to the tree
        try:
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                if os.path.isfile(item_path):
                    # Only show common code files
                    if item.lower().endswith(('.py', '.js', '.ts', '.html', '.css', '.java', '.cpp', '.c', '.h', '.json', '.xml', '.md', '.txt', '.ino')):
                        item_id = self.file_tree.insert(parent, 'end', text=item, values=(item_path,))
                elif os.path.isdir(item_path):
                    # Skip common directories
                    if item not in ['.git', '__pycache__', 'node_modules', '.vscode', '.idea']:
                        folder_id = self.file_tree.insert(parent, 'end', text=f"📁 {item}", values=(item_path,))
                        self.add_files_to_tree(folder_id, item_path)
        except PermissionError:
            pass
    
    def on_file_select(self, event):
        # Handle file selection in the tree
        selection = self.file_tree.selection()
        if selection:
            item = self.file_tree.item(selection[0])
            file_path = item['values'][0]
            if file_path and os.path.isfile(file_path):
                self.open_file(file_path)
    
    def open_file(self, file_path):
        # Open a file in the editor
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.current_file = file_path
            self.code_editor.delete(1.0, tk.END)
            self.code_editor.insert(1.0, content)
            self.file_path_label.config(text=f"File: {os.path.basename(file_path)}")
            self.status_var.set(f"Opened: {file_path}")
            
            # Add initial version to file history
            self.add_file_version(file_path, content, "Original file")
            
            # Clear conversation history when opening a new file
            self.conversation_history.clear()
            self.status_var.set(f"Opened: {file_path} (conversation context cleared)")
            
            # Update file context indicator in chat area
            if hasattr(self, 'file_context_label'):
                self.file_context_label.config(text=f"📁 {os.path.basename(file_path)} available for context")
            
            # Log file operation
            self.add_debug_log(f"File opened: {os.path.basename(file_path)} ({len(content)} chars)", "SYSTEM")
            
            # Warn about large files for token usage
            if len(content) > 10000:
                self.add_debug_log(f"⚠️ Large file detected: {len(content)} chars - this may use significant tokens when included in chat context", "WARNING")
            elif len(content) > 5000:
                self.add_debug_log(f"📊 Medium file: {len(content)} chars - consider token usage when including in chat context", "INFO")
            
        except Exception as e:
            error_msg = f"Could not open file: {str(e)}"
            self.log_error(error_msg, f"File: {file_path}")
            messagebox.showerror("Error", error_msg)
    
    def edit_code(self):
        # Edit code using AI prompt
        if not self.api_key:
            messagebox.showerror("Error", "Please enter your OpenAI API key")
            return
        
        prompt = self.prompt_text.get(1.0, tk.END).strip()
        if not prompt:
            messagebox.showwarning("Warning", "Please enter a prompt")
            return
        
        # Code editing mode - file required
        if not self.current_file:
            messagebox.showwarning("Warning", "Please select a file first")
            return
        
        current_content = self.code_editor.get(1.0, tk.END)
        file_path = self.current_file
        
        # Show status with context info
        context_info = f" (with {len(self.conversation_history)//2} previous interactions)" if self.conversation_history else ""
        self.status_var.set(f"AI is editing your code...{context_info}")
        
        # Run AI interaction in background
        threading.Thread(target=self.run_ai_edit, 
                       args=(prompt, current_content, file_path), 
                       daemon=True).start()
    
    def run_ai_edit(self, prompt, current_content, file_path):
        # Run AI editing in background thread
        start_time = datetime.datetime.now()
        
        try:
            # Log the start of the request
            self.add_debug_log(f"Starting AI edit for file: {os.path.basename(file_path)}", "INFO")
            self.add_debug_log(f"Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}", "REQUEST")
            
            # Code editing mode - edit the code
            system_message = f"""You are an expert code editor. You will receive a file path and current content, along with a user prompt describing what changes to make.

File: {file_path}

Please provide ONLY the edited code content. Do not include explanations, markdown formatting, or any other text - just the pure code that should replace the current content.

If the user wants to add new functionality, modify existing code, fix bugs, or make any other changes, implement them directly in the code you return.

IMPORTANT: Always work with the CURRENT content that is provided. Do not start from scratch unless explicitly requested. Make incremental changes based on the existing code."""

            # Build messages array with conversation history
            messages = [{"role": "system", "content": system_message}]
            
            # Add conversation history if this isn't the first prompt
            if self.conversation_history:
                messages.extend(self.conversation_history)
            
            # Add current file content and user prompt
            messages.append({
                "role": "user", 
                "content": f"Current file content:\n{current_content}\n\nUser request: {prompt}"
            })
            
            # Log API request details
            model_name = self.model_var.get()
            prompt_length = len(f"Current file content:\n{current_content}\n\nUser request: {prompt}")
            
            # Warn about large files for code editing
            if len(current_content) > 15000:
                self.add_debug_log(f"⚠️ Large file for editing: {len(current_content)} chars - this will use significant tokens", "WARNING")
            elif len(current_content) > 8000:
                self.add_debug_log(f"📊 Medium file for editing: {len(current_content)} chars - moderate token usage expected", "INFO")
            
            self.log_api_request(
                model=model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens if not model_name.startswith('gpt-5') else self.max_completion_tokens,
                message_count=len(messages),
                prompt_length=prompt_length
            )
            
            # Build API parameters based on model and user settings
            api_params = {
                "model": model_name,
                "messages": messages,
                "temperature": self.temperature
            }
            
            # GPT-5 uses max_completion_tokens, others use max_tokens
            if model_name.startswith('gpt-5'):
                api_params["max_completion_tokens"] = self.max_completion_tokens
            else:
                api_params["max_tokens"] = self.max_tokens
            
            # Log the actual API call
            self.add_debug_log(f"Making API call with parameters: {api_params}", "API")
            
            # Make the API call
            response = self.client.chat.completions.create(**api_params)
            
            # Calculate response time
            end_time = datetime.datetime.now()
            response_time = (end_time - start_time).total_seconds()
            
            # Get the response
            ai_response = response.choices[0].message.content.strip()
            
            # Log API response details
            token_usage = response.usage.total_tokens if hasattr(response, 'usage') and response.usage else "Unknown"
            self.log_api_response(response_time, token_usage, model_name)
            
            # Track token usage if available
            if hasattr(response, 'usage') and response.usage and hasattr(response.usage, 'total_tokens'):
                self.update_token_usage(response.usage.total_tokens, model_name)
            
            # Log response summary
            self.add_debug_log(f"AI Response Length: {len(ai_response)} characters", "RESPONSE")
            
            # Add to conversation history for context
            self.conversation_history.append({
                "role": "user", 
                "content": f"Current file content:\n{current_content}\n\nUser request: {prompt}"
            })
            self.conversation_history.append({
                "role": "assistant", 
                "content": ai_response
            })
            
            # Keep only last N messages to prevent context from getting too long
            if len(self.conversation_history) > self.conversation_memory_limit:
                old_count = len(self.conversation_history)
                self.conversation_history = self.conversation_history[-self.conversation_memory_limit:]
                self.add_debug_log(f"Conversation history trimmed: {old_count} → {self.conversation_memory_limit} messages", "INFO")
            
            # Code editing mode - replace code content
            # Remove markdown code blocks if present
            edited_content = ai_response
            if edited_content.startswith('```'):
                lines = edited_content.split('\n')
                if len(lines) > 2:
                    edited_content = '\n'.join(lines[1:-1])
                    self.add_debug_log("Removed markdown code blocks from response", "INFO")
            
            # Queue the result for UI update
            self.message_queue.put(('edit_complete', edited_content))
            
        except Exception as e:
            # Calculate response time for errors
            end_time = datetime.datetime.now()
            response_time = (end_time - start_time).total_seconds()
            
            # Provide better error information for model-specific issues
            error_msg = str(e)
            if "max_tokens" in error_msg and "gpt-5" in error_msg.lower():
                error_msg = "GPT-5 model error: This model uses 'max_completion_tokens' instead of 'max_tokens'. Please try again."
            elif "unsupported parameter" in error_msg:
                error_msg = f"Model parameter error: {error_msg}. This may be a model-specific issue."
            elif "temperature" in error_msg.lower():
                error_msg = f"Temperature error: {error_msg}. Try adjusting the temperature in Settings."
            
            # Log the error
            self.log_error(error_msg, f"Response time: {response_time:.2f}s")
            
            self.message_queue.put(('edit_error', error_msg))
    
    def check_queue(self):
        # Check for messages from background threads
        try:
            while True:
                msg_type, data = self.message_queue.get_nowait()
                
                if msg_type == 'edit_complete':
                    # Add current version to history before updating
                    if self.current_file:
                        current_content = self.code_editor.get(1.0, tk.END)
                        self.add_file_version(self.current_file, current_content, "Before AI edit")
                    
                    self.code_editor.delete(1.0, tk.END)
                    self.code_editor.insert(1.0, data)
                    
                    # Add new AI-edited version to history
                    if self.current_file:
                        self.add_file_version(self.current_file, data, "AI edit")
                    
                    # Clear the prompt input after successful editing
                    self.prompt_text.delete(1.0, tk.END)
                    self.status_var.set("AI editing completed")
                    messagebox.showinfo("Success", "Code has been edited by AI!")
                
                elif msg_type == 'chat_complete':
                    # Add AI response to chat history
                    self.add_chat_message("AI", data, "assistant")
                    self.status_var.set("AI chat completed")
                
                elif msg_type == 'edit_error':
                    self.status_var.set(f"Error: {data}")
                    messagebox.showerror("AI Error", f"Failed to edit code: {data}")
                
                elif msg_type == 'chat_error':
                    self.status_var.set(f"Chat Error: {data}")
                    messagebox.showerror("AI Chat Error", f"Failed to get AI response: {data}")
                
        except queue.Empty:
            pass
        
        # Schedule next check
        self.root.after(100, self.check_queue)
    
    def save_file(self):
        # Save the current file
        if not self.current_file:
            messagebox.showwarning("Warning", "No file to save")
            return
        
        try:
            content = self.code_editor.get(1.0, tk.END)
            with open(self.current_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Add saved version to history
            self.add_file_version(self.current_file, content, "Manual save")
            self.status_var.set(f"Saved: {self.current_file}")
            
            # Log save operation
            self.add_debug_log(f"File saved: {os.path.basename(self.current_file)} ({len(content)} chars)", "SYSTEM")
            
        except Exception as e:
            error_msg = f"Could not save file: {str(e)}"
            self.log_error(error_msg, f"File: {self.current_file}")
            messagebox.showerror("Error", error_msg)
    
    def revert_file(self):
        # Revert file to original content
        if not self.current_file:
            messagebox.showwarning("Warning", "No file to reset")
            return
        
        # Show file history dialog for reverting
        self.show_file_history()
    
    def clear_conversation_history(self):
        # Clear the AI conversation history to start fresh
        self.conversation_history.clear()
        self.status_var.set("Conversation history cleared - starting fresh context")
    
    def send_chat(self):
        # Send a chat message to the AI
        if not self.api_key:
            messagebox.showerror("Error", "Please enter your OpenAI API key")
            return
        
        message = self.chat_input.get(1.0, tk.END).strip()
        if not message:
            return
        
        # Add user message to chat history
        self.add_chat_message("You", message, "user")
        
        # Show file context if available and checkbox is checked
        if self.current_file and self.include_file_context.get():
            file_info = f"📁 {os.path.basename(self.current_file)}"
            self.add_chat_message("System", file_info, "system")
        
        # Clear input
        self.chat_input.delete(1.0, tk.END)
        
        # Switch to chat tab if not already there
        self.notebook.select(self.chat_tab)
        
        # Show status
        self.status_var.set("AI is thinking...")
        
        # Run AI chat in background
        threading.Thread(target=self.run_ai_chat, args=(message,), daemon=True).start()
    
    def add_chat_message(self, sender, message, role):
        # Add a message to the chat history display
        self.chat_history.config(state=tk.NORMAL)
        
        # Add timestamp and sender
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M")
        
        # Different styling based on role
        if role == "system":
            self.chat_history.insert(tk.END, f"[{timestamp}] {sender}: ", "system_sender")
            self.chat_history.insert(tk.END, f"{message}\n\n", "system_message")
        else:
            self.chat_history.insert(tk.END, f"[{timestamp}] {sender}: ", "sender")
            self.chat_history.insert(tk.END, f"{message}\n\n", "message")
        
        # Configure tags for styling
        self.chat_history.tag_config("sender", font=('Arial', 10, 'bold'))
        self.chat_history.tag_config("message", font=('Arial', 10))
        self.chat_history.tag_config("system_sender", font=('Arial', 10, 'bold'), foreground='blue')
        self.chat_history.tag_config("system_message", font=('Arial', 10), foreground='blue')
        
        # Scroll to bottom
        self.chat_history.see(tk.END)
        self.chat_history.config(state=tk.DISABLED)
    
    def run_ai_chat(self, message):
        # Run AI chat in background thread
        start_time = datetime.datetime.now()
        
        try:
            # Log the start of the chat request
            self.add_debug_log(f"Starting AI chat request", "INFO")
            self.add_debug_log(f"Message: {message[:100]}{'...' if len(message) > 100 else ''}", "REQUEST")
            
            # Get file context if available and checkbox is checked
            file_context = ""
            if self.include_file_context.get() and self.current_file:
                file_context = self.get_file_context_for_chat()
                self.add_debug_log(f"File context included: {os.path.basename(self.current_file)}", "INFO")
                
                # Warn about large file context
                if len(file_context) > 15000:
                    self.add_debug_log(f"⚠️ Large file context included: {len(file_context)} chars - this will use significant tokens", "WARNING")
                elif len(file_context) > 8000:
                    self.add_debug_log(f"📊 Medium file context: {len(file_context)} chars - moderate token usage expected", "INFO")
            else:
                self.add_debug_log("No file context included", "INFO")
            
            # Build system message for chat
            if file_context:
                system_message = f"""You are an expert programming assistant and code reviewer. You will receive user messages asking questions or seeking advice.

Current File Context:
{file_context}

Please provide helpful, informative responses about programming concepts, code, or any questions the user asks. You can:
- Explain how the current code works
- Suggest improvements to the code
- Answer programming questions
- Provide code examples
- Give best practice advice
- Help debug issues

You can reference and discuss the attached file content. Be conversational, helpful, and provide practical guidance."""
            else:
                system_message = """You are an expert programming assistant and code reviewer. You will receive user messages asking questions or seeking advice.

Please provide helpful, informative responses about programming concepts, code, or any questions the user asks. You can:
- Answer programming questions
- Provide code examples
- Give best practice advice
- Help debug issues
- Explain programming concepts

Be conversational, helpful, and provide practical guidance."""
            
            # Build messages array with conversation history
            messages = [{"role": "system", "content": system_message}]
            
            # Add conversation history if this isn't the first message
            if self.conversation_history:
                messages.extend(self.conversation_history)
            
            # Add current user message
            messages.append({"role": "user", "content": message})
            
            # Log API request details
            model_name = self.model_var.get()
            prompt_length = len(system_message) + len(message)
            
            self.log_api_request(
                model=model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens if not model_name.startswith('gpt-5') else self.max_completion_tokens,
                message_count=len(messages),
                prompt_length=prompt_length
            )
            
            # Make API call with correct parameters for different models
            model_name = self.model_var.get()
            
            # Build API parameters based on model and user settings
            api_params = {
                "model": model_name,
                "messages": messages,
                "temperature": self.temperature
            }
            
            # GPT-5 uses max_completion_tokens, others use max_tokens
            if model_name.startswith('gpt-5'):
                api_params["max_completion_tokens"] = self.max_completion_tokens
            else:
                api_params["max_tokens"] = self.max_tokens
            
            # Log the actual API call
            self.add_debug_log(f"Making chat API call with parameters: {api_params}", "API")
            
            # Make the API call
            response = self.client.chat.completions.create(**api_params)
            
            # Calculate response time
            end_time = datetime.datetime.now()
            response_time = (end_time - start_time).total_seconds()
            
            # Get the response
            ai_response = response.choices[0].message.content.strip()
            
            # Log API response details
            token_usage = response.usage.total_tokens if hasattr(response, 'usage') and response.usage else "Unknown"
            self.log_api_response(response_time, token_usage, model_name)
            
            # Track token usage if available
            if hasattr(response, 'usage') and response.usage and hasattr(response.usage, 'total_tokens'):
                self.update_token_usage(response.usage.total_tokens, model_name)
            
            # Log response summary
            self.add_debug_log(f"Chat Response Length: {len(ai_response)} characters", "RESPONSE")
            
            # Add to conversation history for context
            self.conversation_history.append({"role": "user", "content": message})
            self.conversation_history.append({"role": "assistant", "content": ai_response})
            
            # Keep only last N messages to prevent context from getting too long
            if len(self.conversation_history) > self.conversation_memory_limit:
                old_count = len(self.conversation_history)
                self.conversation_history = self.conversation_history[-self.conversation_memory_limit:]
                self.add_debug_log(f"Conversation history trimmed: {old_count} → {self.conversation_memory_limit} messages", "INFO")
            
            # Queue the result for UI update
            self.message_queue.put(('chat_complete', ai_response))
            
        except Exception as e:
            # Calculate response time for errors
            end_time = datetime.datetime.now()
            response_time = (end_time - start_time).total_seconds()
            
            # Provide better error information for model-specific issues
            error_msg = str(e)
            if "max_tokens" in error_msg and "gpt-5" in error_msg.lower():
                error_msg = "GPT-5 model error: This model uses 'max_completion_tokens' instead of 'max_tokens'. Please try again."
            elif "unsupported parameter" in error_msg:
                error_msg = f"Model parameter error: {error_msg}. This may be a model-specific issue."
            elif "temperature" in error_msg.lower():
                error_msg = f"Temperature error: {error_msg}. Try adjusting the temperature in Settings."
            
            # Log the error
            self.log_error(error_msg, f"Chat response time: {response_time:.2f}s")
            
            self.message_queue.put(('chat_error', error_msg))
    
    def clear_chat_history(self):
        # Clear the chat display (but keep conversation history for context)
        self.chat_history.config(state=tk.NORMAL)
        self.chat_history.delete(1.0, tk.END)
        self.chat_history.config(state=tk.DISABLED)
        self.status_var.set("Chat display cleared")

    def get_current_file_content(self):
        # Get the content of the currently selected file for AI context
        if self.current_file and os.path.exists(self.current_file):
            try:
                with open(self.current_file, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                return f"Error reading file: {str(e)}"
        return None
    
    def get_file_context_for_chat(self):
        # Get file context information for chat
        if not self.current_file:
            return "No file selected"
        
        file_name = os.path.basename(self.current_file)
        file_content = self.get_current_file_content()
        
        if file_content is None:
            return f"File: {file_name} (could not read content)"
        
        return f"File: {file_name}\n\nContent:\n{file_content}"

    def on_model_change(self, event):
        # Callback for model selection changes
        selected_model = self.model_var.get()
        self.model = selected_model
        self.client = None # Clear client if model changes
        if self.api_key:
            self.client = openai.OpenAI(api_key=self.api_key)
        
        # Log the model change
        self.add_debug_log(f"Model changed to: {selected_model}", "SYSTEM")
        messagebox.showinfo("Model Changed", f"Model changed to: {selected_model}")

    def on_api_key_change(self, event):
        # Callback for API key changes
        new_api_key = self.api_key_var.get()
        if new_api_key:
            self.api_key = new_api_key
            self.client = openai.OpenAI(api_key=self.api_key)
            
            # Log the API key change (masked for security)
            masked_key = new_api_key[:8] + "..." + new_api_key[-4:] if len(new_api_key) > 12 else "***"
            self.add_debug_log(f"API key updated: {masked_key}", "SYSTEM")
            messagebox.showinfo("API Key Changed", "API key updated successfully!")
        else:
            self.api_key = ""
            self.client = None
            self.add_debug_log("API key cleared", "SYSTEM")
            messagebox.showwarning("API Key Error", "API key cannot be empty. Please enter a valid key.")

    def add_file_version(self, file_path, content, description="Manual edit"):
        # Add a new version of a file to its history
        
        if file_path not in self.file_history:
            self.file_history[file_path] = []
            self.current_history_index[file_path] = -1
        
        # Add new version
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.file_history[file_path].append((content, timestamp, description))
        
        # Update current index
        self.current_history_index[file_path] = len(self.file_history[file_path]) - 1
        
        # Keep only last 20 versions to prevent memory issues
        if len(self.file_history[file_path]) > 20:
            self.file_history[file_path] = self.file_history[file_path][-20:]
            self.current_history_index[file_path] = len(self.file_history[file_path]) - 1
        
        # Log version addition
        self.add_debug_log(f"File version added: {os.path.basename(file_path)} - {description} ({len(content)} chars)", "SYSTEM")
    
    def get_file_history_info(self, file_path):
        # Get information about file history for display
        if file_path not in self.file_history:
            return []
        
        history_info = []
        for i, (content, timestamp, description) in enumerate(self.file_history[file_path]):
            status = "🔄 Current" if i == self.current_history_index[file_path] else "📝 Version"
            history_info.append(f"{status} {i+1}: {timestamp} - {description}")
        
        return history_info
    
    def revert_to_version(self, file_path, version_index):
        # Revert file to a specific version
        if file_path not in self.file_history or version_index >= len(self.file_history[file_path]):
            return False
        
        # Get the version content
        content, timestamp, description = self.file_history[file_path][version_index]
        
        # Update the editor
        self.code_editor.delete(1.0, tk.END)
        self.code_editor.insert(1.0, content)
        
        # Update current history index
        self.current_history_index[file_path] = version_index
        
        # Update status
        self.status_var.set(f"Reverted to version {version_index + 1}: {description}")
        
        return True
    
    def show_file_history(self):
        # Show file history dialog for reverting
        if not self.current_file:
            messagebox.showwarning("Warning", "No file selected")
            return
        
        file_path = self.current_file
        if file_path not in self.file_history:
            messagebox.showinfo("Info", "No history available for this file")
            return
        
        # Create history dialog
        history_window = tk.Toplevel(self.root)
        history_window.title(f"File History - {os.path.basename(file_path)}")
        history_window.geometry("600x500")
        history_window.transient(self.root)
        history_window.grab_set()
        
        # Main frame
        main_frame = ttk.Frame(history_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(main_frame, text=f"File History: {os.path.basename(file_path)}", 
                               font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # History listbox
        history_frame = ttk.LabelFrame(main_frame, text="Version History")
        history_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        history_listbox = tk.Listbox(history_frame, font=('Arial', 10))
        history_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Populate history
        history_info = self.get_file_history_info(file_path)
        for i, info in enumerate(history_info):
            history_listbox.insert(tk.END, info)
        
        # Select current version
        current_index = self.current_history_index.get(file_path, -1)
        if current_index >= 0:
            history_listbox.selection_set(current_index)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=20)
        
        def revert_selected():
            selection = history_listbox.curselection()
            if selection:
                version_index = selection[0]
                if self.revert_to_version(file_path, version_index):
                    history_window.destroy()
                    messagebox.showinfo("Success", f"Reverted to version {version_index + 1}")
                else:
                    messagebox.showerror("Error", "Failed to revert to selected version")
            else:
                messagebox.showwarning("Warning", "Please select a version to revert to")
        
        def revert_to_original():
            if self.revert_to_version(file_path, 0):
                history_window.destroy()
                messagebox.showinfo("Success", "Reverted to original version")
            else:
                messagebox.showerror("Error", "Failed to revert to original version")
        
        ttk.Button(button_frame, text="Revert to Selected", 
                  command=revert_selected).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Revert to Original", 
                  command=revert_to_original).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Close", 
                  command=history_window.destroy).pack(side=tk.LEFT)
    
    def on_edit_enter(self, event):
        # Handle Enter key in the edit prompt area
        self.edit_code()
        return "break" # Prevent default newline behavior

    def on_edit_shift_enter(self, event):
        # Handle Shift+Enter key in the edit prompt area
        # Allow Shift+Enter for new lines in the edit prompt area
        return None  # Allow default newline behavior

    def on_chat_enter(self, event):
        # Handle Enter key in the chat input area
        self.send_chat()
        return "break" # Prevent default newline behavior

    def on_chat_shift_enter(self, event):
        # Handle Shift+Enter key in the chat input area
        # Allow Shift+Enter for new lines in the chat input area
        return None  # Allow default newline behavior

    def show_status_context_menu(self, event):
        # Show a context menu for the status bar
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Show Token Usage", command=self.show_token_usage_details)
        menu.add_command(label="Settings", command=self.show_settings_panel)
        menu.add_command(label="Instructions", command=self.show_instructions)
        menu.add_command(label="Select Folder", command=self.select_folder)
        menu.add_command(label="Clear Chat History", command=self.clear_chat_history)
        menu.add_command(label="Clear Conversation History", command=self.clear_conversation_history)
        menu.add_command(label="Clear Debug Log", command=self.clear_debug_log)
        menu.add_command(label="Export Debug Log", command=self.export_debug_log)
        menu.add_command(label="Copy Debug Log", command=self.copy_debug_log)
        menu.add_command(label="Save Config", command=self.save_config)
        menu.add_command(label="Reset Token Usage", command=self.reset_token_usage)
        
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

def main():
    root = tk.Tk()
    app = CodeEditor(root)
    root.mainloop()

if __name__ == "__main__":
    main()
