import glob

print(f"{'File':<30} | {'Total Lines':<15} | {'Unique Lines':<15} | {'Padding %':<15}")
print('-' * 80)

for filepath in glob.glob('*.py'):
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
        
    total_lines = len(lines)
    
    unique_lines = set(line.strip() for line in lines if line.strip())
    
    # Let's count empty lines as 1 unique line
    unique_lines_count = len(unique_lines)
    if any(not line.strip() for line in lines):
        unique_lines_count += 1
        
    if total_lines > 0:
        padding_pct = (1 - (unique_lines_count / total_lines)) * 100
    else:
        padding_pct = 0
        
    print(f"{filepath:<30} | {total_lines:<15} | {unique_lines_count:<15} | {padding_pct:.2f}%")
