#!/usr/bin/env python
# -*- coding: utf-8 -*-
# fcaption: simple image caption editor
# Copyright(c) 2015-2016 by wave++ "Yuri D'Elia" <wavexx@thregr.org>
#
# Forked 2021. because original fgallery GH repo is "Archived"
#  - move to PyQt5
#  - avoid recusing directories
#  - avoid relying on file extensions to identify images
#  - presentation order to follow exif timestamps

from __future__ import unicode_literals, generators, print_function

import os, sys
import argparse
import locale
import magic
from exif import Image

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

APP_DESC = "fgallery image caption editor"
ENCODING = locale.getpreferredencoding()
# FILE_EXT = ["jpg", "jpeg", "png", "tif", "tiff"]

if sys.version_info.major < 3:
    str = unicode


class ScaledImage(QLabel):
    def __init__(self):
        super(ScaledImage, self).__init__()
        self._pixmap = QPixmap()

    def setPixmap(self, pixmap):
        self._pixmap = pixmap
        if not pixmap.isNull():
            pixmap = pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        super(ScaledImage, self).setPixmap(pixmap)

    def resizeEvent(self, ev):
        super(ScaledImage, self).resizeEvent(ev)
        if not self._pixmap.isNull():
            pixmap = self._pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            super(ScaledImage, self).setPixmap(pixmap)


class BackgroundLoader(QThread):
    def __init__(self, path, size):
        super(BackgroundLoader, self).__init__()
        self.path = path
        self.size = size
        self.image = None

    def run(self):
        self.image = QImage(self.path)
        if not self.image.isNull() and self.size:
            self.image = self.image.scaled(self.size,
                                           Qt.KeepAspectRatio,
                                           Qt.SmoothTransformation)


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle(APP_DESC)

        # construct UI
        horizontalSplitter = QSplitter(Qt.Horizontal)
        verticalSplitter = QSplitter(Qt.Vertical)
        self.image = ScaledImage()
        self.image.setMinimumSize(480, 319)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(1)
        self.image.setSizePolicy(sizePolicy)
        self.image.setAlignment(Qt.AlignCenter)
        verticalSplitter.addWidget(self.image)
        horizontalLayout = QHBoxLayout()
        formLayout = QFormLayout()
        formLayout.setLabelAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)
        formLayout.setWidget(0, QFormLayout.LabelRole, QLabel("Title:"))
        self.edit_title = QLineEdit()
        formLayout.setWidget(0, QFormLayout.FieldRole, self.edit_title)
        formLayout.setWidget(1, QFormLayout.LabelRole, QLabel("Description:"))
        self.edit_desc = QPlainTextEdit()
        self.edit_desc.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(1)
        self.edit_desc.setSizePolicy(sizePolicy)
        formLayout.setWidget(1, QFormLayout.FieldRole, self.edit_desc)
        horizontalLayout.addLayout(formLayout)
        verticalLayout = QVBoxLayout()
        verticalLayout.setSizeConstraint(QLayout.SetMinimumSize)
        self.btn_next = QPushButton("&Next")
        verticalLayout.addWidget(self.btn_next)
        self.btn_undo = QPushButton("&Undo")
        verticalLayout.addWidget(self.btn_undo)
        self.btn_prev = QPushButton("&Previous")
        verticalLayout.addWidget(self.btn_prev)
        horizontalLayout.addLayout(verticalLayout)
        widget = QWidget()
        widget.setLayout(horizontalLayout)
        verticalSplitter.addWidget(widget)
        horizontalSplitter.addWidget(verticalSplitter)
        self.list_files = QListWidget()
        self.list_files.setIconSize(QSize(64, 64))
        horizontalSplitter.addWidget(self.list_files)
        self.setCentralWidget(horizontalSplitter)

        # signals
        self.list_files.itemActivated.connect(self.on_list)
        self.btn_next.clicked.connect(self.on_next)
        self.btn_prev.clicked.connect(self.on_prev)
        self.btn_undo.clicked.connect(self.on_undo)
        self.edit_title.textEdited.connect(self.on_changed)
        self.edit_desc.textChanged.connect(self.on_changed)

        # initial state
        self.files = list()
        self.missing_thumbs = list()
        self.current = 0
        self.modified = False

    def on_next(self, ev):
        if self.modified: self.save()
        self.load((self.current + 1) % len(self.files))

    def on_prev(self, ev):
        if self.modified: self.save()
        self.load((self.current - 1) % len(self.files))

    def on_list(self, ev):
        if self.modified: self.save()
        self.load(self.list_files.currentRow())

    def on_undo(self, ev):
        self.load(self.current)

    def thumb_ready(self, thread, idx, path):
        icon = thread.image
        if not icon.isNull():
            crow = self.list_files.currentRow()
            item = self.list_files.takeItem(idx)
            item.setIcon(QIcon(QPixmap(icon)))
            self.list_files.insertItem(idx, item)
            self.list_files.setCurrentRow(crow)
        self.thumb_schedule()

    def thumb_schedule(self):
        if not self.missing_thumbs: return
        idx, path = self.missing_thumbs.pop(0)
        thread = BackgroundLoader(path, self.list_files.iconSize())
        thread.finished.connect(lambda: self.thumb_ready(thread, idx, path))
        thread.start()

    def set_files(self, files):
        self.files = list(files)
        self.list_files.clear()
        self.missing_thumbs = list(enumerate(files))
        for path in files:
            self.list_files.addItem(os.path.basename(path))
        if len(files) < 2:
            self.list_files.hide()
            self.btn_next.setEnabled(False)
            self.btn_prev.setEnabled(False)
        else:
            self.list_files.show()
            self.thumb_schedule()
            self.btn_next.setEnabled(True)
            self.btn_prev.setEnabled(True)
        self.load(0)

    def on_changed(self, *_):
        self.modified = True

    def load(self, idx):
        self.current = idx
        self.list_files.setCurrentRow(idx)

        path = self.files[idx]
        pixmap = QPixmap(path)
        if pixmap.isNull():
            self.image.setPixmap(pixmap)
            self.image.setText('Cannot load {}'.format(path))
            self.edit_title.setEnabled(False)
            self.edit_desc.setEnabled(False)
            return

        self.image.clear()
        self.image.setPixmap(pixmap)

        self.edit_title.clear()
        self.edit_desc.clear()
        self.edit_title.setEnabled(True)
        self.edit_desc.setEnabled(True)

        base, _ = os.path.splitext(path)
        txt = base + '.txt'
        if os.path.isfile(txt):
            data = open(txt, 'rb').read().decode(ENCODING).split('\n', 1)
            if len(data) > 0:
                self.edit_title.setText(data[0].strip())
            if len(data) > 1:
                self.edit_desc.setPlainText(data[1].strip())

        self.modified = False
        self.edit_title.setFocus()

    def save(self):
        title = str(self.edit_title.text()).strip()
        desc = str(self.edit_desc.toPlainText()).strip()
        base, _ = os.path.splitext(self.files[self.current])
        txt = base + '.txt'
        if len(title) + len(desc) == 0:
            if os.path.isfile(txt):
                os.remove(txt)
        else:
            data = title + '\n' + desc
            open(txt, 'wb').write(data.encode(ENCODING))

    def closeEvent(self, ev):
        if self.modified: self.save()
        super(MainWindow, self).closeEvent(ev)

