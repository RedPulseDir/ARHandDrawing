"""
AR Hand Drawing - Рисование руками в воздухе
Камера + MediaPipe + Отслеживание рук + Жесты
"""

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.graphics import Color, Line, Ellipse, Rectangle
from kivy.graphics.texture import Texture
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.utils import platform
import math
import time

# Камера
if platform == 'android':
    from jnius import autoclass, cast, PythonJavaClass, java_method
    from android.permissions import request_permissions, Permission
    
    CameraManager = autoclass('android.hardware.camera2.CameraManager')
    CameraDevice = autoclass('android.hardware.camera2.CameraDevice')
    CameraCharacteristics = autoclass('android.hardware.camera2.CameraCharacteristics')
    CaptureRequest = autoclass('android.hardware.camera2.CaptureRequest')
    ImageFormat = autoclass('android.graphics.ImageFormat')
    ImageReader = autoclass('android.media.ImageReader')
    SurfaceTexture = autoclass('android.graphics.SurfaceTexture')
    Surface = autoclass('android.view.Surface')
    HandlerThread = autoclass('android.os.HandlerThread')
    Handler = autoclass('android.os.Handler')
    Context = autoclass('android.content.Context')
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    ByteBuffer = autoclass('java.nio.ByteBuffer')
    ANDROID = True
else:
    ANDROID = False

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    import mediapipe as mp
    MP_AVAILABLE = True
except ImportError:
    MP_AVAILABLE = False


# ============================================================================
# HAND DETECTOR - Обнаружение рук
# ============================================================================

class HandDetector:
    """Детектор рук с использованием MediaPipe или цвета кожи"""
    
    CONNECTIONS = [
        (0,1),(1,2),(2,3),(3,4),
        (0,5),(5,6),(6,7),(7,8),
        (0,9),(9,10),(10,11),(11,12),
        (0,13),(13,14),(14,15),(15,16),
        (0,17),(17,18),(18,19),(19,20),
        (5,9),(9,13),(13,17)
    ]
    TIPS = [4, 8, 12, 16, 20]
    
    def __init__(self, max_hands=2):
        self.max_hands = max_hands
        self.hands_data = []
        self.mp_hands = None
        
        if MP_AVAILABLE:
            self.mp_hands = mp.solutions.hands.Hands(
                static_image_mode=False,
                max_num_hands=max_hands,
                min_detection_confidence=0.7,
                min_tracking_confidence=0.6
            )
    
    def process_frame(self, frame):
        """Обрабатывает кадр и находит руки"""
        self.hands_data = []
        
        if frame is None:
            return self.hands_data
        
        if self.mp_hands and CV2_AVAILABLE:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.mp_hands.process(rgb)
            
            if results.multi_hand_landmarks:
                h, w = frame.shape[:2]
                for hand_lm in results.multi_hand_landmarks:
                    landmarks = []
                    for lm in hand_lm.landmark:
                        landmarks.append({
                            'x': lm.x,
                            'y': lm.y,
                            'z': lm.z,
                            'px': int(lm.x * w),
                            'py': int(lm.y * h)
                        })
                    self.hands_data.append(landmarks)
        elif CV2_AVAILABLE:
            self._detect_by_skin(frame)
        
        return self.hands_data
    
    def _detect_by_skin(self, frame):
        """Детекция по цвету кожи (fallback)"""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, (0, 20, 70), (20, 255, 255))
        mask = cv2.GaussianBlur(mask, (5, 5), 0)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        h, w = frame.shape[:2]
        
        for cnt in sorted(contours, key=cv2.contourArea, reverse=True)[:self.max_hands]:
            if cv2.contourArea(cnt) < 5000:
                continue
            
            M = cv2.moments(cnt)
            if M['m00'] == 0:
                continue
            
            cx = int(M['m10'] / M['m00'])
            cy = int(M['m01'] / M['m00'])
            bbox = cv2.boundingRect(cnt)
            
            hull = cv2.convexHull(cnt, returnPoints=True)
            
            landmarks = self._estimate_landmarks(cx, cy, bbox, hull, w, h)
            self.hands_data.append(landmarks)
    
    def _estimate_landmarks(self, cx, cy, bbox, hull, img_w, img_h):
        """Оценивает позиции 21 точки руки"""
        bx, by, bw, bh = bbox
        landmarks = []
        
        # Wrist
        landmarks.append({
            'x': cx / img_w, 'y': (cy + bh * 0.4) / img_h, 'z': 0,
            'px': cx, 'py': int(cy + bh * 0.4)
        })
        
        finger_offsets = [-0.35, -0.17, 0.0, 0.17, 0.35]
        finger_lengths = [0.55, 0.75, 0.8, 0.7, 0.55]
        
        # Ищем самые дальние точки hull как кончики пальцев
        hull_points = hull.reshape(-1, 2)
        top_points = sorted(hull_points, key=lambda p: p[1])[:5]
        
        for finger in range(5):
            base_x = cx + finger_offsets[finger] * bw * 0.5
            base_y = cy
            
            # Используем hull точки если есть
            if finger < len(top_points):
                tip_x, tip_y = top_points[finger]
            else:
                tip_x = base_x
                tip_y = base_y - finger_lengths[finger] * bh * 0.5
            
            for joint in range(4):
                progress = (joint + 1) / 4.0
                jx = base_x + (tip_x - base_x) * progress
                jy = base_y + (tip_y - base_y) * progress
                
                landmarks.append({
                    'x': jx / img_w, 'y': jy / img_h, 'z': 0,
                    'px': int(jx), 'py': int(jy)
                })
        
        return landmarks
    
    def get_hand_count(self):
        return len(self.hands_data)
    
    def close(self):
        if self.mp_hands:
            self.mp_hands.close()


