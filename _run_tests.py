import subprocess, sys

# Step 1: Verify environment
print("=== Step 1: Verify Python Environment ===")
result1 = subprocess.run(
    [r"D:/conda_data/envs/fay/python.exe", "-c", "import sys; print(sys.executable); print('OK')"],
    capture_output=True, text=True, timeout=30
)
print(result1.stdout)
if result1.stderr:
    print("STDERR:", result1.stderr)
print(f"Exit code: {result1.returncode}")

# Step 2: Run brain tests
print("\n=== Step 2: Run Brain Tests ===")
result2 = subprocess.run(
    [r"D:/conda_data/envs/fay/python.exe", "-m", "pytest", "brain/tests/", "-v", "--tb=short"],
    cwd=r"D:/Code/Vs code/digital_human",
    capture_output=True, text=True, timeout=120
)
output = result2.stdout + "\n" + result2.stderr
print(output)
print(f"Exit code: {result2.returncode}")

# Save to file
with open(r"D:/Code/Vs code/digital_human/_test_results.txt", "w", encoding="utf-8") as f:
    f.write("=== Step 1: Verify Python Environment ===\n")
    f.write(result1.stdout + "\n")
    if result1.stderr:
        f.write("STDERR: " + result1.stderr + "\n")
    f.write(f"Exit code: {result1.returncode}\n\n")
    f.write("=== Step 2: Run Brain Tests ===\n")
    f.write(output)
    f.write(f"\nExit code: {result2.returncode}\n")

print("\nResults saved to _test_results.txt")
