import sys
import os
import h5py
from PyQt5.QtWidgets import (QApplication, QMainWindow, QDialog, QTreeWidget, QTreeWidgetItem, QTableWidget, 
                             QTableWidgetItem, QVBoxLayout, QWidget, QFileDialog, QMenuBar, QMenu, 
                             QAction, QSplitter, QHeaderView, QMessageBox, QPushButton, QLabel, 
                             QLineEdit, QHBoxLayout, QComboBox, QFormLayout, QProgressBar, QTextEdit)
from PyQt5.QtCore import Qt

class HDF5Viewer(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("HDF5 Tool")
        self.setGeometry(100, 100, 1000, 600)

        # 创建菜单栏
        self.menu_bar = self.menuBar()
        file_menu = self.menu_bar.addMenu('File')
        save_menu = self.menu_bar.addMenu('save')
        
        # 打开文件选项
        open_file_action = QAction('Open File', self)
        open_file_action.triggered.connect(self.open_file)
        file_menu.addAction(open_file_action)
        
        # 创建Batch菜单
        batch_menu = self.menu_bar.addMenu('Batch')
        
        # 批量导出选项
        batch_export_action = QAction('批量导出', self)
        batch_export_action.triggered.connect(self.batch_export_menu)
        batch_menu.addAction(batch_export_action)

        # 批量修改选项
        batch_modify_action = QAction('批量修改', self)
        batch_modify_action.triggered.connect(self.batch_modify)
        batch_menu.addAction(batch_modify_action)
        
        # 创建工具栏并添加保存按钮
        #self.toolbar = QToolBar("Main Toolbar")
        #self.addToolBar(self.toolbar)

        # 创建保存按钮
        save_action = QAction("Save", self)
        save_action.triggered.connect(self.save_changes)
        save_menu.addAction(save_action)

        # 创建一个分割器，用于左侧和右侧布局
        self.splitter = QSplitter(self)
        self.setCentralWidget(self.splitter)

        # 左侧：树状视图，用于显示HDF5文件结构
        self.tree = QTreeWidget()
        self.tree.setColumnCount(1)
        self.tree.setHeaderLabels(["HDF5 Structure"])
        self.tree.itemClicked.connect(self.on_item_clicked)
        self.splitter.addWidget(self.tree)

        # 右侧：表格视图，用于显示属性
        self.table = QTableWidget()
        self.table.itemChanged.connect(self.on_item_changed)  # 监听表格编辑事件
        self.splitter.addWidget(self.table)

        # 设置自适应布局，保证表格内容填满右侧窗口
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # 调整分割器比例，左侧较小，右侧较大
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 4)

        # 用于记录当前选中的节点
        self.current_node = None
        self.pass_node = None
        self.attributes_modified = False  # 追踪是否有属性被修改
        self.modified_attributes = {}  # 存储修改的属性

        # 存储已打开的数据窗口引用，避免多次打开
        self.data_windows = []

    def open_file(self):
        """打开文件选择对话框并加载 HDF5 文件"""
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Open HDF5 File", "", "HDF5 Files (*.h5 *.hdf5);;All Files (*)", options=options)

        # 尝试打开文件并处理异常
        if file_name:
            try:
                self.load_hdf5_file(file_name)
            except (OSError, KeyError) as e:
                # 弹出提示框告知用户文件无法打开或损坏
                QMessageBox.critical(self, "文件错误", f"文件无法打开或已损坏。\n错误信息: {str(e)}")

    def batch_export_menu(self):
        """显示批量导出的窗口"""
        self.export_window = QWidget()
        self.export_window.setWindowTitle("批量导出")
        self.export_window.setGeometry(300, 300, 600, 200)

        layout = QVBoxLayout()

        # 第一栏：选择文件夹
        folder_layout = QHBoxLayout()
        self.folder_line_edit = QLineEdit()
        folder_button = QPushButton("选择文件夹")
        folder_button.clicked.connect(self.select_folder)
        folder_layout.addWidget(QLabel("源文件夹:"))
        folder_layout.addWidget(self.folder_line_edit)
        folder_layout.addWidget(folder_button)

        # 第二栏：选择导出目录
        export_layout = QHBoxLayout()
        self.export_folder_line_edit = QLineEdit()
        export_button = QPushButton("选择导出文件夹")
        export_button.clicked.connect(self.select_export_folder)
        export_layout.addWidget(QLabel("导出文件夹:"))
        export_layout.addWidget(self.export_folder_line_edit)
        export_layout.addWidget(export_button)

        # 第三栏：输入文件后缀名
        suffix_layout = QHBoxLayout()
        self.suffix_line_edit = QLineEdit()
        suffix_layout.addWidget(QLabel("文件后缀名:"))
        suffix_layout.addWidget(self.suffix_line_edit)
        
        # 第四栏：进度条和显示框
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setValue(0)
        self.progress_text_edit = QTextEdit()
        self.progress_text_edit.setReadOnly(True)
        
        # 导出按钮
        export_button = QPushButton("导出")
        export_button.clicked.connect(self.run_batch_export)

        layout.addLayout(folder_layout)
        layout.addLayout(export_layout)
        layout.addLayout(suffix_layout)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.progress_text_edit)
        layout.addWidget(export_button)

        self.export_window.setLayout(layout)
        self.export_window.show()

    def select_folder(self):
        """选择源文件夹"""
        folder = QFileDialog.getExistingDirectory(self, "选择源文件夹")
        if folder:
            self.folder_line_edit.setText(folder)

    def select_export_folder(self):
        """选择导出文件夹"""
        folder = QFileDialog.getExistingDirectory(self, "选择导出文件夹")
        if folder:
            self.export_folder_line_edit.setText(folder)

    def run_batch_export(self):
        """批量导出 HDF5 文件中的数据集并保存为 txt 文件"""
        folder = self.folder_line_edit.text()
        export_folder = self.export_folder_line_edit.text()
        suffix = self.suffix_line_edit.text()

        if not folder or not export_folder or not suffix:
            QMessageBox.warning(self, "输入错误", "请填写所有字段")
            return

        # 获取符合后缀名的文件数量，初始化进度条
        total_files = sum([len([f for f in files if f.endswith(f".{suffix}")]) for _, _, files in os.walk(folder)])
        self.progress_bar.setMaximum(total_files)

        file_count = 0  # 记录成功导出的文件数量

        # 遍历文件夹中的 HDF5 文件
        for root, dirs, files in os.walk(folder):
            for file in files:
                if file.endswith(f".{suffix}"):
                    file_path = os.path.join(root, file)
                    try:
                        with h5py.File(file_path, 'r') as hdf_file:
                            for dataset_name in hdf_file:
                                dataset = hdf_file[dataset_name]
                                # 导出数据集内容为txt
                                self.export_dataset_to_txt(dataset, export_folder, dataset_name)
                        file_count += 1
                        self.progress_text_edit.append(f"已导出文件: {file}")
                    except Exception as e:
                        self.progress_text_edit.append(f"文件 {file} 导出失败: {str(e)}")
                
                # 更新进度条
                self.progress_bar.setValue(file_count)

        # 导出完成，显示导出文件的数量
        QMessageBox.information(self, "导出完成", f"批量导出已完成，共导出 {file_count} 个文件")
    
    def export_dataset_to_txt(self, dataset, export_folder, dataset_name):
        """将数据集导出为 txt 文件"""
        file_name = os.path.join(export_folder, f"{dataset_name}.txt")
        with open(file_name, 'w') as txt_file:
            if dataset.ndim == 1:
                # 一维数组
                for item in dataset:
                    txt_file.write(f"{item}\n")
            elif dataset.ndim == 2:
                # 二维数组
                for row in dataset:
                    txt_file.write("\t".join(map(str, row)) + "\n")
            else:
                QMessageBox.warning(self, "导出失败", f"数据集 {dataset_name} 超出了二维数组范围，无法导出。")

    def batch_modify(self):
        """显示批量修改的窗口"""
        self.modify_window = QWidget()
        self.modify_window.setWindowTitle("批量修改")
        self.modify_window.setGeometry(300, 300, 600, 400)

        layout = QVBoxLayout()

        # 第一栏：选择文件夹
        folder_layout = QHBoxLayout()
        self.folder_line_edit = QLineEdit()
        folder_button = QPushButton("选择文件夹")
        folder_button.clicked.connect(self.select_folder)
        folder_layout.addWidget(QLabel("文件夹:"))
        folder_layout.addWidget(self.folder_line_edit)
        folder_layout.addWidget(folder_button)

        # 第二栏：输入后缀名
        suffix_layout = QHBoxLayout()
        self.suffix_line_edit = QLineEdit()
        suffix_layout.addWidget(QLabel("筛选后缀名:"))
        suffix_layout.addWidget(self.suffix_line_edit)

        # 第三栏：输入需要修改的属性名和属性值
        form_layout = QFormLayout()
        self.attr_name_edit = QLineEdit()
        self.attr_value_edit = QLineEdit()
        form_layout.addRow(QLabel("属性名:"), self.attr_name_edit)
        form_layout.addRow(QLabel("属性值:"), self.attr_value_edit)

        # Run按钮
        run_button = QPushButton("Run")
        run_button.clicked.connect(self.run_batch_modify)

        layout.addLayout(folder_layout)
        layout.addLayout(suffix_layout)
        layout.addLayout(form_layout)
        layout.addWidget(run_button)

        self.modify_window.setLayout(layout)
        self.modify_window.show()

    def select_folder(self):
        """选择文件夹"""
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder:
            self.folder_line_edit.setText(folder)

    def run_batch_modify(self):
        """执行批量修改"""
        folder = self.folder_line_edit.text()
        suffix = self.suffix_line_edit.text()
        attr_name = self.attr_name_edit.text()
        attr_value = self.attr_value_edit.text()

        if not folder or not attr_name or not attr_value:
            QMessageBox.warning(self, "输入错误", "请填写所有字段")
            return

        # 遍历文件夹中的文件并进行批量修改
        for root, dirs, files in os.walk(folder):
            for file in files:
                if file.endswith(f".{suffix}"):
                    file_path = os.path.join(root, file)
                    try:
                        with h5py.File(file_path, 'r+') as f:
                            for key in f.keys():
                                obj = f[key]
                                if attr_name in obj.attrs:
                                    obj.attrs.modify(attr_name, attr_value)
                                else:
                                    obj.attrs[attr_name] = attr_value
                    except Exception as e:
                        QMessageBox.warning(self, "修改失败", f"文件 {file} 修改失败。错误: {str(e)}")

        # 弹出提示框表示已完成
        QMessageBox.information(self, "操作完成", "批量修改已完成")

    def batch_process_files(self):
        """批量处理文件的逻辑（可以根据具体需求实现）"""
        print("Batch processing files...")  # 占位符，您可以添加批量处理的逻辑

    def load_hdf5_file(self, file_name):
        """加载 HDF5 文件并在树状视图中显示其结构"""
        try:
            self.hdf5_file = h5py.File(file_name, 'r+')  # 'r+'模式，允许读取和写入
        except (OSError, KeyError) as e:
            raise  # 如果文件无法打开，抛出异常以便在 open_file 中处理
        
        self.tree.clear()  # 清空之前的树状视图
        self.populate_tree(self.hdf5_file)

    def populate_tree(self, hdf5_file):
        """递归加载HDF5文件中的所有组和数据集到树状视图"""
        def add_items(parent, group):
            for key in group:
                item = QTreeWidgetItem(parent)
                item.setText(0, key)
                if isinstance(group[key], h5py.Group):
                    add_items(item, group[key])  # 递归加载组
                    item.setData(0, 1, group[key])  # 关联组到节点
                elif isinstance(group[key], h5py.Dataset):
                    # 对于数据集，创建一个“data”子节点
                    item.setData(0, 1, group[key])  # 将数据集关联到节点
                else:
                    item.setData(0, 1, group[key])  # 将数据集关联到树节点
        
        root = self.tree.invisibleRootItem()
        add_items(root, hdf5_file)

    def on_item_clicked(self, item, column):
        """点击树状视图中的数据集或组时，显示其属性"""
        node = item.data(0, 1)
        self.current_node = node
        if isinstance(node, h5py.Group):
            self.show_attributes(node)  # 只显示组的属性
        elif isinstance(node, h5py.Dataset):
            self.show_attributes(node)  # 显示数据集的属性
            # 弹出分页数据窗口
            self.show_dataset_data(node)
        self.attributes_modified = False  # 每次点击新节点时，重置修改标志
        self.modified_attributes.clear()  # 清空修改的属性字典

    def show_attributes(self, node):
        """在表格视图中显示组或数据集的属性，并铺满右侧区域"""
        self.table.blockSignals(True)  # 暂时停止信号，避免编辑事件干扰
        self.table.clear()
        self.table.setRowCount(len(node.attrs))
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Attribute", "Value"])

        # 填充表格数据
        for i, (key, value) in enumerate(node.attrs.items()):
            self.table.setItem(i, 0, QTableWidgetItem(str(key)))
            self.table.setItem(i, 1, QTableWidgetItem(str(value)))

        # 让表格内容铺满整个右侧窗口
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.blockSignals(False)  # 重新启动信号

    def show_dataset_data(self, dataset):
        """弹出分页显示数据的窗口"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Dataset Data")
        dialog.setGeometry(100, 100, 600, 400)

        layout = QVBoxLayout()
        dialog.setLayout(layout)

        label = QLabel(f"Dataset: {dataset.name}")
        layout.addWidget(label)

        table = QTableWidget()
        layout.addWidget(table)

        # 分页按钮
        next_button = QPushButton("Next Page")
        layout.addWidget(next_button)

        # 显示第一页数据
        self.current_page = 0
        self.items_per_page = 100  # 每页显示的数据条数
        self.display_page(table, dataset, self.current_page)

        def on_next():
            """翻到下一页"""
            self.current_page += 1
            self.display_page(table, dataset, self.current_page)

        next_button.clicked.connect(on_next)

        dialog.exec_()
        
    def display_page(self, table, dataset, page):
        """在弹出窗口中显示数据集的某一页数据"""
        table.clear()

        start = page * self.items_per_page
        end = min(start + self.items_per_page, dataset.size)

        if len(dataset.shape) == 1:
            table.setRowCount(end - start)
            table.setColumnCount(1)
            table.setHorizontalHeaderLabels([f"Data (Page {page + 1})"])
            for i in range(start, end):
                table.setItem(i - start, 0, QTableWidgetItem(str(dataset[i])))
        elif len(dataset.shape) == 2:
            rows, cols = dataset.shape
            table.setRowCount(min(self.items_per_page, rows))
            table.setColumnCount(cols)
            table.setHorizontalHeaderLabels([f"Column {i + 1}" for i in range(cols)])
            for i in range(start, end):
                for j in range(cols):
                    table.setItem(i - start, j, QTableWidgetItem(str(dataset[i, j])))

        
    def on_item_changed(self, item):
        """捕捉用户修改属性值的事件并询问是否保存"""
       
        print(self.current_node)
        #if (self.current_node is None):
            
        if item.column() == 1 and self.current_node is not None:
            print("xuigau")
            attribute_name = self.table.item(item.row(), 0).text()
            new_value = item.text()

            # 弹出保存确认框
            reply = QMessageBox.question(
                self, "属性值已修改",
                f"您修改了属性 '{attribute_name}' 的值为 '{new_value}'，是否保存更改？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # 保存新的属性值到HDF5文件
                self.current_node.attrs.modify(attribute_name, new_value)
                self.attributes_modified = True
            else:
                # 如果不保存，则恢复为旧值
                old_value = str(self.current_node.attrs[attribute_name])
                self.table.blockSignals(True)
                item.setText(old_value)
                self.table.blockSignals(False)
                
    def save_changes(self):
        """保存修改的属性值到HDF5文件"""
        if self.current_node is not None and self.attributes_modified:
            for attribute_name, new_value in self.modified_attributes.items():
                # 将修改的属性值保存到HDF5文件
                self.current_node.attrs.modify(attribute_name, new_value)

            QMessageBox.information(self, "保存成功", "所有修改的属性值已成功保存。")
            self.attributes_modified = False  # 重置修改标志
        else:
            QMessageBox.information(self, "无修改", "没有修改需要保存。")

# 主程序入口
if __name__ == '__main__':
    app = QApplication(sys.argv)
    viewer = HDF5Viewer()
    viewer.show()
    sys.exit(app.exec_())
