from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import Color, Ellipse, Rectangle, Line
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.properties import NumericProperty
import math
import random

# Настройки экрана и игры
WINDOW_WIDTH, WINDOW_HEIGHT = 800, 600
MAP_WIDTH, MAP_HEIGHT = 2000, 2000
PLAYER_SPEED = 250
BULLET_SPEED = 800
FIRE_RATE = 0.15

class Joystick(Widget):
    def __init__(self, pos_center, **kwargs):
        super().__init__(**kwargs)
        self.center_pos = pos_center
        self.radius = 60
        self.knob_radius = 25
        self.knob_pos = list(pos_center)
        self.active = False
        self.touch_id = None
        self.direction = (0, 0)
        
        with self.canvas:
            Color(1, 1, 1, 0.2)
            self.bg = Ellipse(pos=(self.center_pos[0] - self.radius, self.center_pos[1] - self.radius), 
                              size=(self.radius*2, self.radius*2))
            Color(1, 1, 1, 0.5)
            self.knob = Ellipse(pos=(self.knob_pos[0] - self.knob_radius, self.knob_pos[1] - self.knob_radius), 
                                size=(self.knob_radius*2, self.knob_radius*2))
    
    def on_touch_down(self, touch):
        if not self.active and math.dist(touch.pos, self.center_pos) < self.radius * 1.5:
            self.active = True
            self.touch_id = touch.uid
            self._update_knob(touch.pos)
            return True
        return False

    def on_touch_move(self, touch):
        if self.active and touch.uid == self.touch_id:
            self._update_knob(touch.pos)
            return True
        return False

    def on_touch_up(self, touch):
        if self.active and touch.uid == self.touch_id:
            self.active = False
            self.touch_id = None
            self.knob_pos = list(self.center_pos)
            self.knob.pos = (self.center_pos[0] - self.knob_radius, self.center_pos[1] - self.knob_radius)
            self.direction = (0, 0)
            return True
        return False

    def _update_knob(self, touch_pos):
        dx = touch_pos[0] - self.center_pos[0]
        dy = touch_pos[1] - self.center_pos[1]
        dist = math.dist(touch_pos, self.center_pos)
        
        if dist > self.radius:
            dx = (dx / dist) * self.radius
            dy = (dy / dist) * self.radius
        
        self.knob_pos = [self.center_pos[0] + dx, self.center_pos[1] + dy]
        self.knob.pos = (self.knob_pos[0] - self.knob_radius, self.knob_pos[1] - self.knob_radius)
        
        # Нормализованный вектор направления (-1 до 1)
        self.direction = (dx / self.radius, dy / self.radius)

class Bullet(Widget):
    def __init__(self, pos, direction, **kwargs):
        super().__init__(**kwargs)
        self.size = (8, 8)
        self.pos = pos
        self.direction = direction
        with self.canvas:
            Color(1, 1, 0, 1)
            self.rect = Rectangle(pos=self.pos, size=self.size)
    
    def update(self, dt, obstacles):
        self.x += self.direction[0] * BULLET_SPEED * dt
        self.y += self.direction[1] * BULLET_SPEED * dt
        self.rect.pos = self.pos
        
        # Проверка выхода за карту
        if self.x < 0 or self.x > MAP_WIDTH or self.y < 0 or self.y > MAP_HEIGHT:
            return False
            
        # Проверка столкновения со стенами
        for obs in obstacles:
            if obs.collide_point(self.center_x, self.center_y):
                return False
        return True

