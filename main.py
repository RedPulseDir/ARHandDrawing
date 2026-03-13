from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.graphics import Color, Line, Ellipse, Rectangle
from kivy.clock import Clock
from kivy.core.window import Window

# Для Android камеры
try:
    from android.permissions import request_permissions, Permission
    from kivy.uix.camera import Camera
    ANDROID = True
except:
    ANDROID = False

import math


class Stroke:
    def __init__(self, color, width):
        self.points = []
        self.color = color
        self.width = width
        self.offset_x = 0
        self.offset_y = 0
    
    def add(self, x, y):
        self.points.append((x, y))
    
    def apply_offset(self):
        self.points = [(p[0] + self.offset_x, p[1] + self.offset_y) for p in self.points]
        self.offset_x = 0
        self.offset_y = 0


class DrawingCanvas(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.strokes = []
        self.current_stroke = None
        self.color = (1, 0.27, 0.34, 1)
        self.line_width = 4
        
        # Touch drawing
        self.drawing = False
        
        # Grab mode
        self.grab_mode = False
        self.grabbing = False
        self.grabbed = []
        self.last_touch = None
        
        self.bind(size=self.redraw)
        Clock.schedule_interval(self.update, 1/60)
    
    def update(self, dt):
        self.redraw()
    
    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False
        
        x, y = touch.pos
        
        if self.grab_mode:
            self.grabbed = self.find_near(x, y, 60)
            if self.grabbed:
                self.grabbing = True
                self.last_touch = (x, y)
        else:
            self.drawing = True
            self.current_stroke = Stroke(self.color, self.line_width)
            self.current_stroke.add(x, y)
        
        return True
    
    def on_touch_move(self, touch):
        if not self.collide_point(*touch.pos):
            return False
        
        x, y = touch.pos
        
        if self.grab_mode and self.grabbing and self.last_touch:
            dx = x - self.last_touch[0]
            dy = y - self.last_touch[1]
            for i in self.grabbed:
                if i < len(self.strokes):
                    self.strokes[i].offset_x += dx
                    self.strokes[i].offset_y += dy
            self.last_touch = (x, y)
        elif self.drawing and self.current_stroke:
            self.current_stroke.add(x, y)
        
        return True
    
    def on_touch_up(self, touch):
        if self.grab_mode and self.grabbing:
            for i in self.grabbed:
                if i < len(self.strokes):
                    self.strokes[i].apply_offset()
            self.grabbed = []
            self.grabbing = False
            self.last_touch = None
        elif self.drawing and self.current_stroke:
            if len(self.current_stroke.points) >= 2:
                self.strokes.append(self.current_stroke)
            self.current_stroke = None
            self.drawing = False
        
        return True
    
    def find_near(self, x, y, radius):
        found = []
        r2 = radius * radius
        for i, s in enumerate(self.strokes):
            for px, py in s.points:
                dx = (px + s.offset_x) - x
                dy = (py + s.offset_y) - y
                if dx*dx + dy*dy < r2:
                    found.append(i)
                    break
        return found
    
    def redraw(self, *args):
        self.canvas.clear()
        with self.canvas:
            Color(0.04, 0.04, 0.06, 1)
            Rectangle(pos=self.pos, size=self.size)
            
            for s in self.strokes:
                if len(s.points) >= 2:
                    Color(*s.color)
                    pts = []
                    for px, py in s.points:
                        pts.extend([px + s.offset_x, py + s.offset_y])
                    Line(points=pts, width=s.width, cap='round', joint='round')
            
            if self.current_stroke and len(self.current_stroke.points) >= 2:
                Color(*self.current_stroke.color)
                pts = []
                for px, py in self.current_stroke.points:
                    pts.extend([px, py])
                Line(points=pts, width=self.current_stroke.width, cap='round', joint='round')
    
    def clear_all(self):
        self.strokes = []
        self.current_stroke = None
    
    def undo(self):
        if self.strokes:
            self.strokes.pop()
    
    def set_color(self, r, g, b):
        self.color = (r, g, b, 1)
    
    def next_thickness(self):
        sizes = [3, 6, 10, 16]
        try:
            idx = sizes.index(self.line_width)
        except:
            idx = 0
        self.line_width = sizes[(idx + 1) % len(sizes)]
    
    def toggle_grab(self):
        self.grab_mode = not self.grab_mode
        return self.grab_mode


class ColorButton(Button):
    def __init__(self, r, g, b, **kwargs):
        super().__init__(**kwargs)
        self.background_color = (r, g, b, 1)
        self.background_normal = ''
        self.r, self.g, self.b = r, g, b


class ARDrawingApp(App):
    def build(self):
        if ANDROID:
            request_permissions([Permission.CAMERA])
        
        self.root = BoxLayout(orientation='vertical')
        
        # Top bar
        top_bar = BoxLayout(size_hint_y=0.08, spacing=2, padding=5)
        top_bar.canvas.before.clear()
        with top_bar.canvas.before:
            Color(0.1, 0.1, 0.15, 1)
            self.top_rect = Rectangle(pos=top_bar.pos, size=top_bar.size)
        top_bar.bind(pos=self.update_top_rect, size=self.update_top_rect)
        
        self.status = Button(
            text='Draw Mode',
            size_hint_x=0.3,
            background_color=(0.2, 0.8, 0.4, 1),
            background_normal=''
        )
        self.status.bind(on_press=self.toggle_mode)
        top_bar.add_widget(self.status)
        
        self.root.add_widget(top_bar)
        
        # Canvas
        self.canvas_widget = DrawingCanvas()
        self.root.add_widget(self.canvas_widget)
        
        # Bottom bar
        bottom = BoxLayout(size_hint_y=0.1, spacing=2, padding=5)
        bottom.canvas.before.clear()
        with bottom.canvas.before:
            Color(0.1, 0.1, 0.15, 1)
            self.bot_rect = Rectangle(pos=bottom.pos, size=bottom.size)
        bottom.bind(pos=self.update_bot_rect, size=self.update_bot_rect)
        
        colors = [
            (1, 0.27, 0.34),
            (0.18, 0.84, 0.45),
            (0.12, 0.56, 1),
            (1, 0.65, 0.01),
            (1, 1, 1),
            (0.65, 0.37, 0.92)
        ]
        
        for r, g, b in colors:
            btn = ColorButton(r, g, b, size_hint_x=0.12)
            btn.bind(on_press=lambda x, r=r, g=g, b=b: self.set_color(r, g, b))
            bottom.add_widget(btn)
        
        btn_clear = Button(text='🗑', font_size='20sp', size_hint_x=0.12)
        btn_clear.bind(on_press=lambda x: self.canvas_widget.clear_all())
        bottom.add_widget(btn_clear)
        
        btn_undo = Button(text='↩', font_size='20sp', size_hint_x=0.12)
        btn_undo.bind(on_press=lambda x: self.canvas_widget.undo())
        bottom.add_widget(btn_undo)
        
        btn_size = Button(text='Size', size_hint_x=0.12)
        btn_size.bind(on_press=lambda x: self.canvas_widget.next_thickness())
        bottom.add_widget(btn_size)
        
        self.root.add_widget(bottom)
        
        return self.root
    
    def update_top_rect(self, *args):
        self.top_rect.pos = self.root.children[2].pos
        self.top_rect.size = self.root.children[2].size
    
    def update_bot_rect(self, *args):
        self.bot_rect.pos = self.root.children[0].pos
        self.bot_rect.size = self.root.children[0].size
    
    def set_color(self, r, g, b):
        self.canvas_widget.set_color(r, g, b)
    
    def toggle_mode(self, btn):
        grab = self.canvas_widget.toggle_grab()
        if grab:
            self.status.text = 'Grab Mode'
            self.status.background_color = (1, 0.65, 0, 1)
        else:
            self.status.text = 'Draw Mode'
            self.status.background_color = (0.2, 0.8, 0.4, 1)


if __name__ == '__main__':
    ARDrawingApp().run()
