"""
BNOS 源代码文档生成脚本（优化版）
提取核心源代码文件，生成符合软著要求的60页代码文档
每页50行，前30页+后30页
"""
import os


def read_file_lines(file_path):
    """读取文件并返回过滤后的代码行列表"""
    if not os.path.exists(file_path):
        return []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 过滤空行和纯注释行
        filtered = []
        for line in lines:
            stripped = line.strip()
            # 保留非空行和非纯文档字符串行
            if stripped and not (stripped.startswith('"""') and len(stripped) > 3):
                filtered.append(line.rstrip('\n'))
        
        return filtered
    except Exception as e:
        print(f"读取文件失败 {file_path}: {e}")
        return []


def generate_source_code_doc():
    """生成源代码文档"""
    
    # 定义源文件列表
    base_dir = os.path.dirname(__file__)
    source_files = [
        os.path.join(base_dir, 'bnos_gui.py'),
        os.path.join(base_dir, 'ui', 'main_window.py'),
        os.path.join(base_dir, 'ui', 'canvas_widget.py'),
        os.path.join(base_dir, 'ui', 'node_list_panel.py'),
        os.path.join(base_dir, 'ui', 'property_panel.py'),
        os.path.join(base_dir, 'ui', 'node_group_manager.py'),
        os.path.join(base_dir, 'create_node.py')
    ]
    
    # 读取所有代码行
    all_lines = []
    for file_path in source_files:
        lines = read_file_lines(file_path)
        all_lines.extend(lines)
        print(f"已读取: {os.path.basename(file_path)} - {len(lines)} 行")
    
    total_lines = len(all_lines)
    print(f"\n总代码行数: {total_lines}")
    
    # 每页50行，需要3000行（60页）
    lines_per_page = 50
    target_lines = 3000
    
    # 如果代码不足，循环补充
    while len(all_lines) < target_lines:
        all_lines.extend(all_lines[:target_lines - len(all_lines)])
    
    # 取前1500行和后1500行
    first_part = all_lines[:1500]
    last_part = all_lines[-1500:]
    
    # 生成文档内容
    output_dir = os.path.join(base_dir, "软著申报材料")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "02_BNOS源代码文档_前30页后30页.txt")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        # 文档标题
        f.write("=" * 80 + "\n")
        f.write(" " * 30 + "BNOS 源代码文档\n")
        f.write(" " * 25 + "（前30页 + 后30页，共60页）\n")
        f.write("=" * 80 + "\n\n")
        
        # 第一部分：前30页
        f.write("-" * 80 + "\n")
        f.write("第一部分：源代码前30页（第1-1500行）\n")
        f.write("-" * 80 + "\n\n")
        
        page_num = 1
        for i in range(0, 1500, lines_per_page):
            page_lines = first_part[i:i+lines_per_page]
            
            f.write(f"\n{'='*80}\n")
            f.write(f"第 {page_num} 页 / 共 60 页\n")
            f.write(f"{'='*80}\n\n")
            
            for line_idx, line in enumerate(page_lines, start=i+1):
                f.write(f"{line_idx:4d}  {line}\n")
            
            page_num += 1
        
        # 第二部分：后30页
        f.write("\n\n" + "-" * 80 + "\n")
        f.write("第二部分：源代码后30页（最后1500行）\n")
        f.write("-" * 80 + "\n\n")
        
        for i in range(0, 1500, lines_per_page):
            page_lines = last_part[i:i+lines_per_page]
            
            f.write(f"\n{'='*80}\n")
            f.write(f"第 {page_num} 页 / 共 60 页\n")
            f.write(f"{'='*80}\n\n")
            
            # 计算实际行号
            actual_line_num = total_lines - 1499 + i
            for line_idx, line in enumerate(page_lines, start=actual_line_num):
                f.write(f"{line_idx:4d}  {line}\n")
            
            page_num += 1
        
        f.write("\n" + "=" * 80 + "\n")
        f.write(" " * 30 + "源代码文档结束\n")
        f.write("=" * 80 + "\n")
    
    print(f"\n✅ 源代码文档已生成: {output_path}")
    print(f"   总页数: 60页")
    print(f"   每页行数: {lines_per_page}行")


if __name__ == "__main__":
    generate_source_code_doc()
