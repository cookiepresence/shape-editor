import sys
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


class DrawingObject:
    def __init__(self, obj_type, *args):
        self.obj_type = obj_type
        self.args = args

    def draw(self, scene):
        raise NotImplementedError

    def get_properties(self):
        raise NotImplementedError

    def set_properties(self, props):
        raise NotImplementedError


class Line(DrawingObject):
    def __init__(self, x1, y1, x2, y2, color):
        super().__init__("line", x1, y1, x2, y2, color)

    def draw(self, scene):
        pen = QPen(QColor(self.args[4]))
        scene.addLine(self.args[0], self.args[1], self.args[2], self.args[3], pen)

    def get_properties(self):
        return {"color": self.args[4]}

    def set_properties(self, props):
        self.args = (
            self.args[0],
            self.args[1],
            self.args[2],
            self.args[3],
            props["color"],
        )


class Rectangle(DrawingObject):
    def __init__(self, x1, y1, x2, y2, color, style):
        super().__init__("rect", x1, y1, x2, y2, color, style)

    def draw(self, scene):
        pen = QPen(QColor(self.args[4]))
        brush = QBrush(QColor(self.args[4]))
        if self.args[5] == "square":
            scene.addRect(
                min(self.args[0], self.args[2]),
                min(self.args[1], self.args[3]),
                abs(self.args[0] - self.args[2]),
                abs(self.args[1] - self.args[3]),
                pen,
                brush,
            )
        else:
            scene.addEllipse(
                min(self.args[0], self.args[2]),
                min(self.args[1], self.args[3]),
                abs(self.args[0] - self.args[2]),
                abs(self.args[1] - self.args[3]),
                pen,
                brush,
            )

    def get_properties(self):
        return {"color": self.args[4], "style": self.args[5]}

    def set_properties(self, props):
        self.args = (
            self.args[0],
            self.args[1],
            self.args[2],
            self.args[3],
            props["color"],
            props["style"],
        )


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

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.drawing_object:
                self.start_pos = event.pos()
            else:
                if not self.drawing_object:
                    self.select_objects(event.pos())

    def mouseMoveEvent(self, event):
        if self.drawing_object:
            self.update_drawing(event.pos())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.drawing_object:
            self.finish_drawing(event.pos())

    def select_objects(self, pos):
        self.selected_objects.clear()
        for obj in self.objects:
            if obj.obj_type == "line":
                x1, y1, x2, y2, _ = obj.args
                if self.line_rect(x1, y1, x2, y2).contains(pos):
                    self.selected_objects.append(obj)
            elif obj.obj_type == "rect":
                x1, y1, x2, y2, _, _ = obj.args
                rect = self.scene.addRect(
                    min(x1, x2), min(y1, y2), abs(x1 - x2), abs(y1 - y2)
                )
                if rect.contains(pos):
                    self.selected_objects.append(obj)
                    self.scene.removeItem(rect)

    def line_rect(self, x1, y1, x2, y2):
        rect = self.scene.addRect(min(x1, x2), min(y1, y2), abs(x1 - x2), abs(y1 - y2))
        rect_region = rect.boundingRegion(QTransform())
        self.scene.removeItem(rect)
        return rect_region

    def update_drawing(self, pos):
        if self.drawing_object.obj_type == "line":
            self.scene.removeItem(self.drawing_line)
            self.drawing_line = self.scene.addLine(
                self.start_pos.x(), self.start_pos.y(), pos.x(), pos.y(), QPen(Qt.black)
            )
        elif self.drawing_object.obj_type == "rect":
            self.scene.removeItem(self.drawing_rect)
            self.drawing_rect = self.scene.addRect(
                self.start_pos.x(),
                self.start_pos.y(),
                pos.x() - self.start_pos.x(),
                pos.y() - self.start_pos.y(),
                QPen(Qt.black),
                QBrush(Qt.black),
            )

    def finish_drawing(self, pos):
        if self.drawing_object.obj_type == "line":
            self.scene.removeItem(self.drawing_line)
            line = Line(
                self.start_pos.x(), self.start_pos.y(), pos.x(), pos.y(), "black"
            )
            line.draw(self.scene)
            self.objects.append(line)
        elif self.drawing_object.obj_type == "rect":
            self.scene.removeItem(self.drawing_rect)
            rect = Rectangle(
                self.start_pos.x(),
                self.start_pos.y(),
                pos.x(),
                pos.y(),
                "black",
                "square",
            )
            rect.draw(self.scene)
            self.objects.append(rect)
        self.drawing_object = None

    def set_drawing_object(self, obj_type):
        self.drawing_object = DrawingObject(obj_type)

    def group_objects(self):
        if len(self.selected_objects) > 1:
            group = Group(self.selected_objects)
            self.objects.append(group)
            self.selected_objects = [group]
            for obj in group.objects:
                self.objects.remove(obj)

    def ungroup_objects(self):
        if len(self.selected_objects) == 1:
            group = self.selected_objects[0]
            if isinstance(group, Group):
                self.objects.extend(group.objects)
                self.objects.remove(group)
                self.selected_objects = group.objects

    def ungroup_all(self):
        if len(self.selected_objects) == 1:
            group = self.selected_objects[0]
            ungrouped_objects = []
            self.ungroup_recursive(group, ungrouped_objects)
            self.objects.remove(group)
            self.objects.extend(ungrouped_objects)
            self.selected_objects = ungrouped_objects

    def ungroup_recursive(self, obj, ungrouped_objects):
        if isinstance(obj, Group):
            for sub_obj in obj.objects:
                self.ungroup_recursive(sub_obj, ungrouped_objects)
        else:
            ungrouped_objects.append(obj)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.drawing_area = DrawingArea()
        self.setCentralWidget(self.drawing_area)
        self.create_actions()
        self.create_menus()
        self.create_toolbars()

    def create_actions(self):
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

    def create_menus(self):
        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.save_action)
        draw_menu = self.menuBar().addMenu("&Draw")
        draw_menu.addAction(self.line_action)
        draw_menu.addAction(self.rect_action)
        edit_menu = self.menuBar().addMenu("&Edit")
        edit_menu.addAction(self.group_action)

    def create_toolbars(self):
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


class Group(DrawingObject):
    def __init__(self, objects):
        super().__init__("group")
        self.objects = objects

    def draw(self, scene):
        for obj in self.objects:
            obj.draw(scene)

    def get_properties(self):
        return {}

    def set_properties(self, props):
        pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
