import sys
from enum import Enum
from dataclasses import dataclass, asdict

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


class Corner(Enum):
    Rounded = 'r'
    Square = 's'
    
    def xml (self):
        return NotImplementedError()

# Point and Line classes
@dataclass
class Point:
    x: int
    y: int

    def __str__(self):
        return ' '.join([v for _, v in asdict(self)])
    
    def xml (self):
        return NotImplementedError()


@dataclass
class Colour:
    k: int
    r: int
    g: int
    b: int

    def __str__(self):
        return ','.join([v for _, v in asdict(self)])
    
    def xml (self):
        return NotImplementedError()


@dataclass
class Line:
    start: Point
    end: Point
    color: Colour

    def __str__(self):
        return ','.join([v for _, v in asdict(self)])

    def xml (self):
        return NotImplementedError()

@dataclass
class Rectangle:
    upper_left: Point
    lower_right: Point
    color: Colour
    corner: Corner

    def __str__(self):
        return ','.join([v for _, v in asdict(self)])

    def xml (self):
        return NotImplementedError()


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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.drawing_area = DrawingArea()
        self.setCentralWidget(self.drawing_area)

        self._create_actions()
        self._create_menus()
        self._create_toolbars()

    def _create_actions(self):
        """Creates actions to be attached to menus"""
        self.open_action = QAction("&Open", self)
        self.open_action.triggered.connect(self.open_file)
        self.save_action = QAction("&Save", self)
        self.save_action.triggered.connect(self.save_file)
        self.line_action = QAction("&Line", self)
        self.line_action.triggered.connect(
            lambda: self.drawing_area.set_drawing_object("line")
        )
        self.rect_action = QAction("&Rectangle", self)
        self.rect_action.triggered.connect(
            lambda: self.drawing_area.set_drawing_object("rect")
        )
        self.group_action = QAction("&Group", self)
        self.group_action.triggered.connect(self.drawing_area.group_objects)

    def _create_menus(self):
        """Creates menus to be displayed in the menu bar of the program"""
        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.save_action)
        draw_menu = self.menuBar().addMenu("&Draw")
        draw_menu.addAction(self.line_action)
        draw_menu.addAction(self.rect_action)
        edit_menu = self.menuBar().addMenu("&Edit")
        edit_menu.addAction(self.group_action)

    def _create_toolbars(self):
        toolbar = self.addToolBar("Drawing")
        toolbar.addAction(self.open_action)
        toolbar.addAction(self.save_action)
        toolbar.addSeparator()
        toolbar.addAction(self.line_action)
        toolbar.addAction(self.rect_action)

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
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
