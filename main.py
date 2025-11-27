import viz
import vizact
import vizshape
import vizinfo
import math
import random

# Initialize Vizard
viz.setMultiSample(4)
viz.fov(60)
viz.go()

# Game settings
STARTING_HEALTH = 20
STARTING_GOLD = 150
TOWER_COST = 50

# Setup camera for top-down view
viz.MainView.setPosition([0, 15, 0])
viz.MainView.setEuler([0, 90, 0])

# Path for enemies (waypoints in 3D space)
PATH = [
    [-10, 0, -3],
    [-2, 0, -3],
    [-2, 0, 2],
    [4, 0, 2],
    [4, 0, -5],
    [8, 0, -5],
    [8, 0, 4],
    [12, 0, 4]
]


class Enemy:
    def __init__(self, health, speed, reward, color):
        self.path = PATH.copy()
        self.pos = self.path[0].copy()
        self.health = health
        self.max_health = health
        self.speed = speed / 60.0  # Convert to per-frame speed
        self.reward = reward
        self.color = color
        self.path_index = 0
        
        # Create 3D model (sphere for enemy)
        self.model = vizshape.addSphere(radius=0.2)
        self.model.color(color)
        self.model.setPosition(self.pos)
        
        # Create health bar (a flat rectangle above enemy)
        self.health_bar_bg = vizshape.addPlane(size=[0.4, 0.05], axis=vizshape.AXIS_Y)
        self.health_bar_bg.color(viz.RED)
        self.health_bar_bg.setPosition([self.pos[0], self.pos[1] + 0.5, self.pos[2]])
        
        self.health_bar = vizshape.addPlane(size=[0.4, 0.05], axis=vizshape.AXIS_Y)
        self.health_bar.color(viz.GREEN)
        self.health_bar.setPosition([self.pos[0], self.pos[1] + 0.51, self.pos[2]])
        
    def move(self):
        if self.path_index < len(self.path) - 1:
            target = self.path[self.path_index + 1]
            dx = target[0] - self.pos[0]
            dy = target[1] - self.pos[1]
            dz = target[2] - self.pos[2]
            distance = math.sqrt(dx**2 + dy**2 + dz**2)
            
            if distance < self.speed:
                self.path_index += 1
                if self.path_index >= len(self.path) - 1:
                    return True  # Reached end
            else:
                self.pos[0] += (dx / distance) * self.speed
                self.pos[1] += (dy / distance) * self.speed
                self.pos[2] += (dz / distance) * self.speed
                
            self.model.setPosition(self.pos)
            self.update_health_bar()
        else:
            return True  # Reached end
        return False
    
    def update_health_bar(self):
        health_ratio = max(0, self.health / self.max_health)
        self.health_bar_bg.setPosition([self.pos[0], self.pos[1] + 0.5, self.pos[2]])
        self.health_bar.setPosition([self.pos[0] - 0.2 * (1 - health_ratio), self.pos[1] + 0.51, self.pos[2]])
        self.health_bar.setScale([health_ratio, 1, 1])
    
    def take_damage(self, damage):
        self.health -= damage
        self.update_health_bar()
        return self.health <= 0
    
    def remove(self):
        self.model.remove()
        self.health_bar.remove()
        self.health_bar_bg.remove()


class Projectile:
    def __init__(self, pos, target, damage):
        self.pos = pos.copy()
        self.target = target
        self.damage = damage
        self.speed = 0.15
        
        # Create projectile (glowing sphere)
        self.model = vizshape.addSphere(radius=0.1)
        self.model.color(viz.YELLOW)
        self.model.emissive(viz.YELLOW)
        self.model.setPosition(self.pos)
        
    def move(self):
        if self.target and self.target.health > 0:
            dx = self.target.pos[0] - self.pos[0]
            dy = self.target.pos[1] - self.pos[1]
            dz = self.target.pos[2] - self.pos[2]
            distance = math.sqrt(dx**2 + dy**2 + dz**2)
            
            if distance < self.speed:
                return True  # Hit target
            
            self.pos[0] += (dx / distance) * self.speed
            self.pos[1] += (dy / distance) * self.speed
            self.pos[2] += (dz / distance) * self.speed
            self.model.setPosition(self.pos)
            return False
        return True  # Target dead, remove projectile
    
    def remove(self):
        self.model.remove()


