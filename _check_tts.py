import requests
r = requests.get('http://localhost:8010/tts/index.html')
html = r.text
s = html.find('<script>')
e = html.find('</script>', s)
js = html[s:e+9]

# Find all function definitions
import re
funcs = re.findall(r'function\s+\w+|async\s+function\s+\w+', js)
print("Functions found:", funcs[:20])

# Check for onAudioFileChange
if 'onAudioFileChange' in js:
    idx = js.find('function onAudioFileChange')
    print("\n=== onAudioFileChange context ===")
    print(js[max(0,idx-100):idx+300])
else:
    print("onAudioFileChange NOT in JS block")

# Check brace balance
print(f"\nBraces: {js.count('{')} open, {js.count('}')} close")

# Check for UTF-8 replacement characters
if '\ufffd' in js:
    print("WARNING: replacement chars found!")
    # Show where
    for i, c in enumerate(js):
        if c == '\ufffd':
            print(f"  at {i}: {repr(js[max(0,i-20):i+20])}")
            if i > 10:
                break
