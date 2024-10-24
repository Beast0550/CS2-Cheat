import requests
import pyMeow as pm
import pymem
import win32api, win32con
import threading
import time
import random

# Settings
radius = 15
shooting_delay = 0.2
attack_teammates = False
draw_circle = True
draw_rectangles = True
draw_skeletons = True

aim_target = "body"  # Options: "head" or "body"
keybinding = "X"  # Set your keybinding
keybinding_code = ord(keybinding.upper())  # Convert key to virtual key code

random_factor_x = 5
random_factor_y = 5

print(f"Circle Radius = {radius}")
print("Aim Target = " + aim_target)
print("Keybinding = " + keybinding)

class Offsets:
    m_pBoneArray = 496
    m_iShotsFired = 0x23E4
    m_aimPunchAngle = 0x1584

class Colors:
    red = pm.get_color("red")
    black = pm.get_color("black")
    green = pm.get_color("green")
    white = pm.get_color("white")


class Entity:
    def __init__(self, ptr, pawn_ptr, proc):
        self.ptr = ptr
        self.pawn_ptr = pawn_ptr
        self.proc = proc
        self.pos2d = None
        self.head_pos2d = None

    @property
    def name(self):
        return pm.r_string(self.proc, self.ptr + Offsets.m_iszPlayerName)

    @property
    def health(self):
        return pm.r_int(self.proc, self.pawn_ptr + Offsets.m_iHealth)

    @property
    def team(self):
        return pm.r_int(self.proc, self.pawn_ptr + Offsets.m_iTeamNum)

    @property
    def pos(self):
        return pm.r_vec3(self.proc, self.pawn_ptr + Offsets.m_vOldOrigin)
    
    @property
    def dormant(self):
        return pm.r_bool(self.proc, self.pawn_ptr + Offsets.m_bDormant)

    def bone_pos(self, bone):
        game_scene = pm.r_int64(self.proc, self.pawn_ptr + Offsets.m_pGameSceneNode)
        bone_array_ptr = pm.r_int64(self.proc, game_scene + Offsets.m_pBoneArray)
        return pm.r_vec3(self.proc, bone_array_ptr + bone * 32)
    
    def wts(self, view_matrix):
        try:
            self.pos2d = pm.world_to_screen(view_matrix, self.pos, 1)
            self.head_pos2d = pm.world_to_screen(view_matrix, self.bone_pos(6), 1)
        except:
            return False
        return True
    

