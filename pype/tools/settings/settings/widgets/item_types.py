import json
import logging
import collections
from Qt import QtWidgets, QtCore, QtGui
from .widgets import (
    ExpandingWidget,
    NumberSpinBox,
    PathInput
)
from .lib import NOT_SET, METADATA_KEY, TypeToKlass, CHILD_OFFSET
from avalon.vendor import qtawesome


class SettingObject:
    # `is_input_type` attribute says if has implemented item type methods
    is_input_type = True
    # each input must have implemented default value for development
    # when defaults are not filled yet
    default_input_value = NOT_SET
    # will allow to show actions for the item type (disabled for proxies)
    allow_actions = True
    # default state of item type
    default_state = ""

    @classmethod
    def style_state(cls, is_invalid, is_overriden, is_modified):
        """Return stylesheet state by intered booleans."""
        items = []
        if is_invalid:
            items.append("invalid")
        else:
            if is_overriden:
                items.append("overriden")
            if is_modified:
                items.append("modified")
        return "-".join(items) or cls.default_state

    def _set_default_attributes(self):
        """Create and reset attributes required for all item types.

        They may not be used in the item but are required to be set.
        """
        # Default input attributes
        self._has_studio_override = False
        self._had_studio_override = False

        self._is_overriden = False
        self._was_overriden = False

        self._is_modified = False
        self._is_invalid = False

        self._is_nullable = False
        self._as_widget = False
        self._is_group = False

        self._any_parent_is_group = None

        # Parent input
        self._parent = None

        # States of inputs
        self._state = None
        self._child_state = None

        # Attributes where values are stored
        self.default_value = NOT_SET
        self.studio_value = NOT_SET
        self.override_value = NOT_SET

        # Log object
        self._log = None

        # Only for develop mode
        self.defaults_not_set = False

    def initial_attributes(self, input_data, parent, as_widget):
        """Prepare attributes based on entered arguments.

        This method should be same for each item type. Few item types
        may require to extend with specific attributes for their case.
        """
        self._set_default_attributes()

        self._parent = parent
        self._as_widget = as_widget

        self._is_group = input_data.get("is_group", False)
        # TODO not implemented yet
        self._is_nullable = input_data.get("is_nullable", False)

        any_parent_is_group = parent.is_group
        if not any_parent_is_group:
            any_parent_is_group = parent.any_parent_is_group

        self._any_parent_is_group = any_parent_is_group

    @property
    def develop_mode(self):
        """Tool is in develop mode or not.

        Returns:
            bool

        """
        return self._parent.develop_mode

    @property
    def log(self):
        """Auto created logger for debugging."""
        if self._log is None:
            self._log = logging.getLogger(self.__class__.__name__)
        return self._log

    @property
    def had_studio_override(self):
        """Item had studio overrides on refresh.

        Returns:
            bool

        """
        return self._had_studio_override

    @property
    def has_studio_override(self):
        """Item has studio override at the moment.

        With combination of `had_studio_override` is possible to know if item
        has changes (not just value change).

        Returns:
            bool

        """
        return self._has_studio_override or self._parent.has_studio_override

    @property
    def is_group(self):
        """Item represents key that can be overriden.

        Attribute `is_group` can be set to True only once in item hierarchy.

        Returns:
            bool

        """
        return self._is_group

    @property
    def any_parent_is_group(self):
        """Any parent of item is group.

        Attribute holding this information is set during creation and
        stored to `_any_parent_is_group`.

        Why is this information useful: If any parent is group and
        the parent is set as overriden, this item is overriden too.

        Returns:
            bool

        """
        if self._any_parent_is_group is None:
            return super(SettingObject, self).any_parent_is_group
        return self._any_parent_is_group

    @property
    def is_modified(self):
        """Has object any changes that require saving."""
        if self._is_modified or self.defaults_not_set:
            return True

        if self.is_overidable:
            return self.was_overriden != self.is_overriden
        else:
            return self.has_studio_override != self.had_studio_override

    @property
    def is_overriden(self):
        """Is object overriden so should be saved to overrides."""
        return self._is_overriden or self._parent.is_overriden

    @property
    def was_overriden(self):
        """Item had set value of project overrides on project change."""
        if self._as_widget:
            return self._parent.was_overriden
        return self._was_overriden

    @property
    def is_invalid(self):
        """Value set in is not valid."""
        return self._is_invalid

    @property
    def is_nullable(self):
        """Value of item can be set to None.

        NOT IMPLEMENTED!
        """
        return self._is_nullable

    @property
    def is_overidable(self):
        """Should care about overrides."""
        return self._parent.is_overidable

    def any_parent_overriden(self):
        """Any of parent objects up to top hiearchy item is overriden.

        Returns:
            bool

        """
        if self._parent._is_overriden:
            return True
        return self._parent.any_parent_overriden()

    @property
    def ignore_value_changes(self):
        """Most of attribute changes are ignored on value change when True."""
        return self._parent.ignore_value_changes

    @ignore_value_changes.setter
    def ignore_value_changes(self, value):
        """Setter for global parent item to apply changes for all inputs."""
        self._parent.ignore_value_changes = value

    def config_value(self):
        """Output for saving changes or overrides."""
        return {self.key: self.item_value()}

    @classmethod
    def style_state(
        cls, has_studio_override, is_invalid, is_overriden, is_modified
    ):
        items = []
        if is_invalid:
            items.append("invalid")
        else:
            if is_overriden:
                items.append("overriden")
            if is_modified:
                items.append("modified")

        if not items and has_studio_override:
            items.append("studio")

        return "-".join(items) or cls.default_state

    def mouseReleaseEvent(self, event):
        if self.allow_actions and event.button() == QtCore.Qt.RightButton:
            menu = QtWidgets.QMenu()

            actions_mapping = {}
            if self.child_modified:
                action = QtWidgets.QAction("Discard changes")
                actions_mapping[action] = self._discard_changes
                menu.addAction(action)

            if (
                self.is_overidable
                and not self.is_overriden
                and not self.any_parent_is_group
            ):
                action = QtWidgets.QAction("Set project override")
                actions_mapping[action] = self._set_as_overriden
                menu.addAction(action)

            if (
                not self.is_overidable
                and (
                    self.has_studio_override
                )
            ):
                action = QtWidgets.QAction("Reset to pype default")
                actions_mapping[action] = self._reset_to_pype_default
                menu.addAction(action)

            if (
                not self.is_overidable
                and not self.is_overriden
                and not self.any_parent_is_group
                and not self._had_studio_override
            ):
                action = QtWidgets.QAction("Set studio default")
                actions_mapping[action] = self._set_studio_default
                menu.addAction(action)

            if (
                not self.any_parent_overriden()
                and (self.is_overriden or self.child_overriden)
            ):
                # TODO better label
                action = QtWidgets.QAction("Remove project override")
                actions_mapping[action] = self._remove_overrides
                menu.addAction(action)

            if not actions_mapping:
                action = QtWidgets.QAction("< No action >")
                actions_mapping[action] = None
                menu.addAction(action)

            result = menu.exec_(QtGui.QCursor.pos())
            if result:
                to_run = actions_mapping[result]
                if to_run:
                    to_run()
            return

        mro = type(self).mro()
        index = mro.index(self.__class__)
        item = None
        for idx in range(index + 1, len(mro)):
            _item = mro[idx]
            if hasattr(_item, "mouseReleaseEvent"):
                item = _item
                break

        if item:
            return item.mouseReleaseEvent(self, event)

    def _discard_changes(self):
        self.ignore_value_changes = True
        self.discard_changes()
        self.ignore_value_changes = False

    def discard_changes(self):
        raise NotImplementedError(
            "{} Method `discard_changes` not implemented!".format(
                repr(self)
            )
        )

    def _set_studio_default(self):
        self.ignore_value_changes = True
        self.set_studio_default()
        self.ignore_value_changes = False

    def set_studio_default(self):
        raise NotImplementedError(
            "{} Method `set_studio_default` not implemented!".format(
                repr(self)
            )
        )

    def _reset_to_pype_default(self):
        self.ignore_value_changes = True
        self.reset_to_pype_default()
        self.ignore_value_changes = False

    def reset_to_pype_default(self):
        raise NotImplementedError(
            "{} Method `reset_to_pype_default` not implemented!".format(
                repr(self)
            )
        )

    def _remove_overrides(self):
        self.ignore_value_changes = True
        self.remove_overrides()
        self.ignore_value_changes = False

    def remove_overrides(self):
        raise NotImplementedError(
            "{} Method `remove_overrides` not implemented!".format(
                repr(self)
            )
        )

    def _set_as_overriden(self):
        self.ignore_value_changes = True
        self.set_as_overriden()
        self.ignore_value_changes = False

    def set_as_overriden(self):
        raise NotImplementedError(
            "{} Method `set_as_overriden` not implemented!".format(repr(self))
        )

    def hierarchical_style_update(self):
        raise NotImplementedError(
            "{} Method `hierarchical_style_update` not implemented!".format(
                repr(self)
            )
        )

    def update_default_values(self, parent_values):
        raise NotImplementedError(
            "{} does not have implemented `update_default_values`".format(self)
        )

    def update_studio_values(self, parent_values):
        raise NotImplementedError(
            "{} does not have implemented `update_studio_values`".format(self)
        )

    def apply_overrides(self, parent_values):
        raise NotImplementedError(
            "{} does not have implemented `apply_overrides`".format(self)
        )

    @property
    def child_has_studio_override(self):
        """Any children item is modified."""
        raise NotImplementedError(
            "{} does not have implemented `child_has_studio_override`".format(
                self
            )
        )

    @property
    def child_modified(self):
        """Any children item is modified."""
        raise NotImplementedError(
            "{} does not have implemented `child_modified`".format(self)
        )

    @property
    def child_overriden(self):
        """Any children item is overriden."""
        raise NotImplementedError(
            "{} does not have implemented `child_overriden`".format(self)
        )

    @property
    def child_invalid(self):
        """Any children item does not have valid value."""
        raise NotImplementedError(
            "{} does not have implemented `child_invalid`".format(self)
        )

    def get_invalid(self):
        """Return invalid item types all down the hierarchy."""
        raise NotImplementedError(
            "{} does not have implemented `get_invalid`".format(self)
        )

    def item_value(self):
        """Value of an item without key."""
        raise NotImplementedError(
            "Method `item_value` not implemented!"
        )

    def studio_value(self):
        """Output for saving changes or overrides."""
        return {self.key: self.item_value()}


