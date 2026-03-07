"""
Example 8: Advanced Security & Sandboxing (The Swara AI Defenses)

Demonstrates how Jarvis-OS protects the host machine from rogue agents
using the Virtual File System (VFS), AST Sandbox Scanning, and 
Human-in-the-Loop approvals.
"""
import asyncio
import logging
import os
from jarvis_os import AgentConfig, JarvisOS
from developer_tools import jarvis_tool, SandboxManager, CLIExecutor
from vfs import VirtualFileSystem, SecurityViolationError

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("security_demo")
logger.setLevel(logging.INFO)

async def main():
    print("\n" + "="*60)
    print("🛡️ SWARA AI - SECURITY & SANDBOXING DEMO (Phase 10)")
    print("="*60)
    
    config = AgentConfig(name="Secure-Swara-Agent", max_workers=5, auto_optimize=False)
    agent = JarvisOS(config)
    await agent.start()
    
    # ----------------------------------------------------------------------
    # DEMO 1: VirtualFileSystem (VFS) Jail
    # ----------------------------------------------------------------------
    print("\n[TEST 1] Virtual File System Jail")
    
    # Mount a VFS locked strictly to a new './swara_workspace' directory
    jail_dir = os.path.join(os.getcwd(), "swara_workspace")
    vfs = VirtualFileSystem(root_jail_dir=jail_dir, allowed_extensions=[".txt", ".md"])
    
    try:
        # A normal, safe file write inside the jail
        vfs.write_file("safe_notes.txt", "SWARA AI: I am keeping safe notes.")
        print("✅ Safe file write succeeded.")
        
        # A simulated hack/hallucination: trying to escape the jail
        print("\n[Swara AI] Attempting to read system secrets...")
        vfs.read_file("../../windows/system32/config/SAM")
        
    except SecurityViolationError as e:
        print(f"🛑 VFS BLOCKED ESCAPE: {e}")

    # ----------------------------------------------------------------------
    # DEMO 2: AST Parser Sandbox Protection
    # ----------------------------------------------------------------------
    print("\n[TEST 2] AST Code Sandbox Scanner")
    sandbox = SandboxManager(agent)
    
    # Swara generated code trying to access the terminal 
    malicious_code = """
import os
import sys
print("I am hacking the mainframe...")
os.system("echo formatting drives...")
    """
    
    print("[Swara AI] Testing generated script in Sandbox...")
    test_result = await sandbox.evaluate_code(malicious_code)
    
    if test_result["success"]:
        print("❌ Wait, this should have been blocked!")
    else:
        print(f"🛑 AST SCANNER CAUGHT THREAT: {test_result['error']}")

    # ----------------------------------------------------------------------
    # DEMO 3: Human-in-the-Loop Approval via Decorator
    # ----------------------------------------------------------------------
    print("\n[TEST 3] Human-in-the-Loop Approval (@jarvis.tool)")
    
    # Swara AI creates a highly destructive tool, but we flag it!
    @jarvis_tool(agent, "delete_database", requires_approval=True)
    async def drop_tables(db_name: str):
        return f"Database '{db_name}' has been completely erased."

    print("\n[Swara AI] Requesting to drop the production database...")
    print("(For this automated demo, we will simulate the user pressing 'n')")
    
    try:
        # We mock input so the script runs headless for you
        import builtins
        original_input = builtins.input
        builtins.input = lambda prompt: "n"  # Simulate user rejecting
        
        await drop_tables("Swara_Main_DB")
        
        builtins.input = original_input
    except PermissionError as e:
        print(f"🛑 EXECUTION REJECTED BY HUMAN: {e}")
        builtins.input = original_input

    print("\nShutting down Security demo...")
    # cleanup temp jail
    if os.path.exists(os.path.join(jail_dir, "safe_notes.txt")):
        os.remove(os.path.join(jail_dir, "safe_notes.txt"))
    os.rmdir(jail_dir)
        
    await agent.stop()

if __name__ == "__main__":
    asyncio.run(main())
