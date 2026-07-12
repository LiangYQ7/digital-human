p = r'D:/Code/Vs code/digital_human/admin/frontend/index.html'
c = open(p, encoding='utf-8').read()
old = 'if(r.synced){avVoice=voice;document.getElementById("av-refaudio").value=voice;toast'
new = 'if(r.synced){avVoice=voice;document.getElementById("av-refaudio").value=voice;toast'
# The issue: missing } before ;else
# Find and fix the pattern
broken = 'voice;toast('
# Find nearest ;else after the toast
idx = c.find(broken)
if idx > 0:
    # Find the ;else that follows
    end = c.find(';else toast', idx)
    if end > 0:
        # Insert } before ;else
        fixed = c[:end] + '}' + c[end:]
        open(p, 'w', encoding='utf-8').write(fixed)
        print('FIXED')
    else:
        print(';else not found')
else:
    print('broken pattern not found')
