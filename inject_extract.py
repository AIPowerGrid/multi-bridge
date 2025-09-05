#!/usr/bin/env python3
import os
import sys
import signal
import subprocess
import time

def try_signal_approach(pid):
    """Try to send signals to the process to get it to dump config"""
    print(f"Attempting to send signals to process {pid}")
    
    # Try sending SIGUSR1 (custom signal) - might trigger config dump
    try:
        os.kill(pid, signal.SIGUSR1)
        print("Sent SIGUSR1 signal")
        time.sleep(1)
    except Exception as e:
        print(f"Could not send SIGUSR1: {e}")
    
    # Try sending SIGUSR2
    try:
        os.kill(pid, signal.SIGUSR2)
        print("Sent SIGUSR2 signal")
        time.sleep(1)
    except Exception as e:
        print(f"Could not send SIGUSR2: {e}")

def check_terminal_output():
    """Check if we can see the terminal output"""
    print("\nChecking terminal ttys001...")
    try:
        # Try to read from the terminal
        result = subprocess.run(['lsof', '-a', '-p', '17358', '-d', '0,1,2'], 
                              capture_output=True, text=True)
        print("Terminal file descriptors:")
        print(result.stdout)
    except Exception as e:
        print(f"Error checking terminal: {e}")

def try_ptrace_approach():
    """Try using ptrace to attach to the process (limited on macOS)"""
    print("\nAttempting ptrace approach...")
    try:
        # On macOS, ptrace is limited but we can try
        result = subprocess.run(['sudo', 'dtrace', '-p', '17358', '-n', 
                               'syscall::read:entry { printf("read called"); }'],
                              capture_output=True, text=True, timeout=5)
        print("DTrace output:", result.stdout)
    except Exception as e:
        print(f"DTrace approach failed: {e}")

if __name__ == "__main__":
    pid = 17358
    
    print("Attempting multiple approaches to extract configuration...")
    print("=" * 60)
    
    try_signal_approach(pid)
    check_terminal_output()
    
    print("\n" + "=" * 60)
    print("Alternative approaches:")
    print("1. Check the terminal where the process is running (ttys001)")
    print("2. Look for any output files in the current directory")
    print("3. Check if the process created any temporary files")
    print("4. Try to restart the process with debug logging enabled")
    
    # Let's also check for any recent files that might contain config
    print("\nChecking for recent files...")
    try:
        result = subprocess.run(['find', '.', '-name', '*.yaml', '-o', '-name', '*.yml', 
                               '-o', '-name', '*.json', '-o', '-name', '*.txt',
                               '-newer', 'bridgeData_template.yaml'], 
                              capture_output=True, text=True)
        if result.stdout.strip():
            print("Recent files found:")
            print(result.stdout)
        else:
            print("No recent configuration files found")
    except Exception as e:
        print(f"Error checking recent files: {e}") 