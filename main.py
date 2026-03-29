#!/usr/bin/env python3
import sys
import os

# Import the core foundational window we just built
# We add this path to sys.path so it works when running from root
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(current_dir, 'ui'))

from ui.main_window import QApplication, CoreFrameworkWindow

class ApplicationEngine:
    """The master execution engine for 4AM. This manages the main application life cycle."""
    def __init__(self):
        # 1. Start the Qt execution environment
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("4AM Application")
        self.app.setOrganizationName("Novel Project")

        # 2. Creative execution: Load the high-fidelity native framework
        self.framework_window = CoreFrameworkWindow()

    def execute(self):
        """Launches the foundational application and enters the event loop."""
        # This will fail creatively and comprehensively if Module 1 architecture isn't loaded.
        self.framework_window.show()
        print("[System] Application framework has launched. Event loop entered.")
        sys.exit(self.app.exec())

if __name__ == "__main__":
    # This is the single, ultimate starting point for 4AM.
    try:
        engine = ApplicationEngine()
        engine.execute()
    except Exception as e:
        print(f"[CRITICAL FAILURE] The application encountered an unexpected core failure and could not boot.\n\nError details: {e}")