class InputObject(SettingObject):
    def update_default_values(self, parent_values):
        self._state = None
        self._is_modified = False

        value = NOT_SET
        if self._as_widget:
            value = parent_values
        elif parent_values is not NOT_SET:
            value = parent_values.get(self.key, NOT_SET)

        if value is NOT_SET:
            if self.develop_mode:
                value = self.default_input_value
                self.defaults_not_set = True
                if value is NOT_SET:
                    raise NotImplementedError((
                        "{} Does not have implemented"
                        " attribute `default_input_value`"
                    ).format(self))

            else:
                raise ValueError(
                    "Default value is not set. This is implementation BUG."
                )

        self.default_value = value
        self._has_studio_override = False
        self._had_studio_override = False
        self.set_value(value)

    def update_studio_values(self, parent_values):
        self._state = None
        self._is_modified = False

        value = NOT_SET
        if self._as_widget:
            value = parent_values
        elif parent_values is not NOT_SET:
            value = parent_values.get(self.key, NOT_SET)

        self.studio_value = value
        if value is not NOT_SET:
            self._has_studio_override = True
            self._had_studio_override = True
            self.set_value(value)

        else:
            self._has_studio_override = False
            self._had_studio_override = False
            self.set_value(self.default_value)

    def apply_overrides(self, parent_values):
        self._is_modified = False
        self._state = None
        self._had_studio_override = bool(self._has_studio_override)
        if self._as_widget:
            override_value = parent_values
        elif parent_values is NOT_SET or self.key not in parent_values:
            override_value = NOT_SET
        else:
            override_value = parent_values[self.key]

        self.override_value = override_value

        if override_value is NOT_SET:
            self._is_overriden = False
            self._was_overriden = False
            if self.has_studio_override:
                value = self.studio_value
            else:
                value = self.default_value
        else:
            self._is_overriden = True
            self._was_overriden = True
            value = override_value

        self.set_value(value)

    def _on_value_change(self, item=None):
        if self.ignore_value_changes:
            return

        if self.is_overidable:
            self._is_overriden = True
        else:
            self._has_studio_override = True

        if self._is_invalid:
            self._is_modified = True
        elif self._is_overriden:
            self._is_modified = self.item_value() != self.override_value
        elif self._has_studio_override:
            self._is_modified = self.item_value() != self.studio_value
        else:
            self._is_modified = self.item_value() != self.default_value

        self.update_style()

        self.value_changed.emit(self)

    def studio_overrides(self):
        if not self.has_studio_override:
            return NOT_SET, False
        return self.config_value(), self.is_group

    def overrides(self):
        if not self.is_overriden:
            return NOT_SET, False
        return self.config_value(), self.is_group

    def hierarchical_style_update(self):
        self.update_style()

    def remove_overrides(self):
        if self.has_studio_override:
            self.set_value(self.studio_value)
        else:
            self.set_value(self.default_value)
        self._is_overriden = False
        self._is_modified = False

    def reset_to_pype_default(self):
        self.set_value(self.default_value)
        self._has_studio_override = False

    def set_studio_default(self):
        self._has_studio_override = True

    def discard_changes(self):
        self._is_overriden = self._was_overriden
        self._has_studio_override = self._had_studio_override
        if self.is_overidable:
            if self._was_overriden and self.override_value is not NOT_SET:
                self.set_value(self.override_value)
        else:
            if self._had_studio_override:
                self.set_value(self.studio_value)
            else:
                self.set_value(self.default_value)

        if not self.is_overidable:
            if self.has_studio_override:
                self._is_modified = self.studio_value != self.item_value()
            else:
                self._is_modified = self.default_value != self.item_value()
            self._is_overriden = False
            return

        self._is_modified = False
        self._is_overriden = self._was_overriden

    def set_as_overriden(self):
        self._is_overriden = True

    @property
    def child_has_studio_override(self):
        return self._has_studio_override

    @property
    def child_modified(self):
        return self.is_modified

    @property
    def child_overriden(self):
        return self._is_overriden

    @property
    def child_invalid(self):
        return self.is_invalid

    def get_invalid(self):
        output = []
        if self.is_invalid:
            output.append(self)
        return output

    def reset_children_attributes(self):
        return


class BooleanWidget(QtWidgets.QWidget, InputObject):
    default_input_value = True
    value_changed = QtCore.Signal(object)

    def __init__(
        self, input_data, parent,
        as_widget=False, label_widget=None, parent_widget=None
    ):
        if parent_widget is None:
            parent_widget = parent
        super(BooleanWidget, self).__init__(parent_widget)

        self.initial_attributes(input_data, parent, as_widget)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        if not self._as_widget:
            self.key = input_data["key"]
            if not label_widget:
                label = input_data["label"]
                label_widget = QtWidgets.QLabel(label)
                label_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
                layout.addWidget(label_widget, 0)
            self.label_widget = label_widget

        self.checkbox = QtWidgets.QCheckBox(self)
        spacer = QtWidgets.QWidget(self)
        layout.addWidget(self.checkbox, 0)
        layout.addWidget(spacer, 1)

        spacer.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.setFocusProxy(self.checkbox)

        self.checkbox.stateChanged.connect(self._on_value_change)

    def set_value(self, value):
        # Ignore value change because if `self.isChecked()` has same
        # value as `value` the `_on_value_change` is not triggered
        self.checkbox.setChecked(value)

    def update_style(self):
        if self._as_widget:
            if not self.isEnabled():
                state = self.style_state(False, False, False, False)
            else:
                state = self.style_state(
                    False,
                    self._is_invalid,
                    False,
                    self._is_modified
                )
        else:
            state = self.style_state(
                self.has_studio_override,
                self.is_invalid,
                self.is_overriden,
                self.is_modified
            )
        if self._state == state:
            return

        if self._as_widget:
            property_name = "input-state"
        else:
            property_name = "state"

        self.label_widget.setProperty(property_name, state)
        self.label_widget.style().polish(self.label_widget)
        self._state = state

    def item_value(self):
        return self.checkbox.isChecked()


class NumberWidget(QtWidgets.QWidget, InputObject):
    default_input_value = 0
    value_changed = QtCore.Signal(object)
    input_modifiers = ("minimum", "maximum", "decimal")

    def __init__(
        self, input_data, parent,
        as_widget=False, label_widget=None, parent_widget=None
    ):
        if parent_widget is None:
            parent_widget = parent
        super(NumberWidget, self).__init__(parent_widget)

        self.initial_attributes(input_data, parent, as_widget)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        kwargs = {
            modifier: input_data.get(modifier)
            for modifier in self.input_modifiers
            if input_data.get(modifier)
        }
        self.input_field = NumberSpinBox(self, **kwargs)

        self.setFocusProxy(self.input_field)

        if not self._as_widget:
            self.key = input_data["key"]
            if not label_widget:
                label = input_data["label"]
                label_widget = QtWidgets.QLabel(label)
                layout.addWidget(label_widget, 0)
            self.label_widget = label_widget

        layout.addWidget(self.input_field, 1)

        self.input_field.valueChanged.connect(self._on_value_change)

    def set_value(self, value):
        self.input_field.setValue(value)

    def update_style(self):
        if self._as_widget:
            if not self.isEnabled():
                state = self.style_state(False, False, False, False)
            else:
                state = self.style_state(
                    False,
                    self._is_invalid,
                    False,
                    self._is_modified
                )
        else:
            state = self.style_state(
                self.has_studio_override,
                self.is_invalid,
                self.is_overriden,
                self.is_modified
            )
        if self._state == state:
            return

        if self._as_widget:
            property_name = "input-state"
            widget = self.input_field
        else:
            property_name = "state"
            widget = self.label_widget

        widget.setProperty(property_name, state)
        widget.style().polish(widget)

    def item_value(self):
        return self.input_field.value()


