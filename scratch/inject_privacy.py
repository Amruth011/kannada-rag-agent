import re

def convert_to_html(text):
    lines = text.strip().split("\n")
    html_lines = []
    in_list = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith("Privacy Policy —"):
            html_lines.append(f"<h1>{line}</h1>")
        elif line.startswith("Last Updated:"):
            html_lines.append(f'<p class="last-updated">{line}</p>')
        elif re.match(r"^\d+\.\s", line):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h2>{line}</h2>")
        elif line.startswith("- ") or line.startswith("1. Strictly") or line.startswith("2. Analytical") or line.startswith("3. Advertising"):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{line[line.find(' ')+1:] if line.startswith('- ') else line}</li>")
        else:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<p>{line}</p>")
            
    if in_list:
        html_lines.append("</ul>")
        
    return "\n".join(f"        {l}" for l in html_lines)

with open('scratch/build_pages.py', 'r', encoding='utf-8') as f:
    content = f.read()
    
# Extract privacy_text
import ast
module = ast.parse(content)
privacy_text = ""
for node in module.body:
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and getattr(node.targets[0], 'id', '') == 'privacy_text':
        privacy_text = node.value.value

html_content = convert_to_html(privacy_text)

with open('api/index.py', 'r', encoding='utf-8') as f:
    index_content = f.read()
    
# Find the privacy_policy function and replace the <main> block
start_tag = "<main>\n        <h1>Privacy Policy</h1>"
end_tag = "    </main>"
start_idx = index_content.find(start_tag)
end_idx = index_content.find(end_tag, start_idx)

if start_idx != -1 and end_idx != -1:
    new_content = index_content[:start_idx] + "<main>\n" + html_content + "\n" + index_content[end_idx:]
    with open('api/index.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Successfully replaced privacy policy in api/index.py")
else:
    print("Could not find <main> block for privacy policy")