class WizardTower:
    def __init__(self, x, z):
        self.pos = [x, 0, z]
        self.range = 3.0
        self.damage = 15
        self.cooldown = 30  # frames
        self.cooldown_counter = 0
        
        # Create tower base (cylinder)
        self.base = vizshape.addCylinder(height=0.6, radius=0.25)
        self.base.color([0.5, 0, 0.8])  # Purple
        self.base.setPosition([x, 0.3, z])
        
        # Create wizard hat (cone)
        self.hat = vizshape.addCone(height=0.5, radius=0.3)
        self.hat.color(viz.BLUE)
        self.hat.setPosition([x, 0.85, z])
        
        # Create star on hat
        self.star = vizshape.addSphere(radius=0.08)
        self.star.color(viz.YELLOW)
        self.star.emissive(viz.YELLOW)
        self.star.setPosition([x, 1.1, z])
        
        # Range indicator (invisible by default)
        self.range_indicator = vizshape.addCircle(radius=self.range, axis=vizshape.AXIS_Y)
        self.range_indicator.color([0.8, 0.8, 0.8])
        self.range_indicator.alpha(0.3)
        self.range_indicator.setPosition([x, 0.05, z])
        self.range_indicator.visible(viz.OFF)
        
    def update(self, enemies, projectiles):
        self.cooldown_counter += 1
        
        if self.cooldown_counter >= self.cooldown:
            # Find nearest enemy in range
            target = None
            min_distance = float('inf')
            
            for enemy in enemies:
                dx = enemy.pos[0] - self.pos[0]
                dz = enemy.pos[2] - self.pos[2]
                distance = math.sqrt(dx**2 + dz**2)
                
                if distance <= self.range and distance < min_distance:
                    min_distance = distance
                    target = enemy
            
            if target:
                shoot_pos = [self.pos[0], 0.6, self.pos[2]]
                projectiles.append(Projectile(shoot_pos, target, self.damage))
                self.cooldown_counter = 0
    
    def show_range(self, show):
        self.range_indicator.visible(viz.ON if show else viz.OFF)
    
    def remove(self):
        self.base.remove()
        self.hat.remove()
        self.star.remove()
        self.range_indicator.remove()


