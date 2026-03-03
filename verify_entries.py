"""Verify stoic.py entries match the EPUB source."""
import json
import sys
sys.path.insert(0, '.')
from stoic import DAILY_STOIC_ENTRIES

# Load extracted entries
with open('extracted_entries.json', 'r', encoding='utf-8') as f:
    extracted = json.load(f)

# Convert string keys back to tuples
extracted_entries = {}
for k, v in extracted.items():
    # Handle both "11-10" and "(11, 10)" formats
    k_clean = k.strip('()').replace(' ', '')
    month, day = map(int, k_clean.split(','))
    extracted_entries[(month, day)] = v

print(f'Entries in stoic.py: {len(DAILY_STOIC_ENTRIES)}')
print(f'Entries extracted from EPUB: {len(extracted_entries)}')
print()

# Compare entries
mismatch_summary = []
mismatch_details = []

for key in sorted(extracted_entries.keys()):
    if key not in DAILY_STOIC_ENTRIES:
        mismatch_summary.append(f'Missing in stoic.py: {key}')
        continue
    
    epub_entry = extracted_entries[key]
    stoic_entry = DAILY_STOIC_ENTRIES[key]
    entry_mismatches = []
    
    # Compare each field
    for field in ['title', 'quote', 'author', 'reflection']:
        epub_val = epub_entry.get(field, '').strip()
        stoic_val = stoic_entry.get(field, '').strip()
        
        if epub_val != stoic_val:
            entry_mismatches.append(field)
            # Find first difference
            min_len = min(len(epub_val), len(stoic_val))
            diff_pos = 0
            for i in range(min_len):
                if epub_val[i] != stoic_val[i]:
                    diff_pos = max(0, i - 20)
                    break
            mismatch_details.append(f'{key} - Field: {field}')
            mismatch_details.append(f'  EPUB:    {repr(epub_val[diff_pos:diff_pos+60])}')
            mismatch_details.append(f'  stoic.py: {repr(stoic_val[diff_pos:diff_pos+60])}')
            mismatch_details.append('')
    
    if entry_mismatches:
        mismatch_summary.append(f'{key}: {", ".join(entry_mismatches)}')

if mismatch_summary:
    print(f'TOTAL ENTRIES WITH MISMATCHES: {len(mismatch_summary)}')
    print()
    print('SUMMARY:')
    for m in mismatch_summary:
        print(f'  {m}')
    print()
    print('DETAILS (first 20):')
    for m in mismatch_details[:60]:
        print(m)
else:
    print('All entries match verbatim!')
