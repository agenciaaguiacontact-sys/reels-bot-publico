import json
with open('scan_report_utf8.json', encoding='utf-8') as f:
    # First line might have a BOM
    content = f.read()
    if content.startswith('\ufeff'):
        content = content[1:]
    d = json.loads(content)
scan = d['scan']
print(f"Total safe: {scan['total_safe_human']}")
print(f"Total review: {scan['total_review_bytes']} bytes")
print("Safe files:")
for f in scan.get('safe_to_delete', []):
    print(f" - {f['path_relative']} ({f['size_human']})")
print("Review files:")
for f in scan.get('review_needed', []):
    print(f" - {f['path_relative']} ({f['size_human']}) - {f.get('warning', 'Review needed')}")
