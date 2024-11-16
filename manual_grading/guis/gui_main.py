import os
import sys
from PySide2.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QFileDialog, QMessageBox, QLineEdit


import utils.utl_write_team_students_csv as wcsv


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Team CSV Writer")
        self.setGeometry(100, 100, 300, 200)

        main_widget = MainWidget()

        self.setCentralWidget(main_widget)


class MainWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.__init_ui()
        self.ghc_csv = ""
        self.output_dir = ""
        self.students_txt = ""

    def __init_ui(self):
        layout = QVBoxLayout()
        
        btn_ghc_csv = QPushButton("Open GitHub Classroom CSV")
        btn_ghc_csv.clicked.connect(self.btn_ghc_csv_clicked)

        btn_output_dir = QPushButton("Open Output Directory")
        btn_output_dir.clicked.connect(self.btn_output_dir_clicked)
        
        self.le_output_filename = QLineEdit()
        self.le_output_filename.setText("output-filename")

        btn_students_txt = QPushButton("Open Students TXT")
        btn_students_txt.clicked.connect(self.btn_students_txt_clicked)
        
        btn_generate_csv = QPushButton("Generate Team CSV")
        btn_generate_csv.clicked.connect(self.btn_generate_csv_clicked)

        layout.addWidget(self.le_output_filename)
        layout.addWidget(btn_output_dir)
        layout.addWidget(btn_ghc_csv)
        layout.addWidget(btn_students_txt)
        layout.addWidget(btn_generate_csv)

        self.setLayout(layout)

    def btn_ghc_csv_clicked(self):
        fd = QFileDialog()
        fd.setFileMode(QFileDialog.ExistingFile)
        self.ghc_csv, _ = fd.getOpenFileName(self, "Open GHC CSV", os.getcwd(), "CSV Files (*.csv)")

    def btn_output_dir_clicked(self):
        fd = QFileDialog()
        fd.setFileMode(QFileDialog.Directory)
        self.output_dir = fd.getExistingDirectory(self, "Open Output Directory", os.getcwd())

    def btn_students_txt_clicked(self):
        fd = QFileDialog()
        fd.setFileMode(QFileDialog.ExistingFile)
        self.students_txt, _ = fd.getOpenFileName(self, "Open Students TXT", os.getcwd(), "TXT Files (*.txt)")
    
    def btn_generate_csv_clicked(self):
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Warning")
        if self.output_dir == "" or self.ghc_csv == "" or self.students_txt == "" or self.le_output_filename.text() == "":
            msg_box.setText("Output dir, filename, GHC CSV, or Student TXT was empty.")
            msg_box.exec_()
        elif self.output_dir == self.ghc_csv:
            msg_box.setText("Output CSV matches GHC CSV.")
            msg_box.exec_()
        else:
            output_file = f"{self.output_dir}/{self.le_output_filename.text()}.csv"
            print(f"Output file path is: {output_file}")
            if " " in self.le_output_filename.text():
                msg_box.setText("The output filename may not contain any spaces.")
                msg_box.exec_()
            else:
                wcsv.write_student_data_to_csv(output_file, self.ghc_csv, self.students_txt)
                success_window = QMessageBox()
                success_window.setWindowTitle("Success")
                success_window.setText(f"Success! File: {self.le_output_filename.text()}.csv output in: {output_file}")
                success_window.exec_()
        

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
