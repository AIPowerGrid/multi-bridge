#!/usr/bin/env python3
import os
import sys
import yaml
import psutil
import signal

def extract_config_from_process(pid):
    """Try to extract configuration from running process"""
    try:
        # Get process info
        process = psutil.Process(pid)
        print(f"Process: {process.name()} (PID: {pid})")
        print(f"Command: {' '.join(process.cmdline())}")
        
        # Try to get environment variables
        print("\nEnvironment variables:")
        env = process.environ()
        for key, value in env.items():
            if 'bridge' in key.lower() or 'api' in key.lower() or 'key' in key.lower():
                print(f"  {key}: {value}")
        
        # Try to get open files
        print("\nOpen files:")
        for file in process.open_files():
            if 'bridgeData' in file.path or 'yaml' in file.path:
                print(f"  {file.path}")
        
        return True
        
    except Exception as e:
        print(f"Error extracting from process: {e}")
        return False

def try_memory_extraction(pid):
    """Try to extract from process memory (limited on macOS)"""
    try:
        # On macOS, we have limited access to process memory
        # But we can try to get some basic info
        process = psutil.Process(pid)
        
        # Get memory info
        memory_info = process.memory_info()
        print(f"\nMemory usage: {memory_info.rss / 1024 / 1024:.2f} MB")
        
        # Try to get command line arguments
        cmdline = process.cmdline()
        print(f"Command line: {cmdline}")
        
        return True
        
    except Exception as e:
        print(f"Error with memory extraction: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        pid = int(sys.argv[1])
    else:
        # Default to the process we found
        pid = 17358
    
    print(f"Attempting to extract configuration from process {pid}")
    print("=" * 50)
    
    extract_config_from_process(pid)
    try_memory_extraction(pid)
    
    print("\n" + "=" * 50)
    print("Note: On macOS, direct memory access is limited for security reasons.")
    print("If the process is still running, you might be able to:")
    print("1. Check the terminal where it's running for any output")
    print("2. Look for any log files it might have created")
    print("3. Check if it created any temporary files") 