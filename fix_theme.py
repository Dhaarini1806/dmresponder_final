import os
import re

templates = [
    'templates/landing.html',
    'templates/inbox.html',
    'templates/engagement_starter.html',
    'templates/connected_accounts.html',
    'templates/dashboard_base.html',
    'templates/automation_reels.html'
]

# primary color from logo: #933fe2 (Purple)
# secondary/hover: #7827c2

for t in templates:
    if os.path.exists(t):
        with open(t, 'r', encoding='utf-8') as f:
            content = f.read()

        # Fix colors
        content = content.replace('bg-[#0c1220]', 'bg-[#933fe2]')
        content = content.replace('hover:bg-[#1a2233]', 'hover:bg-[#7827c2]')
        content = content.replace('text-[#0c1220]', 'text-[#933fe2]')
        content = content.replace('hover:text-[#0c1220]', 'hover:text-[#933fe2]')
        content = content.replace('ring-[#0c1220]', 'ring-[#933fe2]')
        content = content.replace('border-[#0c1220]', 'border-[#933fe2]')
        
        # In dashboard_base.html, the sidebar text was text-[#0c1220] but maybe it should be text-[#933fe2] or just text-gray-900.
        # Wait, I originally replaced text-indigo-600. So the sidebar active text will be purple, which is fine.
        
        # Change the text DMResponder to DM Responder in the sidebar/navbar
        content = content.replace('DMResponder</span>', 'DM Responder</span>')
        content = content.replace('alt="DMResponder Logo"', 'alt="DM Responder Logo"')
        
        with open(t, 'w', encoding='utf-8') as f:
            f.write(content)

print('Restored UI with logo vibrant colors')