# ============================================================================
# GESTURE RECOGNIZER - Распознавание жестов
# ============================================================================

class GestureRecognizer:
    NONE = 'none'
    POINT = 'point'
    PINCH = 'pinch'
    GRAB = 'grab'
    OPEN = 'open'
    
    GESTURE_NAMES = {
        'none': '🤚 Ожидание',
        'point': '✏️ Рисование',
        'pinch': '👌 Захват',
        'grab': '✊ Захват',
        'open': '✋ Пауза'
    }
    
    GESTURE_COLORS = {
        'none': (0.7, 0.7, 0.7, 0.5),
        'point': (1, 0.27, 0.34, 1),
        'pinch': (1, 0.84, 0, 1),
        'grab': (1, 0.84, 0, 1),
        'open': (0.5, 0.5, 0.5, 0.5)
    }
    
    def __init__(self, max_hands=2):
        self.states = [
            {'confirmed': self.NONE, 'pending': self.NONE, 'frames': 0}
            for _ in range(max_hands)
        ]
        self.CONFIRM_FRAMES = 2
        self.PINCH_THRESHOLD = 0.07
    
    def recognize(self, landmarks, hand_index=0):
        if landmarks is None or len(landmarks) < 21:
            return self._update(hand_index, self.NONE)
        return self._update(hand_index, self._detect(landmarks))
    
    def _detect(self, lm):
        def extended(tip, pip):
            return lm[tip]['y'] < lm[pip]['y'] - 0.03
        
        index_up = extended(8, 6)
        middle_up = extended(12, 10)
        ring_up = extended(16, 14)
        pinky_up = extended(20, 18)
        
        # Расстояние между большим и указательным
        dx = lm[4]['x'] - lm[8]['x']
        dy = lm[4]['y'] - lm[8]['y']
        pinch_dist = math.sqrt(dx*dx + dy*dy)
        
        if pinch_dist < self.PINCH_THRESHOLD:
            return self.PINCH
        if index_up and not middle_up and not ring_up and not pinky_up:
            return self.POINT
        if index_up and middle_up and ring_up and pinky_up:
            return self.OPEN
        if not index_up and not middle_up and not ring_up and not pinky_up:
            return self.GRAB
        return self.NONE
    
    def _update(self, idx, detected):
        s = self.states[idx]
        if detected == s['pending']:
            s['frames'] += 1
        else:
            s['pending'] = detected
            s['frames'] = 1
        if s['frames'] >= self.CONFIRM_FRAMES and s['confirmed'] != s['pending']:
            s['confirmed'] = s['pending']
        return s['confirmed']
    
    def get_name(self, gesture):
        return self.GESTURE_NAMES.get(gesture, '🤚 Ожидание')
    
    def get_color(self, gesture):
        return self.GESTURE_COLORS.get(gesture, (0.7, 0.7, 0.7, 0.5))
    
    def reset(self):
        for s in self.states:
            s['confirmed'] = self.NONE
            s['pending'] = self.NONE
            s['frames'] = 0


