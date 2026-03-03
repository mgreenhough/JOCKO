"""Check missing entries in the EPUB."""
import zipfile
import re
from bs4 import BeautifulSoup

epub_path = 'data/The-Daily-Stoic_-366-Meditations-on-Wisdom-Perseverance-and-the-Art-of-Living-PDFDrive.com-.epub'
z = zipfile.ZipFile(epub_path, 'r')

# Get all HTML pages
files = z.namelist()
html_pages = sorted([f for f in files if f.startswith('EPUB/page_') and f.endswith('.html')],
                    key=lambda x: int(re.search(r'page_(\d+)\.html', x).group(1)))

# Check January 8 (should be around page_0014.html)
for page_file in html_pages[:20]:
    content = z.read(page_file).decode('utf-8')
    soup = BeautifulSoup(content, 'html.parser')
    text = soup.get_text()
    
    if 'January 8' in text:
        print(f'=== {page_file} ===')
        # Print raw HTML around January 8
        idx = content.find('January 8')
        print(content[idx-200:idx+2000])
        print('\n' + '='*50 + '\n')