class TextWidget(QtWidgets.QWidget, InputObject):
    default_input_value = ""
    value_changed = QtCore.Signal(object)

    def __init__(
        self, input_data, parent,
        as_widget=False, label_widget=None, parent_widget=None
    ):
        if parent_widget is None:
            parent_widget = parent
        super(TextWidget, self).__init__(parent_widget)

        self.initial_attributes(input_data, parent, as_widget)

        self.multiline = input_data.get("multiline", False)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        if self.multiline:
            self.text_input = QtWidgets.QPlainTextEdit(self)
        else:
            self.text_input = QtWidgets.QLineEdit(self)

        self.setFocusProxy(self.text_input)

        layout_kwargs = {}
        if self.multiline:
            layout_kwargs["alignment"] = QtCore.Qt.AlignTop

        if not self._as_widget:
            self.key = input_data["key"]
            if not label_widget:
                label = input_data["label"]
                label_widget = QtWidgets.QLabel(label)
                layout.addWidget(label_widget, 0, **layout_kwargs)
            self.label_widget = label_widget

        layout.addWidget(self.text_input, 1, **layout_kwargs)

        self.text_input.textChanged.connect(self._on_value_change)

    def set_value(self, value):
        if self.multiline:
            self.text_input.setPlainText(value)
        else:
            self.text_input.setText(value)

    def update_style(self):
        if self._as_widget:
            if not self.isEnabled():
                state = self.style_state(False, False, False, False)
            else:
                state = self.style_state(
                    False,
                    self._is_invalid,
                    False,
                    self._is_modified
                )
        else:
            state = self.style_state(
                self.has_studio_override,
                self.is_invalid,
                self.is_overriden,
                self.is_modified
            )

        if self._state == state:
            return

        if self._as_widget:
            property_name = "input-state"
            widget = self.text_input
        else:
            property_name = "state"
            widget = self.label_widget

        widget.setProperty(property_name, state)
        widget.style().polish(widget)

    def item_value(self):
        if self.multiline:
            return self.text_input.toPlainText()
        else:
            return self.text_input.text()


class PathInputWidget(QtWidgets.QWidget, InputObject):
    default_input_value = ""
    value_changed = QtCore.Signal(object)

    def __init__(
        self, input_data, parent,
        as_widget=False, label_widget=None, parent_widget=None
    ):
        if parent_widget is None:
            parent_widget = parent
        super(PathInputWidget, self).__init__(parent_widget)

        self.initial_attributes(input_data, parent, as_widget)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        if not self._as_widget:
            self.key = input_data["key"]
            if not label_widget:
                label = input_data["label"]
                label_widget = QtWidgets.QLabel(label)
                layout.addWidget(label_widget, 0)
            self.label_widget = label_widget

        self.path_input = PathInput(self)
        self.setFocusProxy(self.path_input)
        layout.addWidget(self.path_input, 1)

        self.path_input.textChanged.connect(self._on_value_change)

    def set_value(self, value):
        self.path_input.setText(value)

    def focusOutEvent(self, event):
        self.path_input.clear_end_path()
        super(PathInput, self).focusOutEvent(event)

    def update_style(self):
        if self._as_widget:
            if not self.isEnabled():
                state = self.style_state(False, False, False, False)
            else:
                state = self.style_state(
                    False,
                    self._is_invalid,
                    False,
                    self._is_modified
                )
        else:
            state = self.style_state(
                self.has_studio_override,
                self.is_invalid,
                self.is_overriden,
                self.is_modified
            )

        if self._state == state:
            return

        if self._as_widget:
            property_name = "input-state"
            widget = self.path_input
        else:
            property_name = "state"
            widget = self.label_widget

        widget.setProperty(property_name, state)
        widget.style().polish(widget)

    def item_value(self):
        return self.path_input.text()


class RawJsonInput(QtWidgets.QPlainTextEdit):
    tab_length = 4

    def __init__(self, *args, **kwargs):
        super(RawJsonInput, self).__init__(*args, **kwargs)
        self.setObjectName("RawJsonInput")
        self.setTabStopDistance(
            QtGui.QFontMetricsF(
                self.font()
            ).horizontalAdvance(" ") * self.tab_length
        )

    def sizeHint(self):
        document = self.document()
        layout = document.documentLayout()

        height = document.documentMargin() + 2 * self.frameWidth() + 1
        block = document.begin()
        while block != document.end():
            height += layout.blockBoundingRect(block).height()
            block = block.next()

        hint = super(RawJsonInput, self).sizeHint()
        hint.setHeight(height)

        return hint

    def set_value(self, value):
        if value is NOT_SET:
            value = ""
        elif not isinstance(value, str):
            try:
                value = json.dumps(value, indent=4)
            except Exception:
                value = ""
        self.setPlainText(value)

    def json_value(self):
        return json.loads(self.toPlainText())

    def has_invalid_value(self):
        try:
            self.json_value()
            return False
        except Exception:
            return True

    def resizeEvent(self, event):
        self.updateGeometry()
        super(RawJsonInput, self).resizeEvent(event)


class RawJsonWidget(QtWidgets.QWidget, InputObject):
    default_input_value = "{}"
    value_changed = QtCore.Signal(object)

    def __init__(
        self, input_data, parent,
        as_widget=False, label_widget=None, parent_widget=None
    ):
        if parent_widget is None:
            parent_widget = parent
        super(RawJsonWidget, self).__init__(parent_widget)

        self.initial_attributes(input_data, parent, as_widget)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.text_input = RawJsonInput(self)
        self.text_input.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.MinimumExpanding
        )

        self.setFocusProxy(self.text_input)

        if not self._as_widget:
            self.key = input_data["key"]
            if not label_widget:
                label = input_data["label"]
                label_widget = QtWidgets.QLabel(label)
                layout.addWidget(label_widget, 0, alignment=QtCore.Qt.AlignTop)
            self.label_widget = label_widget
        layout.addWidget(self.text_input, 1, alignment=QtCore.Qt.AlignTop)

        self.text_input.textChanged.connect(self._on_value_change)

    def update_studio_values(self, parent_values):
        self._is_invalid = self.text_input.has_invalid_value()
        return super(RawJsonWidget, self).update_studio_values(parent_values)

    def set_value(self, value):
        self.text_input.set_value(value)

    def _on_value_change(self, *args, **kwargs):
        self._is_invalid = self.text_input.has_invalid_value()
        return super(RawJsonWidget, self)._on_value_change(*args, **kwargs)

    def update_style(self):
        if self._as_widget:
            if not self.isEnabled():
                state = self.style_state(False, False, False, False)
            else:
                state = self.style_state(
                    False,
                    self._is_invalid,
                    False,
                    self._is_modified
                )
        else:
            state = self.style_state(
                self.has_studio_override,
                self.is_invalid,
                self.is_overriden,
                self.is_modified
            )

        if self._state == state:
            return

        if self._as_widget:
            property_name = "input-state"
            widget = self.text_input
        else:
            property_name = "state"
            widget = self.label_widget

        widget.setProperty(property_name, state)
        widget.style().polish(widget)

    def item_value(self):
        if self.is_invalid:
            return NOT_SET
        return self.text_input.json_value()


class ListItem(QtWidgets.QWidget, SettingObject):
    _btn_size = 20
    value_changed = QtCore.Signal(object)

    def __init__(self, object_type, input_modifiers, config_parent, parent):
        super(ListItem, self).__init__(parent)

        self._set_default_attributes()

        self._parent = config_parent
        self._any_parent_is_group = True

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        char_up = qtawesome.charmap("fa.angle-up")
        char_down = qtawesome.charmap("fa.angle-down")

        self.add_btn = QtWidgets.QPushButton("+")
        self.remove_btn = QtWidgets.QPushButton("-")
        self.up_btn = QtWidgets.QPushButton(char_up)
        self.down_btn = QtWidgets.QPushButton(char_down)

        font_up_down = qtawesome.font("fa", 13)
        self.up_btn.setFont(font_up_down)
        self.down_btn.setFont(font_up_down)

        self.add_btn.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.remove_btn.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.up_btn.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.down_btn.setFocusPolicy(QtCore.Qt.ClickFocus)

        self.add_btn.setFixedSize(self._btn_size, self._btn_size)
        self.remove_btn.setFixedSize(self._btn_size, self._btn_size)
        self.up_btn.setFixedSize(self._btn_size, self._btn_size)
        self.down_btn.setFixedSize(self._btn_size, self._btn_size)

        self.add_btn.setProperty("btn-type", "tool-item")
        self.remove_btn.setProperty("btn-type", "tool-item")
        self.up_btn.setProperty("btn-type", "tool-item")
        self.down_btn.setProperty("btn-type", "tool-item")

        layout.addWidget(self.add_btn, 0)
        layout.addWidget(self.remove_btn, 0)

        self.add_btn.clicked.connect(self._on_add_clicked)
        self.remove_btn.clicked.connect(self._on_remove_clicked)
        self.up_btn.clicked.connect(self._on_up_clicked)
        self.down_btn.clicked.connect(self._on_down_clicked)

        ItemKlass = TypeToKlass.types[object_type]
        self.value_input = ItemKlass(
            input_modifiers,
            self,
            as_widget=True,
            label_widget=None
        )
        layout.addWidget(self.value_input, 1)

        layout.addWidget(self.up_btn, 0)
        layout.addWidget(self.down_btn, 0)

        self.value_input.value_changed.connect(self._on_value_change)

    def set_as_empty(self, is_empty=True):
        self.value_input.setEnabled(not is_empty)
        self.remove_btn.setEnabled(not is_empty)
        self.order_changed()
        self._on_value_change()

    def order_changed(self):
        row = self.row()
        parent_row_count = self.parent_rows_count()
        if parent_row_count == 1:
            self.up_btn.setEnabled(False)
            self.down_btn.setEnabled(False)

        elif row == 0:
            self.up_btn.setEnabled(False)
            self.down_btn.setEnabled(True)

        elif row == parent_row_count - 1:
            self.up_btn.setEnabled(True)
            self.down_btn.setEnabled(False)

        else:
            self.up_btn.setEnabled(True)
            self.down_btn.setEnabled(True)

    def _on_value_change(self, item=None):
        self.value_changed.emit(self)

    def row(self):
        return self._parent.input_fields.index(self)

    def parent_rows_count(self):
        return len(self._parent.input_fields)

    def _on_add_clicked(self):
        if self.value_input.isEnabled():
            self._parent.add_row(row=self.row() + 1)
        else:
            self.set_as_empty(False)

    def _on_remove_clicked(self):
        self._parent.remove_row(self)

    def _on_up_clicked(self):
        row = self.row()
        self._parent.swap_rows(row - 1, row)

    def _on_down_clicked(self):
        row = self.row()
        self._parent.swap_rows(row, row + 1)

    def config_value(self):
        if self.value_input.isEnabled():
            return self.value_input.item_value()
        return NOT_SET

    @property
    def child_has_studio_override(self):
        return self.value_input.child_has_studio_override

    @property
    def child_modified(self):
        return self.value_input.child_modified

    @property
    def child_overriden(self):
        return self.value_input.child_overriden

    def hierarchical_style_update(self):
        self.value_input.hierarchical_style_update()

    def mouseReleaseEvent(self, event):
        return QtWidgets.QWidget.mouseReleaseEvent(self, event)

    def update_default_values(self, value):
        self.value_input.update_default_values(value)

    def update_studio_values(self, value):
        self.value_input.update_studio_values(value)

    def apply_overrides(self, value):
        self.value_input.apply_overrides(value)