class Enemy(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size = (40, 40)
        self.hp = 100
        with self.canvas:
            Color(1, 0, 0, 1) # Красный враг
            self.body = Ellipse(pos=self.pos, size=self.size)
            Color(0, 0, 0, 1)
            self.eye = Line(circle=(self.center_x, self.center_y, 5))

    def update(self, dt, player_pos):
        # Простейший ИИ: идти к игроку
        dx = player_pos[0] - self.center_x
        dy = player_pos[1] - self.center_y
        dist = math.hypot(dx, dy)
        if dist > 10:
            self.x += (dx / dist) * 100 * dt
            self.y += (dy / dist) * 100 * dt
        self.body.pos = self.pos
        self.eye.circle = (self.center_x, self.center_y, 5)

class GameWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.player_pos = [MAP_WIDTH/2, MAP_HEIGHT/2]
        self.player_angle = 0
        self.bullets = []
        self.enemies = []
        self.obstacles = []
        self.score = 0
        
        # Создаем стены (препятствия)
        self._generate_map()
        
        # Создаем джойстики
        self.move_joy = Joystick((120, 120))
        self.aim_joy = Joystick((Window.width - 120, 120))
        
        # Таймер стрельбы
        self.shoot_timer = 0
        
        # Спавн врагов
        for _ in range(5):
            self._spawn_enemy()
            
        Clock.schedule_interval(self.update, 1/60)

    def _generate_map(self):
        # Рандомные стены
        for i in range(15):
            w, h = random.randint(100, 300), random.randint(100, 300)
            x, y = random.randint(0, MAP_WIDTH - w), random.randint(0, MAP_HEIGHT - h)
            # Не спавним стены прямо на игроке
            if math.dist((x + w/2, y + h/2), self.player_pos) > 300:
                wall = Widget(size=(w, h), pos=(x, y))
                with wall.canvas:
                    Color(0.3, 0.3, 0.3, 1)
                    Rectangle(pos=wall.pos, size=wall.size)
                    Color(0.5, 0.5, 0.5, 1)
                    Line(rectangle=(wall.x, wall.y, wall.width, wall.height), width=2)
                self.obstacles.append(wall)

    def _spawn_enemy(self):
        # Спавн врага подальше от игрока
        while True:
            x = random.randint(100, MAP_WIDTH - 100)
            y = random.randint(100, MAP_HEIGHT - 100)
            if math.dist((x, y), self.player_pos) > 400:
                enemy = Enemy(pos=(x, y))
                self.enemies.append(enemy)
                break

    def update(self, dt):
        # 1. Движение игрока
        dx = self.move_joy.direction[0] * PLAYER_SPEED * dt
        dy = self.move_joy.direction[1] * PLAYER_SPEED * dt
        
        new_x = self.player_pos[0] + dx
        new_y = self.player_pos[1] + dy
        
        # Простая коллизия со стенами для игрока
        player_rect = (new_x - 20, new_y - 20, 40, 40)
        collision = False
        for obs in self.obstacles:
            if self._rect_intersect(player_rect, (obs.x, obs.y, obs.width, obs.height)):
                collision = True
                break
                
        if not collision:
            self.player_pos[0] = max(0, min(new_x, MAP_WIDTH))
            self.player_pos[1] = max(0, min(new_y, MAP_HEIGHT))

        # 2. Прицеливание и стрельба
        aim_x, aim_y = self.aim_joy.direction
        if aim_x != 0 or aim_y != 0:
            self.player_angle = math.atan2(aim_y, aim_x)
            
            # Стрельба
            self.shoot_timer -= dt
            if self.shoot_timer <= 0:
                self.shoot_timer = FIRE_RATE
                bullet = Bullet(
                    pos=(self.player_pos[0], self.player_pos[1]),
                    direction=(math.cos(self.player_angle), math.sin(self.player_angle))
                )
                self.bullets.append(bullet)

        # 3. Обновление пуль
        for b in self.bullets[:]:
            if not b.update(dt, self.obstacles):
                self.bullets.remove(b)
                continue
                
            # Проверка попадания во врагов
            for e in self.enemies[:]:
                if math.dist(b.center, e.center) < e.width / 2:
                    e.hp -= 25
                    if e.hp <= 0:
                        self.enemies.remove(e)
                        self.score += 100
                    self.bullets.remove(b)
                    break

        # 4. Обновление врагов
        for e in self.enemies:
            e.update(dt, self.player_pos)

        # 5. Отрисовка камеры (сдвиг всего мира)
        # Центрируем камеру на игроке
        cam_x = Window.width / 2 - self.player_pos[0]
        cam_y = Window.height / 2 - self.player_pos[1]
        
        self.canvas.clear()
        with self.canvas:
            # Фон (трава)
            Color(0.2, 0.4, 0.2, 1)
            Rectangle(pos=(cam_x, cam_y), size=(MAP_WIDTH, MAP_HEIGHT))
            
            # Стены
            for obs in self.obstacles:
                Color(0.3, 0.3, 0.3, 1)
                Rectangle(pos=(obs.x + cam_x, obs.y + cam_y), size=obs.size)
                Color(0.5, 0.5, 0.5, 1)
                Line(rectangle=(obs.x + cam_x, obs.y + cam_y, obs.width, obs.height), width=2)
            
            # Враги
            for e in self.enemies:
                Color(1, 0.2, 0.2, 1)
                Ellipse(pos=(e.x + cam_x, e.y + cam_y), size=e.size)
                Color(0, 0, 0, 1)
                Line(circle=(e.center_x + cam_x, e.center_y + cam_y, 5))

            # Игрок
            Color(0.2, 0.8, 1, 1)
            Ellipse(pos=(self.player_pos[0] + cam_x - 20, self.player_pos[1] + cam_y - 20), size=(40, 40))
            
            # Ствол игрока
            gun_end_x = self.player_pos[0] + cam_x + math.cos(self.player_angle) * 35
            gun_end_y = self.player_pos[1] + cam_y + math.sin(self.player_angle) * 35
            Color(0, 0, 0, 1)
            Line(points=[self.player_pos[0] + cam_x, self.player_pos[1] + cam_y, gun_end_x, gun_end_y], width=4)

            # Пули
            Color(1, 1, 0, 1)
            for b in self.bullets:
                Ellipse(pos=(b.x + cam_x, b.y + cam_y), size=b.size)

            # Прицел
            if self.aim_joy.direction != (0, 0):
                cross_x = self.player_pos[0] + cam_x + math.cos(self.player_angle) * 150
                cross_y = self.player_pos[1] + cam_y + math.sin(self.player_angle) * 150
                Color(1, 0, 0, 1)
                Line(points=[cross_x - 10, cross_y, cross_x + 10, cross_y], width=2)
                Line(points=[cross_x, cross_y - 10, cross_x, cross_y + 10], width=2)

    def _rect_intersect(self, r1, r2):
        return (r1[0] < r2[0] + r2[2] and r1[0] + r1[2] > r2[0] and
                r1[1] < r2[1] + r2[3] and r1[1] + r1[3] > r2[1])

    def on_touch_down(self, touch):
        if self.move_joy.on_touch_down(touch): return True
        if self.aim_joy.on_touch_down(touch): return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self.move_joy.on_touch_move(touch): return True
        if self.aim_joy.on_touch_move(touch): return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if self.move_joy.on_touch_up(touch): return True
        if self.aim_joy.on_touch_up(touch): return True
        return super().on_touch_up(touch)

class Strike2DApp(App):
    def build(self):
        Window.clearcolor = (0, 0, 0, 1)
        self.game = GameWidget()
        # Добавляем джойстики поверх игрового поля
        self.game.add_widget(self.game.move_joy)
        self.game.add_widget(self.game.aim_joy)
        
        # Добавляем счет
        self.score_label = Label(text="Счет: 0", pos=(20, Window.height - 50), font_size='24sp')
        self.game.add_widget(self.score_label)
        
        Clock.schedule_interval(self.update_score, 1/10)
        return self.game

    def update_score(self, dt):
        self.score_label.text = f"Счет: {self.game.score}"

if __name__ == "__main__":
    Strike2DApp().run()
