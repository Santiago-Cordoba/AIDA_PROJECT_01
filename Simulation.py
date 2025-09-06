import pygame, sys
import numpy as np
import matplotlib

matplotlib.use("Agg")  # Backend sin ventana
import matplotlib.pyplot as plt
from io import BytesIO

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BLUE = (0, 0, 255)
GREEN = (50, 150, 50)
PURPLE = (130, 0, 130)
GREY = (230, 230, 230)
HORRYBLE_YELLOW = (190, 175, 50)
VACCINE_COLOR = (200, 200, 255)
VACCINE_CENTER_COLOR = (255, 255, 255)
ORANGE = (255, 165, 0)
LIGHT_BLUE = (173, 216, 230)
DARK_GREY = (64, 64, 64)

BACKGROUND = WHITE


class Dot(pygame.sprite.Sprite):
    def __init__(self,
                 x,
                 y,
                 width,
                 height,
                 color=BLACK,
                 radius=5,
                 velocity=[0, 0],
                 randomize=False,
                 age=None,
                 health_status=None
                 ):

        super().__init__()
        self.radius = radius
        self.image = pygame.Surface([radius * 2, radius * 2], pygame.SRCALPHA)
        self.image.fill(BACKGROUND)
        pygame.draw.circle(self.image, color, (radius, radius), radius)

        self.rect = self.image.get_rect()
        self.pos = np.array([x, y], dtype=np.float64)
        self.vel = np.asarray(velocity, dtype=np.float64)

        self.killswitch_on = False
        self.recovered = False
        self.randomize = randomize
        self.contagious = False
        self.incubation_counter = 0
        self.vaccinated = False

        self.WIDTH = width
        self.HEIGHT = height

        self.age = age if age is not None else np.random.randint(1, 100)
        self.health_status = health_status if health_status is not None else "susceptible"
        self.location = (x, y)

    def update(self):
        self.pos += self.vel
        x, y = self.pos
        self.location = (x, y)

        # Rebotes en los bordes
        if x < 0:
            self.pos[0] = self.WIDTH
            x = self.WIDTH
        if x > self.WIDTH:
            self.pos[0] = 0
            x = 0
        if y < 0:
            self.pos[1] = self.HEIGHT
            y = self.HEIGHT
        if y > self.HEIGHT:
            self.pos[1] = 0
            y = 0

        self.rect.x = x
        self.rect.y = y

        # Control de velocidad
        vel_norm = np.linalg.norm(self.vel)
        if vel_norm > 3:
            self.vel /= vel_norm

        if self.randomize:
            self.vel += np.random.rand(2) * 2 - 1
        self.check_vaccination()

        # Período de incubación
        if self.health_status == "infected" and not self.contagious:
            self.incubation_counter += 1
            if self.incubation_counter >= self.simulation.incubation_period:
                self.contagious = True

        # Progresión de la enfermedad
        if self.killswitch_on:
            self.cycles_to_fate -= 1
            if self.cycles_to_fate <= 0:
                self.killswitch_on = False
                some_number = np.random.rand()
                age_mortality_rate = self.calculate_age_mortality()
                if age_mortality_rate > some_number:
                    self.health_status = "dead"
                    self.kill()
                else:
                    self.recovered = True
                    self.health_status = "recovered"
                    self.contagious = False

        self.update_appearance()

    def check_vaccination(self):
        if (self.health_status == "susceptible" and
                not self.vaccinated and
                hasattr(self.simulation, 'vaccine_center') and
                self.simulation.vaccine_center.collidepoint(self.pos)):

            if np.random.rand() < self.simulation.vaccination_rate:
                self.health_status = "vaccinated"
                self.vaccinated = True
                if hasattr(self.simulation, 'vaccinated_container'):
                    self.simulation.susceptible_container.remove(self)
                    self.simulation.vaccinated_container.add(self)

    def update_appearance(self):
        self.image = pygame.Surface([self.radius * 2, self.radius * 2], pygame.SRCALPHA)
        self.image.fill(BACKGROUND)

        if self.health_status == "susceptible":
            pygame.draw.circle(self.image, BLUE, (self.radius, self.radius), self.radius)

        elif self.health_status == "infected":
            pygame.draw.circle(self.image, GREEN, (self.radius, self.radius), self.radius)
            if self.contagious:
                pygame.draw.circle(self.image, (255, 0, 0), (self.radius, self.radius), 2)

        elif self.health_status == "recovered":
            pygame.draw.circle(self.image, PURPLE, (self.radius, self.radius), self.radius)

        elif self.health_status == "vaccinated":
            pygame.draw.circle(self.image, VACCINE_COLOR, (self.radius, self.radius), self.radius)
            pygame.draw.line(self.image, WHITE, (2, 2), (self.radius * 2 - 2, self.radius * 2 - 2), 1)
            pygame.draw.line(self.image, WHITE, (self.radius * 2 - 2, 2), (2, self.radius * 2 - 2), 1)

    def respawn(self, color, radius=5):
        new_guy = Dot(
            self.rect.x,
            self.rect.y,
            self.WIDTH,
            self.HEIGHT,
            color=color,
            velocity=self.vel,
            age=self.age,
            health_status=self.health_status
        )
        new_guy.location = self.location
        new_guy.simulation = self.simulation
        new_guy.vaccinated = self.vaccinated
        return new_guy

    def killswitch(self, cycles_to_fate, mortality_rate):
        self.killswitch_on = True
        self.cycles_to_fate = cycles_to_fate
        self.mortality_rate = mortality_rate
        self.health_status = "infected"
        self.contagious = False
        self.incubation_counter = 0

    def calculate_age_mortality(self):
        age_mortality_rates = {
            (0, 9): 0.001,
            (10, 19): 0.002,
            (20, 29): 0.01,
            (30, 39): 0.02,
            (40, 49): 0.05,
            (50, 59): 0.1,
            (60, 69): 0.2,
            (70, 79): 0.3,
            (80, 100): 0.5
        }

        for age_range, mortality_rate in age_mortality_rates.items():
            if age_range[0] <= self.age <= age_range[1]:
                return mortality_rate
        return self.mortality_rate


