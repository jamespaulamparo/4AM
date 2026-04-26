# 4AM

[DOWNLOAD](https://github.com/jamespaulamparo/4AM/releases) | [DOCS](https://github.com/jamespaulamparo/4AM) | [CONTACT](https://github.com/jamespaulamparo)

## Overview

4AM is a high-performance desktop application designed for structured writing and multimedia worldbuilding. It serves as a centralized hub for managing large-scale creative projects by merging the file-management strengths of **Scrivener**, the focus-oriented interface of **iA Writer**, and the non-linear lore connectivity of **Obsidian**.

The application is built using Python and the PySide6 (Qt) framework, providing a native, hardware-accelerated experience on Windows devices.

**Note on Usage:** This application is developed specifically for the creator's personal workflow. While it is functional for general use, external feature requests and broad user support are not a priority.

-----

## Core Functionality

### 1. Unified Folder-Note Architecture
4AM implements a hybrid structure where directories act as individual documents. If a directory contains a Markdown or Canvas file of the same name, the application treats the folder itself as a primary lore entry. This minimizes file-tree clutter while maintaining deep hierarchical organization.

### 2. Immersive Writing Engine (Live Preview)
The editor is designed for maximum creative focus, utilizing a "Live Preview" logic similar to modern Markdown environments.
* **Syntax Concealment:** Markdown symbols (hashes, asterisks, brackets) are visible only on the currently active line. Once the cursor moves away, the syntax is concealed, leaving only the formatted text.
* **Aesthetic Header Gradient:** A custom-mapped color palette (Pink to Green) is applied to H1-H6 headers for rapid visual hierarchy recognition.
* **Locked Viewport Wrapping:** Text wrapping is hardware-locked to the viewport width, ensuring a consistent docs-style experience regardless of window scaling.

### 3. Infinite Multimedia Canvas
The Canvas engine provides a non-linear, infinite spatial interface for visual planning and lore mapping.
* **Unbounded Space:** Supports a massive coordinate system, allowing users to place notes and labels anywhere in a 100,000-pixel void.
* **Minimalist Interface:** All drag-handles and UI indicators are concealed until interaction, providing a clean "Onenote-style" aesthetic.
* **Spatial Anchors:** Drag-and-drop support for images (maps, character portraits) with ratio-locked manual resizing.

### 4. Smart Renaming & Metadata Sync
To maintain vault integrity, 4AM utilizes a custom renaming engine.
* **Synchronized Updates:** Renaming a lore entry automatically renames the associated Ghost-Folder, internal file, and `.meta.json` history files.
* **Metadata Persistence:** High-fidelity data like "Rainbow Pasted Ranges" are preserved during file-system moves.

-----

## Technical Specifications

### Writing & Rendering Engine
* **Hardware Acceleration:** Hardware-accelerated font zooming (Ctrl + Scroll) recalculates header sizes and proportions in real-time.
* **Reading Mode Sync:** High-fidelity Markdown rendering ensures that aesthetic colors and font sizes are consistent between Edit and Reading modes.

### Automated Versioning (Snapshot System)
To prevent data loss, 4AM includes a background version control engine that generates automated local snapshots of all open files every 10 minutes. These are stored in a hidden `.history` directory within the user's vault.

### Vault-Wide Search (The Oracle)
A full-text search engine scans both file titles and internal content across the entire vault, providing a rich-text preview of the surrounding context for each match.

-----

## Changelog

### v1.1.0
**Qol Update**
* **Workspace Optimization:** Removed the central widget void; panes now claim 100% of available screen real estate.
* **Infinite Canvas:** Expanded the spatial engine to support unbounded non-linear worldbuilding.
* **Live Preview Syntax:** Implemented Obsidian-style syntax concealment for immersive writing.
* **Smart Rename Logic:** Added synchronized renaming for Ghost-Folders and associated metadata.
* **Stability Patch:** Resolved Qt recursion loops in the highlighter and dock system to prevent app crashes.

### v1.0.0
**Initial Release**
* Integrated Multi-Pane Split View with persistent state memory.
* Implemented Ghost-Folder hierarchy logic for the sidebar.
* Multimedia Canvas with support for image pasting.
* Automated local snapshots (Versioning system).

-----

## Platform Support

| Platform | Status |
| :--- | :--- |
| Windows 10/11 | Available (Native) |
| MacOS | Not Supported |
| Linux | Not Supported |

-----

## Development Setup

To run the application in a development environment:

1. Clone the repository.
2. Install the required dependencies:
   ```bash
   pip install PySide6 mistune
