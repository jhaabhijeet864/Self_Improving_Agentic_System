import subprocess
import os
import sys
import win32api
import win32job
import win32process
import win32security

class SandboxExecutionError(Exception):
    pass

def execute_in_sandbox(func_code: str, memory_limit_mb: int = 512, timeout: float = 5.0):
    """
    Executes Python code in a sandboxed subprocess using Windows Job Objects.
    """
    # Create a job object
    hJob = win32job.CreateJobObject(None, "")

    # Set limits
    info = win32job.QueryInformationJobObject(hJob, win32job.JobObjectExtendedLimitInformation)
    info['ProcessMemoryLimit'] = memory_limit_mb * 1024 * 1024
    info['LimitFlags'] = (win32job.JOB_OBJECT_LIMIT_PROCESS_MEMORY | 
                          win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE |
                          win32job.JOB_OBJECT_LIMIT_ACTIVE_PROCESS)
    info['ActiveProcessLimit'] = 1
    
    win32job.SetInformationJobObject(hJob, win32job.JobObjectExtendedLimitInformation, info)

    # We need a script to run
    script_path = "temp_sandbox_task.py"
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(func_code)

    # Spawn process
    # Start it suspended to prevent early escape
    startupinfo = win32process.STARTUPINFO()
    
    try:
        hProcess, hThread, dwProcessId, dwThreadId = win32process.CreateProcess(
            None, # appName
            f"{sys.executable} {script_path}", # commandLine
            None, # processAttributes
            None, # threadAttributes
            True, # bInheritHandles
            win32process.CREATE_SUSPENDED | win32process.CREATE_BREAKAWAY_FROM_JOB,
            None, # newEnvironment
            None, # currentDirectory
            startupinfo
        )
        
        # Assign to job object
        win32job.AssignProcessToJobObject(hJob, hProcess)
        
        # Resume thread
        win32process.ResumeThread(hThread)
        
        # Wait for completion
        rc = win32api.WaitForSingleObject(hProcess, int(timeout * 1000))
        
        if rc == win32api.WAIT_TIMEOUT:
            win32api.TerminateProcess(hProcess, 1)
            raise SandboxExecutionError("Execution timed out.")
            
        exit_code = win32process.GetExitCodeProcess(hProcess)
        
        # cleanup handles
        win32api.CloseHandle(hThread)
        win32api.CloseHandle(hProcess)
        
        # Read outputs if we had redirected them (for simplicity, we didn't here, 
        # but in a real implementation we would write stdout to a file and read it).
        if exit_code != 0:
            raise SandboxExecutionError(f"Process exited with code {exit_code}")
            
    finally:
        if os.path.exists(script_path):
            try:
                os.remove(script_path)
            except:
                pass
                
    return "Success"
