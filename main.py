import sys
from enum import Enum
from dataclasses import dataclass, asdict, field
from typing import List

from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QAction,
    QFileDialog,
    QMessageBox,
    QGraphicsScene,
    QGraphicsView,
)
from PyQt5.QtGui import QBrush, QPen, QColor, QTransform
from PyQt5.QtCore import Qt

Format = Enum('Format', ['XML', 'DRW'])

SHAPES = []

class Corner(Enum):
    Rounded = 'r'
    Square = 's'

    def xml (self):
        raise NotImplementedError()

# Point and Line classes
@dataclass
class Point:
    x: float = 0.0
    y: float = 0.0

    def __str__(self):
        return ' '.join([v for _, v in asdict(self)])

    def xml (self):
        raise NotImplementedError()


@dataclass
class Colour:
    k: int
    r: int
    g: int
    b: int

    def __str__(self):
        return ','.join([v for _, v in asdict(self)])

    def xml (self):
        raise NotImplementedError()


@dataclass
class BoundingBox:
    bottom_left: Point = Point()
    bottom_right: Point = Point()
    top_left: Point = Point()
    top_right: Point = Point()

    in_use: bool = False

    def union (self, bb: BoundingBox):
        if not bb.in_use :
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

    def __add__ (self, bb: BoundingBox):
        return self.union(bb)


@dataclass
class Line:
    start: Point
    end: Point
    color: Colour
    _bb: BoundingBox

    def __post_init__(self):
        self._bb = BoundingBox()
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
        return ' '.join([str(v) for k, v in asdict(self).items() if k[0] != '_'])

    def xml (self):
        raise NotImplementedError()

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
    _bb: BoundingBox

    def __post_init__(self):
        self._bb = BoundingBox()
        self.update_bounding_box()

    def update_bounding_box(self):
        self._bb.in_use = True
        self._bb.top_left = self.upper_left
        self._bb.top_right = Point(self.lower_right.x, self.upper_left.y)
        self._bb.bottom_right = self.lower_right
        self._bb.bottom_left = Point(self.upper_left.x, self.lower_right.y)

    def __str__(self):
        return ' '.join([v for k, v in asdict(self).items() if k[0] != '_'])

    def xml (self):
        raise NotImplementedError()

    def contains (self, pos):
        return self._bb.contains(pos)

@dataclass
class Group:
    members: list = field(default_factory=list)
    _bb: BoundingBox = BoundingBox()

    def __str__(self):
        return '\n'.join(["begin"] + [str(m) for m in self.members] + ["end"])

    def xml (self):
        raise NotImplementedError()

    def create_group (self, shapes: List):
        for shape in shapes:
            self.add_to_group(shape)

    def add_to_group(self, shape):
        self.members.append(shape)
        self._bb = self._bb.union(shape._bb)

    def contains (self, pos):
        return self._bb.contains(pos)


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
        self.drawing_rect = None  # Initialize drawing_rect to None

    def group_objects (self, selection):
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
        self.setCentralWidget(self.drawing_area)

        self.toolbar = self.addToolBar("Drawing")

        #TODO: Can be redone with Named Tuples/Dataclasses?
        self.menu = [
            ("&File", [
                ("&Open", self.open_file, True),
                ("&Save", self.save_file, True)
            ]),
            ("&Draw", [
                ("&Line", lambda: self.drawing_area.set_drawing_object(Line), True),
                ("&Rect", lambda: self.drawing_area.set_drawing_object(Rectangle), True)
            ]),
            ("&Edit", [
                ("&Group", self.drawing_area.group_objects, False)
            ])
        ]

        self._create_menubar()

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
                with open(filename, "r") as f:
                    self.drawing_area.objects.clear()
                    self.drawing_area.scene.clear()
                    for line in f:
                        obj_type, *args = line.strip().split()
                        if obj_type == "line":
                            x1, y1, x2, y2, color = args
                            obj = Line(int(x1), int(y1), int(x2), int(y2), color)
                        elif obj_type == "rect":
                            x1, y1, x2, y2, color, style = args
                            obj = Rectangle(
                                int(x1), int(y1), int(x2), int(y2), color, style
                            )
                        obj.draw(self.drawing_area.scene)
                        self.drawing_area.objects.append(obj)
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def save_file(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save File", "", "Drawing Files (*.drw)"
        )
        if filename:
            try:
                with open(filename, "w") as f:
                    for obj in self.drawing_area.objects:
                        args = " ".join(map(str, obj.args))
                        f.write(f"{obj.obj_type} {args}\n")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def parse_file(self, format: Format, file_contents: str) -> DrawingArea:
        def parse_xml(self, file_contents: str) -> DrawingArea:
            raise NotImplementedError("To be implemented")
        
        def parse_drw(self, file_contents: str) -> DrawingArea:
            raise NotImplementedError("To be implemented")
        
        match format:
            case Format.XML:
                return parse_xml(self, file_contents)
            case Format.DRW:
                return parse_drw(self, file_contents)

    def drawing_to_string(self, format: Format) -> str:
        match format:
            case Format.XML:
                return '\n'.join([str(obj) for obj in self.drawing_area.objects])
            case Format.DRW:
                return '\n'.join([obj.xml() for obj in self.drawing_area.objects])


if __name__ == "__main__":
    SHAPES = [Line, Rectangle]
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