class ListWidget(QtWidgets.QWidget, InputObject):
    default_input_value = []
    value_changed = QtCore.Signal(object)

    def __init__(
        self, input_data, parent,
        as_widget=False, label_widget=None, parent_widget=None
    ):
        if parent_widget is None:
            parent_widget = parent
        super(ListWidget, self).__init__(parent_widget)
        self.setObjectName("ListWidget")

        self.initial_attributes(input_data, parent, as_widget)

        self.object_type = input_data["object_type"]
        self.input_modifiers = input_data.get("input_modifiers") or {}

        self.key = input_data["key"]

        self.input_fields = []

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 5)
        layout.setSpacing(5)

        if not label_widget:
            label_widget = QtWidgets.QLabel(input_data["label"], self)
            layout.addWidget(label_widget, alignment=QtCore.Qt.AlignTop)

        self.label_widget = label_widget

        inputs_widget = QtWidgets.QWidget(self)
        inputs_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        layout.addWidget(inputs_widget)

        inputs_layout = QtWidgets.QVBoxLayout(inputs_widget)
        inputs_layout.setContentsMargins(0, 0, 0, 0)
        inputs_layout.setSpacing(3)

        self.inputs_widget = inputs_widget
        self.inputs_layout = inputs_layout

        self.add_row(is_empty=True)

    def count(self):
        return len(self.input_fields)

    def update_studio_values(self, parent_values):
        super(ListWidget, self).update_studio_values(parent_values)

        self.hierarchical_style_update()

    def set_value(self, value):
        previous_inputs = tuple(self.input_fields)
        for item_value in value:
            self.add_row(value=item_value)

        for input_field in previous_inputs:
            self.remove_row(input_field)

        if self.count() == 0:
            self.add_row(is_empty=True)

    def swap_rows(self, row_1, row_2):
        if row_1 == row_2:
            return

        if row_1 > row_2:
            row_1, row_2 = row_2, row_1

        field_1 = self.input_fields[row_1]
        field_2 = self.input_fields[row_2]

        self.input_fields[row_1] = field_2
        self.input_fields[row_2] = field_1

        layout_index = self.inputs_layout.indexOf(field_1)
        self.inputs_layout.insertWidget(layout_index + 1, field_1)

        field_1.order_changed()
        field_2.order_changed()

    def add_row(self, row=None, value=None, is_empty=False):
        # Create new item
        item_widget = ListItem(
            self.object_type, self.input_modifiers, self, self.inputs_widget
        )
        if row is None:
            if self.input_fields:
                self.input_fields[-1].order_changed()
            self.inputs_layout.addWidget(item_widget)
            self.input_fields.append(item_widget)
        else:
            previous_field = None
            if row > 0:
                previous_field = self.input_fields[row - 1]

            next_field = None
            max_index = self.count()
            if row < max_index:
                next_field = self.input_fields[row]

            self.inputs_layout.insertWidget(row, item_widget)
            self.input_fields.insert(row, item_widget)
            if previous_field:
                previous_field.order_changed()

            if next_field:
                next_field.order_changed()

        if is_empty:
            item_widget.set_as_empty()
        item_widget.value_changed.connect(self._on_value_change)

        item_widget.order_changed()

        previous_input = None
        for input_field in self.input_fields:
            if previous_input is not None:
                self.setTabOrder(
                    previous_input, input_field.value_input.focusProxy()
                )
            previous_input = input_field.value_input.focusProxy()

        # Set text if entered text is not None
        # else (when add button clicked) trigger `_on_value_change`
        if value is not None:
            if self._is_overriden:
                item_widget.apply_overrides(value)
            elif not self._has_studio_override:
                item_widget.update_default_values(value)
            else:
                item_widget.update_studio_values(value)
            self.hierarchical_style_update()
        else:
            self._on_value_change()
        self.updateGeometry()

    def remove_row(self, item_widget):
        item_widget.value_changed.disconnect()

        row = self.input_fields.index(item_widget)
        previous_field = None
        next_field = None
        if row > 0:
            previous_field = self.input_fields[row - 1]

        if row != len(self.input_fields) - 1:
            next_field = self.input_fields[row + 1]

        self.inputs_layout.removeWidget(item_widget)
        self.input_fields.pop(row)
        item_widget.setParent(None)
        item_widget.deleteLater()

        if previous_field:
            previous_field.order_changed()

        if next_field:
            next_field.order_changed()

        if self.count() == 0:
            self.add_row(is_empty=True)

        self._on_value_change()
        self.updateGeometry()

    def apply_overrides(self, parent_values):
        self._is_modified = False
        if parent_values is NOT_SET or self.key not in parent_values:
            override_value = NOT_SET
        else:
            override_value = parent_values[self.key]

        self.override_value = override_value

        if override_value is NOT_SET:
            self._is_overriden = False
            self._was_overriden = False
            if self.has_studio_override:
                value = self.studio_value
            else:
                value = self.default_value
        else:
            self._is_overriden = True
            self._was_overriden = True
            value = override_value

        self._is_modified = False
        self._state = None

        self.set_value(value)

    def hierarchical_style_update(self):
        for input_field in self.input_fields:
            input_field.hierarchical_style_update()
        self.update_style()

    def update_style(self):
        if self._as_widget:
            if not self.isEnabled():
                state = self.style_state(False, False, False, False)
            else:
                state = self.style_state(
                    False,
                    self._is_invalid,
                    False,
                    self._is_modified
                )
        else:
            state = self.style_state(
                self.has_studio_override,
                self.is_invalid,
                self.is_overriden,
                self.is_modified
            )
        if self._state == state:
            return

        self.label_widget.setProperty("state", state)
        self.label_widget.style().polish(self.label_widget)

    def item_value(self):
        output = []
        for item in self.input_fields:
            value = item.config_value()
            if value is not NOT_SET:
                output.append(value)
        return output


