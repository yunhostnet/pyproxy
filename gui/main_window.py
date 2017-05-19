import traceback
import urllib.request

from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton, QVBoxLayout, QMessageBox, \
    QFileDialog

from gui.plugins import PLUGINS
from gui.plugins.plugin_registry import PluginRegistry
from gui.widgets.connection_config import ConnectionConfig
from gui.widgets.http_messages_tabs import HttpMessagesTabs
from gui.widgets.http_messages_tree_view import HttpMessagesTreeView
from gui.worker import Worker
from parser.http_parser import HttpMessage
from pipe.apipe import ProxyParameters
from pipe.communication import RequestResponse
from pipe.persistence import parse_message_pairs, serialize_message_pairs


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.plugin_registry = PluginRegistry()
        self.plugin_registry.plugins = PLUGINS

        self.setGeometry(300, 300, 750, 750)
        self.setWindowTitle('PyProxy')

        self.parameters = ProxyParameters("localhost", 8888, "www.httpwatch.com", 80)

        self.worker = Worker(self.parameters)

        self.settings = QSettings("MyCompany", "MyApp")
        if self.settings.value("geometry", None):
            self.restoreGeometry(self.settings.value("geometry"))

        self.initUI()

    def initUI(self):
        self.connection_config = ConnectionConfig(self.parameters, self)
        self.connection_config.changed.connect(self.worker.setParameters)
        self.connection_config.restoreSettings(self.settings)

        self.startButton = QPushButton("Start")
        self.stopButton = QPushButton("Stop")
        self.restartButton = QPushButton("Restart")
        self.requestButton = QPushButton("Request")
        self.saveButton = QPushButton("Save")
        self.loadButton = QPushButton("Load")

        self.startButton.clicked.connect(self.onStartClicked)
        self.stopButton.clicked.connect(self.onStopClicked)
        self.restartButton.clicked.connect(self.onRestartClicked)
        self.requestButton.clicked.connect(self.onRequestClicked)
        self.saveButton.clicked.connect(self.onSaveClicked)
        self.loadButton.clicked.connect(self.onLoadClicked)
        self.worker.received.connect(self.onReceived)
        self.worker.error.connect(self.onError)
        self.worker.running_changed.connect(self.update_status)

        hbox = QHBoxLayout()
        hbox.addWidget(self.startButton)
        hbox.addWidget(self.stopButton)
        hbox.addWidget(self.restartButton)
        hbox.addWidget(self.requestButton)
        hbox.addWidget(self.saveButton)
        hbox.addWidget(self.loadButton)

        self.treeView = HttpMessagesTreeView(self.plugin_registry, self)
        self.treeView.selected.connect(self.onMessageSelected)

        self.tabs = HttpMessagesTabs(self.plugin_registry)

        vbox = QVBoxLayout()
        vbox.addWidget(self.connection_config)
        vbox.addLayout(hbox)
        vbox.addWidget(self.treeView)
        vbox.addWidget(self.tabs)

        self.setLayout(vbox)
        self.show()

        self.update_status(self.worker.status())

    def onStartClicked(self, event):
        self.worker.start()

    def onStopClicked(self, event):
        self.worker.stop()

    def onRestartClicked(self, event):
        self.worker.stop()
        self.treeView.clear()
        self.worker.start()

    def onRequestClicked(self):
        try:
            urllib.request.urlopen("http://{}:{}".format(self.parameters.local_address, self.parameters.local_port))
        except Exception as e:
            print(traceback.format_exc())
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("The request resulted in an error:")
            msg.setInformativeText(str(e))
            msg.setWindowTitle("Error")
            msg.exec_()

    def onSaveClicked(self, event):
        file_name = QFileDialog.getSaveFileName(self, 'Save HTTP messages', '.', filter='*.http')[0]
        if not file_name:
            return

        if not file_name.endswith(".http"):
            file_name += ".http"

        self.save(file_name)


    def onLoadClicked(self, event):
        file_name = QFileDialog.getOpenFileName(self, 'Save HTTP messages', '.', filter='*.http')[0]
        if file_name:
            self.load(file_name)

    def load(self, file_name):
        f = open(file_name, "rb")
        for pair in parse_message_pairs(f):
            self.onReceived(pair)
        f.close()

    def save(self, file_name):
        f = open(file_name, "wb")
        serialize_message_pairs(self.treeView.getAllMessagePairs(), f)
        f.close()

    def closeEvent(self, QCloseEvent):
        if self.worker.status():
            self.worker.stop()

        self.settings.setValue("geometry", self.saveGeometry())
        self.connection_config.saveSettings(self.settings)
        super().closeEvent(QCloseEvent)

    def onReceived(self, rr: RequestResponse):
        self.treeView.onRequestResponse(rr)

    def onError(self, e: Exception):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText("There was an error:")
        msg.setInformativeText(str(e))
        msg.setWindowTitle("Error")
        msg.exec_()

    def onMessageSelected(self, message: HttpMessage):
        self.tabs.onMessageSelected(message)

    def update_status(self, status):
        self.startButton.setDisabled(status)
        self.stopButton.setDisabled(not status)
        self.restartButton.setDisabled(not status)
        # self.requestButton.setDisabled(not status)
