#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pdfplumber
import re
import os
import logging
from typing import List, Tuple, Optional, Dict
import argparse

# 配置日志
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s')

class CustomPDFExtractor:
    def __init__(self, pdf_path: str, debug: bool = False):
        # 设置日志级别
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG if debug else logging.INFO)
        self.pdf_path = pdf_path
        self.footer_threshold = 0.9  # 页面底部20%区域视为页脚
        self.title_threshold = 0.30  # 页面顶部15%区域用于检测标题
        self.sections: Dict[str, Dict[str, Any]] = {}  # 存储标题、作者信息和正文
        
    def validate_pdf(self) -> bool:
        """验证PDF文件格式和可访问性"""
        if not os.path.exists(self.pdf_path):
            logging.error(f"PDF文件不存在: {self.pdf_path}")
            return False
            
        if not os.path.isfile(self.pdf_path):
            logging.error(f"指定路径不是文件: {self.pdf_path}")
            return False
            
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                if len(pdf.pages) == 0:
                    logging.error("PDF文件没有包含任何页面")
                    return False
            return True
        except Exception as e:
            logging.error(f"PDF文件格式无效或无法访问: {str(e)}")
            return False

    def detect_title(self, page) -> Optional[str]:
        """检测页面前四行的标题信息，基于文本内容和结构分析"""
        try:
            # 提取页面文本并按行分割
            text = page.extract_text()
            if not text:
                return None
                
            # 获取前四行文本
            lines = text.split('\n')[:4]
            if len(lines) < 2:  # 至少需要两行文本
                return None
                
            # 清理每行文本
            lines = [line.strip() for line in lines if line.strip()]
            if len(lines) < 2:
                return None
            
            # 检查是否符合标题-作者的结构
            for i in range(1, len(lines)):
                # 检查当前行是否包含作者信息
                author_line = lines[i]
                if len(author_line) >= 4 and '作者名' in author_line:
                    # 将前面的行合并作为标题
                    title_text = ' '.join(lines[:i]).strip()
                    self.logger.debug(f"检测到标题: {title_text}")
                    self.logger.debug(f"检测到作者行: {author_line}")
                    return {'title': title_text, 'author_info': author_line}
            
            return None
            
        except Exception as e:
            logging.warning(f"检测标题时出错: {str(e)}")
            return None
            
    def extract_text(self) -> bool:
        """提取PDF文本内容，按标题分类存储"""
        if not self.validate_pdf():
            return False
            
        current_title = "未分类内容"  # 默认标题
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                total_pages = len(pdf.pages)
                logging.info(f"开始处理PDF文件，共{total_pages}页")
                
                for page_num, page in enumerate(pdf.pages, 1):
                    logging.info(f"正在处理第{page_num}页，共{total_pages}页")
                    
                    # 检测新标题
                    title_info = self.detect_title(page)
                    if title_info:
                        current_title = title_info['title']
                        if current_title not in self.sections:
                            self.sections[current_title] = {
                                'title': current_title,
                                'author_info': title_info['author_info'],
                                'content': []
                            }
                        logging.info(f"检测到新标题: {current_title}")
                    
                    # 获取页面尺寸
                    height = page.height
                    footer_height = height * self.footer_threshold
                    
                    try:
                        # 提取文本
                        full_text = page.extract_text()
                        if not full_text:
                            logging.warning(f"第{page_num}页没有可提取的文本")
                            continue
                            
                        # 按行分割文本
                        lines = full_text.split('\n')
                        filtered_lines = []
                        self.logger.debug(f"第{page_num}页原始文本行数: {len(lines)}")
                        self.logger.debug(f"页面高度: {height}, 页脚阈值: {footer_height}")
                        
                        # 处理每一行文本
                        for line in lines:
                            # 过滤包含页脚关键词的行
                            if 'xxx' not in line:
                                filtered_lines.append(line)
                        
                        if filtered_lines:
                            # 合并行并清理格式
                            page_text = ' '.join(filtered_lines)
                            page_text = re.sub(r'\s+', ' ', page_text).strip()
                            self.sections[current_title]['content'].append(page_text)
                            
                    except Exception as e:
                        logging.error(f"处理第{page_num}页时出错: {str(e)}")
                        continue

        except Exception as e:
            logging.error(f"处理PDF文件时出错: {str(e)}")
            return False

        return len(self.sections) > 0

    def save_to_files(self, output_dir: str) -> bool:
        """将提取的文本按标题分别保存到文件"""
        try:
            # 创建输出目录
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                logging.info(f"创建输出目录: {output_dir}")

            # 保存每个部分的文本
            for title, section_data in self.sections.items():
                if not section_data['content']:  # 跳过空内容
                    continue
                    
                # 生成安全的文件名
                safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
                file_path = os.path.join(output_dir, f"{safe_title}.txt")
                
                # 写入文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    # 写入标题和作者信息
                    f.write(f"{section_data['title']}\n")
                    f.write(f"{section_data['author_info']}\n\n")
                    # 写入正文内容
                    f.write('\n\n'.join(section_data['content']))
                logging.info(f"已保存文件: {file_path}")
                
            return True
        except Exception as e:
            logging.error(f"保存文件时出错: {str(e)}")
            return False

def main():
    parser = argparse.ArgumentParser(description='从PDF文件中提取文本内容，按标题分类保存')
    parser.add_argument('input_pdf', help='输入PDF文件路径')
    parser.add_argument('output_dir', help='输出目录路径')
    parser.add_argument('--footer-threshold', type=float, default=0.8,
                        help='页脚区域阈值 (0-1之间的小数，默认0.8)')
    parser.add_argument('--title-threshold', type=float, default=0.15,
                        help='标题检测区域阈值 (0-1之间的小数，默认0.15)')
    parser.add_argument('--debug', action='store_true',
                        help='启用调试模式，输出详细的处理信息')
    args = parser.parse_args()

    # 验证阈值参数
    if not (0 < args.footer_threshold < 1 and 0 < args.title_threshold < 1):
        logging.error("无效的阈值设置")
        return

    extractor = CustomPDFExtractor(args.input_pdf, args.debug)
    extractor.footer_threshold = args.footer_threshold
    extractor.title_threshold = args.title_threshold

    if extractor.extract_text() and extractor.save_to_files(args.output_dir):
        logging.info("文本提取和保存成功完成")
    else:
        logging.error("文本提取或保存失败")

if __name__ == '__main__':
    main()