class ModifiableDictItem(QtWidgets.QWidget, SettingObject):
    _btn_size = 20
    value_changed = QtCore.Signal(object)

    def __init__(self, object_type, input_modifiers, config_parent, parent):
        super(ModifiableDictItem, self).__init__(parent)

        self._set_default_attributes()
        self._parent = config_parent

        self.is_key_duplicated = False

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        ItemKlass = TypeToKlass.types[object_type]

        self.key_input = QtWidgets.QLineEdit(self)
        self.key_input.setObjectName("DictKey")

        self.value_input = ItemKlass(
            input_modifiers,
            self,
            as_widget=True,
            label_widget=None
        )
        self.add_btn = QtWidgets.QPushButton("+")
        self.remove_btn = QtWidgets.QPushButton("-")

        self.add_btn.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.remove_btn.setFocusPolicy(QtCore.Qt.ClickFocus)

        self.add_btn.setProperty("btn-type", "tool-item")
        self.remove_btn.setProperty("btn-type", "tool-item")

        layout.addWidget(self.add_btn, 0)
        layout.addWidget(self.remove_btn, 0)
        layout.addWidget(self.key_input, 0)
        layout.addWidget(self.value_input, 1)

        self.setFocusProxy(self.value_input)

        self.add_btn.setFixedSize(self._btn_size, self._btn_size)
        self.remove_btn.setFixedSize(self._btn_size, self._btn_size)
        self.add_btn.clicked.connect(self.on_add_clicked)
        self.remove_btn.clicked.connect(self.on_remove_clicked)

        self.key_input.textChanged.connect(self._on_value_change)
        self.value_input.value_changed.connect(self._on_value_change)

        self.origin_key = NOT_SET

    def key_value(self):
        return self.key_input.text()

    def _is_enabled(self):
        return self.key_input.isEnabled()

    def is_key_invalid(self):
        if not self._is_enabled():
            return False

        if self.key_value() == "":
            return True

        if self.is_key_duplicated:
            return True
        return False

    def _on_value_change(self, item=None):
        self.update_style()
        self.value_changed.emit(self)

    def update_default_values(self, key, value):
        self.origin_key = key
        self.key_input.setText(key)
        self.value_input.update_default_values(value)

    def update_studio_values(self, key, value):
        self.origin_key = key
        self.key_input.setText(key)
        self.value_input.update_studio_values(value)

    def apply_overrides(self, key, value):
        self.origin_key = key
        self.key_input.setText(key)
        self.value_input.apply_overrides(value)

    @property
    def is_group(self):
        return self._parent.is_group

    def on_add_clicked(self):
        if self._is_enabled():
            self._parent.add_row(row=self.row() + 1)
        else:
            self.set_as_empty(False)

    def on_remove_clicked(self):
        self._parent.remove_row(self)

    def set_as_empty(self, is_empty=True):
        self.key_input.setEnabled(not is_empty)
        self.value_input.setEnabled(not is_empty)
        self.remove_btn.setEnabled(not is_empty)
        self._on_value_change()

    @property
    def any_parent_is_group(self):
        return self._parent.any_parent_is_group

    def is_key_modified(self):
        return self.key_value() != self.origin_key

    def is_value_modified(self):
        return self.value_input.is_modified

    @property
    def is_modified(self):
        return self.is_value_modified() or self.is_key_modified()

    def hierarchical_style_update(self):
        self.value_input.hierarchical_style_update()
        self.update_style()

    @property
    def is_invalid(self):
        if not self._is_enabled():
            return False
        return self.is_key_invalid() or self.value_input.is_invalid

    def update_style(self):
        state = ""
        if self._is_enabled():
            if self.is_key_invalid():
                state = "invalid"
            elif self.is_key_modified():
                state = "modified"

        self.key_input.setProperty("state", state)
        self.key_input.style().polish(self.key_input)

    def row(self):
        return self._parent.input_fields.index(self)

    def item_value(self):
        key = self.key_input.text()
        value = self.value_input.item_value()
        return {key: value}

    def config_value(self):
        if self._is_enabled():
            return self.item_value()
        return {}

    def mouseReleaseEvent(self, event):
        return QtWidgets.QWidget.mouseReleaseEvent(self, event)


class ModifiableDict(QtWidgets.QWidget, InputObject):
    default_input_value = {}
    # Should be used only for dictionary with one datatype as value
    # TODO this is actually input field (do not care if is group or not)
    value_changed = QtCore.Signal(object)

    def __init__(
        self, input_data, parent,
        as_widget=False, label_widget=None, parent_widget=None
    ):
        if parent_widget is None:
            parent_widget = parent
        super(ModifiableDict, self).__init__(parent_widget)
        self.setObjectName("ModifiableDict")

        self.initial_attributes(input_data, parent, as_widget)

        self.input_fields = []

        self.key = input_data["key"]

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        content_widget = QtWidgets.QWidget(self)
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(CHILD_OFFSET, 3, 0, 3)

        if as_widget:
            main_layout.addWidget(content_widget)
            body_widget = None
        else:
            body_widget = ExpandingWidget(input_data["label"], self)
            main_layout.addWidget(body_widget)
            body_widget.set_content_widget(content_widget)

            self.body_widget = body_widget
            self.label_widget = body_widget.label_widget

            collapsable = input_data.get("collapsable", True)
            if collapsable:
                collapsed = input_data.get("collapsed", True)
                if not collapsed:
                    body_widget.toggle_content()

            else:
                body_widget.hide_toolbox(hide_content=False)

        self.body_widget = body_widget
        self.content_widget = content_widget
        self.content_layout = content_layout

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.object_type = input_data["object_type"]
        self.input_modifiers = input_data.get("input_modifiers") or {}

        self.add_row(is_empty=True)

    def count(self):
        return len(self.input_fields)

    def set_value(self, value):
        previous_inputs = tuple(self.input_fields)
        for item_key, item_value in value.items():
            self.add_row(key=item_key, value=item_value)

        for input_field in previous_inputs:
            self.remove_row(input_field)

        if self.count() == 0:
            self.add_row(is_empty=True)

    def _on_value_change(self, item=None):
        if self.ignore_value_changes:
            return

        fields_by_keys = collections.defaultdict(list)
        for input_field in self.input_fields:
            key = input_field.key_value()
            fields_by_keys[key].append(input_field)

        for fields in fields_by_keys.values():
            if len(fields) == 1:
                field = fields[0]
                if field.is_key_duplicated:
                    field.is_key_duplicated = False
                    field.update_style()
            else:
                for field in fields:
                    field.is_key_duplicated = True
                    field.update_style()

        if self.is_overidable:
            self._is_overriden = True
        else:
            self._has_studio_override = True

        if self._is_invalid:
            self._is_modified = True
        elif self._is_overriden:
            self._is_modified = self.item_value() != self.override_value
        elif self._has_studio_override:
            self._is_modified = self.item_value() != self.studio_value
        else:
            self._is_modified = self.item_value() != self.default_value

        self.update_style()

        self.value_changed.emit(self)

    def hierarchical_style_update(self):
        for input_field in self.input_fields:
            input_field.hierarchical_style_update()
        self.update_style()

    def update_style(self):
        if self._as_widget:
            if not self.isEnabled():
                state = self.style_state(False, False, False, False)
            else:
                state = self.style_state(
                    False,
                    self.is_invalid,
                    False,
                    self._is_modified
                )
        else:
            state = self.style_state(
                self.has_studio_override,
                self.is_invalid,
                self.is_overriden,
                self.is_modified
            )
        if self._state == state:
            return

        if state:
            child_state = "child-{}".format(state)
        else:
            child_state = ""

        if self.body_widget:
            self.body_widget.side_line_widget.setProperty("state", child_state)
            self.body_widget.side_line_widget.style().polish(
                self.body_widget.side_line_widget
            )

        if not self._as_widget:
            self.label_widget.setProperty("state", state)
            self.label_widget.style().polish(self.label_widget)

        self._state = state

    def all_item_values(self):
        output = {}
        for item in self.input_fields:
            output.update(item.item_value())
        return output

    def item_value(self):
        output = {}
        for item in self.input_fields:
            output.update(item.config_value())
        return output

    def add_row(self, row=None, key=None, value=None, is_empty=False):
        # Create new item
        item_widget = ModifiableDictItem(
            self.object_type, self.input_modifiers, self, self.content_widget
        )
        if is_empty:
            item_widget.set_as_empty()

        item_widget.value_changed.connect(self._on_value_change)

        if row is None:
            self.content_layout.addWidget(item_widget)
            self.input_fields.append(item_widget)
        else:
            self.content_layout.insertWidget(row, item_widget)
            self.input_fields.insert(row, item_widget)

        previous_input = None
        for input_field in self.input_fields:
            if previous_input is not None:
                self.setTabOrder(
                    previous_input, input_field.key_input
                )
            previous_input = input_field.value_input.focusProxy()
            self.setTabOrder(
                input_field.key_input, previous_input
            )

        # Set value if entered value is not None
        # else (when add button clicked) trigger `_on_value_change`
        if value is not None and key is not None:
            if not self._has_studio_override:
                item_widget.update_default_values(key, value)
            elif self._is_overriden:
                item_widget.apply_overrides(key, value)
            else:
                item_widget.update_studio_values(key, value)
            self.hierarchical_style_update()
        else:
            self._on_value_change()
        self.parent().updateGeometry()

    def remove_row(self, item_widget):
        item_widget.value_changed.disconnect()

        self.content_layout.removeWidget(item_widget)
        self.input_fields.remove(item_widget)
        item_widget.setParent(None)
        item_widget.deleteLater()

        if self.count() == 0:
            self.add_row(is_empty=True)

        self._on_value_change()
        self.parent().updateGeometry()

    @property
    def is_invalid(self):
        return self._is_invalid or self.child_invalid

    @property
    def child_invalid(self):
        for input_field in self.input_fields:
            if input_field.is_invalid:
                return True
        return False