class Game:
    def __init__(self):
        self.health = STARTING_HEALTH
        self.gold = STARTING_GOLD
        self.wave = 0
        self.enemies = []
        self.towers = []
        self.projectiles = []
        self.placing_tower = False
        self.game_over = False
        self.wave_in_progress = False
        self.enemy_spawn_timer = 0
        self.enemies_to_spawn = []
        self.preview_tower = None
        
        # Create ground plane
        self.ground = vizshape.addPlane(size=[25, 15], axis=vizshape.AXIS_Y)
        self.ground.color([0.2, 0.7, 0.2])
        
        # Create path visualization
        self.create_path()
        
        # Create UI
        self.create_ui()
    
    def create_path(self):
        # Draw path segments
        for i in range(len(PATH) - 1):
            start = PATH[i]
            end = PATH[i + 1]
            
            # Calculate midpoint and dimensions
            mid_x = (start[0] + end[0]) / 2
            mid_z = (start[2] + end[2]) / 2
            
            length = math.sqrt((end[0] - start[0])**2 + (end[2] - start[2])**2)
            
            # Create path segment
            segment = vizshape.addPlane(size=[length, 0.6], axis=vizshape.AXIS_Y)
            segment.color([0.6, 0.6, 0.6])
            segment.setPosition([mid_x, 0.02, mid_z])
            
            # Rotate to align with path direction
            angle = math.degrees(math.atan2(end[0] - start[0], end[2] - start[2]))
            segment.setEuler([angle, 0, 0])
    
    def create_ui(self):
        # Create info panel
        self.info = vizinfo.InfoPanel('', align=vizinfo.UPPER_LEFT, icon=False)
        self.update_ui()
        
    def update_ui(self):
        ui_text = f'Health: {self.health}  |  Gold: {self.gold}  |  Wave: {self.wave}\n'
        if not self.wave_in_progress:
            ui_text += 'Press SPACE to start next wave\n'
        else:
            ui_text += 'Wave in progress...\n'
        ui_text += f'Press T to place tower (${TOWER_COST}) | Press ESC to cancel\n'
        if self.game_over:
            ui_text += f'\n=== GAME OVER ===\nYou survived {self.wave} waves!\nPress R to restart'
        
        self.info.setText(ui_text)
        
    def start_wave(self):
        if not self.wave_in_progress and not self.game_over:
            self.wave += 1
            self.wave_in_progress = True
            self.enemy_spawn_timer = 0
            
            # Generate enemies for this wave
            self.enemies_to_spawn = []
            num_enemies = 5 + self.wave * 3
            
            for i in range(num_enemies):
                if self.wave < 3:
                    # Basic enemies
                    self.enemies_to_spawn.append(('basic', i * 30))
                elif self.wave < 6:
                    # Mix of basic and fast
                    if i % 2 == 0:
                        self.enemies_to_spawn.append(('basic', i * 25))
                    else:
                        self.enemies_to_spawn.append(('fast', i * 25))
                else:
                    # All types including tanks
                    if i % 3 == 0:
                        self.enemies_to_spawn.append(('tank', i * 20))
                    elif i % 3 == 1:
                        self.enemies_to_spawn.append(('fast', i * 20))
                    else:
                        self.enemies_to_spawn.append(('basic', i * 20))
    
    def spawn_enemies(self):
        if self.enemies_to_spawn:
            self.enemy_spawn_timer += 1
            
            # Check if it's time to spawn next enemy
            while self.enemies_to_spawn and self.enemy_spawn_timer >= self.enemies_to_spawn[0][1]:
                enemy_type, _ = self.enemies_to_spawn.pop(0)
                
                if enemy_type == 'basic':
                    self.enemies.append(Enemy(health=30 + self.wave * 10, speed=2, reward=10, color=viz.RED))
                elif enemy_type == 'fast':
                    self.enemies.append(Enemy(health=20 + self.wave * 5, speed=4, reward=15, color=viz.YELLOW))
                elif enemy_type == 'tank':
                    self.enemies.append(Enemy(health=100 + self.wave * 20, speed=1, reward=25, color=viz.GRAY))
        
        # Check if wave is complete
        if not self.enemies_to_spawn and not self.enemies:
            self.wave_in_progress = False
    
    def place_tower(self, x, z):
        # Check if position is valid (not on path, not too close to other towers)
        if self.gold >= TOWER_COST:
            # Check distance from path
            on_path = False
            for i in range(len(PATH) - 1):
                x1, _, z1 = PATH[i]
                x2, _, z2 = PATH[i + 1]
                # Check if point is close to path segment
                dist = self.point_to_segment_distance(x, z, x1, z1, x2, z2)
                if dist < 0.8:
                    on_path = True
                    break
            
            # Check distance from other towers
            too_close = False
            for tower in self.towers:
                dist = math.sqrt((tower.pos[0] - x)**2 + (tower.pos[2] - z)**2)
                if dist < 1.0:
                    too_close = True
                    break
            
            if not on_path and not too_close:
                self.towers.append(WizardTower(x, z))
                self.gold -= TOWER_COST
                self.update_ui()
                return True
        return False
    
    def point_to_segment_distance(self, px, pz, x1, z1, x2, z2):
        dx = x2 - x1
        dz = z2 - z1
        if dx == 0 and dz == 0:
            return math.sqrt((px - x1)**2 + (pz - z1)**2)
        
        t = max(0, min(1, ((px - x1) * dx + (pz - z1) * dz) / (dx * dx + dz * dz)))
        nearest_x = x1 + t * dx
        nearest_z = z1 + t * dz
        return math.sqrt((px - nearest_x)**2 + (pz - nearest_z)**2)
    
    def update(self):
        if self.game_over:
            return
        
        # Spawn enemies for current wave
        if self.wave_in_progress:
            self.spawn_enemies()
        
        # Update enemies
        for enemy in self.enemies[:]:
            if enemy.move():
                self.enemies.remove(enemy)
                enemy.remove()
                self.health -= 1
                self.update_ui()
                if self.health <= 0:
                    self.game_over = True
                    self.update_ui()
        
        # Update towers
        for tower in self.towers:
            tower.update(self.enemies, self.projectiles)
        
        # Update projectiles
        for projectile in self.projectiles[:]:
            if projectile.move():
                self.projectiles.remove(projectile)
                projectile.remove()
                if projectile.target and projectile.target.health > 0:
                    if projectile.target.take_damage(projectile.damage):
                        if projectile.target in self.enemies:
                            self.enemies.remove(projectile.target)
                            self.gold += projectile.target.reward
                            self.update_ui()
                            projectile.target.remove()
    
    def toggle_tower_placement(self):
        self.placing_tower = not self.placing_tower
        if self.placing_tower:
            if self.preview_tower is None:
                self.preview_tower = WizardTower(0, 0)
                self.preview_tower.show_range(True)
        else:
            if self.preview_tower:
                self.preview_tower.remove()
                self.preview_tower = None
    
    def update_tower_preview(self):
        if self.placing_tower and self.preview_tower:
            # Get mouse position in 3D world
            info = viz.intersect(viz.MainView.screenToWorld([0.5, 0.5]), viz.MainView.screenToWorld([0.5, 0.4]))
            if info.valid:
                self.preview_tower.base.setPosition([info.point[0], 0.3, info.point[2]])
                self.preview_tower.hat.setPosition([info.point[0], 0.85, info.point[2]])
                self.preview_tower.star.setPosition([info.point[0], 1.1, info.point[2]])
                self.preview_tower.range_indicator.setPosition([info.point[0], 0.05, info.point[2]])
                self.preview_tower.pos = [info.point[0], 0, info.point[2]]
    
    def reset(self):
        # Remove all game objects
        for enemy in self.enemies:
            enemy.remove()
        for tower in self.towers:
            tower.remove()
        for projectile in self.projectiles:
            projectile.remove()
        if self.preview_tower:
            self.preview_tower.remove()
        
        # Reset game state
        self.__init__()


# Create game instance
game = Game()

# Key handlers
def onKeyDown(key):
    if key == ' ':  # Space to start wave
        game.start_wave()
    elif key == 't' or key == 'T':  # T to toggle tower placement
        if game.gold >= TOWER_COST and not game.game_over:
            game.toggle_tower_placement()
    elif key == viz.KEY_ESCAPE:  # ESC to cancel placement
        if game.placing_tower:
            game.toggle_tower_placement()
    elif key == 'r' or key == 'R':  # R to restart
        if game.game_over:
            game.reset()

# Mouse click handler
def onMouseDown(button):
    if button == viz.MOUSEBUTTON_LEFT and game.placing_tower and not game.game_over:
        if game.preview_tower:
            pos = game.preview_tower.pos
            if game.place_tower(pos[0], pos[2]):
                game.toggle_tower_placement()

# Register callbacks
vizact.onkeydown(viz.KEY_ANY, onKeyDown)
vizact.onmousedown(viz.MOUSEBUTTON_LEFT, onMouseDown)

# Main update loop
def updateGame():
    game.update()
    game.update_tower_preview()

vizact.ontimer(0, updateGame)
