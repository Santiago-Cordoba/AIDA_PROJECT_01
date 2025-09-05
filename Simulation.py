import pygame, sys
import numpy as np

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BLUE = (0, 0, 255)
GREEN = (50, 150, 50)
PURPLE = (130, 0, 130)
GREY = (230, 230, 230)
HORRYBLE_YELLOW = (190, 175, 50)
VACCINE_COLOR = (200, 200, 255)
VACCINE_CENTER_COLOR = (255, 255, 255)

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

    def start(self, randomize=False):
        self.N = self.n_susceptible + self.n_infected + self.n_quarantined

        pygame.init()
        screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption("Simulación Epidemiológica con Vacunación")

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

        stats = pygame.Surface((self.WIDTH // 4, self.HEIGHT // 4))
        stats.fill(GREY)
        stats.set_alpha(230)
        stats_pos = (self.WIDTH // 40, self.HEIGHT // 40)

        try:
            font = pygame.font.SysFont("Arial", 24)
        except:
            font = pygame.font.SysFont(None, 24)

        clock = pygame.time.Clock()

        for i in range(self.T):
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

            self.all_container.update()
            screen.fill(BACKGROUND)

            # Dibujar centro de vacunación
            pygame.draw.rect(screen, VACCINE_CENTER_COLOR, self.vaccine_center, 2)
            pygame.draw.rect(screen, (200, 255, 200), self.vaccine_center.inflate(-4, -4))
            text = font.render("⚕", True, BLACK)
            screen.blit(text, (self.vaccine_center.centerx - 6, self.vaccine_center.centery - 12))

            # Actualizar estadísticas
            stats_height = stats.get_height()
            stats_width = stats.get_width()
            n_inf_now = len(self.infected_container)
            n_pop_now = len(self.all_container)
            n_rec_now = len(self.recovered_container)
            n_vac_now = len(self.vaccinated_container)
            t = int((i / self.T) * stats_width)
            y_infect = int(stats_height - (n_inf_now / n_pop_now) * stats_height)
            y_dead = int(((self.N - n_pop_now) / self.N) * stats_height)
            y_recovered = int((n_rec_now / n_pop_now) * stats_height)
            y_vaccinated = int((n_vac_now / n_pop_now) * stats_height)

            stats_graph = pygame.PixelArray(stats)
            stats_graph[t, y_infect:] = pygame.Color(*GREEN)
            stats_graph[t, :y_dead] = pygame.Color(*HORRYBLE_YELLOW)
            stats_graph[t, y_dead:y_dead + y_recovered] = pygame.Color(*PURPLE)
            stats_graph[t, y_dead + y_recovered:y_dead + y_recovered + y_vaccinated] = pygame.Color(*VACCINE_COLOR)

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
            del stats_graph
            stats.unlock()
            screen.blit(stats, stats_pos)
            pygame.display.flip()
            clock.tick(30)

        pygame.quit()


if __name__ == "__main__":
    covid = Simulation()
    covid.n_susceptible = 45 # Poblacion total: 50, 5 infectados, 45 susceptibles.
    covid.n_quarantined = 0
    covid.n_infected = 5
    covid.cycles_to_fate = 200
    covid.mortality_rate = 0.3
    covid.start(randomize=True)