# Dictionaries
class DictWidget(QtWidgets.QWidget, SettingObject):
    value_changed = QtCore.Signal(object)

    def __init__(
        self, input_data, parent,
        as_widget=False, label_widget=None, parent_widget=None
    ):
        if as_widget:
            raise TypeError("Can't use \"{}\" as widget item.".format(
                self.__class__.__name__
            ))

        if parent_widget is None:
            parent_widget = parent
        super(DictWidget, self).__init__(parent_widget)
        self.setObjectName("DictWidget")

        self.initial_attributes(input_data, parent, as_widget)

        if input_data.get("highlight_content", False):
            content_state = "hightlighted"
            bottom_margin = 5
        else:
            content_state = ""
            bottom_margin = 0

        self.input_fields = []

        self.key = input_data["key"]

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        body_widget = ExpandingWidget(input_data["label"], self)

        main_layout.addWidget(body_widget)

        content_widget = QtWidgets.QWidget(body_widget)
        content_widget.setObjectName("ContentWidget")
        content_widget.setProperty("content_state", content_state)
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(CHILD_OFFSET, 5, 0, bottom_margin)

        body_widget.set_content_widget(content_widget)

        self.body_widget = body_widget
        self.content_widget = content_widget
        self.content_layout = content_layout

        self.label_widget = body_widget.label_widget

        self.checkbox_widget = None
        self.checkbox_key = input_data.get("checkbox_key")

        for child_data in input_data.get("children", []):
            self.add_children_gui(child_data)

        collapsable = input_data.get("collapsable", True)
        if len(self.input_fields) == 1 and self.checkbox_widget:
            body_widget.hide_toolbox(hide_content=True)

        elif collapsable:
            collapsed = input_data.get("collapsed", True)
            if not collapsed:
                body_widget.toggle_content()
        else:
            body_widget.hide_toolbox(hide_content=False)

    def add_children_gui(self, child_configuration):
        item_type = child_configuration["type"]
        klass = TypeToKlass.types.get(item_type)

        if not klass.is_input_type:
            item = klass(child_configuration, self)
            self.content_layout.addWidget(item)
            return item

        if self.checkbox_key and not self.checkbox_widget:
            key = child_configuration.get("key")
            if key == self.checkbox_key:
                return self._add_checkbox_child(child_configuration)

        item = klass(child_configuration, self)
        item.value_changed.connect(self._on_value_change)
        self.content_layout.addWidget(item)

        self.input_fields.append(item)
        return item

    def _add_checkbox_child(self, child_configuration):
        item = BooleanWidget(
            child_configuration, self, label_widget=self.label_widget
        )
        item.value_changed.connect(self._on_value_change)

        self.body_widget.add_widget_after_label(item)
        self.checkbox_widget = item
        self.input_fields.append(item)
        return item

    def remove_overrides(self):
        self._is_overriden = False
        self._is_modified = False
        for input_field in self.input_fields:
            input_field.remove_overrides()

    def reset_to_pype_default(self):
        for input_field in self.input_fields:
            input_field.reset_to_pype_default()
        self._has_studio_override = False

    def set_studio_default(self):
        for input_field in self.input_fields:
            input_field.set_studio_default()

        if self.is_group:
            self._has_studio_override = True

    def discard_changes(self):
        self._is_overriden = self._was_overriden
        self._is_modified = False

        for input_field in self.input_fields:
            input_field.discard_changes()

        self._is_modified = self.child_modified

    def set_as_overriden(self):
        if self.is_overriden:
            return

        if self.is_group:
            self._is_overriden = True
            return

        for item in self.input_fields:
            item.set_as_overriden()

    def update_default_values(self, parent_values):
        value = NOT_SET
        if self._as_widget:
            value = parent_values
        elif parent_values is not NOT_SET:
            value = parent_values.get(self.key, NOT_SET)

        for item in self.input_fields:
            item.update_default_values(value)

    def update_studio_values(self, parent_values):
        value = NOT_SET
        if parent_values is not NOT_SET:
            value = parent_values.get(self.key, NOT_SET)

        self._has_studio_override = False
        if self.is_group and value is not NOT_SET:
            self._has_studio_override = True

        self._had_studio_override = bool(self._has_studio_override)

        for item in self.input_fields:
            item.update_studio_values(value)

    def apply_overrides(self, parent_values):
        # Make sure this is set to False
        self._state = None
        self._child_state = None

        metadata = {}
        groups = tuple()
        override_values = NOT_SET
        if parent_values is not NOT_SET:
            metadata = parent_values.get(METADATA_KEY) or metadata
            groups = metadata.get("groups") or groups
            override_values = parent_values.get(self.key, override_values)

        self._is_overriden = self.key in groups

        for item in self.input_fields:
            item.apply_overrides(override_values)

        if not self._is_overriden:
            self._is_overriden = (
                self.is_group
                and self.is_overidable
                and self.child_overriden
            )
        self._was_overriden = bool(self._is_overriden)

    def _on_value_change(self, item=None):
        if self.ignore_value_changes:
            return

        if self.is_group:
            if self.is_overidable:
                self._is_overriden = True
            else:
                self._has_studio_override = True

            self.hierarchical_style_update()

        self.value_changed.emit(self)

        self.update_style()

    def hierarchical_style_update(self):
        for input_field in self.input_fields:
            input_field.hierarchical_style_update()
        self.update_style()

    def update_style(self, is_overriden=None):
        child_has_studio_override = self.child_has_studio_override
        child_modified = self.child_modified
        child_invalid = self.child_invalid
        child_state = self.style_state(
            child_has_studio_override,
            child_invalid,
            self.child_overriden,
            child_modified
        )
        if child_state:
            child_state = "child-{}".format(child_state)

        if child_state != self._child_state:
            self.body_widget.side_line_widget.setProperty("state", child_state)
            self.body_widget.side_line_widget.style().polish(
                self.body_widget.side_line_widget
            )
            self._child_state = child_state

        state = self.style_state(
            self.had_studio_override,
            child_invalid,
            self.is_overriden,
            self.is_modified
        )
        if self._state == state:
            return

        self.label_widget.setProperty("state", state)
        self.label_widget.style().polish(self.label_widget)

        self._state = state

    @property
    def is_modified(self):
        if self.is_group:
            return self._is_modified or self.child_modified
        return False

    @property
    def child_has_studio_override(self):
        for input_field in self.input_fields:
            if (
                input_field.has_studio_override
                or input_field.child_has_studio_override
            ):
                return True
        return False

    @property
    def child_modified(self):
        for input_field in self.input_fields:
            if input_field.child_modified:
                return True
        return False

    @property
    def child_overriden(self):
        for input_field in self.input_fields:
            if input_field.is_overriden or input_field.child_overriden:
                return True
        return False

    @property
    def child_invalid(self):
        for input_field in self.input_fields:
            if input_field.child_invalid:
                return True
        return False

    def get_invalid(self):
        output = []
        for input_field in self.input_fields:
            output.extend(input_field.get_invalid())
        return output

    def item_value(self):
        output = {}
        for input_field in self.input_fields:
            # TODO maybe merge instead of update should be used
            # NOTE merge is custom function which merges 2 dicts
            output.update(input_field.config_value())
        return output

    def studio_overrides(self):
        if not self.has_studio_override and not self.child_has_studio_override:
            return NOT_SET, False

        values = {}
        groups = []
        for input_field in self.input_fields:
            value, is_group = input_field.studio_overrides()
            if value is not NOT_SET:
                values.update(value)
                if is_group:
                    groups.extend(value.keys())
        if groups:
            values[METADATA_KEY] = {"groups": groups}
        return {self.key: values}, self.is_group

    def overrides(self):
        if not self.is_overriden and not self.child_overriden:
            return NOT_SET, False

        values = {}
        groups = []
        for input_field in self.input_fields:
            value, is_group = input_field.overrides()
            if value is not NOT_SET:
                values.update(value)
                if is_group:
                    groups.extend(value.keys())
        if groups:
            values[METADATA_KEY] = {"groups": groups}
        return {self.key: values}, self.is_group


