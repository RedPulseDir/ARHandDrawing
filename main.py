from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.graphics import Color, Line, Rectangle
from kivy.clock import Clock


class Stroke:
    def __init__(self, color, width):
        self.points = []
        self.color = color
        self.width = width
        self.ox = 0
        self.oy = 0


class Canvas(Widget):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.strokes = []
        self.cur = None
        self.col = (1, 0.3, 0.35, 1)
        self.w = 4
        self.grab = False
        self.held = []
        self.lp = None
        Clock.schedule_interval(self.draw, 1/30)

    def on_touch_down(self, t):
        if not self.collide_point(*t.pos):
            return
        x, y = t.pos
        if self.grab:
            self.held = [i for i, s in enumerate(self.strokes)
                        if any((p[0]+s.ox-x)**2+(p[1]+s.oy-y)**2 < 2500 for p in s.points)]
            if self.held:
                self.lp = (x, y)
        else:
            self.cur = Stroke(self.col, self.w)
            self.cur.points.append((x, y))
        return True

    def on_touch_move(self, t):
        if not self.collide_point(*t.pos):
            return
        x, y = t.pos
        if self.grab and self.lp and self.held:
            dx, dy = x - self.lp[0], y - self.lp[1]
            for i in self.held:
                self.strokes[i].ox += dx
                self.strokes[i].oy += dy
            self.lp = (x, y)
        elif self.cur:
            self.cur.points.append((x, y))
        return True

    def on_touch_up(self, t):
        if self.grab and self.held:
            for i in self.held:
                s = self.strokes[i]
                s.points = [(p[0]+s.ox, p[1]+s.oy) for p in s.points]
                s.ox = s.oy = 0
            self.held = []
            self.lp = None
        elif self.cur and len(self.cur.points) > 1:
            self.strokes.append(self.cur)
        self.cur = None
        return True

    def draw(self, dt):
        self.canvas.clear()
        with self.canvas:
            Color(0.05, 0.05, 0.08, 1)
            Rectangle(pos=self.pos, size=self.size)
            all_s = self.strokes + ([self.cur] if self.cur else [])
            for s in all_s:
                if s and len(s.points) > 1:
                    Color(*s.color)
                    pts = []
                    for p in s.points:
                        pts.extend([p[0]+s.ox, p[1]+s.oy])
                    Line(points=pts, width=s.width)

    def clear(self):
        self.strokes = []
        self.cur = None

    def undo(self):
        if self.strokes:
            self.strokes.pop()

    def set_col(self, r, g, b):
        self.col = (r, g, b, 1)

    def next_w(self):
        ws = [3, 6, 10, 16]
        self.w = ws[(ws.index(self.w) + 1) % 4] if self.w in ws else 4

    def tog_grab(self):
        self.grab = not self.grab
        return self.grab


class MyApp(App):
    def build(self):
        root = BoxLayout(orientation='vertical')
        
        top = BoxLayout(size_hint_y=0.08)
        self.btn = Button(text='Draw', background_color=(0.2, 0.8, 0.4, 1), background_normal='')
        self.btn.bind(on_press=self.tog)
        top.add_widget(self.btn)
        root.add_widget(top)
        
        self.c = Canvas()
        root.add_widget(self.c)
        
        bot = BoxLayout(size_hint_y=0.1, spacing=2, padding=2)
        cols = [(1,0.3,0.35), (0.2,0.85,0.45), (0.1,0.55,1), (1,0.65,0), (1,1,1), (0.65,0.4,0.9)]
        for r, g, b in cols:
            bt = Button(background_color=(r, g, b, 1), background_normal='')
            bt.bind(on_press=lambda x, r=r, g=g, b=b: self.c.set_col(r, g, b))
            bot.add_widget(bt)
        
        for txt, fn in [('X', self.c.clear), ('Z', self.c.undo), ('W', self.c.next_w)]:
            bt = Button(text=txt)
            bt.bind(on_press=lambda x, f=fn: f())
            bot.add_widget(bt)
        
        root.add_widget(bot)
        return root

    def tog(self, b):
        g = self.c.tog_grab()
        self.btn.text = 'Grab' if g else 'Draw'
        self.btn.background_color = (1, 0.65, 0, 1) if g else (0.2, 0.8, 0.4, 1)


if __name__ == '__main__':
    MyApp().run()
