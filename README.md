# 4AM

[DOWNLOAD](https://www.google.com/search?q=https://github.com/jamespaulamparo/4AM/releases) | [DOCS](https://github.com/jamespaulamparo/4AM) | [CONTACT](https://www.google.com/search?q=https://github.com/jamespaulamparo)

## Overview

4AM is a high-performance desktop application designed for structured writing and multimedia worldbuilding. It serves as a centralized hub for managing large-scale creative projects by merging the file-management strengths of **Scrivener**, the focus-oriented interface of **iA Writer**, and the non-linear lore connectivity of **Obsidian**.

The application is built using Python and the PySide6 (Qt) framework, providing a native, hardware-accelerated experience on Windows devices.

**Note on Usage:** This application is developed specifically for the creator's personal workflow. While it is functional for general use, external feature requests and broad user support are not a priority.

-----

## Core Functionality

### 1\. Unified Folder-Note Architecture

4AM implements a hybrid structure where directories act as individual documents. If a directory contains a Markdown file of the same name, the application treats the folder itself as a primary lore entry. This minimizes file-tree clutter while maintaining deep hierarchical organization.

### 2\. Dynamic Workspace Management

Utilizing a custom implementation of the Qt Dock System, 4AM supports infinite pane nesting and split-view configurations.

  * **State Persistence:** Pane dimensions and sidebar widths are cached locally and restored automatically upon application launch.
  * **Contextual Focus:** Active panes are tracked globally to ensure commands like "Reading Mode" (Markdown rendering) target the user's current focus point.

### 3\. Multimedia Lore Canvas

The Canvas engine provides an infinite spatial interface for visual planning.

  * **Spatial Anchors:** Users can paste images (maps, character portraits) directly onto the canvas.
  * **Interactive Resizing:** Image cards support ratio-locked manual resizing via hardware-accelerated drag handles.
  * **Z-Layering:** Text-based lore cards are explicitly layered above visual assets for map labeling and annotation.

### 4\. Automated Versioning (Snapshot System)

To prevent data loss, 4AM includes a background version control engine that generates automated local snapshots of all open files every 10 minutes. These are stored in a hidden `.history` directory within the user's vault.

-----

## Technical Specifications

### Internal Wiki Linking

The application supports the `[[Wiki Link]]` protocol.

  * **Deep Routing:** Clicking a link initiates a recursive search through the vault, bypassing nested Ghost-Folders to locate the target file.
  * **Real-time Autocomplete:** Typing `[[` triggers a vault-wide search popup to facilitate rapid internal referencing.

### Attachment Protocol

4AM uses a portable attachment system. All visual assets pasted into the editor or canvas are automatically copied to a localized `_attachments` directory.

  * **Obsidian-Style Syntax:** Supports inline image resizing via the `![[image.png|width]]` syntax.
  * **Lifecycle Management:** Users can locate or permanently delete binary attachments directly through the raw text context menu.

### Vault-Wide Search (The Oracle)

A full-text search engine scans both file titles and internal content across the entire vault, providing a rich-text preview of the surrounding context for each match.

-----

## Changelog

### v1.0.0

**Initial Release**

  * Integrated Multi-Pane Split View with persistent state memory.
  * Implemented Ghost-Folder hierarchy logic for the sidebar.
  * Multimedia Canvas with support for image pasting and text card labeling.
  * Automated local snapshots (Versioning system).
  * Vault-wide full-text search with context previews.
  * Inline image resizing via Alt+Scroll and Markdown syntax.
  * Wiki-link autocomplete and deep-routing.

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

1.  Clone the repository.
2.  Install the required dependencies:
    ```bash
    pip install PySide6 mistune
    ```
3.  Initialize the application:
    ```bash
    python main.py
    ```

-----

## Resources & Contact

  * **Documentation:** GitHub Repository Wiki (in progress).
  * **Contact:** For bugs or personal inquiries, open an **Issue** on the GitHub repository.