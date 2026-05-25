"""
BNOS 打包工具类 - 负责节点和项目的压缩/解压操作
支持自定义扩展名 .bnos（节点包）和 .bnosc（项目包）
"""
import os
import zipfile
import shutil
import tempfile
from ui.core.logger import logger


class Packager:
    """压缩打包工具类"""
    
    BNOS_EXTENSION = ".bnos"
    BNOSC_EXTENSION = ".bnosc"
    ZIP_EXTENSION = ".zip"
    
    @staticmethod
    def compress_directory(source_dir, output_path, custom_extension=None):
        """
        压缩目录并可选添加自定义扩展名
        
        Args:
            source_dir (str): 要压缩的源目录路径
            output_path (str): 输出文件路径（不含扩展名）
            custom_extension (str): 自定义扩展名，如 ".bnos"
        
        Returns:
            str: 生成的压缩包路径，失败返回 None
        """
        try:
            if not os.path.isdir(source_dir):
                logger.error(f"源目录不存在: {source_dir}")
                return None
            
            # 生成临时ZIP文件
            temp_zip = tempfile.NamedTemporaryFile(suffix=Packager.ZIP_EXTENSION, delete=False)
            temp_zip_path = temp_zip.name
            temp_zip.close()
            
            # 压缩目录（包含空目录）
            with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 获取源目录下的所有文件和目录
                for root, dirs, files in os.walk(source_dir):
                    # 添加空目录
                    for dir_name in dirs:
                        dir_path = os.path.join(root, dir_name)
                        arcname = os.path.relpath(dir_path, source_dir) + os.sep
                        if arcname not in zipf.namelist():
                            zipf.writestr(arcname, '')
                    
                    # 添加文件
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, source_dir)
                        zipf.write(file_path, arcname)
            
            # 添加自定义扩展名
            final_path = output_path + (custom_extension or Packager.ZIP_EXTENSION)
            
            # 如果目标文件已存在，先删除
            if os.path.exists(final_path):
                os.remove(final_path)
            
            # 重命名为最终路径
            shutil.move(temp_zip_path, final_path)
            
            logger.info(f"成功压缩目录: {source_dir} -> {final_path}")
            return final_path
            
        except Exception as e:
            logger.error(f"压缩目录失败: {e}")
            return None
    
    @staticmethod
    def extract_package(package_path, target_dir):
        """
        解压自定义扩展名的压缩包
        
        Args:
            package_path (str): 压缩包路径（支持 .bnos, .bnosc, .zip）
            target_dir (str): 解压目标目录
        
        Returns:
            str: 解压后的根目录路径，失败返回 None
        """
        try:
            if not os.path.exists(package_path):
                logger.error(f"压缩包不存在: {package_path}")
                return None
            
            # 确保目标目录存在
            os.makedirs(target_dir, exist_ok=True)
            
            # 获取原始扩展名
            _, ext = os.path.splitext(package_path)
            
            # 如果是自定义扩展名，创建临时ZIP文件
            if ext in (Packager.BNOS_EXTENSION, Packager.BNOSC_EXTENSION):
                temp_zip_path = tempfile.NamedTemporaryFile(suffix=Packager.ZIP_EXTENSION, delete=False).name
                shutil.copy(package_path, temp_zip_path)
            else:
                temp_zip_path = package_path
            
            # 解压ZIP文件
            with zipfile.ZipFile(temp_zip_path, 'r') as zipf:
                zipf.extractall(target_dir)
            
            # 清理临时文件
            if temp_zip_path != package_path:
                os.remove(temp_zip_path)
            
            # 查找解压后的根目录（假设只有一个顶层目录）
            extracted_items = os.listdir(target_dir)
            if len(extracted_items) == 1:
                root_dir = os.path.join(target_dir, extracted_items[0])
                if os.path.isdir(root_dir):
                    logger.info(f"成功解压: {package_path} -> {root_dir}")
                    return root_dir
            
            logger.info(f"成功解压: {package_path} -> {target_dir}")
            return target_dir
            
        except zipfile.BadZipFile:
            logger.error(f"无效的压缩包: {package_path}")
            return None
        except Exception as e:
            logger.error(f"解压失败: {e}")
            return None
    
    @staticmethod
    def validate_bnos_package(package_path):
        """
        验证 .bnos 节点包格式
        
        Args:
            package_path (str): 节点包路径
        
        Returns:
            bool: 是否为有效节点包
        """
        try:
            if not package_path.endswith(Packager.BNOS_EXTENSION):
                return False
            
            temp_dir = tempfile.mkdtemp()
            extracted_dir = Packager.extract_package(package_path, temp_dir)
            
            if not extracted_dir:
                shutil.rmtree(temp_dir)
                return False
            
            # 检查必需文件
            required_files = ['config.json', 'main.py']
            for req_file in required_files:
                if not os.path.exists(os.path.join(extracted_dir, req_file)):
                    shutil.rmtree(temp_dir)
                    return False
            
            shutil.rmtree(temp_dir)
            return True
            
        except Exception as e:
            logger.error(f"验证节点包失败: {e}")
            return False
    
    @staticmethod
    def validate_bnosc_package(package_path):
        """
        验证 .bnosc 项目包格式
        
        Args:
            package_path (str): 项目包路径
        
        Returns:
            bool: 是否为有效项目包
        """
        try:
            if not package_path.endswith(Packager.BNOSC_EXTENSION):
                return False
            
            temp_dir = tempfile.mkdtemp()
            extracted_dir = Packager.extract_package(package_path, temp_dir)
            
            if not extracted_dir:
                shutil.rmtree(temp_dir)
                return False
            
            # 检查必需文件和目录
            required_items = ['project.json', 'canvas_layout.json', 'nodes']
            for req_item in required_items:
                path = os.path.join(extracted_dir, req_item)
                if not os.path.exists(path):
                    shutil.rmtree(temp_dir)
                    return False
            
            shutil.rmtree(temp_dir)
            return True
            
        except Exception as e:
            logger.error(f"验证项目包失败: {e}")
            return False