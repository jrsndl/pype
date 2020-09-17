from Qt import QtWidgets, QtCore, QtGui


class NumberSpinBox(QtWidgets.QDoubleSpinBox):
    def __init__(self, *args, **kwargs):
        min_value = kwargs.pop("minimum", -99999)
        max_value = kwargs.pop("maximum", 99999)
        decimals = kwargs.pop("decimal", 0)
        super(NumberSpinBox, self).__init__(*args, **kwargs)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setDecimals(decimals)
        self.setMinimum(min_value)
        self.setMaximum(max_value)

    def wheelEvent(self, event):
        if self.hasFocus():
            super(NumberSpinBox, self).wheelEvent(event)
        else:
            event.ignore()

    def value(self):
        output = super(NumberSpinBox, self).value()
        if self.decimals() == 0:
            output = int(output)
        return output


class PathInput(QtWidgets.QLineEdit):
    def clear_end_path(self):
        value = self.text().strip()
        if value.endswith("/"):
            while value and value[-1] == "/":
                value = value[:-1]
            self.setText(value)

    def keyPressEvent(self, event):
        # Always change backslash `\` for forwardslash `/`
        if event.key() == QtCore.Qt.Key_Backslash:
            event.accept()
            new_event = QtGui.QKeyEvent(
                event.type(),
                QtCore.Qt.Key_Slash,
                event.modifiers(),
                "/",
                event.isAutoRepeat(),
                event.count()
            )
            QtWidgets.QApplication.sendEvent(self, new_event)
            return
        super(PathInput, self).keyPressEvent(event)

    def focusOutEvent(self, event):
        super(PathInput, self).focusOutEvent(event)
        self.clear_end_path()


class ClickableWidget(QtWidgets.QWidget):
    clicked = QtCore.Signal()

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit()
        super(ClickableWidget, self).mouseReleaseEvent(event)


class ExpandingWidget(QtWidgets.QWidget):
    def __init__(self, label, parent):
        super(ExpandingWidget, self).__init__(parent)

        self.toolbox_hidden = False

        top_part = ClickableWidget(parent=self)

        button_size = QtCore.QSize(5, 5)
        button_toggle = QtWidgets.QToolButton(parent=top_part)
        button_toggle.setProperty("btn-type", "expand-toggle")
        button_toggle.setIconSize(button_size)
        button_toggle.setArrowType(QtCore.Qt.RightArrow)
        button_toggle.setCheckable(True)
        button_toggle.setChecked(False)

        label_widget = QtWidgets.QLabel(label, parent=top_part)
        label_widget.setObjectName("DictLabel")

        side_line_widget = QtWidgets.QWidget(top_part)
        side_line_widget.setObjectName("SideLineWidget")
        side_line_layout = QtWidgets.QHBoxLayout(side_line_widget)
        side_line_layout.setContentsMargins(5, 10, 0, 10)
        side_line_layout.addWidget(button_toggle)
        side_line_layout.addWidget(label_widget)

        top_part_layout = QtWidgets.QHBoxLayout(top_part)
        top_part_layout.setContentsMargins(0, 0, 0, 0)
        top_part_layout.addWidget(side_line_widget)

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.top_part_ending = None
        self.after_label_layout = None
        self.end_of_layout = None

        self.side_line_widget = side_line_widget
        self.side_line_layout = side_line_layout
        self.button_toggle = button_toggle
        self.label_widget = label_widget

        top_part.clicked.connect(self._top_part_clicked)
        self.button_toggle.clicked.connect(self._btn_clicked)

        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.main_layout.addWidget(top_part)

    def hide_toolbox(self, hide_content=False):
        self.button_toggle.setArrowType(QtCore.Qt.NoArrow)
        self.toolbox_hidden = True
        self.content_widget.setVisible(not hide_content)
        self.parent().updateGeometry()

    def set_content_widget(self, content_widget):
        content_widget.setVisible(False)
        self.main_layout.addWidget(content_widget)
        self.content_widget = content_widget

    def _btn_clicked(self):
        self.toggle_content(self.button_toggle.isChecked())

    def _top_part_clicked(self):
        self.toggle_content()

    def toggle_content(self, *args):
        if self.toolbox_hidden:
            return

        if len(args) > 0:
            checked = args[0]
        else:
            checked = not self.button_toggle.isChecked()
        arrow_type = QtCore.Qt.RightArrow
        if checked:
            arrow_type = QtCore.Qt.DownArrow
        self.button_toggle.setChecked(checked)
        self.button_toggle.setArrowType(arrow_type)
        self.content_widget.setVisible(checked)
        self.parent().updateGeometry()

    def add_widget_after_label(self, widget):
        self._add_side_widget_subwidgets()
        self.after_label_layout.addWidget(widget)

    def _add_side_widget_subwidgets(self):
        if self.top_part_ending is not None:
            return

        top_part_ending = QtWidgets.QWidget(self.side_line_widget)
        top_part_ending.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        top_part_ending_layout = QtWidgets.QHBoxLayout(top_part_ending)
        top_part_ending_layout.setContentsMargins(0, 0, 0, 0)
        top_part_ending_layout.setSpacing(0)
        top_part_ending_layout.setAlignment(QtCore.Qt.AlignVCenter)

        after_label_widget = QtWidgets.QWidget(top_part_ending)
        spacer_item = QtWidgets.QWidget(top_part_ending)
        end_of_widget = QtWidgets.QWidget(top_part_ending)

        self.after_label_layout = QtWidgets.QVBoxLayout(after_label_widget)
        self.after_label_layout.setContentsMargins(0, 0, 0, 0)

        self.end_of_layout = QtWidgets.QVBoxLayout(end_of_widget)
        self.end_of_layout.setContentsMargins(0, 0, 0, 0)

        spacer_layout = QtWidgets.QVBoxLayout(spacer_item)
        spacer_layout.setContentsMargins(0, 0, 0, 0)

        top_part_ending_layout.addWidget(after_label_widget, 0)
        top_part_ending_layout.addWidget(spacer_item, 1)
        top_part_ending_layout.addWidget(end_of_widget, 0)

        top_part_ending.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        after_label_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        spacer_item.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        end_of_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.top_part_ending = top_part_ending
        self.side_line_layout.addWidget(top_part_ending)

    def resizeEvent(self, event):
        super(ExpandingWidget, self).resizeEvent(event)
        self.content_widget.updateGeometry()


class UnsavedChangesDialog(QtWidgets.QDialog):
    message = "You have unsaved changes. What do you want to do with them?"

    def __init__(self, parent=None):
        super().__init__(parent)
        message_label = QtWidgets.QLabel(self.message)

        btns_widget = QtWidgets.QWidget(self)
        btns_layout = QtWidgets.QHBoxLayout(btns_widget)

        btn_ok = QtWidgets.QPushButton("Save")
        btn_ok.clicked.connect(self.on_ok_pressed)
        btn_discard = QtWidgets.QPushButton("Discard")
        btn_discard.clicked.connect(self.on_discard_pressed)
        btn_cancel = QtWidgets.QPushButton("Cancel")
        btn_cancel.clicked.connect(self.on_cancel_pressed)

        btns_layout.addWidget(btn_ok)
        btns_layout.addWidget(btn_discard)
        btns_layout.addWidget(btn_cancel)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(message_label)
        layout.addWidget(btns_widget)

        self.state = None

    def on_cancel_pressed(self):
        self.done(0)

    def on_ok_pressed(self):
        self.done(1)

    def on_discard_pressed(self):
        self.done(2)
