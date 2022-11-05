import signal
from PyQt6.QtCore import QDateTime, Qt, QTimer, QCoreApplication
from PyQt6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDateTimeEdit,
        QDial, QDialog, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
        QProgressBar, QPushButton, QRadioButton, QScrollBar, QSizePolicy,
        QSlider, QSpinBox, QStyleFactory, QTableWidget, QTabWidget, QTextEdit,
        QVBoxLayout, QWidget, QStackedWidget, QPlainTextEdit)
import sys
import copy
import datetime
from multiprocessing import Manager, Process, Value, Array
import configparser
import os
from pynput.keyboard import Key, Listener
import pydirectinput as pyd
import time
import psutil

MODE = {
    "Inactivate": "Inactivate",
    "Activate": "Activate"
}
VERSION = 1
CWD_PATH = os.getcwd()
CONFIG = os.path.join(CWD_PATH, "config.ini")
PET_CONFIG = os.path.join(CWD_PATH, "petgroup.ini.ini")


def main():
    with Manager() as manager:
        GROUP_COUNT = manager.list()
        CALL_TIME = manager.list()
        MESSAGE = manager.list()
        TOGGLE = manager.Value("i", 0)
        gui = Process(target=run_gui, args=[MESSAGE, CALL_TIME, GROUP_COUNT, TOGGLE])
        keylogger = Process(target=run_keylogger, args=[MESSAGE, CALL_TIME, GROUP_COUNT, TOGGLE])
        gui.start()
        keylogger.start()

        observer = Process(target=observer_func, args=[gui.pid, keylogger.pid])
        observer.start()

        gui.join()
        keylogger.join()
        observer.join()

def test_GUI():
    message = list()
    run_gui(message)


def run_gui(message, call_time, group_count, toggle):
    app = QApplication([])
    window = UI(message, call_time, group_count, toggle)
    window.show()
    sys.exit(app.exec())


def run_keylogger(message, call_time, group_count, toggle):
    keylogger = Keylogger(message, call_time, group_count, toggle)
    keylogger.run()


