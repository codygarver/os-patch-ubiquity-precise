# -*- coding: utf-8 -*-

import os

from PyQt4 import uic
from PyQt4 import QtGui

from ubiquity.frontend.kde_components.PartitionBar import PartitionsBar
from ubiquity import misc

_uidir="/usr/share/ubiquity/qt/"

def addBars(parent, before_bar, after_bar):
    frame = QtGui.QWidget(parent)
    frame.setLayout(QtGui.QVBoxLayout())
    frame.layout().setSpacing(0)

    # TODO
    #frame.layout().addWidget(QtGui.QLabel(get_string('ubiquity/text/partition_layout_before')))
    frame.layout().addWidget(QtGui.QLabel("Before:"))
    frame.layout().addWidget(before_bar)
    #frame.layout().addWidget(QtGui.QLabel(get_string('ubiquity/text/partition_layout_after')))
    frame.layout().addWidget(QtGui.QLabel("After:"))
    frame.layout().addWidget(after_bar)

    parent.layout().addWidget(frame)
    return frame

class PartAuto(QtGui.QWidget):

    def __init__(self, controller):
        QtGui.QWidget.__init__(self)
        self.controller = controller

        uic.loadUi(os.path.join(_uidir,'stepPartAuto.ui'), self)

        self.diskLayout = None

        self.autopartition_buttongroup = QtGui.QButtonGroup(self)
        self.autopartition_buttongroup.buttonClicked[int].connect(
            self.on_button_toggled)
        self.part_auto_disk_box.currentIndexChanged[int].connect(
            self.on_disks_combo_changed)

        self._clearInfo()

    def _clearInfo(self):
        self.bar_frames = []
        self.autopartitionTexts = []

        self.disks = []

        self.resizeSize = None
        self.resizeChoice = None
        self.manualChoice = None
        self.useDeviceChoice = None

    def setDiskLayout(self, diskLayout):
        self.diskLayout = diskLayout

    def setupChoices (self, choices, extra_options, resize_choice,
                      manual_choice, biggest_free_choice, use_device_choice):
        self._clearInfo()

        self.resizeChoice = resize_choice
        self.manualChoice = manual_choice
        self.useDeviceChoice = use_device_choice
        self.extra_options = extra_options

        # remove any previous autopartition selections
        for child in self.autopart_selection_frame.children():
            if isinstance(child, QtGui.QWidget):
                child.setParent(None)
                del child

        for child in self.barsFrame.children():
            if isinstance(child, QtGui.QWidget):
                self.barsFrame.layout().removeWidget(child)
                child.setParent(None)
                del child

        release_name = misc.get_release().name

        bId = 0
        if 'resize' in extra_options:
            button = QtGui.QRadioButton(self.resizeChoice, self.autopart_selection_frame)
            self.autopart_selection_frame.layout().addWidget(button)
            self.autopartition_buttongroup.addButton(button, bId)
            self.autopartitionTexts.append(resize_choice)
            button.clicked.connect(self.controller.setNextButtonTextInstallNow)
            bId += 1

            disks = []
            for disk_id in extra_options['resize']:
                # information about what can be resized
                unused, min_size, max_size, pref_size, \
                resize_path, unused, unused = \
                    extra_options['resize'][disk_id]

                for text, path in extra_options['use_device'][1].items():
                    path = path[0]
                    if path.rsplit('/', 1)[1] == disk_id:
                        bar_frame = QtGui.QFrame()
                        bar_frame.setLayout(QtGui.QVBoxLayout())
                        bar_frame.setVisible(False)
                        bar_frame.layout().setSpacing(0)
                        self.barsFrame.layout().addWidget(bar_frame)
                        self.bar_frames.append(bar_frame)

                        disks.append((text, bar_frame))
                        self.resizeSize = pref_size
                        dev = self.diskLayout[disk_id]
                        before_bar = PartitionsBar()
                        after_bar = PartitionsBar()

                        for p in dev:
                            before_bar.addPartition(p[0], int(p[1]), p[3])
                            after_bar.addPartition(p[0], int(p[1]), p[3])

                        after_bar.setResizePartition(resize_path,
                            min_size, max_size, pref_size, release_name)
                        after_bar.partitionResized.connect(self.on_partitionResized)
                        addBars(bar_frame, before_bar, after_bar)
            self.disks.append(disks)

        # TODO biggest_free_choice

        # Use entire disk.
        button = QtGui.QRadioButton(self.useDeviceChoice, self.autopart_selection_frame)
        self.autopartitionTexts.append(self.useDeviceChoice)
        self.autopart_selection_frame.layout().addWidget(button)
        self.autopartition_buttongroup.addButton(button, bId)
        button.clicked.connect(self.controller.setNextButtonTextInstallNow)
        bId += 1

        disks = []
        for text, path in extra_options['use_device'][1].items():
            path = path[0]
            bar_frame = QtGui.QFrame()
            bar_frame.setLayout(QtGui.QVBoxLayout())
            bar_frame.setVisible(False)
            bar_frame.layout().setSpacing(0)
            self.barsFrame.layout().addWidget(bar_frame)
            self.bar_frames.append(bar_frame)

            disks.append((text, bar_frame))

            dev = self.diskLayout[path.rsplit('/', 1)[1]]
            before_bar = PartitionsBar()
            after_bar = PartitionsBar()

            for p in dev:
                before_bar.addPartition(p.device, int(p.size), p.filesystem)
            if before_bar.diskSize > 0:
                after_bar.addPartition(release_name, before_bar.diskSize, 'auto')
            else:
                after_bar.addPartition(release_name, 1, 'auto')

            addBars(bar_frame, before_bar, after_bar)
        self.disks.append(disks)

        # Manual partitioning.

        button = QtGui.QRadioButton(manual_choice, self.autopart_selection_frame)
        self.autopartitionTexts.append(manual_choice)
        self.autopart_selection_frame.layout().addWidget(button)
        self.autopartition_buttongroup.addButton(button, bId)
        button.clicked.connect(self.controller.setNextButtonTextNext)
        self.disks.append([])

        #select the first button
        b = self.autopartition_buttongroup.button(0)
        b and b.click()

    # slot for when partition is resized on the bar
    def on_partitionResized(self, unused, size):
        self.resizeSize = size

    def getChoice (self):
        bId = self.autopartition_buttongroup.checkedId()
        if bId > -1:
            choice = unicode(self.autopartitionTexts[bId])
        else:
            raise AssertionError("no active autopartitioning choice")

        if choice == self.resizeChoice:
            # resize choice should have been hidden otherwise
            assert self.resizeSize is not None
            comboText = unicode(self.part_auto_disk_box.currentText())
            disk_id = self.extra_options['use_device'][1][comboText][0]
            disk_id = disk_id.rsplit('/', 1)[1]
            option = self.extra_options['resize'][disk_id][0]
            return option, '%d B' % self.resizeSize
        elif choice == self.useDeviceChoice:
            return (self.extra_options['use_device'][0],
                    unicode(self.part_auto_disk_box.currentText()))
        else:
            return choice, None

    def on_disks_combo_changed(self, index):
        for e in self.bar_frames:
            e.setVisible(False)
        button_id = self.autopartition_buttongroup.checkedId()
        length = len(self.disks[button_id])
        if index < length and length > 0:
            self.disks[button_id][index][1].setVisible(True)

    def on_button_toggled(self, unused):
        button_id = self.autopartition_buttongroup.checkedId()
        self.part_auto_disk_box.clear()
        if not [self.part_auto_disk_box.addItem(disk[0])
                for disk in self.disks[button_id]]:
            self.part_auto_disk_box.hide()
        else:
            # If we haven't added any items to the disk combobox, hide it.
            self.part_auto_disk_box.show()
