import pygame
import math
import random
import time
import os
import heapq
from collections import deque


class Enemy:

    def __init__(self, spawn_x=None, spawn_y=None):

        # =====================================================
        # POSITION
        # =====================================================

        if spawn_x is not None and spawn_y is not None:

            self.x = spawn_x
            self.y = spawn_y

        else:

            # Random fallback spawn position
            self.x = random.randint(50, 950)
            self.y = random.randint(50, 650)


        self.width = 40
        self.height = 40


        self.rect = pygame.Rect(
            self.x,
            self.y,
            self.width,
            self.height
        )


        self.speed = 1.3

        self.alive = True

        # Only the enemy selected by main.py is allowed to chase/attack.
        self.active = False

        self.health = 30


        # =====================================================
        # A* NAVIGATION SETTINGS
        # =====================================================

        # Size of each invisible navigation grid cell.
        self.grid_size = 32

        # Navigation area matches the game window.
        self.map_left = 0
        self.map_top = 0
        self.map_right = 1000
        self.map_bottom = 700

        # Current A* path.
        self.path = []

        # Current waypoint index.
        self.path_index = 0

        # When the path was last calculated.
        self.last_path_time = (
            time.time()+random.uniform(-1, 0.0)
        )

        # Recalculate periodically because the player moves.
        self.path_recalculate_delay = 1.0

        # Remember last target cell.
        self.last_target_cell = None

        #stuck detection
        self.last_position = (self.x, self.y)

        self.stuck_time = 0.0
        self.last_stuck_check_time = time.time()
        self.force_new_path = False

        # =====================================================
        # ACTION STATES
        # =====================================================

        self.is_shooting = False
        self.is_reloading = False
        self.is_melee = False


        # =====================================================
        # RANDOM WEAPON
        # =====================================================

        self.available_weapons = [
            "handgun",
            "shotgun",
            "rifle",
            "knife"
        ]


        self.current_weapon = random.choice(
            self.available_weapons
        )


        # =====================================================
        # WEAPON STATS
        # =====================================================

        self.weapon_stats = {

            "handgun": {
                "damage": 2,
                "melee_damage": 1,
                "shoot_range": 200,
                "stop_distance": 140,
                "fire_cooldown": 0.70
            },

            "shotgun": {
                "damage": 5,
                "melee_damage": 5,
                "shoot_range": 110,
                "stop_distance": 75,
                "fire_cooldown": 1.20
            },

            "rifle": {
                "damage": 1,
                "melee_damage": 2,
                "shoot_range": 280,
                "stop_distance": 200,
                "fire_cooldown": 0.25
            },

            "knife": {
                "damage": None,
                "melee_damage": 6,
                "shoot_range": 0,
                "stop_distance": 0,
                "fire_cooldown": None
            }
        }


        # =====================================================
        # COMBAT SETTINGS
        # =====================================================

        self.melee_range = 55
        self.melee_cooldown = 0.90

        self.last_shot_time = 0
        self.last_melee_time = 0

        self.pending_shots = []


        # =====================================================
        # INFINITE AMMO SYSTEM
        # =====================================================

        self.weapon_max_ammo = {

            "handgun": 12,
            "shotgun": 6,
            "rifle": 30
        }


        if self.current_weapon == "knife":

            self.max_ammo = None
            self.ammo = None

        else:

            self.max_ammo = (
                self.weapon_max_ammo[
                    self.current_weapon
                ]
            )

            self.ammo = self.max_ammo


        # =====================================================
        # FEET ANIMATIONS
        # =====================================================

        self.feet_idle_frames = []
        self.feet_walk_frames = []
        self.feet_run_frames = []
        self.feet_strafe_left_frames = []
        self.feet_strafe_right_frames = []


        # =====================================================
        # HANDGUN ANIMATIONS
        # =====================================================

        self.handgun_idle_frames = []
        self.handgun_move_frames = []
        self.handgun_shoot_frames = []
        self.handgun_reload_frames = []
        self.handgun_melee_frames = []


        # =====================================================
        # SHOTGUN ANIMATIONS
        # =====================================================

        self.shotgun_idle_frames = []
        self.shotgun_move_frames = []
        self.shotgun_shoot_frames = []
        self.shotgun_reload_frames = []
        self.shotgun_melee_frames = []


        # =====================================================
        # RIFLE ANIMATIONS
        # =====================================================

        self.rifle_idle_frames = []
        self.rifle_move_frames = []
        self.rifle_shoot_frames = []
        self.rifle_reload_frames = []
        self.rifle_melee_frames = []


        # =====================================================
        # KNIFE ANIMATIONS
        # =====================================================

        self.knife_idle_frames = []
        self.knife_move_frames = []
        self.knife_melee_frames = []


        # =====================================================
        # CURRENT WEAPON ANIMATIONS
        # =====================================================

        self.weapon_idle_frames = []
        self.weapon_move_frames = []
        self.weapon_shoot_frames = []
        self.weapon_reload_frames = []
        self.weapon_melee_frames = []

        self.weapon_animation = []


        # =====================================================
        # ANIMATION SETTINGS
        # =====================================================

        self.animation_speed = 0.20
        self.melee_animation_speed = 0.38
        self.feet_animation_speed = 0.25
        self.reload_animation_speed = 0.20


        # =====================================================
        # CURRENT ANIMATION STATE
        # =====================================================

        self.current_frame = 0
        self.feet_frame = 0

        self.current_feet_animation = []
        self.feet_animation = []


        # =====================================================
        # LOAD ASSETS
        # =====================================================

        current_dir = os.path.dirname(__file__)

        player_folder = os.path.join(
            current_dir,
            "..",
            "assets",
            "player"
        )

        feet_folder = os.path.join(
            player_folder,
            "feet"
        )


        # =====================================================
        # LOAD FRAMES
        # =====================================================

        def load_frames(folder):

            frames = []

            if not os.path.exists(folder):

                print(
                    "WARNING: Animation folder not found:",
                    folder
                )

                return frames


            files = sorted(
                [
                    file
                    for file in os.listdir(folder)
                    if file.lower().endswith(".png")
                ]
            )


            for file in files:

                image_path = os.path.join(
                    folder,
                    file
                )

                image = pygame.image.load(
                    image_path
                ).convert_alpha()

                image = pygame.transform.scale(
                    image,
                    (
                        self.width,
                        self.height
                    )
                )

                frames.append(image)


            return frames


        # =====================================================
        # LOAD FEET
        # =====================================================

        self.feet_idle_frames = load_frames(
            os.path.join(feet_folder, "idle")
        )

        self.feet_walk_frames = load_frames(
            os.path.join(feet_folder, "walk")
        )

        self.feet_run_frames = load_frames(
            os.path.join(feet_folder, "run")
        )

        self.feet_strafe_left_frames = load_frames(
            os.path.join(
                feet_folder,
                "strafe_left"
            )
        )

        self.feet_strafe_right_frames = load_frames(
            os.path.join(
                feet_folder,
                "strafe_right"
            )
        )


        # =====================================================
        # LOAD WEAPON ANIMATIONS
        # =====================================================

        def load_weapon(
            weapon,
            animation
        ):

            return load_frames(
                os.path.join(
                    player_folder,
                    weapon,
                    animation
                )
            )


        # =====================================================
        # HANDGUN
        # =====================================================

        self.handgun_idle_frames = load_weapon(
            "handgun",
            "idle"
        )

        self.handgun_move_frames = load_weapon(
            "handgun",
            "move"
        )

        self.handgun_shoot_frames = load_weapon(
            "handgun",
            "shoot"
        )

        self.handgun_reload_frames = load_weapon(
            "handgun",
            "reload"
        )

        self.handgun_melee_frames = load_weapon(
            "handgun",
            "meleeattack"
        )


        # =====================================================
        # SHOTGUN
        # =====================================================

        self.shotgun_idle_frames = load_weapon(
            "shotgun",
            "idle"
        )

        self.shotgun_move_frames = load_weapon(
            "shotgun",
            "move"
        )

        self.shotgun_shoot_frames = load_weapon(
            "shotgun",
            "shoot"
        )

        self.shotgun_reload_frames = load_weapon(
            "shotgun",
            "reload"
        )

        self.shotgun_melee_frames = load_weapon(
            "shotgun",
            "meleeattack"
        )


        # =====================================================
        # RIFLE
        # =====================================================

        self.rifle_idle_frames = load_weapon(
            "rifle",
            "idle"
        )

        self.rifle_move_frames = load_weapon(
            "rifle",
            "move"
        )

        self.rifle_shoot_frames = load_weapon(
            "rifle",
            "shoot"
        )

        self.rifle_reload_frames = load_weapon(
            "rifle",
            "reload"
        )

        self.rifle_melee_frames = load_weapon(
            "rifle",
            "meleeattack"
        )


        # =====================================================
        # KNIFE
        # =====================================================

        self.knife_idle_frames = load_weapon(
            "knife",
            "idle"
        )

        self.knife_move_frames = load_weapon(
            "knife",
            "move"
        )

        self.knife_melee_frames = load_weapon(
            "knife",
            "meleeattack"
        )


        # =====================================================
        # SET CURRENT WEAPON
        # =====================================================

        self.set_weapon(
            self.current_weapon
        )


        # =====================================================
        # DEFAULT FEET
        # =====================================================

        self.current_feet_animation = (
            self.feet_idle_frames
        )

        self.feet_animation = (
            self.feet_idle_frames
        )


        if len(
            self.current_feet_animation
        ) > 0:

            self.original_feet_image = (
                self.current_feet_animation[0]
            )

        else:

            self.original_feet_image = None


        if len(
            self.weapon_animation
        ) > 0:

            self.original_image = (
                self.weapon_animation[0]
            )

        else:

            self.original_image = None


    # =========================================================
    # ACTIVE ENEMY STATE
    # =========================================================

    def set_active(self, active):

        self.active = active

        # Inactive enemies must never keep an old route.
        if not active:
            self.path = []
            self.path_index = 0
            self.force_new_path = False
            self.stuck_time = 0.0

            self.current_feet_animation = self.feet_idle_frames
            self.weapon_animation = self.weapon_idle_frames
            self.current_frame = 0
            self.feet_frame = 0

    # =========================================================
    # SET NAVIGATION BOUNDS
    # =========================================================

    def set_navigation_bounds(
        self,
        map_left,
        map_top,
        map_right,
        map_bottom
    ):

        self.map_left = float(map_left)
        self.map_top = float(map_top)
        self.map_right = float(map_right)
        self.map_bottom = float(map_bottom)

        # Force the next active navigation update to use the new bounds.
        self.path = []
        self.path_index = 0
        self.force_new_path = True


    # =========================================================
    # SET WEAPON
    # =========================================================

    def set_weapon(
        self,
        weapon
    ):

        if weapon not in self.available_weapons:
            return False


        if weapon == "handgun":

            self.weapon_idle_frames = (
                self.handgun_idle_frames
            )

            self.weapon_move_frames = (
                self.handgun_move_frames
            )

            self.weapon_shoot_frames = (
                self.handgun_shoot_frames
            )

            self.weapon_reload_frames = (
                self.handgun_reload_frames
            )

            self.weapon_melee_frames = (
                self.handgun_melee_frames
            )


        elif weapon == "shotgun":

            self.weapon_idle_frames = (
                self.shotgun_idle_frames
            )

            self.weapon_move_frames = (
                self.shotgun_move_frames
            )

            self.weapon_shoot_frames = (
                self.shotgun_shoot_frames
            )

            self.weapon_reload_frames = (
                self.shotgun_reload_frames
            )

            self.weapon_melee_frames = (
                self.shotgun_melee_frames
            )


        elif weapon == "rifle":

            self.weapon_idle_frames = (
                self.rifle_idle_frames
            )

            self.weapon_move_frames = (
                self.rifle_move_frames
            )

            self.weapon_shoot_frames = (
                self.rifle_shoot_frames
            )

            self.weapon_reload_frames = (
                self.rifle_reload_frames
            )

            self.weapon_melee_frames = (
                self.rifle_melee_frames
            )


        elif weapon == "knife":

            self.weapon_idle_frames = (
                self.knife_idle_frames
            )

            self.weapon_move_frames = (
                self.knife_move_frames
            )

            self.weapon_shoot_frames = []

            self.weapon_reload_frames = []

            self.weapon_melee_frames = (
                self.knife_melee_frames
            )


        self.current_weapon = weapon


        if weapon == "knife":

            self.max_ammo = None
            self.ammo = None

        else:

            self.max_ammo = (
                self.weapon_max_ammo[
                    weapon
                ]
            )

            self.ammo = self.max_ammo


        self.current_frame = 0

        self.weapon_animation = (
            self.weapon_idle_frames
        )

        return True


    # =========================================================
    # DAMAGE
    # =========================================================

    def take_damage(
        self,
        damage
    ):

        self.health -= damage

        if self.health <= 0:

            self.health = 0
            self.alive = False


    # =========================================================
    # LINE OF SIGHT
    # =========================================================

    def has_line_of_sight(
        self,
        player,
        obstacles
    ):

        if not obstacles:
            return True


        enemy_center = (
            self.x + self.width / 2,
            self.y + self.height / 2
        )

        player_center = (
            player.x + player.width / 2,
            player.y + player.height / 2
        )


        for obstacle in obstacles:

            if obstacle.rect.clipline(
                enemy_center,
                player_center
            ):

                return False


        return True


    # =========================================================
    # GRID CONVERSION
    # =========================================================
    # =========================================================
