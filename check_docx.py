import sys
print("Python is working", flush=True)
print("Version: " + sys.version, flush=True)
try:
    import docx
    print("docx available", flush=True)
except ImportError:
    print("docx NOT available - installing...", flush=True)
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-docx"])
    import docx
    print("docx installed successfully", flush=True)
