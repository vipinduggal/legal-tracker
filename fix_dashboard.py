import os, re

home = os.path.expanduser("~")
path = os.path.join(home, "legal-tracker", "src", "server.js")

with open(path, 'r') as f:
    content = f.read()

# Fix 1: filt function name issue - ensure it's defined before called
content = content.replace("oninput='filt()'", "oninput='filterList()'")
content = content.replace("function filt()", "function filterList()")
content = content.replace("function filt(){", "function filterList(){")

# Fix 2: the bdg class reference syntax issue - replace escaped quotes pattern
# The issue is \\' sequences in the JS that are causing syntax errors
# Replace the problematic sbdg function definition
old_sbdg = "const sbdg=s=>'<span class=\\'bdg '+({'Pending':'ba','Ongoing':'ba','Under investigation':'ba','Resolved':'bg','Settled':'bg','Dismissed':'bg','Closed':'bg'}[s]||'bb')+'\\'>' +s+'</span>';"
new_sbdg = """const sbdg=s=>{const m={'Pending':'ba','Ongoing':'ba','Under investigation':'ba','Resolved':'bg','Settled':'bg','Dismissed':'bg','Closed':'bg'};const cls=m[s]||'bb';return '<span class="bdg '+cls+'">'+s+'</span>';};"""

content = content.replace(old_sbdg, new_sbdg)

# Fix 3: also fix itl and emp functions that use escaped quotes
old_itl = "const itl=t=>'<div class=\\'intel\\'><div class=\\'il\\'>Sales Intel</div><div class=\\'it\\'>'+t+'</div></div>';"
new_itl = """const itl=t=>'<div class="intel"><div class="il">Sales Intel</div><div class="it">'+t+'</div></div>';"""
content = content.replace(old_itl, new_itl)

old_emp = "const emp=(m,c)=>'<div class=\\'emp\\'><p>'+m+'</p>'+(c?'<p style=\\'font-size:11px;margin-top:4px\\'>Run: <code>'+c+'</code></p>':'')+'</div>';"
new_emp = """const emp=(m,c)=>'<div class="emp"><p>'+m+'</p>'+(c?'<p style="font-size:11px;margin-top:4px">Run: <code>'+c+'</code></p>':'')+'</div>';"""
content = content.replace(old_emp, new_emp)

with open(path, 'w') as f:
    f.write(content)

print("Done — dashboard patched")
print("File size: " + str(os.path.getsize(path)) + " bytes")