# UPDATE NAVIGATION BOUNDS
# =========================================================

    def update_navigation_bounds(
        self,
        player=None,
        obstacles=None
    ):
        """Legacy compatibility method.

        Navigation bounds are now supplied by main.py from the actual
        scaled Tiled map. We intentionally do not calculate bounds from
        the current player/enemy positions because that makes the A* grid
        move around during gameplay.
        """
        return


    def world_to_grid(
        self,
        x,
        y
    ):

        return (

            int(x-self.map_left) // self.grid_size,

            int(y-self.map_top) // self.grid_size
        )


    def grid_to_world(
        self,
        cell
    ):

        grid_x, grid_y = cell

        return (

            self.map_left +
            grid_x *
            self.grid_size +
            self.grid_size / 2,

            self.map_top +
            grid_y *
            self.grid_size +
            self.grid_size / 2
        )


    # =========================================================
    # CHECK GRID CELL
    # =========================================================

    def is_cell_walkable(
        self,
        cell,
        obstacles
    ):

        world_x, world_y = (
            self.grid_to_world(
                cell
            )
        )

       #check navigation bounds
        if (world_x - self.width / 2 < self.map_left):
            return False

        if (world_y -self.height / 2 <self.map_top):
            return False
        if (world_x + self.width / 2 > self.map_right):
            return False
        if (world_y + self.height / 2 > self.map_bottom):
            return False

        #check complete enemy body
        enemy_test_rect = pygame.Rect(
            int(
                world_x -
                self.width / 2
            ),

            int(
                world_y -
                self.height / 2
            ),

            self.width,

            self.height
        )
        for obstacle in obstacles:

            if enemy_test_rect.colliderect(
                obstacle.rect
            ):

                return False
      



        return True


    # =========================================================
    # FIND NEAREST WALKABLE CELL
    # =========================================================

    def find_nearest_walkable(
        self,
        start_cell,
        obstacles
    ):

        if self.is_cell_walkable(
            start_cell,
            obstacles
        ):

            return start_cell


        queue = deque([
            start_cell
        ])

        visited = {
            start_cell
        }


        directions = [

            (1, 0),
            (-1, 0),
            (0, 1),
            (0, -1)
        ]


        while queue:

            current = queue.popleft()


            for dx, dy in directions:

                neighbour = (

                    current[0] + dx,

                    current[1] + dy
                )


                if neighbour in visited:
                    continue


                visited.add(
                    neighbour
                )


                if self.is_cell_walkable(
                    neighbour,
                    obstacles
                ):

                    return neighbour


                queue.append(
                    neighbour
                )


        return None


    # =========================================================
    # A* HEURISTIC
    # =========================================================

    def heuristic(
        self,
        cell_a,
        cell_b
    ):

        return (

            abs(
                cell_a[0] -
                cell_b[0]
            )

            +

            abs(
                cell_a[1] -
                cell_b[1]
            )
        )


    # =========================================================
    # A* PATHFINDING
    # =========================================================

    def calculate_path(
        self,
        target_x,
        target_y,
        obstacles
    ):

        enemy_center_x = (
            self.x +
            self.width / 2
        )

        enemy_center_y = (
            self.y +
            self.height / 2
        )


        start_cell = (
            self.world_to_grid(
                enemy_center_x,
                enemy_center_y
            )
        )


        target_cell = (
            self.world_to_grid(
                target_x,
                target_y
            )
        )


        start_cell = (
            self.find_nearest_walkable(
                start_cell,
                obstacles
            )
        )


        target_cell = (
            self.find_nearest_walkable(
                target_cell,
                obstacles
            )
        )


        if start_cell is None:
            return []

        if target_cell is None:
            return []


        open_heap = []

        heapq.heappush(
            open_heap,
            (
                0,
                start_cell
            )
        )


        came_from = {}

        g_score = {
            start_cell: 0
        }


        closed_set = set()


        directions = [

            (1, 0),
            (-1, 0),
            (0, 1),
            (0, -1),

            (1, 1),
            (1, -1),
            (-1, 1),
            (-1, -1)
        ]


        while open_heap:


            current = (
                heapq.heappop(
                    open_heap
                )[1]
            )


            if current in closed_set:
                continue


            if current == target_cell:


                path = []

                while current in came_from:

                    path.append(
                        current
                    )

                    current = (
                        came_from[
                            current
                        ]
                    )


                path.reverse()


                # Convert grid cells into
                # actual screen waypoints.

                world_path = []


                for cell in path:

                    world_path.append(

                        self.grid_to_world(
                            cell
                        )
                    )


                return world_path


            closed_set.add(
                current
            )


            for dx, dy in directions:


                neighbour = (

                    current[0] + dx,

                    current[1] + dy
                )


                if neighbour in closed_set:
                    continue


                if not self.is_cell_walkable(
                    neighbour,
                    obstacles
                ):

                    continue


                # Prevent diagonal corner cutting.

                if dx != 0 and dy != 0:


                    side_a = (

                        current[0] + dx,

                        current[1]
                    )


                    side_b = (

                        current[0],

                        current[1] + dy
                    )


                    if (

                        not self.is_cell_walkable(
                            side_a,
                            obstacles
                        )

                        or

                        not self.is_cell_walkable(
                            side_b,
                            obstacles
                        )

                    ):

                        continue


                if dx != 0 and dy != 0:

                    movement_cost = (
                        1.414
                    )

                else:

                    movement_cost = 1


                tentative_g_score = (

                    g_score[
                        current
                    ]

                    +

                    movement_cost
                )


                if (

                    neighbour
                    not in g_score

                    or

                    tentative_g_score
                    <
                    g_score[
                        neighbour
                    ]

                ):


                    came_from[
                        neighbour
                    ] = current


                    g_score[
                        neighbour
                    ] = (
                        tentative_g_score
                    )


                    f_score = (

                        tentative_g_score

                        +

                        self.heuristic(
                            neighbour,
                            target_cell
                        )
                    )


                    heapq.heappush(

                        open_heap,

                        (

                            f_score,

                            neighbour
                        )
                    )


        return []


    # =========================================================
    # UPDATE NAVIGATION PATH
    # =========================================================

    def update_path(
        self,
        player,
        obstacles
    ):

        if not self.alive or not self.active:
            return

        current_time = time.time()

        if(
            not self.force_new_path

            and

            current_time - self.last_path_time
            <
            self.path_recalculate_delay
        ):

            return


        target_x = (
            player.x +
            player.width / 2
        )

        target_y = (
            player.y +
            player.height / 2
        )


        target_cell = (
            self.world_to_grid(
                target_x,
                target_y
            )
        )


        should_recalculate = False


        if len(self.path) == 0:

            should_recalculate = True

        elif self.force_new_path:

            should_recalculate = True
        elif(
            target_cell != self.last_target_cell
        ):

            should_recalculate = True

        # Do not rebuild A* just because a timer expired.
        # Recalculate only when the path is missing, the target grid
        # cell changed, or movement explicitly requested a new route.
        if not should_recalculate:
            return 
        self.path = (
            self.calculate_path(
                target_x,
                target_y,
                obstacles
            )
        )


        self.path_index = 0

        self.last_path_time = (
                current_time
     )

        self.last_target_cell = (
                target_cell
     )

        self.force_new_path = False


    # =========================================================
    # SHOOT
    # =========================================================

    def shoot(
        self,
        player
    ):

        if not self.alive or not self.active:
            return False

        if self.current_weapon == "knife":
            return False


        if (
            self.is_shooting
            or self.is_reloading
            or self.is_melee
        ):
            return False


        if self.ammo <= 0:

            self.reload()

            return False


        current_time = time.time()


        cooldown = (
            self.weapon_stats[
                self.current_weapon
            ]["fire_cooldown"]
        )


        if (

            current_time -
            self.last_shot_time

            <

            cooldown

        ):

            return False


        if len(
            self.weapon_shoot_frames
        ) == 0:

            return False


        self.ammo -= 1


        self.is_shooting = True

        self.weapon_animation = (
            self.weapon_shoot_frames
        )

        self.current_frame = 0

        self.last_shot_time = (
            current_time
        )


        enemy_center_x = (
            self.x +
            self.width / 2
        )

        enemy_center_y = (
            self.y +
            self.height / 2
        )


        player_center_x = (
            player.x +
            player.width / 2
        )

        player_center_y = (
            player.y +
            player.height / 2
        )


        dx = (
            player_center_x -
            enemy_center_x
        )

        dy = (
            player_center_y -
            enemy_center_y
        )


        distance = math.sqrt(
            dx ** 2 +
            dy ** 2
        )


        if distance == 0:
            return False


        direction_x = (
            dx /
            distance
        )

        direction_y = (
            dy /
            distance
        )


        muzzle_distance = 25


        bullet_x = (

            enemy_center_x

            +

            direction_x *
            muzzle_distance
        )

        bullet_y = (

            enemy_center_y

            +

            direction_y *
            muzzle_distance
        )


        self.pending_shots.append({

            "x": bullet_x,

            "y": bullet_y,

            "target_x": player_center_x,

            "target_y": player_center_y,

            "damage": self.weapon_stats[
                self.current_weapon
            ]["damage"],

            "weapon": self.current_weapon
        })


        return True


    # =========================================================
    # GET PENDING SHOTS
    # =========================================================

    def get_pending_shots(self):

        shots = (
            self.pending_shots[:]
        )

        self.pending_shots.clear()

        return shots


    # =========================================================
    # RELOAD
    # =========================================================

    def reload(self):

        if not self.alive or not self.active:
            return False

        if self.current_weapon == "knife":
            return False


        if (
            self.is_shooting
            or self.is_reloading
            or self.is_melee
        ):
            return False


        if self.ammo >= self.max_ammo:
            return False


        if len(
            self.weapon_reload_frames
        ) == 0:

            self.ammo = (
                self.max_ammo
            )

            return True


        self.is_reloading = True

        self.weapon_animation = (
            self.weapon_reload_frames
        )

        self.current_frame = 0

        return True


    # =========================================================
    # START AUTO RELOAD
    # =========================================================

    def start_auto_reload_if_needed(self):

        if not self.alive or not self.active:
            return

        if self.current_weapon == "knife":
            return


        if self.ammo is None:
            return


        if self.ammo > 0:
            return


        if self.is_reloading:
            return


        if len(
            self.weapon_reload_frames
        ) > 0:

            self.is_reloading = True

            self.weapon_animation = (
                self.weapon_reload_frames
            )

            self.current_frame = 0

        else:

            self.ammo = (
                self.max_ammo
            )


    # =========================================================
    # MELEE ATTACK
    # =========================================================

    def melee_attack(
        self,
        player
    ):

        if not self.alive or not self.active:
            return False

        if (
            self.is_shooting
            or self.is_reloading
            or self.is_melee
        ):
            return False


        current_time = time.time()


        if (

            current_time -
            self.last_melee_time

            <

            self.melee_cooldown

        ):

            return False


        if len(
            self.weapon_melee_frames
        ) == 0:

            return False


        self.is_melee = True

        self.weapon_animation = (
            self.weapon_melee_frames
        )

        self.current_frame = 0


        damage = (
            self.weapon_stats[
                self.current_weapon
            ]["melee_damage"]
        )


        player.take_damage(
            damage
        )


        self.last_melee_time = (
            current_time
        )


        return True


    # =========================================================
    # COMBAT AI
    # =========================================================

    def update_combat(
        self,
        player,
        obstacles=None
    ):

        if not self.alive or not self.active:
            return


        enemy_center_x = (
            self.x +
            self.width / 2
        )

        enemy_center_y = (
            self.y +
            self.height / 2
        )


        player_center_x = (
            player.x +
            player.width / 2
        )

        player_center_y = (
            player.y +
            player.height / 2
        )


        dx = (
            player_center_x -
            enemy_center_x
        )

        dy = (
            player_center_y -
            enemy_center_y
        )


        distance = math.sqrt(
            dx ** 2 +
            dy ** 2
        )


        # =====================================================
        # MELEE PRIORITY
        # =====================================================

        if distance <= self.melee_range:

            # Prevent melee through obstacles.

            if self.has_line_of_sight(
                player,
                obstacles
            ):

                self.melee_attack(
                    player
                )

            return


        # =====================================================
        # KNIFE DOES NOT SHOOT
        # =====================================================

        if self.current_weapon == "knife":

            return


        # =====================================================
        # SHOOT RANGE
        # =====================================================

        shoot_range = (
            self.weapon_stats[
                self.current_weapon
            ]["shoot_range"]
        )


        if distance <= shoot_range:


            # Enemy can ONLY shoot if the player
            # is visible and no obstacle blocks
            # the line.

            if self.has_line_of_sight(
                player,
                obstacles
            ):

                self.shoot(
                    player
                )


    # =========================================================
    # UPDATE WEAPON ANIMATION
    # =========================================================

    def update_weapon_animation(self):

        if len(
            self.weapon_animation
        ) == 0:

            return


        if self.is_melee:

            self.current_frame += (
                self.melee_animation_speed
            )


        elif self.is_reloading:

            self.current_frame += (
                self.reload_animation_speed
            )


        else:

            self.current_frame += (
                self.animation_speed
            )


        if (

            self.current_frame

            >=

            len(
                self.weapon_animation
            )

        ):


            if self.is_shooting:

                self.is_shooting = False

                self.current_frame = 0


                if (

                    self.current_weapon
                    !=
                    "knife"

                    and

                    self.ammo <= 0

                ):

                    self.start_auto_reload_if_needed()

                else:

                    self.weapon_animation = (
                        self.weapon_idle_frames
                    )


            elif self.is_reloading:

                self.is_reloading = False

                self.current_frame = 0


                self.ammo = (
                    self.max_ammo
                )


                self.weapon_animation = (
                    self.weapon_idle_frames
                )


            elif self.is_melee:

                self.is_melee = False

                self.current_frame = 0

                self.weapon_animation = (
                    self.weapon_idle_frames
                )


            else:

                self.current_frame = 0


        if len(
            self.weapon_animation
        ) == 0:

            return


        frame_index = (

            int(
                self.current_frame
            )

            %

            len(
                self.weapon_animation
            )
        )


        self.original_image = (
            self.weapon_animation[
                frame_index
            ]
        )


    # =========================================================
    # UPDATE FEET ANIMATION
    # =========================================================

    def update_feet_animation(self):

        if len(
            self.current_feet_animation
        ) == 0:

            return


        self.feet_frame += (
            self.feet_animation_speed
        )


        if (

            self.feet_frame

            >=

            len(
                self.current_feet_animation
            )

        ):

            self.feet_frame = 0


        frame_index = (

            int(
                self.feet_frame
            )

            %

            len(
                self.current_feet_animation
            )
        )


        self.original_feet_image = (
            self.current_feet_animation[
                frame_index
            ]
        )


    # =========================================================
    # CHECK MOVEMENT COLLISION
    # =========================================================

    def can_move_to(
        self,
        new_x,
        new_y,
        enemies,
        obstacles
    ):

        test_rect = pygame.Rect(

            int(new_x),

            int(new_y),

            self.width,

            self.height
        )


        if obstacles:

            for obstacle in obstacles:

                if test_rect.colliderect(
                    obstacle.rect
                ):

                    return False


        for other in enemies:

            if other is self:
                continue

            if not other.alive:
                continue


            other_rect = pygame.Rect(

                int(other.x),

                int(other.y),

                other.width,

                other.height
            )


            if test_rect.colliderect(
                other_rect
            ):

                return False


        return True


        # =========================================================