# ============================================================================
# STROKE - Штрих рисования
# ============================================================================

class Stroke:
    def __init__(self, color, width):
        self.points = []
        self.color = color
        self.width = width
        self.ox = 0
        self.oy = 0
    
    def add(self, x, y):
        self.points.append((x, y))
    
    def apply_offset(self):
        self.points = [(p[0] + self.ox, p[1] + self.oy) for p in self.points]
        self.ox = 0
        self.oy = 0


# ============================================================================
# HAND STATE - Состояние каждой руки
# ============================================================================

class HandState:
    def __init__(self):
        self.reset()
    
    def reset(self):
        self.drawing = False
        self.grabbing = False
        self.stroke = None
        self.grabbed = []
        self.last_pos = None
        self.smooth_x = 0
        self.smooth_y = 0
        self.last_gesture = 'none'


# ============================================================================
# DRAWING ENGINE - Движок рисования
# ============================================================================

class DrawingEngine:
    COLORS = [
        (1, 0.27, 0.34, 1),    # Красный
        (0.18, 0.84, 0.45, 1), # Зелёный
        (0.12, 0.56, 1, 1),    # Синий
        (1, 0.65, 0.01, 1),    # Оранжевый
        (1, 1, 1, 1),          # Белый
        (0.65, 0.37, 0.92, 1), # Фиолетовый
    ]
    
    THICKNESSES = [3, 6, 10, 16]
    
    def __init__(self):
        self.strokes = []
        self.hands = [HandState(), HandState()]
        self.color_idx = 0
        self.color = self.COLORS[0]
        self.thick_idx = 0
        self.thickness = 4
        self.SMOOTH = 0.35
        self.GRAB_R = 60
    
    def set_color(self, idx):
        if 0 <= idx < len(self.COLORS):
            self.color_idx = idx
            self.color = self.COLORS[idx]
    
    def next_thickness(self):
        self.thick_idx = (self.thick_idx + 1) % len(self.THICKNESSES)
        self.thickness = self.THICKNESSES[self.thick_idx]
    
    def clear(self):
        self.strokes = []
        for h in self.hands:
            h.reset()
    
    def undo(self):
        if self.strokes:
            self.strokes.pop()
    
    def smooth(self, state, x, y):
        state.smooth_x = state.smooth_x * self.SMOOTH + x * (1 - self.SMOOTH)
        state.smooth_y = state.smooth_y * self.SMOOTH + y * (1 - self.SMOOTH)
        return state.smooth_x, state.smooth_y
    
    def find_near(self, x, y):
        found = []
        r2 = self.GRAB_R ** 2
        for i, s in enumerate(self.strokes):
            for px, py in s.points:
                dx, dy = (px + s.ox) - x, (py + s.oy) - y
                if dx*dx + dy*dy < r2:
                    found.append(i)
                    break
        return found
    
    def process(self, gesture, x, y, hand_idx=0, detected=True):
        state = self.hands[hand_idx]
        
        if not detected:
            self._change(state, state.last_gesture, 'none')
            state.last_gesture = 'none'
            return None
        
        sx, sy = self.smooth(state, x, y)
        
        if gesture != state.last_gesture:
            self._change(state, state.last_gesture, gesture)
            state.last_gesture = gesture
        
        if gesture == 'point':
            if not state.drawing:
                state.drawing = True
                state.stroke = Stroke(self.color, self.thickness)
            if state.stroke:
                state.stroke.add(sx, sy)
        
        elif gesture in ('pinch', 'grab'):
            if not state.grabbing:
                state.grabbed = self.find_near(sx, sy)
                if state.grabbed:
                    state.grabbing = True
                    state.last_pos = (sx, sy)
            elif state.last_pos:
                dx = sx - state.last_pos[0]
                dy = sy - state.last_pos[1]
                for i in state.grabbed:
                    if i < len(self.strokes):
                        self.strokes[i].ox += dx
                        self.strokes[i].oy += dy
                state.last_pos = (sx, sy)
        
        return sx, sy
    
    def _change(self, state, from_g, to_g):
        if from_g == 'point' and state.drawing:
            if state.stroke and len(state.stroke.points) >= 2:
                self.strokes.append(state.stroke)
            state.stroke = None
            state.drawing = False
        
        if from_g in ('pinch', 'grab') and state.grabbing:
            for i in state.grabbed:
                if i < len(self.strokes):
                    self.strokes[i].apply_offset()
            state.grabbed = []
            state.grabbing = False
            state.last_pos = None