class DictInvisible(QtWidgets.QWidget, SettingObject):
    # TODO is not overridable by itself
    value_changed = QtCore.Signal(object)
    allow_actions = False

    def __init__(
        self, input_data, parent,
        as_widget=False, label_widget=None, parent_widget=None
    ):
        if parent_widget is None:
            parent_widget = parent
        super(DictInvisible, self).__init__(parent_widget)
        self.setObjectName("DictInvisible")

        self.initial_attributes(input_data, parent, as_widget)

        if self._is_group:
            raise TypeError("DictInvisible can't be marked as group input.")

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.input_fields = []

        self.key = input_data["key"]

        for child_data in input_data.get("children", []):
            self.add_children_gui(child_data)

    def add_children_gui(self, child_configuration):
        item_type = child_configuration["type"]
        klass = TypeToKlass.types.get(item_type)

        if not klass.is_input_type:
            item = klass(child_configuration, self)
            self.layout().addWidget(item)
            return item

        item = klass(child_configuration, self)
        self.layout().addWidget(item)

        item.value_changed.connect(self._on_value_change)

        self.input_fields.append(item)
        return item

    def update_style(self, *args, **kwargs):
        return

    @property
    def child_has_studio_override(self):
        for input_field in self.input_fields:
            if (
                input_field.has_studio_override
                or input_field.child_has_studio_override
            ):
                return True
        return False

    @property
    def child_modified(self):
        for input_field in self.input_fields:
            if input_field.child_modified:
                return True
        return False

    @property
    def child_overriden(self):
        for input_field in self.input_fields:
            if input_field.is_overriden or input_field.child_overriden:
                return True
        return False

    @property
    def child_invalid(self):
        for input_field in self.input_fields:
            if input_field.child_invalid:
                return True
        return False

    def get_invalid(self):
        output = []
        for input_field in self.input_fields:
            output.extend(input_field.get_invalid())
        return output

    def item_value(self):
        output = {}
        for input_field in self.input_fields:
            # TODO maybe merge instead of update should be used
            # NOTE merge is custom function which merges 2 dicts
            output.update(input_field.config_value())
        return output

    def _on_value_change(self, item=None):
        if self.ignore_value_changes:
            return

        if self.is_group:
            if self.is_overidable:
                self._is_overriden = True
            else:
                self._has_studio_override = True
            self.hierarchical_style_update()

        self.value_changed.emit(self)

    def hierarchical_style_update(self):
        for input_field in self.input_fields:
            input_field.hierarchical_style_update()
        self.update_style()

    def remove_overrides(self):
        self._is_overriden = False
        self._is_modified = False
        for input_field in self.input_fields:
            input_field.remove_overrides()

    def reset_to_pype_default(self):
        for input_field in self.input_fields:
            input_field.reset_to_pype_default()
        self._has_studio_override = False

    def set_studio_default(self):
        for input_field in self.input_fields:
            input_field.set_studio_default()

        if self.is_group:
            self._has_studio_override = True

    def discard_changes(self):
        self._is_modified = False
        self._is_overriden = self._was_overriden

        for input_field in self.input_fields:
            input_field.discard_changes()

        self._is_modified = self.child_modified

    def set_as_overriden(self):
        if self.is_overriden:
            return

        if self.is_group:
            self._is_overriden = True
            return

        for item in self.input_fields:
            item.set_as_overriden()

    def update_default_values(self, parent_values):
        value = NOT_SET
        if self._as_widget:
            value = parent_values
        elif parent_values is not NOT_SET:
            value = parent_values.get(self.key, NOT_SET)

        for item in self.input_fields:
            item.update_default_values(value)

    def update_studio_values(self, parent_values):
        value = NOT_SET
        if parent_values is not NOT_SET:
            value = parent_values.get(self.key, NOT_SET)

        for item in self.input_fields:
            item.update_studio_values(value)

    def apply_overrides(self, parent_values):
        # Make sure this is set to False
        self._state = None
        self._child_state = None

        metadata = {}
        groups = tuple()
        override_values = NOT_SET
        if parent_values is not NOT_SET:
            metadata = parent_values.get(METADATA_KEY) or metadata
            groups = metadata.get("groups") or groups
            override_values = parent_values.get(self.key, override_values)

        self._is_overriden = self.key in groups

        for item in self.input_fields:
            item.apply_overrides(override_values)

        if not self._is_overriden:
            self._is_overriden = (
                self.is_group
                and self.is_overidable
                and self.child_overriden
            )
        self._was_overriden = bool(self._is_overriden)

    def studio_overrides(self):
        if not self.has_studio_override and not self.child_has_studio_override:
            return NOT_SET, False

        values = {}
        groups = []
        for input_field in self.input_fields:
            value, is_group = input_field.studio_overrides()
            if value is not NOT_SET:
                values.update(value)
                if is_group:
                    groups.extend(value.keys())
        if groups:
            values[METADATA_KEY] = {"groups": groups}
        return {self.key: values}, self.is_group

    def overrides(self):
        if not self.is_overriden and not self.child_overriden:
            return NOT_SET, False

        values = {}
        groups = []
        for input_field in self.input_fields:
            value, is_group = input_field.overrides()
            if value is not NOT_SET:
                values.update(value)
                if is_group:
                    groups.extend(value.keys())
        if groups:
            values[METADATA_KEY] = {"groups": groups}
        return {self.key: values}, self.is_group


class PathWidget(QtWidgets.QWidget, SettingObject):
    value_changed = QtCore.Signal(object)
    platforms = ("windows", "darwin", "linux")
    platform_labels_mapping = {
        "windows": "Windows",
        "darwin": "MacOS",
        "linux": "Linux"
    }

    def __init__(
        self, input_data, parent,
        as_widget=False, label_widget=None, parent_widget=None
    ):
        if parent_widget is None:
            parent_widget = parent
        super(PathWidget, self).__init__(parent_widget)

        self.initial_attributes(input_data, parent, as_widget)

        # This is partial input and dictionary input
        if not self.any_parent_is_group and not self._as_widget:
            self._is_group = True
        else:
            self._is_group = False

        self.multiplatform = input_data.get("multiplatform", False)
        self.multipath = input_data.get("multipath", False)

        self.input_fields = []

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        if not self._as_widget:
            self.key = input_data["key"]
            if not label_widget:
                label = input_data["label"]
                label_widget = QtWidgets.QLabel(label)
                label_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
                layout.addWidget(label_widget, 0, alignment=QtCore.Qt.AlignTop)
            self.label_widget = label_widget

        self.content_widget = QtWidgets.QWidget(self)
        self.content_layout = QtWidgets.QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(0)
        self.content_layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.content_widget)

        self.create_gui()

    @property
    def default_input_value(self):
        if self.multipath:
            value_type = list
        else:
            value_type = str

        if self.multiplatform:
            return {
                platform: value_type()
                for platform in self.platforms
            }
        else:
            return value_type()

    def create_gui(self):
        if not self.multiplatform and not self.multipath:
            input_data = {"key": self.key}
            path_input = PathInputWidget(
                input_data, self, label_widget=self.label_widget
            )
            self.setFocusProxy(path_input)
            self.content_layout.addWidget(path_input)
            self.input_fields.append(path_input)
            path_input.value_changed.connect(self._on_value_change)
            return

        input_data_for_list = {
            "object_type": "path-input"
        }
        if not self.multiplatform:
            input_data_for_list["key"] = self.key
            input_widget = ListWidget(
                input_data_for_list, self, label_widget=self.label_widget
            )
            self.setFocusProxy(input_widget)
            self.content_layout.addWidget(input_widget)
            self.input_fields.append(input_widget)
            input_widget.value_changed.connect(self._on_value_change)
            return

        proxy_widget = QtWidgets.QWidget(self.content_widget)
        proxy_layout = QtWidgets.QFormLayout(proxy_widget)
        for platform_key in self.platforms:
            platform_label = self.platform_labels_mapping[platform_key]
            label_widget = QtWidgets.QLabel(platform_label, proxy_widget)
            if self.multipath:
                input_data_for_list["key"] = platform_key
                input_widget = ListWidget(
                    input_data_for_list, self, label_widget=label_widget
                )
            else:
                input_data = {"key": platform_key}
                input_widget = PathInputWidget(
                    input_data, self, label_widget=label_widget
                )
            proxy_layout.addRow(label_widget, input_widget)
            self.input_fields.append(input_widget)
            input_widget.value_changed.connect(self._on_value_change)

        self.setFocusProxy(self.input_fields[0])
        self.content_layout.addWidget(proxy_widget)

    def update_default_values(self, parent_values):
        self._state = None
        self._child_state = None
        self._is_modified = False

        value = NOT_SET
        if self._as_widget:
            value = parent_values
        elif parent_values is not NOT_SET:
            if not self.multiplatform:
                value = parent_values
            else:
                value = parent_values.get(self.key, NOT_SET)

        if value is NOT_SET:
            if self.develop_mode:
                if self._as_widget or not self.multiplatform:
                    value = {self.key: self.default_input_value}
                else:
                    value = self.default_input_value
                self.defaults_not_set = True
                if value is NOT_SET:
                    raise NotImplementedError((
                        "{} Does not have implemented"
                        " attribute `default_input_value`"
                    ).format(self))

            else:
                raise ValueError(
                    "Default value is not set. This is implementation BUG."
                )

        self.default_value = value
        self._has_studio_override = False
        self._had_studio_override = False

        if not self.multiplatform:
            self.input_fields[0].update_default_values(value)
        else:
            for input_field in self.input_fields:
                input_field.update_default_values(value)

    def update_studio_values(self, parent_values):
        self._state = None
        self._child_state = None
        self._is_modified = False

        value = NOT_SET
        if self._as_widget:
            value = parent_values
        elif parent_values is not NOT_SET:
            if not self.multiplatform:
                value = parent_values
            else:
                value = parent_values.get(self.key, NOT_SET)

        self.studio_value = value
        if value is not NOT_SET:
            self._has_studio_override = True
            self._had_studio_override = True
        else:
            self._has_studio_override = False
            self._had_studio_override = False
            value = self.default_value

        if not self.multiplatform:
            self.input_fields[0].update_studio_values(value)
        else:
            for input_field in self.input_fields:
                input_field.update_studio_values(value)

    def apply_overrides(self, parent_values):
        self._is_modified = False
        self._state = None
        self._child_state = None

        override_values = NOT_SET
        if self._as_widget:
            override_values = parent_values
        elif parent_values is not NOT_SET:
            if not self.multiplatform:
                override_values = parent_values
            else:
                override_values = parent_values.get(self.key, NOT_SET)

        self._is_overriden = override_values is not NOT_SET
        self._was_overriden = bool(self._is_overriden)

        if not self.multiplatform:
            self.input_fields[0].apply_overrides(parent_values)
        else:
            for input_field in self.input_fields:
                input_field.apply_overrides(override_values)

        if not self._is_overriden:
            self._is_overriden = (
                self.is_group
                and self.is_overidable
                and self.child_overriden
            )
        self._is_modified = False
        self._was_overriden = bool(self._is_overriden)

    def set_value(self, value):
        if not self.multiplatform:
            self.input_fields[0].set_value(value)

        else:
            for input_field in self.input_fields:
                _value = value[input_field.key]
                input_field.set_value(_value)

    def _on_value_change(self, item=None):
        if self.ignore_value_changes:
            return

        if self.is_overidable:
            self._is_overriden = True
        else:
            self._has_studio_override = True

        if self._is_invalid:
            self._is_modified = True
        elif self._is_overriden:
            self._is_modified = self.item_value() != self.override_value
        elif self._has_studio_override:
            self._is_modified = self.item_value() != self.studio_value
        else:
            self._is_modified = self.item_value() != self.default_value

        self.hierarchical_style_update()

        self.value_changed.emit(self)

    def update_style(self, is_overriden=None):
        child_has_studio_override = self.child_has_studio_override
        child_modified = self.child_modified
        child_invalid = self.child_invalid
        child_state = self.style_state(
            child_has_studio_override,
            child_invalid,
            self.child_overriden,
            child_modified
        )
        if child_state:
            child_state = "child-{}".format(child_state)

        if child_state != self._child_state:
            self.setProperty("state", child_state)
            self.style().polish(self)
            self._child_state = child_state

        if not self._as_widget:
            state = self.style_state(
                child_has_studio_override,
                child_invalid,
                self.is_overriden,
                self.is_modified
            )
            if self._state == state:
                return

            self.label_widget.setProperty("state", state)
            self.label_widget.style().polish(self.label_widget)

            self._state = state

    def remove_overrides(self):
        self._is_overriden = False
        self._is_modified = False
        for input_field in self.input_fields:
            input_field.remove_overrides()

    def reset_to_pype_default(self):
        for input_field in self.input_fields:
            input_field.reset_to_pype_default()
        self._has_studio_override = False

    def set_studio_default(self):
        for input_field in self.input_fields:
            input_field.set_studio_default()

        if self.is_group:
            self._has_studio_override = True

    def discard_changes(self):
        self._is_modified = False
        self._is_overriden = self._was_overriden

        for input_field in self.input_fields:
            input_field.discard_changes()

        self._is_modified = self.child_modified

    def set_as_overriden(self):
        self._is_overriden = True

    @property
    def child_has_studio_override(self):
        for input_field in self.input_fields:
            if (
                input_field.has_studio_override
                or input_field.child_has_studio_override
            ):
                return True
        return False

    @property
    def child_modified(self):
        for input_field in self.input_fields:
            if input_field.child_modified:
                return True
        return False

    @property
    def child_overriden(self):
        for input_field in self.input_fields:
            if input_field.child_overriden:
                return True
        return False

    @property
    def child_invalid(self):
        for input_field in self.input_fields:
            if input_field.child_invalid:
                return True
        return False

    def hierarchical_style_update(self):
        for input_field in self.input_fields:
            input_field.hierarchical_style_update()
        self.update_style()

    def item_value(self):
        if not self.multiplatform and not self.multipath:
            return self.input_fields[0].item_value()

        if not self.multiplatform:
            return self.input_fields[0].item_value()

        output = {}
        for input_field in self.input_fields:
            output.update(input_field.config_value())
        return output

    def studio_overrides(self):
        if not self.has_studio_override and not self.child_has_studio_override:
            return NOT_SET, False

        value = self.item_value()
        if not self.multiplatform:
            value = {self.key: value}
        return value, self.is_group

    def overrides(self):
        if not self.is_overriden and not self.child_overriden:
            return NOT_SET, False

        value = self.item_value()
        if not self.multiplatform:
            value = {self.key: value}
        return value, self.is_group


