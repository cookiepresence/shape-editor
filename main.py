import sys
from enum import Enum
from dataclasses import dataclass, field, fields
from typing import List

from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QAction,
    QFileDialog,
    QMessageBox,
    QGraphicsScene,
    QGraphicsView,
    QGraphicsItem
)
from PyQt5.QtGui import QBrush, QPen, QColor, QTransform, QPainter
from PyQt5.QtCore import Qt, QPointF, QRectF

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QComboBox, QPushButton

def asdict (obj):
    # from the official Python docs: https://docs.python.org/3/library/dataclasses.html
    return {field.name: getattr(obj, field.name) for field in fields(obj)}

class ObjectDialog(QDialog):
    def __init__(self, obj):
        super().__init__()
        self.obj = obj
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        if isinstance(self.obj, Line):
            color_label = QLabel("Line Color:")
            self.color_combo = QComboBox()
            self.color_combo.addItems(["black", "red", "green", "blue"])
            current_color = self.get_color_name(self.obj.color)
            self.color_combo.setCurrentText(current_color)
            layout.addWidget(color_label)
            layout.addWidget(self.color_combo)
        elif isinstance(self.obj, Rectangle):
            color_label = QLabel("Rectangle Color:")
            self.color_combo = QComboBox()
            self.color_combo.addItems(["black", "red", "green", "blue"])
            current_color = self.get_color_name(self.obj.color)
            self.color_combo.setCurrentText(current_color)
            layout.addWidget(color_label)
            layout.addWidget(self.color_combo)

            corner_label = QLabel("Corner Style:")
            self.corner_combo = QComboBox()
            self.corner_combo.addItems(["square", "rounded"])
            self.corner_combo.setCurrentText(self.obj.corner.name.lower())
            layout.addWidget(corner_label)
            layout.addWidget(self.corner_combo)

        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        layout.addWidget(ok_button)

        self.setLayout(layout)
        self.setWindowTitle("Edit Object")

    def get_color_name(self, color):
        match color:
            case Colour(0, 0, 0, 0): return "black"
            case Colour(0, _, 0, 0): return "red"
            case Colour(0, 0, _, 0): return "green"
            case Colour(0, 0, 0, _): return "blue"
            case Colour(_, _, _, _): return "black"
            
    def get_properties(self):
        if isinstance(self.obj, Line):
            color = self.color_combo.currentText()
            return {"color": color}
        elif isinstance(self.obj, Rectangle):
            color = self.color_combo.currentText()
            corner = self.corner_combo.currentText()
            return {"color": color, "corner": corner}


Format = Enum('Format', ['XML', 'DRW'])

SHAPES = []

class Corner(Enum):
    Rounded = 'r'
    Square = 's'

    def __str__(self):
        return self.value

    def xml (self):
        return f'<corner>{self.value}</corner>'

# Point and Line classes
@dataclass
class Point:
    x: float = 0.0
    y: float = 0.0

    def __str__(self):
        return ' '.join([str(v) for _, v in asdict(self).items()])

    def xml (self):
        print(asdict(self).items())
        print([f"<{k}>{v}</{k}>" for k, v in asdict(self).items()])
        return ''.join([f"<{k}>{v}</{k}>" for k, v in asdict(self).items()])


@dataclass
class Colour:
    k: int
    r: int
    g: int
    b: int

    def __str__(self):
        return ','.join([str(v) for _, v in asdict(self).items()])

    def xml (self):
        return ''.join([f"<{k}>{v}</{k}>" for k, v in asdict(self).items()])


@dataclass
class BoundingBox:
    bottom_left: Point = field(default_factory=Point)
    bottom_right: Point = field(default_factory=Point)
    top_left: Point = field(default_factory=Point)
    top_right: Point = field(default_factory=Point)

    in_use: bool = False

    def union (self, bb):
        if not bb.in_use:
            return self
        elif not self.in_use:
            return bb

        return BoundingBox(
            top_left = Point (
                min(self.top_left.x, bb.top_left.x),
                min(self.top_left.y, bb.top_left.y)
            ),
            bottom_left = Point (
                min(self.bottom_left.x, bb.bottom_left.x),
                max(self.bottom_left.y, bb.bottom_left.y)
            ),
            bottom_right = Point (
                max(self.bottom_right.x, bb.bottom_right.x),
                max(self.bottom_right.y, bb.bottom_right.y)
            ),
            top_right = Point (
                max(self.top_right.x, bb.top_right.x),
                max(self.top_right.y, bb.top_right.y)
            ),
            in_use = True
        )

    def contains (self, pos: Point):
        if not self.in_use:
            return True

        # Since most graphics screens are weird, and y increments from the top
        return ((self.bottom_left.x <= pos.x < self.top_right.x) and
                (self.top_left.y <= pos.y < self.bottom_right.y))

    def __add__ (self, bb):
        return self.union(bb)


