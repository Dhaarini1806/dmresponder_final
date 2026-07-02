import re
import glob
import os

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Generic color replacements
    content = content.replace('bg-indigo-600', 'bg-[#0c1220]')
    content = content.replace('hover:bg-indigo-700', 'hover:bg-[#1a2233]')
    content = content.replace('text-indigo-600', 'text-[#0c1220]')
    content = content.replace('hover:text-indigo-600', 'hover:text-[#0c1220]')
    content = content.replace('shadow-indigo-100', 'shadow-gray-300')
    content = content.replace('bg-indigo-50', 'bg-gray-100')
    content = content.replace('ring-indigo-500', 'ring-[#0c1220]')
    content = content.replace('border-indigo-500', 'border-[#0c1220]')
    
    # Replace the bolt logo
    new_logo_html = '<img src="/static/img/logo.png" alt="DMResponder Logo" class="h-8 object-contain">'
    content = re.sub(r'<div class="w-8 h-8 bg-\[#0c1220\] rounded-lg flex items-center justify-center text-white">\s*<i class="fas fa-bolt"></i>\s*</div>', new_logo_html, content)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

# Apply to typical files
templates = [
    'templates/landing.html',
    'templates/inbox.html',
    'templates/engagement_starter.html',
    'templates/connected_accounts.html'
]

for t in templates:
    if os.path.exists(t):
        process_file(t)
        print(f"Updated {t}")
