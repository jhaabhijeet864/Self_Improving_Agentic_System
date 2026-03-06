#!/usr/bin/env python3
"""
Jarvis-OS initialization script to create project structure
"""
import os
import sys

def create_project_structure():
    """Create the complete Jarvis-OS project structure"""
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.join(base_dir, 'jarvis-os')
    
    # Create directories
    directories = [
        'jarvis_os',
        'jarvis_os/core',
        'jarvis_os/memory',
        'jarvis_os/router',
        'jarvis_os/sandbox',
        'jarvis_os/logging',
        'jarvis_os/server',
        'tests',
        'docs',
    ]
    
    for directory in directories:
        dir_path = os.path.join(project_root, directory)
        os.makedirs(dir_path, exist_ok=True)
        print(f"✓ Created: {dir_path}")
    
    print("\n✓ Project structure created successfully!")
    return project_root

if __name__ == '__main__':
    create_project_structure()