@dataclass
class Line:
    start: Point
    end: Point
    color: Colour
    _bb: BoundingBox = field(default_factory=BoundingBox)

    def __post_init__(self):
        # self._bb = BoundingBox()
        self.update_bounding_box()

    def update_bounding_box(self):
        self._bb.in_use = True
        self._bb.top_left = Point(min(self.start.x, self.end.x),
                                  min(self.start.y, self.end.y))
        self._bb.top_right = Point(max(self.start.x, self.end.x),
                                   min(self.start.y, self.end.y))
        self._bb.bottom_left = Point(min(self.start.x, self.end.x),
                                     max(self.start.y, self.end.y))
        self._bb.bottom_right = Point(max(self.start.x, self.end.x),
                                      max(self.start.y, self.end.y))

    def __str__(self):
        return ' '.join(["line"] + [str(v) for k, v in asdict(self).items() if k[0] != '_'])

    def xml (self):
        print(asdict(self).items())
        return '\n'.join(["<line>"] +
                         [f"<{k.replace('_', '-')}>{v.xml()}</{k.replace('_', '-')}>"
                          for k, v in asdict(self).items() if k[0] != '_'] + 
                         ["</line>"])

    def contains (self, pos):
        def dot(v, w):
            return v.x * w.x + v.y * w.y
        def cross(v, w):
            return v.x * w.y + v.y * w.x

        v = Point(pos.x - self.start.x, pos.y - self.start.y)
        w = Point(self.end.x - pos.x, self.end.y - pos.y)

        return dot(v, w) > 0 and cross(v, w) == 0


@dataclass
class Rectangle:
    upper_left: Point
    lower_right: Point
    color: Colour
    corner: Corner
    _bb: BoundingBox = field(default_factory=BoundingBox)

    def __post_init__(self):
        # self._bb = BoundingBox()
        self.update_bounding_box()

    def update_bounding_box(self):
        self._bb.in_use = True
        self._bb.top_left = self.upper_left
        self._bb.top_right = Point(self.lower_right.x, self.upper_left.y)
        self._bb.bottom_right = self.lower_right
        self._bb.bottom_left = Point(self.upper_left.x, self.lower_right.y)

    def __str__(self):
        return ' '.join(["rect"] + [str(v) for k, v in asdict(self).items() if k[0] != '_'])

    def xml (self):
        return '\n'.join(["<rectangle>"] +
                         [f"<{k.replace('_', '-')}>{v.xml()}</{k.replace('_', '-')}>"
                          for k, v in asdict(self).items() if k[0] != '_'] +
                         ["</rectangle>"])

    def contains (self, pos):
        return self._bb.contains(pos)

@dataclass
class Group:
    members: list = field(default_factory=list)
    _bb: BoundingBox = field(default_factory=BoundingBox)

    def __str__(self):
        return '\n'.join(["begin"] + [str(m) for m in self.members] + ["end"])

    def xml (self):
        return f'<group>{"".join([m.xml() for m in self.members])}</group>'

    def create_group (self, shapes: List):
        for shape in shapes:
            self.add_to_group(shape)

        return self

    def add_to_group(self, shape):
        self.members.append(shape)
        self._bb = self._bb.union(shape._bb)

    def contains (self, pos):
        return self._bb.contains(pos)

class LineItem(QGraphicsItem):
    def __init__(self, line):
        super().__init__()
        self.line = line
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def boundingRect(self):
        return QRectF(self.line.start.x, self.line.start.y,
                      self.line.end.x - self.line.start.x,
                      self.line.end.y - self.line.start.y)

    def paint(self, painter, option, widget):
        pen = QPen(QColor(self.line.color.r, self.line.color.g, self.line.color.b))
        painter.setPen(pen)
        painter.drawLine(QPointF(self.line.start.x, self.line.start.y),
                         QPointF(self.line.end.x, self.line.end.y))

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedChange:
            self.setSelected(value)
        return super().itemChange(change, value)


