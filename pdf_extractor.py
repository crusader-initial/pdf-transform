#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pdfplumber
import re
import os
import logging
from typing import List, Tuple, Optional
import argparse

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class PDFExtractor:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.header_threshold = 0.2  # 页面顶部20%区域视为页眉
        self.footer_threshold = 0.8  # 页面底部20%区域视为页脚
        
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

    def extract_text(self) -> Optional[str]:
        """提取PDF文本内容，去除页眉页脚"""
        if not self.validate_pdf():
            return None
            
        extracted_text = []
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                total_pages = len(pdf.pages)
                logging.info(f"开始处理PDF文件，共{total_pages}页")
                
                for page_num, page in enumerate(pdf.pages, 1):
                    logging.info(f"正在处理第{page_num}页，共{total_pages}页")
                    
                    # 获取页面尺寸
                    height = page.height
                    header_height = height * self.header_threshold
                    footer_height = height * self.footer_threshold
                    
                    try:
                        # 使用extract_text()方法提取整页文本
                        full_text = page.extract_text()
                        if not full_text:
                            logging.warning(f"第{page_num}页没有可提取的文本")
                            continue
                            
                        # 按行分割文本
                        lines = full_text.split('\n')
                        filtered_lines = []
                        
                        # 处理每一行文本
                        for line in lines:
                            # 获取行的垂直位置
                            line_bbox = page.search(line)
                            if line_bbox:
                                line_top = line_bbox[0]['top']
                                # 过滤页眉页脚
                                if header_height < line_top < footer_height:
                                    filtered_lines.append(line)
                        
                        if filtered_lines:
                            # 合并行并清理格式
                            page_text = ' '.join(filtered_lines)
                            page_text = re.sub(r'\s+', ' ', page_text).strip()
                            extracted_text.append(page_text)
                            
                    except Exception as e:
                        logging.error(f"处理第{page_num}页时出错: {str(e)}")
                        continue

        except Exception as e:
            logging.error(f"处理PDF文件时出错: {str(e)}")
            return None

        if not extracted_text:
            logging.warning("未能从PDF中提取到任何文本")
            return None
            
        return '\n\n'.join(extracted_text)

    def save_to_file(self, output_path: str) -> bool:
        """将提取的文本保存到文件"""
        try:
            # 验证输出路径
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
                logging.info(f"创建输出目录: {output_dir}")

            text = self.extract_text()
            if text is not None:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                logging.info(f"文本已成功保存到: {output_path}")
                return True
            return False
        except Exception as e:
            logging.error(f"保存文件时出错: {str(e)}")
            return False

def main():
    parser = argparse.ArgumentParser(description='从PDF文件中提取文本内容，并去除页眉页脚')
    parser.add_argument('input_pdf', help='输入PDF文件路径')
    parser.add_argument('output_txt', help='输出文本文件路径')
    parser.add_argument('--header-threshold', type=float, default=0.2,
                        help='页眉区域阈值 (0-1之间的小数，默认0.2)')
    parser.add_argument('--footer-threshold', type=float, default=0.8,
                        help='页脚区域阈值 (0-1之间的小数，默认0.8)')
    args = parser.parse_args()

    # 验证阈值参数
    if not (0 < args.header_threshold < args.footer_threshold < 1):
        logging.error("无效的页眉页脚阈值设置")
        return

    extractor = PDFExtractor(args.input_pdf)
    extractor.header_threshold = args.header_threshold
    extractor.footer_threshold = args.footer_threshold

    if extractor.save_to_file(args.output_txt):
        logging.info(f"文本提取成功完成")
    else:
        logging.error("文本提取失败")

if __name__ == '__main__':
    main()