# ============================================================================
# MAIN WIDGET - Главный виджет с камерой и рисованием
# ============================================================================

class ARDrawingWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.detector = HandDetector(max_hands=2)
        self.gesture_rec = GestureRecognizer(max_hands=2)
        self.engine = DrawingEngine()
        
        # Камера
        self.cap = None
        self.frame = None
        self.texture = None
        self.camera_ready = False
        
        # FPS
        self.fps = 0
        self.frame_count = 0
        self.last_fps_time = time.time()
        
        # Размеры
        self.cam_w = 640
        self.cam_h = 480
        
        self.init_camera()
        Clock.schedule_interval(self.update, 1.0 / 30.0)
    
    def init_camera(self):
        """Инициализация камеры"""
        if ANDROID:
            request_permissions([Permission.CAMERA])
            Clock.schedule_once(self._init_android_camera, 2)
        elif CV2_AVAILABLE:
            self._init_cv2_camera()
    
    def _init_cv2_camera(self):
        """OpenCV камера для десктопа"""
        self.cap = cv2.VideoCapture(0)
        if self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.cam_w)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.cam_h)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.cam_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.cam_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.camera_ready = True
    
    def _init_android_camera(self, dt):
        """Android камера через Camera2 API"""
        if ANDROID:
            try:
                activity = PythonActivity.mActivity
                self.camera_manager = activity.getSystemService(Context.CAMERA_SERVICE)
                
                camera_list = self.camera_manager.getCameraIdList()
                front_id = None
                
                for cam_id in camera_list:
                    chars = self.camera_manager.getCameraCharacteristics(cam_id)
                    facing = chars.get(CameraCharacteristics.LENS_FACING)
                    if facing == CameraCharacteristics.LENS_FACING_FRONT:
                        front_id = cam_id
                        break
                
                if front_id is None and len(camera_list) > 0:
                    front_id = camera_list[0]
                
                if front_id:
                    self.image_reader = ImageReader.newInstance(
                        self.cam_w, self.cam_h,
                        ImageFormat.YUV_420_888, 2
                    )
                    self.camera_ready = True
            except Exception as e:
                print(f"Camera init error: {e}")
                self.camera_ready = False
    
    def read_frame(self):
        """Читает кадр с камеры"""
        if not CV2_AVAILABLE:
            return None
        
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                return cv2.flip(frame, 1)
        
        return None
    
    def update(self, dt):
        """Главный цикл обновления"""
        # Читаем кадр
        frame = self.read_frame()
        
        # Обнаруживаем руки
        hands = self.detector.process_frame(frame) if frame is not None else []
        hand_count = len(hands)
        
        # Обрабатываем каждую руку
        gestures = []
        cursor_data = []
        
        for i in range(2):
            if i < hand_count:
                lm = hands[i]
                gesture = self.gesture_rec.recognize(lm, i)
                gestures.append(gesture)
                
                # Позиция курсора
                if gesture == 'pinch':
                    # Середина между большим и указательным
                    cx = ((1 - lm[4]['x']) + (1 - lm[8]['x'])) / 2 * self.width
                    cy = (1 - (lm[4]['y'] + lm[8]['y']) / 2) * self.height
                else:
                    cx = (1 - lm[8]['x']) * self.width
                    cy = (1 - lm[8]['y']) * self.height
                
                pos = self.engine.process(gesture, cx, cy, i, True)
                
                if pos:
                    cursor_data.append({
                        'x': pos[0], 'y': pos[1],
                        'gesture': gesture, 'hand': i
                    })
            else:
                gestures.append('none')
                self.gesture_rec.recognize(None, i)
                self.engine.process('none', 0, 0, i, False)
        
        # FPS
        self.frame_count += 1
        now = time.time()
        if now - self.last_fps_time >= 1.0:
            self.fps = self.frame_count
            self.frame_count = 0
            self.last_fps_time = now
        
        # Рендерим
        self.render(frame, hands, gestures, cursor_data)
    
    def render(self, frame, hands, gestures, cursors):
        """Отрисовка всего"""
        self.canvas.clear()
        
        with self.canvas:
            # Фон (чёрный или камера)
            if frame is not None and CV2_AVAILABLE:
                self.draw_camera(frame)
            else:
                Color(0.04, 0.04, 0.06, 1)
                Rectangle(pos=self.pos, size=self.size)
            
            # Штрихи
            self.draw_strokes()
            
            # Скелет рук
            for i, hand_lm in enumerate(hands):
                self.draw_skeleton(hand_lm, i)
            
            # Курсоры
            for c in cursors:
                self.draw_cursor(c)
            
            # Подсветка захвата
            for i in range(2):
                self.draw_grab_highlight(i)
    
    def draw_camera(self, frame):
        """Отрисовка камеры"""
        # Затемняем камеру для лучшей видимости рисунка
        frame = (frame * 0.4).astype('uint8')
        
        buf = cv2.flip(frame, 0)
        buf = buf.tobytes()
        
        h, w = frame.shape[:2]
        
        if self.texture is None or self.texture.size != (w, h):
            self.texture = Texture.create(size=(w, h), colorfmt='bgr')
            self.texture.flip_vertical = False
        
        self.texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
        
        Color(1, 1, 1, 1)
        
        # Масштабирование без растяжения
        tex_ratio = w / h
        scr_ratio = self.width / self.height
        
        if scr_ratio > tex_ratio:
            draw_h = self.height
            draw_w = draw_h * tex_ratio
        else:
            draw_w = self.width
            draw_h = draw_w / tex_ratio
        
        draw_x = (self.width - draw_w) / 2
        draw_y = (self.height - draw_h) / 2
        
        Rectangle(texture=self.texture, pos=(draw_x, draw_y), size=(draw_w, draw_h))
    
    def draw_strokes(self):
        """Отрисовка штрихов"""
        all_strokes = self.engine.strokes[:]
        for h in self.engine.hands:
            if h.stroke and len(h.stroke.points) >= 2:
                all_strokes.append(h.stroke)
        
        for s in all_strokes:
            if len(s.points) < 2:
                continue
            
            # Свечение
            Color(s.color[0], s.color[1], s.color[2], 0.3)
            glow_pts = []
            for p in s.points:
                glow_pts.extend([p[0] + s.ox, p[1] + s.oy])
            Line(points=glow_pts, width=s.width + 6, cap='round', joint='round')
            
            # Основная линия
            Color(*s.color)
            pts = []
            for p in s.points:
                pts.extend([p[0] + s.ox, p[1] + s.oy])
            Line(points=pts, width=s.width, cap='round', joint='round')
    
    def draw_skeleton(self, landmarks, hand_idx):
        """Отрисовка скелета руки"""
        if not landmarks or len(landmarks) < 21:
            return
        
        colors = [
            (0, 1, 0.8, 0.6),   # Бирюзовый для руки 0
            (1, 0.8, 0, 0.6)    # Жёлтый для руки 1
        ]
        dot_colors = [
            (0, 1, 0.8, 1),
            (1, 0.8, 0, 1)
        ]
        
        lc = colors[hand_idx % 2]
        dc = dot_colors[hand_idx % 2]
        
        # Линии
        Color(*lc)
        for a, b in HandDetector.CONNECTIONS:
            x1 = (1 - landmarks[a]['x']) * self.width
            y1 = (1 - landmarks[a]['y']) * self.height
            x2 = (1 - landmarks[b]['x']) * self.width
            y2 = (1 - landmarks[b]['y']) * self.height
            Line(points=[x1, y1, x2, y2], width=1.5)
        
        # Точки
        for i, lm in enumerate(landmarks):
            x = (1 - lm['x']) * self.width
            y = (1 - lm['y']) * self.height
            
            is_tip = i in HandDetector.TIPS
            radius = 8 if is_tip else 4
            
            if is_tip:
                # Свечение для кончиков
                Color(dc[0], dc[1], dc[2], 0.3)
                Ellipse(pos=(x - radius*2, y - radius*2), size=(radius*4, radius*4))
            
            Color(*dc)
            Ellipse(pos=(x - radius, y - radius), size=(radius*2, radius*2))
    
    def draw_cursor(self, cursor):
        """Отрисовка курсора"""
        x, y = cursor['x'], cursor['y']
        gesture = cursor['gesture']
        
        gc = self.gesture_rec.get_color(gesture)
        
        if gesture == 'point':
            size = self.engine.thickness * 2 + 12
            # Внешний круг
            Color(gc[0], gc[1], gc[2], 0.3)
            Ellipse(pos=(x-size, y-size), size=(size*2, size*2))
            # Основной
            Color(*gc)
            Line(circle=(x, y, size), width=2)
            Ellipse(pos=(x-3, y-3), size=(6, 6))
        
        elif gesture in ('pinch', 'grab'):
            size = 25
            Color(1, 0.84, 0, 0.2)
            Ellipse(pos=(x-size, y-size), size=(size*2, size*2))
            Color(1, 0.84, 0, 1)
            Line(circle=(x, y, size), width=2)
            Ellipse(pos=(x-4, y-4), size=(8, 8))
        
        else:
            Color(0.7, 0.7, 0.7, 0.4)
            Line(circle=(x, y, 15), width=1)
    
    def draw_grab_highlight(self, hand_idx):
        """Подсветка захваченных штрихов"""
        state = self.engine.hands[hand_idx]
        if not state.grabbing or not state.grabbed:
            return
        
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        
        for idx in state.grabbed:
            if idx >= len(self.engine.strokes):
                continue
            s = self.engine.strokes[idx]
            for px, py in s.points:
                ax, ay = px + s.ox, py + s.oy
                min_x = min(min_x, ax)
                min_y = min(min_y, ay)
                max_x = max(max_x, ax)
                max_y = max(max_y, ay)
        
        if min_x != float('inf'):
            pad = 15
            Color(1, 0.84, 0, 0.4)
            Line(
                rectangle=(min_x-pad, min_y-pad, max_x-min_x+pad*2, max_y-min_y+pad*2),
                width=2, dash_offset=4, dash_length=8
            )
    
    def cleanup(self):
        if self.cap:
            self.cap.release()
        self.detector.close()


