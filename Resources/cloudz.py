#!/usr/bin/env python3

"""
Cloudz

profiles for web browsing

Author: darkoverlordofdata@gmail.com
"""

import sys
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QDesktopWidget, QWidget, QPushButton,
                             QCheckBox, QGroupBox, QRadioButton,
                             QLabel, QLineEdit,QTextEdit, QGridLayout,
                             QHBoxLayout, QVBoxLayout, QApplication)

class Cloudz(QWidget):

    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):

        webUrl = QLabel('Web Url')
        appName = QLabel('App Name')
        iconPath = QLabel('Icon')

        webUrlEdit = QLineEdit()
        appNameEdit = QLineEdit()
        iconPathEdit = QLineEdit()

        grid = QGridLayout()
        grid.setSpacing(10)

        grid.addWidget(webUrl, 1, 0)
        grid.addWidget(webUrlEdit, 1, 1)

        grid.addWidget(appName, 2, 0)
        grid.addWidget(appNameEdit, 2, 1)

        cb = QCheckBox('FavIcon?', self)
        cb.move(20, 20)
        cb.toggle()
        cb.stateChanged.connect(self.useFavIcon)
        grid.addWidget(cb, 3, 1)

        grid.addWidget(iconPath, 4, 0)
        grid.addWidget(iconPathEdit, 4, 1)

        grid.addWidget(self.createBrowserGroup(), 5, 1)

        cancelButton = QPushButton("Cancel")
        okButton = QPushButton("Create")

        hbox = QHBoxLayout()
        hbox.addStretch(1)
        hbox.addWidget(okButton)
        hbox.addWidget(cancelButton)

        vbox = QVBoxLayout()
        vbox.addStretch(1)
        vbox.addLayout(grid)
        vbox.addLayout(hbox)

        self.setLayout(vbox)

        self.setGeometry(0, 0, 500, 280)
        self.center()
        self.setWindowTitle('Create Cloud App')
        self.show()


    def useFavIcon(self, state):
        pass
        

    def createBrowserGroup(self):
        groupBox = QGroupBox("Select Browser:")

        radio1 = QRadioButton("&Chrome")
        radio2 = QRadioButton("C&hromium")
        radio3 = QRadioButton("&Vivaldi")
        radio4 = QRadioButton("&Firefox")

        radio1.setChecked(True)

        vbox = QVBoxLayout()
        vbox.addWidget(radio1)
        vbox.addWidget(radio2)
        vbox.addWidget(radio3)
        vbox.addWidget(radio4)
        vbox.addStretch(1)
        groupBox.setLayout(vbox)

        return groupBox


    def center(self):

        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())


def main():
    app = QApplication(sys.argv)
    ex = Cloudz()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()