# Benchmark Python sample: Attempted unauthorized imports designed to verify AST security pre-filter
import os
import subprocess

def dangerous_action():
    os.system("echo malicious_command")
    subprocess.run(["cmd.exe", "/c", "dir"])

dangerous_action()