class RectangleItem(QGraphicsItem):
    def __init__(self, rect):
        super().__init__()
        self.rect = rect
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def boundingRect(self):
        return QRectF(self.rect.upper_left.x, self.rect.upper_left.y,
                      self.rect.lower_right.x - self.rect.upper_left.x,
                      self.rect.lower_right.y - self.rect.upper_left.y)

    def paint(self, painter, option, widget):
        pen = QPen(QColor(self.rect.color.r, self.rect.color.g, self.rect.color.b))
        painter.setPen(pen)
        if self.rect.corner == Corner.Rounded:
            painter.drawRoundedRect(self.boundingRect(), 10, 10)
        else:
            painter.drawRect(self.boundingRect())

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedChange:
            self.setSelected(value)
        return super().itemChange(change, value)

class DrawingArea(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.objects = []
        self.selected_objects = []
        self.setSceneRect(0, 0, 800, 600)
        self.drawing_object = None
        self.drawing_line = None
        self.drawing_rect = None
        self.drawing_line_item = None
        self.drawing_rect_item = None
        self.move_mode = False
        self.moving_item = None
        self.selected_items = []
        self.delete_mode = False
        self.copy_mode = False
        self.copied_item = None
        self.edit_mode = False

    def display_objects(self, objects):
        self.objects = objects
        self.scene.clear()
        for obj in self.objects:
            if isinstance(obj, Line):
                item = LineItem(obj)
            elif isinstance(obj, Rectangle):
                item = RectangleItem(obj)
            else:
                continue
            self.scene.addItem(item)

    def toggle_copy_mode(self):
        self.copy_mode = not self.copy_mode
        if not self.copy_mode:
            self.copied_item = None

    # def delete_item(self, item):
    #     if isinstance(item, Group):
    #         self.objects.remove(item)
    #     else:
    #         for obj in self.objects:
    #             if isinstance(obj, Group) and item in obj.members:
    #                 obj.members.remove(item)
    #                 break
    #         else:
    #             self.objects.remove(item)
    #     self.scene.removeItem(item)

    def delete_item(self, item):
        for obj in self.objects:
            if isinstance(obj, Line) and isinstance(item, LineItem) and obj == item.line:
                self.objects.remove(obj)
                break
            elif isinstance(obj, Rectangle) and isinstance(item, RectangleItem) and obj == item.rect:
                self.objects.remove(obj)
                break
        self.scene.removeItem(item)

    def toggle_delete_mode(self):
        self.delete_mode = not self.delete_mode

    # def delete_selected_objects(self):
    #     for item in self.selected_items:
    #         if isinstance(item, Group):
    #             self.objects.remove(item)
    #         else:
    #             for obj in self.objects:
    #                 if isinstance(obj, Group) and item in obj.members:
    #                     obj.members.remove(item)
    #                     break
    #             else:
    #                 self.objects.remove(item)
    #         self.scene.removeItem(item)
    #     self.selected_items = []

    def edit_item(self, item):
        if isinstance(item, LineItem):
            obj = item.line
        elif isinstance(item, RectangleItem):
            obj = item.rect
        else:
            return

        dialog = ObjectDialog(obj)
        if dialog.exec_() == QDialog.Accepted:
            properties = dialog.get_properties()
            if isinstance(obj, Line):
                obj.color = self.get_color_from_name(properties["color"])
                item.update()
            elif isinstance(obj, Rectangle):
                obj.color = self.get_color_from_name(properties["color"])
                obj.corner = getattr(Corner, properties["corner"].capitalize())
                item.update()

    def get_color_from_name(self, color_name):
        if color_name == "black":
            return Colour(0, 0, 0, 0)
        elif color_name == "red":
            return Colour(0, 255, 0, 0)
        elif color_name == "green":
            return Colour(0, 0, 255, 0)
        elif color_name == "blue":
            return Colour(0, 0, 0, 255)
        else:
            return Colour(0, 0, 0, 0) 

    def toggle_move_mode(self):
        self.move_mode = not self.move_mode
        if self.move_mode:
            self.setDragMode(QGraphicsView.RubberBandDrag)
        else:
            self.setDragMode(QGraphicsView.NoDrag)

    def paste_item(self, pos):
        match self.copied_item:
            case LineItem():
                line = self.copied_item.line
                new_line = Line(Point(line.start.x + pos.x(), line.start.y + pos.y()),
                                Point(line.end.x + pos.x(), line.end.y + pos.y()),
                                line.color)
                new_item = LineItem(new_line)
                self.objects.append(new_line)
                self.scene.addItem(new_item)
            case RectangleItem():
                rect = self.copied_item.rect
                new_rect = Rectangle(Point(rect.upper_left.x + pos.x(), rect.upper_left.y + pos.y()),
                                    Point(rect.lower_right.x + pos.x(), rect.lower_right.y + pos.y()),
                                    rect.color, rect.corner)
                new_item = RectangleItem(new_rect)
                self.objects.append(new_rect)
                self.scene.addItem(new_item)

            case _:
                pass

    def mousePressEvent(self, event):
        if self.edit_mode:
            item = self.itemAt(event.pos())
            if item:
                self.edit_item(item)
                event.accept()
            else:
                event.ignore()
        if self.copy_mode:
            item = self.itemAt(event.pos())
            if item:
                self.copied_item = item
                event.accept()
            else:
                self.paste_item(event.pos())
                event.accept()
        elif self.delete_mode:
            item = self.itemAt(event.pos())
            if item:
                self.delete_item(item)
                event.accept()
            else:
                event.ignore()
        elif self.move_mode:
            item = self.itemAt(event.pos())
            if item:
                self.setDragMode(QGraphicsView.NoDrag)
                self.start_pos = event.pos()
                self.moving_item = item
            else:
                self.setDragMode(QGraphicsView.RubberBandDrag)
                self.moving_item = None
                super().mousePressEvent(event)
        else:
            if self.drawing_object == Line:
                self.drawing_line = Line(Point(event.x(), event.y()), Point(event.x(), event.y()),
                                        Colour(0, 0, 0, 0))
            elif self.drawing_object == Rectangle:
                self.drawing_rect = Rectangle(Point(event.x(), event.y()), Point(event.x(), event.y()),
                                            Colour(0, 0, 0, 0), Corner.Square)
            else:
                super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.move_mode:
            if self.moving_item:
                delta = event.pos() - self.start_pos
                self.moving_item.setPos(self.moving_item.pos() + delta)
                self.start_pos = event.pos()
            else:
                item = self.itemAt(event.pos())
                if item:
                    self.setDragMode(QGraphicsView.NoDrag)
                    self.start_pos = event.pos()
                    self.moving_item = item
                else:
                    super().mouseMoveEvent(event)
        elif self.drawing_line:
            self.drawing_line.end = Point(event.x(), event.y())
            if not self.drawing_line_item:
                self.drawing_line_item = LineItem(self.drawing_line)
                self.scene.addItem(self.drawing_line_item)
            else:
                self.drawing_line_item.prepareGeometryChange()
                self.drawing_line_item.line = self.drawing_line
                self.drawing_line_item.update()
        elif self.drawing_rect:
            self.drawing_rect.lower_right = Point(event.x(), event.y())
            if not self.drawing_rect_item:
                self.drawing_rect_item = RectangleItem(self.drawing_rect)
                self.scene.addItem(self.drawing_rect_item)
            else:
                self.drawing_rect_item.prepareGeometryChange()
                self.drawing_rect_item.rect = self.drawing_rect
                self.drawing_rect_item.update()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.move_mode:
            self.setDragMode(QGraphicsView.RubberBandDrag)
            self.moving_item = None
            super().mouseReleaseEvent(event)
        elif self.drawing_line:
            self.objects.append(self.drawing_line)
            self.drawing_line = None
            self.drawing_line_item = None
        elif self.drawing_rect:
            self.objects.append(self.drawing_rect)
            self.drawing_rect = None
            self.drawing_rect_item = None
        else:
            super().mouseReleaseEvent(event)

    def set_drawing_object(self, obj_type):
        self.drawing_object = obj_type

    def group_objects (self, selection):
        print(self.selected_objects)
        # TODO: Need to delete elements from the current array, and add to a group that will store everything
        raise NotImplementedError()

    def ungroup_all_objects (self):
        for obj in self.objects:
            if isinstance(obj, Group):
                self.objects.extend(obj.members)
                obj.members = []
                obj._bb.in_use = False

    def select_objects(self, pos):
        pos = Point(pos.x(), pos.y())
        selected_objs = filter(lambda x: x.contains(pos), self.objects)
        return selected_objs


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.drawing_area = DrawingArea()
        self.drawing_area.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setCentralWidget(self.drawing_area)

        self.toolbar = self.addToolBar("Drawing")

        #TODO: Can be redone with Named Tuples/Dataclasses?
        self.menu = [
            ("&File", [
                ("&Open", self.open_file, True),
                ("&Save", self.save_file, True),
                ("&Copy", self.toggle_copy_mode, True)
            ]),
            ("&Draw", [
                ("&Line", lambda: self.drawing_area.set_drawing_object(Line), True),
                ("&Rect", lambda: self.drawing_area.set_drawing_object(Rectangle), True)
            ]),
            ("&Edit", [
                ("&Group", self.drawing_area.group_objects, False),
                ("&Move", self.toggle_move_mode, True),
                ("&Delete", self.toggle_delete_mode, True),
                ("&Edit", self.toggle_edit_mode, True)
            ])
        ]

        self._create_menubar()

    def toggle_edit_mode(self):
        self.drawing_area.edit_mode = not self.drawing_area.edit_mode

    def toggle_copy_mode(self):
        self.drawing_area.toggle_copy_mode()

    def toggle_delete_mode(self):
        self.drawing_area.toggle_delete_mode()

    def toggle_move_mode(self):
        self.drawing_area.toggle_move_mode()

    def _create_menubar (self):
        for menu in self.menu:
            q_menu = self.menuBar().addMenu(menu[0])
            for action in menu[1]:
                q_action = QAction(action[0], self)
                q_action.triggered.connect(action[1])
                q_menu.addAction(q_action)

                if action[2]:
                    self.toolbar.addAction(q_action)

            self.toolbar.addSeparator()

    def open_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open File", "", "Drawing Files (*.drw)"
        )
        if filename:
            try:
                file_contents = ""
                with open(filename, "r") as f:
                    file_contents = f.read()

                objects = self.parse_file(Format.DRW, file_contents)
                self.drawing_area.display_objects(objects)
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def save_file(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save File", "", "Drawing Files (*.drw)"
        )
        if filename:
            try:
                with open(filename, "w") as f:
                    f.write(self.drawing_to_string(Format.DRW))
            except ZeroDivisionError as e:
                QMessageBox.critical(self, "Error", str(e))

    def parse_file(self, format: Format, file_contents: str) -> DrawingArea:
        def parse_xml(self, file_contents: str) -> DrawingArea:
            raise NotImplementedError("To be implemented")
    
        def parse_drw(self, file_contents: str) -> DrawingArea:
            def parse_line(line):
                tokens = line.split()
                if tokens[0] == "line":
                    start = Point(float(tokens[1]), float(tokens[2]))
                    end = Point(float(tokens[3]), float(tokens[4]))
                    colour = Colour(*map(int, tokens[5].split(',')))
                    return Line(start, end, colour)
                elif tokens[0] == "rect":
                    upper_left = Point(float(tokens[1]), float(tokens[2]))
                    bottom_right = Point(float(tokens[3]), float(tokens[4]))
                    colour = Colour(*map(int, tokens[5].split(',')))
                    corner = Corner(tokens[6]) if len(tokens) > 6 else Corner.Square
                    return Rectangle(upper_left, bottom_right, colour, corner)

            def parse_group(lines):
                current_group = []
                while lines != []:
                    line = lines[0]
                    line = line.strip()
                    if line == "begin":
                        sub_group, remaining_lines = parse_group(lines[1:])
                        current_group.append(sub_group)
                        lines = remaining_lines
                    elif line == "end":
                        return Group().create_group(current_group), lines[1:]
                    else:
                        parsed_line = parse_line(line)
                        current_group.append(parsed_line)
                        lines = lines[1:]
                return Group().create_group(current_group), []

            return parse_group(file_contents.split('\n'))[0].members
        
        match format:
            case Format.XML:
                return parse_xml(self, file_contents)
            case Format.DRW:
                return parse_drw(self, file_contents)

    def drawing_to_string(self, format: Format) -> str:
        match format:
            case Format.DRW:
                return '\n'.join([str(obj) for obj in self.drawing_area.objects])
            case Format.XML:
                return '\n'.join([obj.xml() for obj in self.drawing_area.objects])


if __name__ == "__main__":
    SHAPES = [Line, Rectangle]
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