class Keylogger:
    def __init__(self, message, call_time, group_count, toggle):
        super().__init__()
        # Shared var
        self.message = message
        self.shared_call_time = call_time
        self.shared_call_time = [time.time()-60, time.time()-60, time.time()-60, time.time()-60]
        self.shared_group_count = group_count
        self.shared_group_count = [1, 1, 1, 1]
        self.shared_toggle = toggle

        self.petconfig = configparser.ConfigParser()
        self.petconfig.read(os.path.join(CWD_PATH, "petgroup.ini"))
        self.petconfig.sections()
        self.config = configparser.ConfigParser()
        self.config.read(os.path.join(CWD_PATH, "config.ini"))
        self.call_key = self.config.get("PET_KEY", "group1_call")
        self.conf_pet_key: list = [
            self.config.get("PET_KEY", "group1_call"),
            self.config.get("PET_KEY", "group2_call"),
            self.config.get("PET_KEY", "group3_call"),
            self.config.get("PET_KEY", "group4_call"),
        ]
        self.cancel_key = self.config.get("PET_KEY", "pet_cancel")
        self.pet_group_name1 = self.petconfig.get("GROUP_NAME", "GROUP1")
        self.pet_group_name2 = self.petconfig.get("GROUP_NAME", "GROUP2")
        self.pet_group_name3 = self.petconfig.get("GROUP_NAME", "GROUP3")
        self.pet_group_name4 = self.petconfig.get("GROUP_NAME", "GROUP4")
        self.conf_group_name: list = [
            self.petconfig.get("GROUP_NAME", "GROUP1"),
            self.petconfig.get("GROUP_NAME", "GROUP2"),
            self.petconfig.get("GROUP_NAME", "GROUP3"),
            self.petconfig.get("GROUP_NAME", "GROUP4"),
        ]
        # Pet max count
        self.conf_pet_max: list = [
            len(self.petconfig["PET_1_GROUP"]),
            len(self.petconfig["PET_2_GROUP"]),
            len(self.petconfig["PET_3_GROUP"]),
            len(self.petconfig["PET_4_GROUP"]),
        ]
        # Pet Shortcut.
        self.conf_pet_group_key = [
            self.petconfig["PET_1_GROUP"],
            self.petconfig["PET_2_GROUP"],
            self.petconfig["PET_3_GROUP"],
            self.petconfig["PET_4_GROUP"],
        ]
        print(self.conf_pet_group_key[0]["PET_2"])
        self.conf_pet_group_key_2 = self.petconfig["PET_2_GROUP"]
        self.conf_pet_group_key_3 = self.petconfig["PET_3_GROUP"]
        self.conf_pet_group_key_4 = self.petconfig["PET_4_GROUP"]

        self.message.append("Logger loaded.")

    def old_call_pet(self, pet_group_id: int):
        self.pi()
        # When the pet was called to the max.
        if self.shared_group_count[pet_group_id] == self.conf_pet_max[pet_group_id]:
            self.shared_group_count[pet_group_id] = 1
        # When the first pet is ready and the cool time is resolved.
        if self.is_cool_time(pet_group_id):
            self.message.append(self.conf_pet_key[pet_group_id] +
                                "Key Pressed. Call:" + self.conf_group_name[pet_group_id] + " " +
                                str(self.shared_group_count[pet_group_id])
                                )
            pyd.keyDown(self.conf_pet_group_key[pet_group_id]["PET_" + str(self.shared_group_count[pet_group_id])])
            pyd.keyUp(self.conf_pet_group_key[pet_group_id]["PET_" + str(self.shared_group_count[pet_group_id])])
            pyd.keyDown(self.cancel_key)
            pyd.keyUp(self.cancel_key)
            # When you have finished calling the first pet.
            if self.shared_group_count[pet_group_id] == 1:
                self.shared_call_time[pet_group_id] = time.time()
                print("time time inject")
            self.shared_group_count[pet_group_id] = self.shared_group_count[pet_group_id] + 1

    def call_pets(self, g_id):
        now_count = self.shared_group_count[g_id]
        max_count = self.conf_pet_max[g_id]

        # If it was the 1st call, check CT.
        # CT does nothing if it has occurred, otherwise timestamp
        if now_count == 1:
            if not self.is_callable(g_id):
                self.message.append("{0} is on cool time.".format(self.conf_group_name[g_id]))
                return False
            self.shared_call_time[g_id] = time.time()

        self.press_key(self.conf_pet_group_key[g_id]["PET_" + str(self.shared_group_count[g_id])])
        self.press_key(self.cancel_key)

        if now_count >= max_count:
            self.shared_group_count[g_id] = 1
        else:
            self.shared_group_count[g_id] = now_count + 1

    # True -> callable , False -> No
    def is_callable(self, g_id):
        callable_time = self.shared_call_time[g_id] + 60
        if callable_time < time.time():
            return True
        else:
            return False

    def press_key(self, send_key, dec_key1="", dec_key2=""):
        # fix me
        s_key = send_key
        pyd.keyDown(s_key)
        pyd.keyUp(s_key)

    def test_pi(self):
        print("pet count:{0}".format(str(self.shared_group_count)))
        print("pet time:{0}".format(str(self.shared_call_time)))
        print("timetime:{0}".format(str(time.time())))

    def on_press(self, key):
        print(key.char)
        try:
            # Toggle On
            if self.shared_toggle.value == 1:
                if key.char == self.conf_pet_key[0]:
                    self.call_pets(0)
                if key.char == self.conf_pet_key[1]:
                    self.call_pets(1)
                if key.char == self.conf_pet_key[2]:
                    self.call_pets(2)
                if key.char == self.conf_pet_key[3]:
                    self.call_pets(3)
        except:
            char = key
            char = ''
        finally:
            pass

    def on_release(self, key):
        return key


    def run(self):
        try:
            with Listener(on_press=self.on_press, on_release=self.on_release) as listener:
                listener.join()
        except:
            pass

    def load_setting(self):
        pass


