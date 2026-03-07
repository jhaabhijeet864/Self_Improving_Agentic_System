"""
Virtual File System (VFS) Layer - Jarvis-OS
Provides a simulated "chroot jail" for attached tooling (e.g. Swara AI)
to prevent path traversal attacks (../../../system32) and enforce
safe, sandboxed file operations.
"""

import os
import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

class SecurityViolationError(Exception):
    """Raised when an agent attempts to access files outside its VFS Jail."""
    pass

class VirtualFileSystem:
    def __init__(self, root_jail_dir: str, allowed_extensions: Optional[List[str]] = None):
        """
        Initialize the Virtual File System.
        
        Args:
            root_jail_dir: The absolute path to the directory the agent is restricted to.
            allowed_extensions: E.g., ['.py', '.json', '.md']. If None, all are allowed.
        """
        # Resolve to an absolute, normalized path to prevent clever symlink escapes
        self.jail_root = Path(root_jail_dir).resolve()
        self.allowed_extensions = allowed_extensions
        
        # Ensure the jail exists
        if not self.jail_root.exists():
            self.jail_root.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created new VFS Jail at: {self.jail_root}")
        else:
            logger.info(f"VFS mounted to existing Jail: {self.jail_root}")

    def _resolve_and_verify(self, requested_path: str) -> Path:
        """
        Resolves a requested path and ensures it does not escape the jail_root.
        Returns the absolute Path object, or raises SecurityViolationError.
        """
        # 1. Join the requested path to the jail root and resolve it fully
        # Resolution eliminates any '..' traverses.
        try:
            target_path = (self.jail_root / requested_path).resolve()
        except Exception as e:
            raise SecurityViolationError(f"Malformed path request: {e}")

        # 2. Check if the resolved path starts with the jail root path
        try:
            target_path.relative_to(self.jail_root)
        except ValueError:
             # The resolved path is NOT inside the the jail_root! Array traversal attack!
             logger.warning(f"SECURITY ALERT: Blocked traversal attempt to '{requested_path}'")
             raise SecurityViolationError(
                f"Path escaping! Agent attempted to access '{requested_path}' "
                f"which resolves to '{target_path}', outside the Jail ({self.jail_root})."
             )

        # 3. Check allowed extensions (if applied and if it's not a directory)
        if self.allowed_extensions and target_path.suffix and not target_path.is_dir():
            if target_path.suffix not in self.allowed_extensions:
                logger.warning(f"SECURITY ALERT: Blocked forbidden extension write: {target_path.name}")
                raise SecurityViolationError(
                    f"File type '{target_path.suffix}' is not permitted by VFS policy. "
                    f"Allowed: {self.allowed_extensions}"
                )

        return target_path

    # --- Safe File Operations ---

    def read_file(self, path: str) -> str:
        safe_path = self._resolve_and_verify(path)
        if not safe_path.exists():
             raise FileNotFoundError(f"VFS file not found: {path}")
        with open(safe_path, 'r', encoding='utf-8') as f:
             return f.read()

    def write_file(self, path: str, content: str) -> bool:
        safe_path = self._resolve_and_verify(path)
        # Ensure parent directories inside the jail exist
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        with open(safe_path, 'w', encoding='utf-8') as f:
             f.write(content)
        return True

    def list_files(self, path: str = ".") -> List[str]:
        safe_path = self._resolve_and_verify(path)
        if not safe_path.is_dir():
             raise NotADirectoryError(f"Not a directory in VFS: {path}")
        
        # Return names relative to the jail path requested
        return [f.name for f in safe_path.iterdir()]