# Proxy for form layout
class FormLabel(QtWidgets.QLabel):
    def __init__(self, *args, **kwargs):
        super(FormLabel, self).__init__(*args, **kwargs)
        self.item = None


class DictFormWidget(QtWidgets.QWidget, SettingObject):
    value_changed = QtCore.Signal(object)
    allow_actions = False

    def __init__(
        self, input_data, parent,
        as_widget=False, label_widget=None, parent_widget=None
    ):
        if parent_widget is None:
            parent_widget = parent
        super(DictFormWidget, self).__init__(parent_widget)

        self.initial_attributes(input_data, parent, as_widget)

        self._as_widget = False
        self._is_group = False

        self.input_fields = []
        self.content_layout = QtWidgets.QFormLayout(self)
        self.content_layout.setContentsMargins(0, 0, 0, 0)

        for child_data in input_data.get("children", []):
            self.add_children_gui(child_data)

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

    def add_children_gui(self, child_configuration):
        item_type = child_configuration["type"]
        # Pop label to not be set in child
        label = child_configuration["label"]

        klass = TypeToKlass.types.get(item_type)

        label_widget = FormLabel(label, self)

        item = klass(child_configuration, self, label_widget=label_widget)
        label_widget.item = item

        item.value_changed.connect(self._on_value_change)
        self.content_layout.addRow(label_widget, item)
        self.input_fields.append(item)
        return item

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.RightButton:
            position = self.mapFromGlobal(QtGui.QCursor().pos())
            widget = self.childAt(position)
            if widget and isinstance(widget, FormLabel):
                widget.item.mouseReleaseEvent(event)
                event.accept()
                return
        super(DictFormWidget, self).mouseReleaseEvent(event)

    def apply_overrides(self, parent_values):
        for item in self.input_fields:
            item.apply_overrides(parent_values)

    def discard_changes(self):
        self._is_modified = False
        self._is_overriden = self._was_overriden

        for item in self.input_fields:
            item.discard_changes()

        self._is_modified = self.child_modified

    def remove_overrides(self):
        self._is_overriden = False
        self._is_modified = False
        for input_field in self.input_fields:
            input_field.remove_overrides()

    def reset_to_pype_default(self):
        for input_field in self.input_fields:
            input_field.reset_to_pype_default()
        self._has_studio_override = False

    def set_studio_default(self):
        for input_field in self.input_fields:
            input_field.set_studio_default()

        if self.is_group:
            self._has_studio_override = True

    def set_as_overriden(self):
        if self.is_overriden:
            return

        if self.is_group:
            self._is_overriden = True
            return

        for item in self.input_fields:
            item.set_as_overriden()

    def update_default_values(self, value):
        for item in self.input_fields:
            item.update_default_values(value)

    def update_studio_values(self, value):
        for item in self.input_fields:
            item.update_studio_values(value)

    def _on_value_change(self, item=None):
        if self.ignore_value_changes:
            return

        self.value_changed.emit(self)
        if self.any_parent_is_group:
            self.hierarchical_style_update()

    @property
    def child_has_studio_override(self):
        for input_field in self.input_fields:
            if (
                input_field.has_studio_override
                or input_field.child_has_studio_override
            ):
                return True
        return False

    @property
    def child_modified(self):
        for input_field in self.input_fields:
            if input_field.child_modified:
                return True
        return False

    @property
    def child_overriden(self):
        for input_field in self.input_fields:
            if input_field.is_overriden or input_field.child_overriden:
                return True
        return False

    @property
    def child_invalid(self):
        for input_field in self.input_fields:
            if input_field.child_invalid:
                return True
        return False

    def get_invalid(self):
        output = []
        for input_field in self.input_fields:
            output.extend(input_field.get_invalid())
        return output

    def hierarchical_style_update(self):
        for input_field in self.input_fields:
            input_field.hierarchical_style_update()

    def item_value(self):
        output = {}
        for input_field in self.input_fields:
            # TODO maybe merge instead of update should be used
            # NOTE merge is custom function which merges 2 dicts
            output.update(input_field.config_value())
        return output

    def config_value(self):
        return self.item_value()

    def studio_overrides(self):
        if not self.has_studio_override and not self.child_has_studio_override:
            return NOT_SET, False

        values = {}
        groups = []
        for input_field in self.input_fields:
            value, is_group = input_field.studio_overrides()
            if value is not NOT_SET:
                values.update(value)
                if is_group:
                    groups.extend(value.keys())
        if groups:
            values[METADATA_KEY] = {"groups": groups}
        return values, self.is_group

    def overrides(self):
        if not self.is_overriden and not self.child_overriden:
            return NOT_SET, False

        values = {}
        groups = []
        for input_field in self.input_fields:
            value, is_group = input_field.overrides()
            if value is not NOT_SET:
                values.update(value)
                if is_group:
                    groups.extend(value.keys())
        if groups:
            values[METADATA_KEY] = {"groups": groups}
        return values, self.is_group


class LabelWidget(QtWidgets.QWidget):
    is_input_type = False

    def __init__(self, configuration, parent=None):
        super(LabelWidget, self).__init__(parent)
        self.setObjectName("LabelWidget")

        label = configuration["label"]

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        label_widget = QtWidgets.QLabel(label, self)
        layout.addWidget(label_widget)


class SplitterWidget(QtWidgets.QWidget):
    is_input_type = False
    _height = 2

    def __init__(self, configuration, parent=None):
        super(SplitterWidget, self).__init__(parent)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        splitter_item = QtWidgets.QWidget(self)
        splitter_item.setObjectName("SplitterItem")
        splitter_item.setMinimumHeight(self._height)
        splitter_item.setMaximumHeight(self._height)
        layout.addWidget(splitter_item)


TypeToKlass.types["boolean"] = BooleanWidget
TypeToKlass.types["number"] = NumberWidget
TypeToKlass.types["text"] = TextWidget
TypeToKlass.types["path-input"] = PathInputWidget
TypeToKlass.types["raw-json"] = RawJsonWidget
TypeToKlass.types["list"] = ListWidget
TypeToKlass.types["dict-modifiable"] = ModifiableDict
TypeToKlass.types["dict"] = DictWidget
TypeToKlass.types["dict-invisible"] = DictInvisible
TypeToKlass.types["path-widget"] = PathWidget
TypeToKlass.types["dict-form"] = DictFormWidget

TypeToKlass.types["label"] = LabelWidget
TypeToKlass.types["splitter"] = SplitterWidget
