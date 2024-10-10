import requests
import pyMeow as pm
import win32api, win32con
import threading
import time

print("Settings Classes...")

radius=15
print("Radius = " + str(radius))


class Offsets:
    m_pBoneArray = 496


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
        time.sleep(0.5)
        print("Hooking...")
        self.proc = pm.open_process("cs2.exe")
        self.mod = pm.get_module(self.proc, "client.dll")["base"]
        time.sleep(2.5)
        print("Attached!")
        time.sleep(0.1)
        print("Updating Offsets...")
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
        time.sleep(1.5)
        print("Offsets up to date!")
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
            if win32api.GetAsyncKeyState(0xC0):
                try:
                    player = pm.r_int64(self.proc, self.mod + Offsets.dwLocalPlayerPawn)
                    entityId = pm.r_int(self.proc, player + Offsets.m_iIDEntIndex)

                    if entityId > 0:
                        entList = pm.r_int64(self.proc, self.mod + Offsets.dwEntityList)
                        entEntry = pm.r_int64(self.proc, entList + 0x8 * (entityId >> 9) + 0x10)
                        entity = pm.r_int64(self.proc, entEntry + 120 * (entityId & 0x1FF))
                        entityTeam = pm.r_int(self.proc, entity + Offsets.m_iTeamNum)
                        playerTeam = pm.r_int(self.proc, player + Offsets.m_iTeamNum)

                        
                        #if playerTeam == entityTeam: continue
                        entityHp = pm.r_int(self.proc, entity + Offsets.m_iHealth)
                        if entityHp > 0:
                            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
                            time.sleep(0.005)
                            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)
                            time.sleep(0.08)#M4A1-S
                            #SNIPER time.sleep(1.4)
                except:
                    pass


    def aimBot(self, target_list, radius, aim_mode_distance):
        if not target_list:
            return
        
        center_x = win32api.GetSystemMetrics(0) // 2
        center_y = win32api.GetSystemMetrics(1) // 2
        
        if radius == 0:
            closest_target = None
            closest_dist = float('inf')

            for target in target_list:
                # Check if the target's team is different from the local team
                #if target['team'] == self.localTeam:
                    #continue  # Skip if it's on the same team
                
                dist = ((target['head_pos'][0] - center_x) ** 2 + (target['head_pos'][1] - center_y) ** 2) ** 0.5
                if dist < closest_dist:
                    closest_target = target['head_pos']
                    closest_dist = dist 

        else:
            screen_radius = radius / 100.0 * min(center_x, center_y)
            closest_target = None
            closest_dist = float('inf')

            if aim_mode_distance == 1:
                target_with_max_deltaZ = None
                max_deltaZ = -float('inf')

                for target in target_list:
                    # Check if the target's team is different from the local team
                    #if target['team'] == self.localTeam:
                        #continue  # Skip if it's on the same team
                    
                    dist = ((target['head_pos'][0] - center_x) ** 2 + (target['head_pos'][1] - center_y) ** 2) ** 0.5

                    if dist < screen_radius and target['deltaZ'] > max_deltaZ:
                        max_deltaZ = target['deltaZ']
                        target_with_max_deltaZ = target

                closest_target = target_with_max_deltaZ['head_pos'] if target_with_max_deltaZ else None

            else:
                for target in target_list:
                    # Check if the target's team is different from the local team
                    #if target['team'] == self.localTeam:
                        #continue  # Skip if it's on the same team
                    
                    dist = ((target['head_pos'][0] - center_x) ** 2 + (target['head_pos'][1] - center_y) ** 2) ** 0.5

                    if dist < screen_radius and dist < closest_dist:
                        closest_target = target['head_pos']
                        closest_dist = dist

        if closest_target:
            target_x, target_y = closest_target
            if win32api.GetAsyncKeyState(0xC0):
                dx = target_x - center_x
                dy = target_y - center_y + 18
                step_x = dx * 0.5  # Slow down movement by adjusting the step size
                step_y = dy * 0.5
                
                if abs(dx) > 1 or abs(dy) > 1:
                    win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, int(step_x), int(step_y), 0, 0)
    
    def run(self):
        pm.overlay_init("Counter-Strike 2", fps=144)
        #mem = pm.open_process("cs2.exe")
        client = pm.get_module(self.proc, "client.dll")["base"]
        center_x = win32api.GetSystemMetrics(0) // 2
        center_y = win32api.GetSystemMetrics(1) // 2
        while pm.overlay_loop():
            view_matrix = pm.r_floats(self.proc, self.mod + Offsets.dwViewMatrix, 16)
            target_list = []
            pm.begin_drawing()
            pm.draw_fps(0, 0)

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

                    #Rectangle
                    pm.draw_rectangle_lines(
                        ent.head_pos2d["x"] - center,
                        ent.head_pos2d["y"] - center / 2,
                        width,
                        head + center / 2,
                        color,
                        3
                    )
                    #Skeleton
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
                        "team": ent.team  # Add this line to include team info
                    })


            self.aimBot(target_list, radius, aim_mode_distance=0)
            pm.end_drawing()

esp = CS2Esp()

# Run both aimbot and trigger bot simultaneously
threading.Thread(target=esp.triggerBot).start()
threading.Thread(target=esp.run).start()
