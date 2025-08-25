import customtkinter as ctk
import threading
import queue
from typing import Callable, Optional
import sys
from io import StringIO

class CTkConsole(ctk.CTkTextbox):
    def __init__(self, master, **kwargs):
        default_kwargs = {
            'font': ctk.CTkFont(family="Consolas", size=12),
            'fg_color': "#1e1e1e",
            'text_color': "#ffffff",
            'corner_radius': 5,
            'wrap': "word",
            'state': "disabled"
        }
        default_kwargs.update(kwargs)
        
        super().__init__(master, **default_kwargs)
        
        self.message_queue = queue.Queue()
        
        # Auto-scroll settings
        self.auto_scroll = True
        self.max_lines = 1000
        
        # Start checking for messages
        self._check_queue()
        
        # Bind scroll events to detect manual scrolling
        self.bind("<Button-1>", self._on_manual_scroll)
        self.bind("<Key>", self._on_manual_scroll)
    
    def print(self, message: str, color: Optional[str] = None, end: str = "\n"):
        full_message = str(message) + end
        self.message_queue.put(("print", full_message, color))
    
    def print_success(self, message: str):
        self.print(f"✓ {message}", color="#00ff00")
    
    def print_error(self, message: str):
        self.print(f"✗ {message}", color="#ff4444")
    
    def print_warning(self, message: str):
        self.print(f"⚠ {message}", color="#ffaa00")
    
    def print_info(self, message: str):
        self.print(f"ℹ {message}", color="#4488ff")
    
    def print_path(self, path: str, prefix: str = ""):
        if prefix:
            self.print(f"{prefix} {path}", color="#88ffaa")
        else:
            self.print(path, color="#88ffaa")
    
    def clear(self):
        """Clear the console"""
        self.message_queue.put(("clear", None, None))
    
    def _check_queue(self):
        """Check message queue and update display"""
        try:
            while not self.message_queue.empty():
                action, message, color = self.message_queue.get_nowait()
                
                if action == "print":
                    self._add_text(message, color)
                elif action == "clear":
                    self._clear_text()
                    
        except queue.Empty:
            pass
        
        # Schedule next check
        self.after(100, self._check_queue)
    
    def _add_text(self, text: str, color: Optional[str] = None):
        """Add text to the console (must be called from main thread)"""
        self.configure(state="normal")
        
        # Insert text with color if specified
        if color:
            # Create a unique tag for this color
            tag_name = f"color_{color.replace('#', '')}"
            self.tag_config(tag_name, foreground=color)
            
            # Insert text with the colored tag
            current_pos = self.index("end-1c")
            self.insert("end", text)
            end_pos = self.index("end-1c")
            self.tag_add(tag_name, current_pos, end_pos)
        else:
            self.insert("end", text)
        
        # Limit lines if needed
        self._limit_lines()
        
        # Auto-scroll to bottom if enabled
        if self.auto_scroll:
            self.see("end")
        
        self.configure(state="disabled")
    
    def _clear_text(self):
        """Clear all text from console"""
        self.configure(state="normal")
        self.delete("1.0", "end")
        self.configure(state="disabled")
    
    def _limit_lines(self):
        """Limit the number of lines in the console"""
        lines = self.get("1.0", "end").split('\n')
        if len(lines) > self.max_lines:
            self.configure(state="normal")
            # Calculate how many lines to remove
            lines_to_remove = len(lines) - self.max_lines
            end_line = f"{lines_to_remove + 1}.0"
            self.delete("1.0", end_line)
            self.configure(state="disabled")
    
    def _on_manual_scroll(self, event):
        """Detect manual scrolling and disable auto-scroll temporarily"""
        # Check if user scrolled up from bottom
        if self.yview()[1] < 1.0:
            self.auto_scroll = False
            # Re-enable auto-scroll after 5 seconds
            self.after(5000, lambda: setattr(self, 'auto_scroll', True))

class OutputRedirector:
    """Redirect stdout/stderr to console widget"""
    
    def __init__(self, console: CTkConsole, original_stream, color: Optional[str] = None):
        self.console = console
        self.original_stream = original_stream
        self.color = color
    
    def write(self, message):
        # Also write to original stream (for debugging)
        self.original_stream.write(message)
        self.original_stream.flush()
        
        # Write to console
        if message.strip():  # Only write non-empty messages
            # Check if message originally had a newline
            has_newline = message.endswith('\n')
            clean_message = message.rstrip()
            self.console.print(clean_message, color=self.color, end="\n" if has_newline else "")
    
    def flush(self):
        self.original_stream.flush()

def redirect_output_to_console(console: CTkConsole):
    """Redirect stdout and stderr to the console widget"""
    # Redirect stdout (normal print) - white text
    sys.stdout = OutputRedirector(console, sys.__stdout__)
    
    # Redirect stderr (error messages) - red text  
    sys.stderr = OutputRedirector(console, sys.__stderr__, color="#ff4444")

def restore_output():
    """Restore original stdout and stderr"""
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__