class UI(QDialog):
    def __init__(self, message, call_time, group_count, toggle, parent=None):
        # shared var
        self.shared_toggle = toggle
        self.message: list = message
        self.call_time: list = call_time
        self.count = group_count

        super(UI, self).__init__(parent)
        self.originalPalette = QApplication.palette()
        ModeComboBox = QComboBox()
        ModeComboBox.addItems(MODE.keys())
        self.message = message
        styleLabel = QLabel("&Mode")
        styleLabel.setBuddy(ModeComboBox)

        self.useStylePaletteCheckBox = QCheckBox("&Front Window")
        self.useStylePaletteCheckBox.setChecked(False)

        self.pet1box = QCheckBox("&Pet 1 Group")


        self.disableWidgetsCheckBox = QCheckBox("&Lock")

        # self.createTopLeftGroupBox()
        # self.createTopRightGroupBox()
        self.createProgressBar()
        self.createLogger()

        ModeComboBox.textActivated.connect(self.modeChange)
        self.useStylePaletteCheckBox.toggled.connect(self.changeFrontWindow)


        topLayout = QHBoxLayout()
        topLayout.addWidget(styleLabel)
        topLayout.addWidget(ModeComboBox)
        topLayout.addStretch(1)
        topLayout.addWidget(self.useStylePaletteCheckBox)
        topLayout.addWidget(self.disableWidgetsCheckBox)

        self.topLeftGroupBox = QGroupBox("Pet Group")
        self.checkBox1 = QCheckBox("Pet 1 Group")
        self.checkBox2 = QCheckBox("Pet 2 Group")
        self.checkBox3 = QCheckBox("Pet 3 Group")
        self.checkBox4 = QCheckBox("Pet 4 Group")
        self.checkBox5 = QCheckBox("Don't consider CT")
        self.checkBox6 = QCheckBox("Check Client")
        self.checkBox1.setTristate(True)
        self.checkBox1.setChecked(True)
        self.checkBox2.setTristate(True)
        self.checkBox3.setTristate(True)
        self.checkBox4.setTristate(True)
        self.checkBox5.setTristate(True)
        self.checkBox6.setTristate(True)
        layout = QVBoxLayout()
        layout.addWidget(self.checkBox1)
        layout.addWidget(self.checkBox2)
        layout.addWidget(self.checkBox3)
        layout.addWidget(self.checkBox4)
        layout.addWidget(self.checkBox5)
        layout.addWidget(self.checkBox6)
        layout.addStretch(1)
        self.topLeftGroupBox.setLayout(layout)


        self.checkBox1.toggled.connect(self.save_config)
        self.checkBox2.toggled.connect(self.save_config)
        self.checkBox3.toggled.connect(self.save_config)
        self.checkBox4.toggled.connect(self.save_config)
        self.checkBox5.toggled.connect(self.save_config)
        self.checkBox6.toggled.connect(self.save_config)


        self.topRightGroupBox = QGroupBox("Config")
        self.pet1group = QLabel("Pet 1 Group loaded:")
        self.pet1count = QLabel("0")
        self.pet2group = QLabel("Pet 2 Group loaded:")
        self.pet2count = QLabel("0")
        self.pet3group = QLabel("Pet 3 Group loaded:")
        self.pet3count = QLabel("0")
        self.pet4group = QLabel("Pet 4 Group loaded:")
        self.pet4count = QLabel("0")

        self.pet1group.setBuddy(self.pet1count)
        self.defaultPushButton = QPushButton("Reload Config")
        self.defaultPushButton.setDefault(True)

        pet1GroupLayout = QHBoxLayout()
        pet1GroupLayout.addWidget(self.pet1group)
        pet1GroupLayout.addWidget(self.pet1count)
        pet2GroupLayout = QHBoxLayout()
        pet2GroupLayout.addWidget(self.pet2group)
        pet2GroupLayout.addWidget(self.pet2count)
        pet3GroupLayout = QHBoxLayout()
        pet3GroupLayout.addWidget(self.pet3group)
        pet3GroupLayout.addWidget(self.pet3count)
        pet4GroupLayout = QHBoxLayout()
        pet4GroupLayout.addWidget(self.pet4group)
        pet4GroupLayout.addWidget(self.pet4count)

        layout = QVBoxLayout()
        layout.addLayout(pet1GroupLayout)
        layout.addLayout(pet2GroupLayout)
        layout.addLayout(pet3GroupLayout)
        layout.addLayout(pet4GroupLayout)
        layout.addWidget(self.defaultPushButton)
        self.topRightGroupBox.setLayout(layout)


        mainLayout = QGridLayout()
        mainLayout.addLayout(topLayout, 0, 0, 1, 2)
        mainLayout.addWidget(self.topLeftGroupBox, 1, 0)
        mainLayout.addWidget(self.topRightGroupBox, 1, 1)
        mainLayout.addWidget(self.logger, 2, 0, 1, 2)
        mainLayout.addWidget(self.progressBar, 3, 0, 1, 2)
        mainLayout.setRowStretch(1, 1)
        mainLayout.setRowStretch(2, 1)
        mainLayout.setColumnStretch(0, 1)
        mainLayout.setColumnStretch(1, 1)
        self.setLayout(mainLayout)

        self.setWindowTitle("Pet Launcher ver." + str(VERSION))
        QApplication.setStyle("WindowsVista")
        self.load_config()
        self.load_pet_config()

        # 操作不可を強制する
        self.disableWidgetsCheckBox.toggled.connect(self.topLeftGroupBox.setDisabled)
        self.disableWidgetsCheckBox.toggled.connect(self.topRightGroupBox.setDisabled)

        # ペットをロードする
        self.defaultPushButton.clicked.connect(self.load_pet_config)

    def save_config(self):
        config = configparser.ConfigParser()
        config.read(os.path.join(CWD_PATH, "config.ini"))
        config.set("PET_GROUP", "group1", self.bool2str(self.checkBox1.isChecked()))
        config.set("PET_GROUP", "group2", self.bool2str(self.checkBox2.isChecked()))
        config.set("PET_GROUP", "group3", self.bool2str(self.checkBox3.isChecked()))
        config.set("PET_GROUP", "group4", self.bool2str(self.checkBox4.isChecked()))
        config.set("PET_GROUP", "group5", self.bool2str(self.checkBox5.isChecked()))
        config.set("PET_GROUP", "group6", self.bool2str(self.checkBox6.isChecked()))
        with open("config.ini", "w") as f:
            config.write(f)

    def load_config(self):
        config = configparser.SafeConfigParser()
        config.read(os.path.join(CWD_PATH, "config.ini"))
        self.checkBox1.setChecked(self.str2bool(config.get("PET_GROUP", "group1")))
        self.checkBox2.setChecked(self.str2bool(config.get("PET_GROUP", "group2")))
        self.checkBox3.setChecked(self.str2bool(config.get("PET_GROUP", "group3")))
        self.checkBox4.setChecked(self.str2bool(config.get("PET_GROUP", "group4")))
        self.checkBox5.setChecked(self.str2bool(config.get("PET_GROUP", "group5")))
        self.checkBox6.setChecked(self.str2bool(config.get("PET_GROUP", "group6")))
        self.send_logger("Auto loaded: " + "config.ini")

    def load_pet_config(self):
        config = configparser.SafeConfigParser()

        config.read(os.path.join(CWD_PATH, "petgroup.ini"))
        config.sections()
        self.pet1count.setText(str(len(config["PET_1_GROUP"])))
        self.pet2count.setText(str(len(config["PET_2_GROUP"])))
        self.pet3count.setText(str(len(config["PET_3_GROUP"])))
        self.pet4count.setText(str(len(config["PET_4_GROUP"])))
        self.send_logger("Loaded: " + "petgroup.ini")

    def str2bool(self, s):
        if s in ["True", "true"]:
            return True
        elif s in ["False", "false"]:
            return False

    def bool2str(self, b):
        if b is True:
            return "True"
        elif b is False:
            return "False"

    def modeChange(self, modeName):
        if modeName == "Activate":
            self.shared_toggle.value = 1
            self.lock_group()
            self.send_logger("Battle Mode is Activated.")
            print(self.shared_toggle.value)
        elif modeName == "Inactivate":
            self.shared_toggle.value = 0
            self.unlock_group()
            self.send_logger("Battle Mode is Inactivated.")
            print(self.shared_toggle.value)

    def lock_group(self):
        self.topLeftGroupBox.setDisabled(True)
        self.topRightGroupBox.setDisabled(True)

    def unlock_group(self):
        self.topLeftGroupBox.setEnabled(True)
        self.topRightGroupBox.setEnabled(True)

    def send_logger(self, message):
        datetime_now = datetime.datetime.now().strftime("%H:%M:%S")
        self.logger.insertPlainText("[" + str(datetime_now) + "] " + message + "\n")
        self.logger.ensureCursorVisible()

    def changeFrontWindow(self):
        if (self.useStylePaletteCheckBox.isChecked()):
            # もしチェックしているなら最前面へ
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
            self.show()
        else:
            # もしチェックしていないなら通常ウィンドウへ
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, False)
            self.show()

    def keylogger_finished(self):
        del self.init_keylogger


    def advanceProgressBar(self):
        curVal = self.progressBar.value()
        maxVal = self.progressBar.maximum()
        self.pop_message()
        self.progressBar.setValue(curVal + (maxVal - curVal) // 100)

    def pop_message(self):
        message_temp = copy.deepcopy(self.message)
        del self.message[:len(message_temp)]
        for m in message_temp:
            self.send_logger(str(m))


    def createProgressBar(self):
        self.progressBar = QProgressBar()
        self.progressBar.setRange(0, 10000)
        self.progressBar.setValue(0)

        timer = QTimer(self)
        timer.timeout.connect(self.advanceProgressBar)
        timer.start(1000)

    def createLogger(self):
        self.logger = QPlainTextEdit()
        self.logger.setReadOnly(True)
        self.logger.insertPlainText("Welcome.\n")


def observer_func(pid1, pid2):
    stat = [True, True]
    time.sleep(3)
    while True:
        if not psutil.pid_exists(pid1):
            stat[0] = False
            os.kill(pid2, signal.SIGTERM)
            os.system("taskkill  /F /pid " + str(pid2))
        if not psutil.pid_exists(pid2):
            stat[1] = False
            os.system("taskkill  /F /pid " + str(pid1))
        if False in stat:
            os.system("taskkill  /F /pid " + str(os.getpid()))
        time.sleep(10)


if __name__ == '__main__':
    main()
