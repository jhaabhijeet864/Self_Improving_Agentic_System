import os
import glob

def audit_directory(directory="."):
    py_files = glob.glob(os.path.join(directory, "*.py"))
    
    with open("audit_results.txt", "w", encoding="utf-8") as out_f:
        out_f.write(f"{'File Name':<30} | {'Total Lines':<15} | {'Unique Content':<15} | {'Padding %':<15}\n")
        out_f.write("-" * 80 + "\n")
        
        total_lines_all = 0
        total_unique_all = 0
        
        for file_path in py_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                total_lines = len(lines)
                
                unique_lines = set()
                for line in lines:
                    cleaned_line = line.strip()
                    if cleaned_line: 
                        unique_lines.add(cleaned_line)
                        
                unique_count = len(unique_lines)
                padding_pct = ((total_lines - unique_count) / total_lines * 100) if total_lines > 0 else 0
                
                file_name = os.path.basename(file_path)
                out_f.write(f"{file_name:<30} | {total_lines:<15} | {unique_count:<15} | {padding_pct:.1f}%\n")
                
                total_lines_all += total_lines
                total_unique_all += unique_count
                
            except Exception as e:
                out_f.write(f"Error reading {file_path}: {e}\n")
                
        if total_lines_all > 0:
            overall_padding = ((total_lines_all - total_unique_all) / total_lines_all) * 100
            out_f.write("-" * 80 + "\n")
            out_f.write(f"{'OVERALL':<30} | {total_lines_all:<15} | {total_unique_all:<15} | {overall_padding:.1f}%\n")

if __name__ == '__main__':
    audit_directory()