class CS2Esp:
    def __init__(self):
        self.proc = pm.open_process("cs2.exe")
        self.mod = pm.get_module(self.proc, "client.dll")["base"]
        self.localTeam = None
        offsets_name = ["dwViewMatrix", "dwEntityList", "dwLocalPlayerController", "dwLocalPlayerPawn"]
        offsets = requests.get("https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/offsets.json").json()
        [setattr(Offsets, k, offsets["client.dll"][k]) for k in offsets_name]

        client_dll_name = {
            "m_iIDEntIndex": "C_CSPlayerPawnBase",
            "m_hPlayerPawn": "CCSPlayerController",
            "m_fFlags": "C_BaseEntity",
            "m_iszPlayerName": "CBasePlayerController",
            "m_iHealth": "C_BaseEntity",
            "m_iTeamNum": "C_BaseEntity",
            "m_vOldOrigin": "C_BasePlayerPawn",
            "m_pGameSceneNode": "C_BaseEntity",
            "m_bDormant": "CGameSceneNode",
        }
        clientDll = requests.get("https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/client_dll.json").json()
        [setattr(Offsets, k, clientDll["client.dll"]["classes"][client_dll_name[k]]["fields"][k]) for k in client_dll_name]

    def it_entities(self):
        ent_list = pm.r_int64(self.proc, self.mod + Offsets.dwEntityList)
        local = pm.r_int64(self.proc, self.mod + Offsets.dwLocalPlayerController)
        for i in range(1, 65):
            try:
                entry_ptr = pm.r_int64(self.proc, ent_list + (8 * (i & 0x7FFF) >> 9) + 16)
                controller_ptr = pm.r_int64(self.proc, entry_ptr + 120 * (i & 0x1FF))

                if controller_ptr == local:
                    self.localTeam = pm.r_int(self.proc, local + Offsets.m_iTeamNum)
                    continue
                
                controller_pawn_ptr = pm.r_int64(self.proc, controller_ptr + Offsets.m_hPlayerPawn)
                list_entry_ptr = pm.r_int64(self.proc, ent_list + 0x8 * ((controller_pawn_ptr & 0x7FFF) >> 9) + 16)
                pawn_ptr = pm.r_int64(self.proc, list_entry_ptr + 120 * (controller_pawn_ptr & 0x1FF))
            except:
                continue

            yield Entity(controller_ptr, pawn_ptr, self.proc)

    
    def triggerBot(self):
        while True:
            if win32api.GetAsyncKeyState(keybinding_code):
                try:
                    player = pm.r_int64(self.proc, self.mod + Offsets.dwLocalPlayerPawn)
                    entityId = pm.r_int(self.proc, player + Offsets.m_iIDEntIndex)

                    if entityId > 0:
                        entList = pm.r_int64(self.proc, self.mod + Offsets.dwEntityList)
                        entEntry = pm.r_int64(self.proc, entList + 0x8 * (entityId >> 9) + 0x10)
                        entity = pm.r_int64(self.proc, entEntry + 120 * (entityId & 0x1FF))
                        entityTeam = pm.r_int(self.proc, entity + Offsets.m_iTeamNum)
                        playerTeam = pm.r_int(self.proc, player + Offsets.m_iTeamNum)

                        if not attack_teammates and playerTeam == entityTeam: 
                            continue
                        
                        entityHp = pm.r_int(self.proc, entity + Offsets.m_iHealth)
                        if entityHp > 0:
                            #time.sleep(0.005)
                            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
                            time.sleep(0.005)
                            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)
                            #M4A1-S
                            if aim_target == "body":
                                time.sleep(shooting_delay - shooting_delay / 1.5)
                            else:
                                time.sleep(shooting_delay)
                            #time.sleep(1.4) #SNIPER
                            #time.sleep(0.08)#AUTO-SNIPER
                except:
                    pass


    def aimBot(self, target_list, radius, aim_mode_distance):
        if not target_list:
            return
        
        center_x = win32api.GetSystemMetrics(0) // 2
        center_y = win32api.GetSystemMetrics(1) // 2
        
        screen_radius = radius / 100.0 * min(center_x, center_y)
        closest_target = None
        closest_dist = float('inf')
        
        for target in target_list:
            if not attack_teammates and target['team'] == self.localTeam:
                continue
            
            head_x, head_y = target['head_pos'][0], target['head_pos'][1]
            center_mass_x, center_mass_y = (target['head_pos'][0] + target['pos'][0]) / 2, (target['head_pos'][1] + target['pos'][1]) / 2
            midpoint_x = (head_x + center_mass_x) / 2
            midpoint_y = (head_y + center_mass_y) / 2
            adjusted_y = midpoint_y - (center_mass_y - head_y) * 0.1

            if aim_target == "head":
                dist = ((target['head_pos'][0] - center_x) ** 2 + (target['head_pos'][1] - center_y) ** 2) ** 0.5
                if dist < screen_radius and dist < closest_dist:
                    closest_target = target['head_pos']
                    closest_dist = dist
            else:
                dist = ((midpoint_x - center_x) ** 2 + (adjusted_y - center_y) ** 2) ** 0.5
                if dist < screen_radius and dist < closest_dist:
                    closest_target = {'x': midpoint_x, 'y': adjusted_y}
                    closest_dist = dist

        if closest_target:
            if aim_target == "head":
                target_x, target_y = closest_target
            else:
                target_x, target_y = closest_target['x'], closest_target['y']
                
            if win32api.GetAsyncKeyState(keybinding_code):
                dx = target_x - center_x
                dy = target_y - center_y

                random_x = random.uniform(-random_factor_x, random_factor_x)
                random_y = random.uniform(-random_factor_y, random_factor_y)

                step_x = dx * 0.5 + random_x
                step_y = dy * 0.5 + random_y

                win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, int(step_x), int(step_y))

    
    def run(self):
        pm.overlay_init("Counter-Strike 2", fps=144)
        client = pm.get_module(self.proc, "client.dll")["base"]
        center_x = win32api.GetSystemMetrics(0) // 2
        center_y = win32api.GetSystemMetrics(1) // 2
        toggle_delay = 0.3
        last_toggle_time = time.time()
        
        while pm.overlay_loop():
            view_matrix = pm.r_floats(self.proc, self.mod + Offsets.dwViewMatrix, 16)
            target_list = []
            global aim_target
            
            if win32api.GetAsyncKeyState(ord('O')) and time.time() - last_toggle_time > toggle_delay:
                if aim_target == "head":
                    aim_target = "body"
                else:
                    aim_target = "head"
                last_toggle_time = time.time()

            pm.begin_drawing()
            pm.draw_fps(0, 0)
            pm.draw_text(str(aim_target), 0, 20, 20, Colors.white)
            #Draw Circle
            if draw_circle:
                screen_radius = radius / 100.0 * min(center_x, center_y)
                pm.draw_ellipse_lines(center_x, center_y, screen_radius, screen_radius, Colors.white)
            
            for ent in self.it_entities():
                if ent.wts(view_matrix) and ent.health > 0 and not ent.dormant:
                    if ent.team != self.localTeam:
                        color = Colors.red
                    else:
                        color = Colors.green
                    head = ent.pos2d["y"] - ent.head_pos2d["y"]
                    width = head / 2
                    center = width / 2
            
                    #Draw Rectangle
                    if draw_rectangles:
                        pm.draw_rectangle_lines(
                            ent.head_pos2d["x"] - center,
                            ent.head_pos2d["y"] - center / 2,
                            width,
                            head + center / 2,
                            color,
                            3
                        )
                    #Draw Skeleton
                    if draw_skeletons:
                        try:
                                cou = pm.world_to_screen(view_matrix, ent.bone_pos(5), 1)
                                shoulderR = pm.world_to_screen(view_matrix, ent.bone_pos(8), 1)
                                shoulderL = pm.world_to_screen(view_matrix, ent.bone_pos(13), 1)
                                brasR = pm.world_to_screen(view_matrix, ent.bone_pos(9), 1)
                                brasL = pm.world_to_screen(view_matrix, ent.bone_pos(14), 1)
                                handR = pm.world_to_screen(view_matrix, ent.bone_pos(11), 1)
                                handL = pm.world_to_screen(view_matrix, ent.bone_pos(16), 1)
                                waist = pm.world_to_screen(view_matrix, ent.bone_pos(0), 1)
                                kneesR = pm.world_to_screen(view_matrix, ent.bone_pos(23), 1)
                                kneesL = pm.world_to_screen(view_matrix, ent.bone_pos(26), 1)
                                feetR = pm.world_to_screen(view_matrix, ent.bone_pos(24), 1)
                                feetL = pm.world_to_screen(view_matrix, ent.bone_pos(27), 1)
                                pm.draw_line(cou["x"], cou["y"], shoulderR["x"], shoulderR["y"], color, 1)
                                pm.draw_line(cou["x"], cou["y"], shoulderL["x"], shoulderL["y"], color, 1)
                                pm.draw_line(brasL["x"], brasL["y"], shoulderL["x"], shoulderL["y"], color, 1)
                                pm.draw_line(brasR["x"], brasR["y"], shoulderR["x"], shoulderR["y"], color, 1)
                                pm.draw_line(brasR["x"], brasR["y"], handR["x"], handR["y"], color, 1)
                                pm.draw_line(brasL["x"], brasL["y"], handL["x"], handL["y"], color, 1)
                                pm.draw_line(cou["x"], cou["y"], waist["x"], waist["y"], color, 1)
                                pm.draw_line(kneesR["x"], kneesR["y"], waist["x"], waist["y"], color, 1)
                                pm.draw_line(kneesL["x"], kneesL["y"], waist["x"], waist["y"], color, 1)
                                pm.draw_line(kneesL["x"], kneesL["y"], feetL["x"], feetL["y"], color, 1)
                                pm.draw_line(kneesR["x"], kneesR["y"], feetR["x"], feetR["y"], color, 1)
                        except:
                            pass
                        
                    target_list.append({
                        "pos": [ent.pos2d["x"], ent.pos2d["y"]],
                        "head_pos": [ent.head_pos2d["x"], ent.head_pos2d["y"]],
                        "deltaZ": ent.head_pos2d["y"] - ent.pos2d["y"],
                        "team": ent.team
                    })


            self.aimBot(target_list, radius, aim_mode_distance=0)
            pm.end_drawing()

esp = CS2Esp()

#Threading The Script
print()
threading.Thread(target=esp.triggerBot).start()
threading.Thread(target=esp.run).start()
print("Threading Functions")