# ============================================================================
# MAIN APP - Главное приложение
# ============================================================================

class ARHandDrawingApp(App):
    def build(self):
        Window.clearcolor = (0.04, 0.04, 0.06, 1)
        
        if ANDROID:
            request_permissions([Permission.CAMERA])
        
        root = FloatLayout()
        
        # Главный виджет рисования
        self.drawing = ARDrawingWidget()
        root.add_widget(self.drawing)
        
        # Верхняя панель
        top_bar = BoxLayout(
            size_hint=(0.9, 0.06),
            pos_hint={'center_x': 0.5, 'top': 0.98},
            spacing=5
        )
        
        # Статус
        self.status_label = Label(
            text='🔴 Ожидание камеры...',
            size_hint_x=0.4,
            color=(1, 1, 1, 0.9),
            font_size='13sp',
            halign='left'
        )
        top_bar.add_widget(self.status_label)
        
        # FPS
        self.fps_label = Label(
            text='0 fps',
            size_hint_x=0.15,
            color=(0.6, 0.6, 0.6, 0.8),
            font_size='12sp'
        )
        top_bar.add_widget(self.fps_label)
        
        root.add_widget(top_bar)
        
        # Подсказка
        hint = Label(
            text='☝️ Указательный=Рисовать | 👌 Щипок=Перетащить | ✋ Ладонь=Пауза',
            size_hint=(0.95, 0.04),
            pos_hint={'center_x': 0.5, 'y': 0.11},
            color=(0.7, 0.7, 0.7, 0.6),
            font_size='10sp'
        )
        root.add_widget(hint)
        
        # Нижняя панель
        bottom_bar = BoxLayout(
            size_hint=(0.95, 0.08),
            pos_hint={'center_x': 0.5, 'y': 0.01},
            spacing=4,
            padding=4
        )
        
        # Кнопки цветов
        colors_rgba = [
            (1, 0.27, 0.34, 1),
            (0.18, 0.84, 0.45, 1),
            (0.12, 0.56, 1, 1),
            (1, 0.65, 0.01, 1),
            (1, 1, 1, 1),
            (0.65, 0.37, 0.92, 1)
        ]
        
        for i, (r, g, b, a) in enumerate(colors_rgba):
            btn = Button(
                background_color=(r, g, b, 1),
                background_normal='',
                size_hint_x=0.1
            )
            btn.bind(on_press=lambda x, idx=i: self.set_color(idx))
            bottom_bar.add_widget(btn)
        
        # Разделитель
        spacer = Widget(size_hint_x=0.05)
        bottom_bar.add_widget(spacer)
        
        # Кнопки действий
        clear_btn = Button(
            text='🗑️',
            font_size='20sp',
            size_hint_x=0.12,
            background_color=(0.3, 0.3, 0.35, 0.8),
            background_normal=''
        )
        clear_btn.bind(on_press=lambda x: self.drawing.engine.clear())
        bottom_bar.add_widget(clear_btn)
        
        undo_btn = Button(
            text='↩️',
            font_size='20sp',
            size_hint_x=0.12,
            background_color=(0.3, 0.3, 0.35, 0.8),
            background_normal=''
        )
        undo_btn.bind(on_press=lambda x: self.drawing.engine.undo())
        bottom_bar.add_widget(undo_btn)
        
        thick_btn = Button(
            text='🖊️',
            font_size='20sp',
            size_hint_x=0.12,
            background_color=(0.3, 0.3, 0.35, 0.8),
            background_normal=''
        )
        thick_btn.bind(on_press=lambda x: self.drawing.engine.next_thickness())
        bottom_bar.add_widget(thick_btn)
        
        root.add_widget(bottom_bar)
        
        # Обновление UI
        Clock.schedule_interval(self.update_ui, 0.5)
        
        return root
    
    def set_color(self, idx):
        self.drawing.engine.set_color(idx)
    
    def update_ui(self, dt):
        # FPS
        self.fps_label.text = f'{self.drawing.fps} fps'
        
        # Статус
        hand_count = self.drawing.detector.get_hand_count()
        
        if hand_count >= 2:
            self.status_label.text = '🟢🟢 Две руки'
            self.status_label.color = (0.2, 1, 0.5, 1)
        elif hand_count == 1:
            self.status_label.text = '🟢 Одна рука'
            self.status_label.color = (0.2, 1, 0.5, 1)
        elif self.drawing.camera_ready:
            self.status_label.text = '🟡 Покажите руку'
            self.status_label.color = (1, 0.8, 0.2, 1)
        else:
            self.status_label.text = '🔴 Нет камеры'
            self.status_label.color = (1, 0.3, 0.3, 1)
    
    def on_stop(self):
        self.drawing.cleanup()


# ============================================================================
# ЗАПУСК
# ============================================================================

if __name__ == '__main__':
    ARHandDrawingApp().run()