# put files in exif datetime order
def exif_sort(files):
    datetime = {}
    for tmp in files:
        with open(tmp, 'rb') as image_file:
            exif = Image(image_file)

            # datetime[
                # min(
                    # exif.get('datetime_original'),
                    # exif.get('datetime')
                    #, exif.get('datetime_digitized')
                    #, os.stat(image_file)

                # ) + '_' + tmp] = tmp   # guard for same exact time

            datetime[
                exif.datetime_original + "." +
                exif.subsec_time_original + '_' + tmp] = tmp

    return [datetime[k] for k in  sorted(datetime.keys())]


# main application
def expand_dir(path):

    # for root, dirs, files in os.walk(path):
    for tmp in os.scandir(path):
        # filter for image files despite extension
        if tmp.is_file() and magic.from_file(tmp.path, mime=True)[:5] == 'image':
            #print(tmp.name)
            yield tmp.path


class Application(QApplication):
    def __init__(self, args):
        super(Application, self).__init__(args)

        # command-line flags
        ap = argparse.ArgumentParser(description=APP_DESC)
        ap.add_argument(
            'files', metavar="image", nargs='*',
             help='image or directory to caption')
        args = ap.parse_args(map(str, args[1:]))

        # ask for a directory if no files were specified
        if not args.files:
            path = QFileDialog.getExistingDirectory(
                None, "Select an image directory")
            if not path: sys.exit(1)
            args.files = [str(path)]

        # expand directories to files
        files = []
        for path in args.files:
            if not os.path.isdir(path):
                files.append(path)
            else:
                files.extend(expand_dir(path))

        # files.sort()  # lexical sort by filename
        files = exif_sort(files)  # chronologically by creation date

        if not files:
            print("no files to caption", file=sys.stderr)
            sys.exit(1)

        # initialize
        self.main_window = MainWindow()
        self.main_window.set_files(files)
        self.main_window.show()

if __name__ == '__main__':
    app = Application(sys.argv)
    sys.exit(app.exec_())