class Simulation:
    def __init__(self, width=600, height=480):
        self.WIDTH = width
        self.HEIGHT = height
        self.cycles_per_day = 30
        self.current_day = 0

        self.susceptible_container = pygame.sprite.Group()
        self.infected_container = pygame.sprite.Group()
        self.recovered_container = pygame.sprite.Group()
        self.vaccinated_container = pygame.sprite.Group()
        self.all_container = pygame.sprite.Group()

        # Parámetros de población
        self.n_susceptible = 45
        self.n_infected = 5
        self.n_quarantined = 0
        self.n_vaccinated = 0

        # Parámetros de enfermedad
        self.T = 1000
        self.max_days = 100  # Duración máxima en días
        self.transmission_rate = 0.7
        self.incubation_period = 50
        self.recovery_period_min = 150
        self.recovery_period_max = 250
        self.mortality_rate = 0.3

        # Centro de vacunación
        self.vaccine_center = pygame.Rect(20, self.HEIGHT - 120, 100, 100)
        self.vaccination_rate = 0.8

        self.history_infected = []
        self.history_recovered = []
        self.history_vaccinated = []
        self.history_dead = []
        self.history_susceptible = []

    def start(self, randomize=False):
        self.N = self.n_susceptible + self.n_infected + self.n_quarantined + self.n_vaccinated

        pygame.init()
        EXTRA_WIDTH = 450
        screen = pygame.display.set_mode((self.WIDTH + EXTRA_WIDTH, self.HEIGHT))
        pygame.display.set_caption("Disease Simulator")

        # Crear población susceptible
        for i in range(self.n_susceptible):
            x = np.random.randint(0, self.WIDTH + 1)
            y = np.random.randint(0, self.HEIGHT + 1)
            vel = (np.random.rand(2) * 2 - 1).tolist()
            age = np.random.randint(1, 100)
            guy = Dot(x, y, self.WIDTH, self.HEIGHT, color=BLUE, velocity=vel,
                      randomize=randomize, age=age, health_status="susceptible")
            guy.simulation = self
            guy.vaccinated = False
            self.susceptible_container.add(guy)
            self.all_container.add(guy)

        # Crear población en cuarentena
        for i in range(self.n_quarantined):
            x = np.random.randint(0, self.WIDTH + 1)
            y = np.random.randint(0, self.HEIGHT + 1)
            vel = [0, 0]
            age = np.random.randint(1, 100)
            guy = Dot(x, y, self.WIDTH, self.HEIGHT, color=BLUE, velocity=vel,
                      randomize=False, age=age, health_status="susceptible")
            guy.simulation = self
            guy.vaccinated = False
            self.susceptible_container.add(guy)
            self.all_container.add(guy)

        # Crear población vacunada inicial
        for i in range(self.n_vaccinated):
            x = np.random.randint(0, self.WIDTH + 1)
            y = np.random.randint(0, self.HEIGHT + 1)
            vel = (np.random.rand(2) * 2 - 1).tolist()
            age = np.random.randint(1, 100)
            guy = Dot(x, y, self.WIDTH, self.HEIGHT, color=VACCINE_COLOR, velocity=vel,
                      randomize=randomize, age=age, health_status="vaccinated")
            guy.simulation = self
            guy.vaccinated = True
            self.vaccinated_container.add(guy)
            self.all_container.add(guy)

        # Crear población infectada inicial
        for i in range(self.n_infected):
            x = np.random.randint(0, self.WIDTH + 1)
            y = np.random.randint(0, self.HEIGHT + 1)
            vel = (np.random.rand(2) * 2 - 1).tolist()
            age = np.random.randint(1, 100)
            guy = Dot(x, y, self.WIDTH, self.HEIGHT, color=GREEN, velocity=vel,
                      randomize=randomize, age=age, health_status="infected")
            guy.simulation = self
            guy.contagious = True
            guy.killswitch_on = True
            guy.cycles_to_fate = np.random.randint(self.recovery_period_min, self.recovery_period_max)
            guy.mortality_rate = guy.calculate_age_mortality()
            guy.vaccinated = False
            self.infected_container.add(guy)
            self.all_container.add(guy)

        stats_width = EXTRA_WIDTH - 40  # ancho con márgenes
        stats_height = (self.HEIGHT - 80) // 2  # alto con márgenes
        stats = pygame.Surface((stats_width, stats_height))
        stats.fill(WHITE)  # fondo del cuadro de la gráfica
        stats.set_alpha(230)

        # Posición: 20px desde el borde izquierdo del panel y 40px desde arriba
        stats_pos = (self.WIDTH + 20, 40)

        try:
            font = pygame.font.SysFont("Arial", 24)
        except:
            font = pygame.font.SysFont(None, 24)

        clock = pygame.time.Clock()
        running = True
        i = 0

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

            if i < self.T and self.current_day < self.max_days:

                self.all_container.update()
                screen.fill(BACKGROUND)

                pygame.draw.rect(screen, GREY, (self.WIDTH, 0, EXTRA_WIDTH, self.HEIGHT))

                # Dibujar centro de vacunación
                pygame.draw.rect(screen, VACCINE_CENTER_COLOR, self.vaccine_center, 2)
                pygame.draw.rect(screen, (200, 255, 200), self.vaccine_center.inflate(-4, -4))
                text = font.render("⚕", True, BLACK)
                screen.blit(text, (self.vaccine_center.centerx - 6, self.vaccine_center.centery - 12))

                # Incrementar el numero de dias
                if i % self.cycles_per_day == 0:
                    self.current_day += 1

                # Actualizar estadísticas
                stats_height = stats.get_height()
                stats_width = stats.get_width()
                n_inf_now = len(self.infected_container)
                n_pop_now = len(self.all_container)
                n_rec_now = len(self.recovered_container)
                n_vac_now = len(self.vaccinated_container)
                n_dead_now = self.N - n_pop_now
                n_sus_now = len(self.susceptible_container)
                # Verificar si no quedan infectados activos
                if n_inf_now == 0 and i > 0:
                    print(f"\n🎉 Simulación terminada - No quedan infectados activos")
                    print(f"📊 Estadísticas finales:")
                    print(f"   • Días transcurridos: {self.current_day}")
                    print(f"   • Recuperados: {n_rec_now}")
                    print(f"   • Vacunados: {n_vac_now}")
                    print(f"   • Fallecidos: {n_dead_now}")
                    print(f"   • Susceptibles restantes: {n_sus_now}")

                    # Mostrar mensaje en pantalla por unos segundos
                    end_font = pygame.font.SysFont("Arial", 32, bold=True)
                    end_text = end_font.render("¡Simulación Completada!", True, (0, 150, 0))
                    end_rect = end_text.get_rect(center=(self.WIDTH // 2, self.HEIGHT // 2))

                    # Fondo semi-transparente
                    overlay = pygame.Surface((self.WIDTH, self.HEIGHT))
                    overlay.set_alpha(180)
                    overlay.fill((255, 255, 255))
                    screen.blit(overlay, (0, 0))
                    screen.blit(end_text, end_rect)

                    # Mostrar estadísticas finales
                    stats_font = pygame.font.SysFont("Arial", 20)
                    final_stats = [
                        f"Duración: {self.current_day} días",
                        f"Recuperados: {n_rec_now}",
                        f"Fallecidos: {n_dead_now}",
                        f"Vacunados: {n_vac_now}"
                    ]

                    for j, stat in enumerate(final_stats):
                        stat_text = stats_font.render(stat, True, BLACK)
                        stat_rect = stat_text.get_rect(center=(self.WIDTH // 2, self.HEIGHT // 2 + 50 + j * 30))
                        screen.blit(stat_text, stat_rect)

                    pygame.display.flip()
                    pygame.time.wait(10000)  # Esperar 10 segundos
                    break

                # Guardar historial
                if i % self.cycles_per_day == 0:
                    self.history_infected.append(n_inf_now)
                    self.history_recovered.append(n_rec_now)
                    self.history_vaccinated.append(n_vac_now)
                    self.history_dead.append(n_dead_now)
                    self.history_susceptible.append(n_sus_now)

                # Dibujar gráfica con matplotlib
                dias = list(range(1, len(self.history_infected) + 1))
                plt.figure(figsize=(3, 2))
                plt.plot(self.history_infected, color="green", label="Infectados")
                plt.plot(self.history_recovered, color="purple", label="Recuperados")
                plt.plot(self.history_vaccinated, color="blue", label="Vacunados")
                plt.plot(self.history_dead, color="orange", label="Muertos")
                plt.plot(self.history_susceptible, color="red", label="Susceptibles")
                plt.xlabel("Días")
                plt.ylabel("Número de personas")
                plt.legend(fontsize=6)
                plt.tight_layout()

                buf = BytesIO()
                plt.savefig(buf, format="png")
                buf.seek(0)
                plt.close()

                graph_img = pygame.image.load(buf, "png")
                buf.close()

                # Ajustar tamaño al recuadro
                graph_img = pygame.transform.scale(graph_img, (stats_width, stats_height))

                # Detección de colisiones
                collision_group = pygame.sprite.groupcollide(
                    self.susceptible_container,
                    self.infected_container,
                    True,
                    False,
                )

                for guy in collision_group:
                    infectantes = [inf for inf in collision_group[guy] if inf.contagious]
                    if infectantes and np.random.rand() < self.transmission_rate:
                        new_guy = guy.respawn(GREEN)
                        new_guy.vel *= -1
                        recovery_time = np.random.randint(self.recovery_period_min, self.recovery_period_max)
                        new_guy.killswitch(recovery_time, new_guy.calculate_age_mortality())
                        self.infected_container.add(new_guy)
                        self.all_container.add(new_guy)
                    else:
                        self.susceptible_container.add(guy)
                        self.all_container.add(guy)

                # Recuperaciones
                recovered = []
                for guy in self.infected_container:
                    if guy.recovered:
                        new_guy = guy.respawn(PURPLE)
                        self.recovered_container.add(new_guy)
                        self.all_container.add(new_guy)
                        recovered.append(guy)
                if recovered:
                    self.infected_container.remove(*recovered)
                    self.all_container.remove(*recovered)

                self.all_container.draw(screen)
                screen.blit(graph_img, stats_pos)
                # Mostrar día actual
                day_text = font.render(f"Día {self.current_day}", True, BLACK)
                screen.blit(day_text, (self.WIDTH + 20, stats_pos[1] + stats_height + 10))

                # Tabla con estadísticas en tiempo real
                stats_y = stats_pos[1] + stats_height + 40
                line_spacing = 25

                labels = [
                    ("Infectados", n_inf_now, GREEN),
                    ("Recuperados", n_rec_now, PURPLE),
                    ("Vacunados", n_vac_now, BLUE),
                    ("Muertos", n_dead_now, ORANGE),
                    ("Susceptibles", n_sus_now, BLACK),
                ]

                for j, (label, value, color) in enumerate(labels):
                    text = font.render(f"{label}: {value}", True, color)
                    screen.blit(text, (self.WIDTH + 20, stats_y + j * line_spacing))
            i += 1
            pygame.display.flip()
            clock.tick(30)

        pygame.quit()


class InputBox:
    def __init__(self, x, y, w, h, text='', placeholder=''):
        self.rect = pygame.Rect(x, y, w, h)
        self.color_inactive = pygame.Color(200, 200, 200)
        self.color_active = pygame.Color(100, 150, 255)
        self.color_border = pygame.Color(150, 150, 150)
        self.color = self.color_inactive
        self.text = text
        self.placeholder = placeholder
        self.font = pygame.font.SysFont("Arial", 20)
        self.txt_surface = self.font.render(text, True, BLACK)
        self.active = False
        self.cursor_visible = True
        self.cursor_counter = 0

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.active = not self.active
            else:
                self.active = False
            self.color = self.color_active if self.active else self.color_inactive

        if event.type == pygame.KEYDOWN:
            if self.active:
                if event.key == pygame.K_RETURN:
                    return self.text
                elif event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                else:
                    if event.unicode.isdigit() and len(self.text) < 6:
                        self.text += event.unicode
                self.txt_surface = self.font.render(self.text, True, BLACK)

        return None

    def draw(self, screen):
        # Cursor parpadeante
        self.cursor_counter += 1
        if self.cursor_counter >= 30:
            self.cursor_visible = not self.cursor_visible
            self.cursor_counter = 0

        # Fondo del input
        pygame.draw.rect(screen, WHITE, self.rect)
        pygame.draw.rect(screen, self.color_border, self.rect, 2)

        if self.active:
            pygame.draw.rect(screen, self.color_active, self.rect, 3)

        # Texto o placeholder
        if self.text:
            screen.blit(self.txt_surface, (self.rect.x + 10, self.rect.y + 10))
        else:
            placeholder_surface = self.font.render(self.placeholder, True, (150, 150, 150))
            screen.blit(placeholder_surface, (self.rect.x + 10, self.rect.y + 10))

        # Cursor
        if self.active and self.cursor_visible and self.text:
            cursor_x = self.rect.x + 10 + self.txt_surface.get_width()
            pygame.draw.line(screen, BLACK, (cursor_x, self.rect.y + 5), (cursor_x, self.rect.y + self.rect.height - 5),
                             2)


def draw_gradient_rect(screen, color1, color2, rect):
    """Dibuja un rectángulo con gradiente vertical"""
    for y in range(rect.height):
        blend = y / rect.height
        r = int(color1[0] * (1 - blend) + color2[0] * blend)
        g = int(color1[1] * (1 - blend) + color2[1] * blend)
        b = int(color1[2] * (1 - blend) + color2[2] * blend)
        pygame.draw.line(screen, (r, g, b), (rect.x, rect.y + y), (rect.x + rect.width, rect.y + y))


def draw_button(screen, rect, text, font, base_color, hover_color, is_hovered=False):
    """Dibuja un botón con efecto hover y gradiente"""
    color = hover_color if is_hovered else base_color

    # Gradiente para el botón
    lighter = tuple(min(255, c + 30) for c in color)
    darker = tuple(max(0, c - 30) for c in color)
    draw_gradient_rect(screen, lighter, darker, rect)

    # Borde
    pygame.draw.rect(screen, (100, 100, 100), rect, 2)

    # Texto centrado
    text_surface = font.render(text, True, WHITE)
    text_rect = text_surface.get_rect(center=rect.center)
    screen.blit(text_surface, text_rect)


if __name__ == "__main__":
    pygame.init()

    # Configuración de la ventana
    WINDOW_WIDTH = 800
    WINDOW_HEIGHT = 600
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Configuración del Simulador de Pandemia")

    # Fuentes
    title_font = pygame.font.SysFont("Arial", 36, bold=True)
    font = pygame.font.SysFont("Arial", 24)
    label_font = pygame.font.SysFont("Arial", 20)

    # Colores
    BACKGROUND_COLOR = (240, 248, 255)  # Alice Blue
    HEADER_COLOR = (70, 130, 180)  # Steel Blue
    SECTION_COLOR = (245, 245, 245)  # WhiteSmoke

    # Crear input boxes con placeholders
    input_boxes = {
        'total': InputBox(400, 160, 180, 40, placeholder="Ej: 100"),
        'infectados': InputBox(400, 210, 180, 40, placeholder="Ej: 5"),
        'vacunados': InputBox(400, 260, 180, 40, placeholder="Ej: 10"),
        'cuarentena': InputBox(400, 310, 180, 40, placeholder="Ej: 0"),
        'duracion': InputBox(400, 360, 180, 40, placeholder="Ej: 100")
    }

    # Configuración del botón
    button_rect = pygame.Rect(225, 520, 200, 50)
    reset_button_rect = pygame.Rect(450, 520, 120, 50)

    # Variables para validación
    mouse_pos = (0, 0)
    all_boxes = list(input_boxes.values())

    # Valores por defecto
    defaults = {
        'total': '50',
        'infectados': '5',
        'vacunados': '0',
        'cuarentena': '0',
        'duracion': '100'
    }

    running = True

    while running:
        mouse_pos = pygame.mouse.get_pos()

        # Verificar hover en botones
        start_hovered = button_rect.collidepoint(mouse_pos)
        reset_hovered = reset_button_rect.collidepoint(mouse_pos)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # Manejar eventos de input boxes
            for box in all_boxes:
                box.handle_event(event)

            if event.type == pygame.MOUSEBUTTONDOWN:
                # Botón iniciar simulación
                if button_rect.collidepoint(event.pos):
                    # Validar que todos los campos tengan valores válidos
                    values = {}
                    valid = True

                    for key, box in input_boxes.items():
                        if box.text and box.text.isdigit():
                            values[key] = int(box.text)
                        elif key in defaults:
                            values[key] = int(defaults[key])
                        else:
                            valid = False
                            break

                    # Validar que el total sea mayor o igual a la suma de otros
                    if valid:
                        total_others = values['infectados'] + values['vacunados'] + values['cuarentena']
                        if values['total'] < total_others:
                            valid = False

                    if valid:
                        # Iniciar simulación
                        covid = Simulation()
                        covid.n_susceptible = values['total'] - total_others
                        covid.n_infected = values['infectados']
                        covid.n_vaccinated = values['vacunados']
                        covid.n_quarantined = values['cuarentena']
                        covid.max_days = values['duracion']
                        running = False
                        covid.start(randomize=True)

                # Botón reset
                elif reset_button_rect.collidepoint(event.pos):
                    for key, box in input_boxes.items():
                        box.text = defaults[key]
                        box.txt_surface = box.font.render(box.text, True, BLACK)

        # Dibujar interfaz
        screen.fill(BACKGROUND_COLOR)

        # Header con gradiente
        header_rect = pygame.Rect(0, 0, WINDOW_WIDTH, 100)
        draw_gradient_rect(screen, HEADER_COLOR, (50, 100, 150), header_rect)

        # Título
        title_text = title_font.render("Simulador de Pandemia", True, WHITE)
        title_rect = title_text.get_rect(center=(WINDOW_WIDTH // 2, 40))
        screen.blit(title_text, title_rect)

        subtitle_text = font.render("Configura los parámetros iniciales de la simulación", True, WHITE)
        subtitle_rect = subtitle_text.get_rect(center=(WINDOW_WIDTH // 2, 70))
        screen.blit(subtitle_text, subtitle_rect)

        # Sección de configuración
        config_rect = pygame.Rect(50, 120, WINDOW_WIDTH - 100, 320)
        pygame.draw.rect(screen, SECTION_COLOR, config_rect, border_radius=10)
        pygame.draw.rect(screen, (200, 200, 200), config_rect, 2, border_radius=10)

        # Título de sección
        section_title = font.render("Parámetros de Población", True, DARK_GREY)
        screen.blit(section_title, (70, 140))

        # Labels con iconos y descripciones
        labels = [
            ("Población Total:", "Número total de individuos en la simulación", 'total'),
            ("Infectados Iniciales:", "Personas infectadas al comenzar", 'infectados'),
            ("Vacunados Iniciales:", "Personas ya vacunadas al inicio", 'vacunados'),
            ("En Cuarentena:", "Personas en cuarentena (sin movimiento)", 'cuarentena'),
            ("Duración Máxima:", "Días máximos de simulación", 'duracion')
        ]

        y_positions = [160, 210, 260, 310, 360]

        for i, (label, description, key) in enumerate(labels):
            y = y_positions[i]

            # Label principal
            label_text = label_font.render(label, True, DARK_GREY)
            screen.blit(label_text, (80, y + 5))

            # Descripción pequeña
            desc_font = pygame.font.SysFont("Arial", 14)
            desc_text = desc_font.render(description, True, (120, 120, 120))
            screen.blit(desc_text, (80, y + 25))

        # Dibujar input boxes
        for box in all_boxes:
            box.draw(screen)

        # Validación visual
        total_val = int(input_boxes['total'].text) if input_boxes['total'].text.isdigit() else 0
        others_sum = sum(int(input_boxes[key].text) if input_boxes[key].text.isdigit() else 0
                         for key in ['infectados', 'vacunados', 'cuarentena'])

        if total_val > 0 and others_sum > total_val:
            error_text = font.render(
                "Error: La suma de infectados, vacunados y cuarentena no puede exceder el total", True,
                (220, 20, 60))
            screen.blit(error_text, (80, 410))
        elif total_val > 0:
            susceptible = total_val - others_sum
            info_text = label_font.render(f"Susceptibles resultantes: {susceptible}", True, (34, 139, 34))
            screen.blit(info_text, (80, 410))

        # Instrucciones
        instructions = [
            "• Ingresa valores numéricos en cada campo",
            "• La población total debe ser mayor a la suma de los demás valores",
            "• Los campos vacíos usarán valores por defecto"
        ]

        inst_y = 450
        for instruction in instructions:
            inst_font = pygame.font.SysFont("Arial", 16)
            inst_text = inst_font.render(instruction, True, (100, 100, 100))
            screen.blit(inst_text, (80, inst_y))
            inst_y += 20

        # Botones
        can_start = total_val >= others_sum and total_val > 0
        start_color = (34, 139, 34) if can_start else (150, 150, 150)
        start_hover_color = (50, 205, 50) if can_start else (170, 170, 170)

        draw_button(screen, button_rect, "Iniciar Simulación", font,
                    start_color, start_hover_color, start_hovered and can_start)

        draw_button(screen, reset_button_rect, "Reset", font,
                    (70, 130, 180), (100, 149, 237), reset_hovered)

        pygame.display.flip()

    pygame.quit()