# CHECK IF ENEMY IS STUCK
# =========================================================

    def check_if_stuck(self):

     current_time = time.time()


     elapsed = (
        current_time -
        self.last_stuck_check_time
     )


     if elapsed < 0.40:

        return


     moved_distance = math.sqrt(

        (
            self.x -
            self.last_position[0]
        ) ** 2

        +

        (
            self.y -
            self.last_position[1]
        ) ** 2
     )


    # Enemy should have moved but barely moved.
     if moved_distance < 2:

        self.stuck_time += elapsed

     else:

        self.stuck_time = 0


     self.last_position = (
        self.x,
        self.y
     )


     self.last_stuck_check_time = (
        current_time
     )


    # Force a new route.
     if self.stuck_time >= 1.0:

        self.path = []
        self.path_index = 0

        self.force_new_path = True

        self.stuck_time = 0
    
    # =========================================================
    # TRY MOVEMENT WITH WALL SLIDING
    # =========================================================

    def try_move_with_slide(
        self,
        move_x,
        move_y,
        enemies,
        obstacles
    ):
        """Try the requested movement, then slide along obstacles.

        The old movement code could fail both X and Y movement at once
        when the diagonal movement touched an obstacle. This made the
        enemy wait for the stuck timer before recovering.

        We first try the full movement, then X-only, then Y-only.
        If none work, the current path is immediately invalidated.
        """

        # Full movement
        new_x = self.x + move_x
        new_y = self.y + move_y

        if self.can_move_to(
            new_x,
            new_y,
            enemies,
            obstacles
        ):
            self.x = new_x
            self.y = new_y
            return True

        # X-only movement: slide vertically along a wall.
        if abs(move_x) > 0:
            new_x = self.x + move_x

            if self.can_move_to(
                new_x,
                self.y,
                enemies,
                obstacles
            ):
                self.x = new_x
                return True

        # Y-only movement: slide horizontally along a wall.
        if abs(move_y) > 0:
            new_y = self.y + move_y

            if self.can_move_to(
                self.x,
                new_y,
                enemies,
                obstacles
            ):
                self.y = new_y
                return True

        # Nothing worked. Do not wait a full second before
        # requesting a fresh route.
        self.path = []
        self.path_index = 0
        self.force_new_path = True

        return False


    # =========================================================
    # MOVE
    # =========================================================

    def move(
        self,
        player,
        enemies,
        obstacles=None
    ):

        if not self.alive or not self.active:
            return

        self.check_if_stuck()


        if (
            self.is_melee
            or self.is_shooting
            or self.is_reloading
        ):
            return


        enemy_center_x = (
            self.x +
            self.width / 2
        )

        enemy_center_y = (
            self.y +
            self.height / 2
        )


        player_center_x = (
            player.x +
            player.width / 2
        )

        player_center_y = (
            player.y +
            player.height / 2
        )


        dx_to_player = (
            player_center_x -
            enemy_center_x
        )

        dy_to_player = (
            player_center_y -
            enemy_center_y
        )


        player_distance = math.sqrt(
            dx_to_player ** 2 +
            dy_to_player ** 2
        )


        # =====================================================
        # GUN ENEMIES:
        # STOP ONLY IF THEY HAVE A CLEAR LINE OF SIGHT
        # AND ARE CLOSE ENOUGH.
        # =====================================================

        if self.current_weapon != "knife":

            # Activation happens at 80 px in main.py.
            # Keep a smaller stop distance so an activated enemy
            # actually chases before stopping.
            stop_distance = 60

            visible = (
                self.has_line_of_sight(
                    player,
                    obstacles
                )
            )


            if (
                visible
                and
                player_distance <= stop_distance
            ):

                self.path = []
                self.path_index = 0

                self.current_feet_animation = (
                    self.feet_idle_frames
                )

                self.weapon_animation = (
                    self.weapon_idle_frames
                )

                return


        # =====================================================
        # UPDATE A* PATH
        # =====================================================

        self.update_path(
            player,
            obstacles
        )


        # =====================================================
        # CHOOSE MOVEMENT TARGET
        # =====================================================

        target_x = player_center_x
        target_y = player_center_y


        if len(self.path) > 0:

            # Skip reached waypoints.
            while (
                self.path_index <
                len(self.path)
            ):

                waypoint_x, waypoint_y = (
                    self.path[
                        self.path_index
                    ]
                )

                waypoint_distance = math.sqrt(
                    (
                        waypoint_x -
                        enemy_center_x
                    ) ** 2
                    +
                    (
                        waypoint_y -
                        enemy_center_y
                    ) ** 2
                )

                if waypoint_distance < 8:
                    self.path_index += 1
                else:
                    break


            # -------------------------------------------------
            # WAYPOINT LOOK-AHEAD
            # -------------------------------------------------
            # If a later waypoint is directly reachable, skip
            # the unnecessary intermediate waypoint(s).
            #
            # This reduces the small "zig-zag" movement caused
            # by following every 32 px grid cell.
            while (
                self.path_index + 1 <
                len(self.path)
            ):

                next_x, next_y = (
                    self.path[
                        self.path_index + 1
                    ]
                )

                clear_x = (
                    next_x -
                    self.width / 2
                )

                clear_y = (
                    next_y -
                    self.height / 2
                )

                if self.can_move_to(
                    clear_x,
                    clear_y,
                    enemies,
                    obstacles
                ):

                    self.path_index += 1

                else:
                    break


            if (
                self.path_index <
                len(self.path)
            ):

                target_x, target_y = (
                    self.path[
                        self.path_index
                    ]
                )


        # =====================================================
        # MOVE TOWARD CURRENT WAYPOINT
        # =====================================================

        dx = (
            target_x -
            enemy_center_x
        )

        dy = (
            target_y -
            enemy_center_y
        )


        distance = math.sqrt(
            dx ** 2 +
            dy ** 2
        )


        if distance == 0:
            return


        move_x = (
            dx /
            distance
        ) * self.speed

        move_y = (
            dy /
            distance
        ) * self.speed


        self.current_feet_animation = (
            self.feet_walk_frames
        )

        self.weapon_animation = (
            self.weapon_move_frames
        )


        # =====================================================
        # COLLISION-AWARE MOVEMENT
        # =====================================================

        moved = self.try_move_with_slide(
            move_x,
            move_y,
            enemies,
            obstacles
        )

        if not moved:
            # A new path will be requested on the next update.
            return


        self.rect.topleft = (
            int(self.x),
            int(self.y)
        )


    # =========================================================
    # DRAW
    # =========================================================

    def draw(
        self,
        screen,
        player
    ):

        if not self.alive:
            return


        self.update_weapon_animation()
        self.update_feet_animation()


        center_x = (
            self.x +
            self.width // 2
        )

        center_y = (
            self.y +
            self.height // 2
        )


        # =====================================================
        # FACE PLAYER
        # =====================================================

        player_center_x = (
            player.x +
            player.width // 2
        )

        player_center_y = (
            player.y +
            player.height // 2
        )


        dx = (
            player_center_x -
            center_x
        )

        dy = (
            player_center_y -
            center_y
        )


        angle = math.degrees(
            math.atan2(
                -dy,
                dx
            )
        )


        # =====================================================
        # FEET
        # =====================================================

        if (
            self.original_feet_image
            is not None
        ):


            rotated_feet = (
                pygame.transform.rotate(
                    self.original_feet_image,
                    angle
                )
            )


            feet_rect = (
                rotated_feet.get_rect(
                    center=(
                        center_x,
                        center_y
                    )
                )
            )


            screen.blit(
                rotated_feet,
                feet_rect.topleft
            )


        # =====================================================
        # BODY / WEAPON
        # =====================================================

        if (
            self.original_image
            is not None
        ):


            rotated_weapon = (
                pygame.transform.rotate(
                    self.original_image,
                    angle
                )
            )


            weapon_rect = (
                rotated_weapon.get_rect(
                    center=(
                        center_x,
                        center_y
                    )
                )
            )


            screen.blit(
                rotated_weapon,
                weapon_rect.topleft
            )


        # =====================================================
        # HEALTH BAR
        # =====================================================

        pygame.draw.rect(
            screen,
            (100, 100, 100),
            (
                self.x,
                self.y - 12,
                self.width,
                6
            )
        )


        health_width = max(
            0,
            (
                self.health /
                30
            )
            *
            self.width
        )


        pygame.draw.rect(
            screen,
            (0, 255, 0),
            (
                self.x,
                self.y - 12,
                health_width,
                6
            )
        )


    # =========================================================
    # BULLET COLLISION
    # =========================================================

    def check_collision(
        self,
        bullet
    ):

        if not self.alive:
            return False


        return self.rect.collidepoint(
            bullet.x,
            bullet.y
        )


    # =========================================================
    # PLAYER COLLISION
    # =========================================================

    def check_player_collision(
        self,
        player
    ):

        if not self.alive:
            return False


        return self.rect.colliderect(
            player.rect
        )


    # =========================================================
    # OLD ATTACK METHOD
    # =========================================================

    def attack(
        self,
        player
    ):

        self.melee_attack(
            player
        )