from cx_Freeze import setup, Executable

# 定义可执行文件及其相关的参数
executables = [
    Executable(
        script="hdf5_tool.py",  
        base="Win32GUI", 
        target_name="HDF5Tool.exe", 
    )
]

# 设置打包选项
build_options = {
    'packages': ['os', 'sys', 'h5py', 'PyQt5'], 
    'include_files': [], 
    'excludes': [], 
}

setup(
    name="HDF5Tool", 
    version="1.0.0", 
    description="读取HDF5文件并批量修改参数的小工具",  
    options={"build_exe": build_options},  
    executables=executables  
)
