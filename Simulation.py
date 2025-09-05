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

        # Parámetros de enfermedad
        self.T = 1000
        self.transmission_rate = 0.7
        self.incubation_period = 50
        self.recovery_period_min = 150
        self.recovery_period_max = 250
        self.mortality_rate = 0.3

        #Centro de vacunación
        self.vaccine_center = pygame.Rect(20, self.HEIGHT - 120, 100, 100)
        self.vaccination_rate = 0.8

        self.history_infected = []
        self.history_recovered = []
        self.history_vaccinated = []
        self.history_dead = []
        self.history_susceptible = []

    def start(self, randomize=False):
        self.N = self.n_susceptible + self.n_infected + self.n_quarantined

        pygame.init()
        EXTRA_WIDTH = 450
        screen = pygame.display.set_mode((self.WIDTH + EXTRA_WIDTH, self.HEIGHT))
        pygame.display.set_caption("Desease Simulator")


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

            if i < self.T:

                self.all_container.update()
                screen.fill(BACKGROUND)

                pygame.draw.rect(screen, GREY, (self.WIDTH, 0, EXTRA_WIDTH, self.HEIGHT))

                # Dibujar centro de vacunación
                pygame.draw.rect(screen, VACCINE_CENTER_COLOR, self.vaccine_center, 2)
                pygame.draw.rect(screen, (200, 255, 200), self.vaccine_center.inflate(-4, -4))
                text = font.render("⚕", True, BLACK)
                screen.blit(text, (self.vaccine_center.centerx - 6, self.vaccine_center.centery - 12))

                #Incrementar el numero de dias
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
                plt.plot(self.history_susceptible, color="black", label="Susceptibles")
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
    def __init__(self, x, y, w, h, text=''):
        self.rect = pygame.Rect(x, y, w, h)
        self.color_inactive = pygame.Color('lightskyblue3')
        self.color_active = pygame.Color('dodgerblue2')
        self.color = self.color_inactive
        self.text = text
        self.font = pygame.font.SysFont("Arial", 24)
        self.txt_surface = self.font.render(text, True, self.color)
        self.active = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Si clic dentro del input → activar
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
                    if event.unicode.isdigit():
                        self.text += event.unicode
                self.txt_surface = self.font.render(self.text, True, BLACK)

        return None

    def draw(self, screen):
        # Renderizar texto
        screen.blit(self.txt_surface, (self.rect.x+5, self.rect.y+5))
        pygame.draw.rect(screen, self.color, self.rect, 2)



if __name__ == "__main__":
    pygame.init()
    screen = pygame.display.set_mode((600, 400))
    pygame.display.set_caption("Configuración de la simulación")
    font = pygame.font.SysFont("Arial", 28)

    input_total = InputBox(250, 100, 140, 40)
    input_infectados = InputBox(250, 180, 140, 40)
    input_boxes = [input_total, input_infectados]

    button_rect = pygame.Rect(200, 280, 200, 50)

    running = True
    total_poblacion = None
    infectados_iniciales = None

    while running:
        screen.fill(WHITE)

        # Etiquetas
        txt1 = font.render("Población total:", True, BLACK)
        txt2 = font.render("Infectados iniciales:", True, BLACK)
        screen.blit(txt1, (50, 105))
        screen.blit(txt2, (50, 185))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            for box in input_boxes:
                box.handle_event(event)

            if event.type == pygame.MOUSEBUTTONDOWN:
                if button_rect.collidepoint(event.pos):
                    if input_total.text.isdigit() and input_infectados.text.isdigit():
                        total_poblacion = int(input_total.text)
                        infectados_iniciales = int(input_infectados.text)
                        running = False

        # Dibujar input boxes
        for box in input_boxes:
            box.draw(screen)

        # Dibujar botón
        pygame.draw.rect(screen, (100, 200, 100), button_rect)
        btn_txt = font.render("Iniciar simulación", True, WHITE)
        screen.blit(btn_txt, (button_rect.x + 15, button_rect.y + 10))

        pygame.display.flip()

    # 🚀 Ya tenemos los valores
    covid = Simulation()
    covid.n_infected = infectados_iniciales
    covid.n_susceptible = total_poblacion - infectados_iniciales
    covid.n_quarantined = 0
    covid.start(randomize=True)
