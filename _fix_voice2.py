p = r'D:/Code/Vs code/digital_human/admin/frontend/index.html'
c = open(p, encoding='utf-8').read()
c = c.replace('};else toast', '}else toast')
open(p, 'w', encoding='utf-8').write(c)
print('FIXED')
