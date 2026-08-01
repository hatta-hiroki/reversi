import os
import sys
import random
import json
import threading
import pygame
import tkinter as tk
from PIL import ImageTk, Image
from tkinter import messagebox

# プレイヤーを示す値
YOU = 1
COM = 2

# 色の設定
YOUR_COLOR = "black"        # あなたの石の色(初期値)
COM_COLOR = "white"         # 相手の石の色(初期値)

# レイアウト設定
CANVAS_SIZE = 400           # 盤面サイズ
BOARD_COLOR = "green"       # 盤面の背景色
NUM_SQUARE = 8              # 横方向・縦方向のマスの数
INFO_HEIGHT = 40            # 上部UI設定
INFO_BG_COLOR= "#e6f0ff"  # 上部UIの背景色
INFO_TEXT_COLOR = "black"   # 上部UIの文字色

#ジャンケン設定
ROCK, SCISSORS, PAPER = "rock", "scissors", "paper"
RESULT_DISPLAY_TIME = 2000  # ジャンケン結果表示タイマー(ms)

# 盤面の評価重みテーブル(デフォルト)
DEFAULT_EVAL_WEIGHTS = [
    [ 30, -12,  0, -1, -1,  0, -12,  30],
    [-12, -15, -3, -3, -3, -3, -15, -12],
    [  0,  -3,  0, -1, -1,  0,  -3,   0],
    [ -1,  -3, -1, -1, -1, -1,  -3,  -1],
    [ -1,  -3, -1, -1, -1, -1,  -3,  -1],
    [  0,  -3,  0, -1, -1,  0,  -3,   0],
    [-12, -15, -3, -3, -3, -3, -15, -12],
    [ 30, -12,  0, -1, -1,  0, -12,  30],
]

# 学習済み重みファイルパス
LEARNED_WEIGHTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "learned_weights.json")

# 学習済み重みの読み込み
def load_learned_weights():
    if os.path.exists(LEARNED_WEIGHTS_PATH):
        try:
            with open(LEARNED_WEIGHTS_PATH, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
    return None

# 学習済み重みの保存
def save_learned_weights(weights):
    try:
        with open(LEARNED_WEIGHTS_PATH, "w") as f:
            json.dump(weights, f, indent=2)
    except (IOError, OSError) as e:
        print(f"Warning: Could not save learned weights: {e}")

# 難易度設定
DIFFICULTY_BEGINNER = 1   # 初級: depth=1
DIFFICULTY_MEDIUM = 3     # 中級: depth=3
DIFFICULTY_ADVANCED = 5   # 上級: depth=5

#pygameのミキサーを初期化
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.mixer.init()

# exe化した際のパス指定
def resource_path(relative_path):
    try:
        # PyInstallerで実行されている場合、一時フォルダのパスを取得
        base_path = sys._MEIPASS
    except Exception:
        # 通常実行時はスクリプトの階層
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

IMG_DIR = resource_path("image")
SOUND_DIR = resource_path("sounds")

# ガイド表示
SHOW_GUIDE = True

# 音声ファイル読み込み
def safe_load_sound(filename):
    path = os.path.join(SOUND_DIR, filename)
    if not os.path.exists(path):
        print(f"Warning: {filename} not found at {path}")
        return None
    try:
        return pygame.mixer.Sound(path)
    except pygame.error:
        print(f"Error: Could not load sound {filename}")
        return None

sound_put = safe_load_sound("put.mp3")
sound_win = safe_load_sound("win.mp3")
sound_lose = safe_load_sound("lose.mp3")

# BGMの再生設定
bgm_path = os.path.join(SOUND_DIR, "bgm.mp3")
if os.path.exists(bgm_path):
    pygame.mixer.music.load(bgm_path)
    pygame.mixer.music.set_volume(0.2)
    pygame.mixer.music.play(-1)

# ===== Minimax AI エンジン (GUIに依存しない純粋なロジック) =====

def get_board_colors(board):
    """GUI盤面から色情報のみの2D配列を作成する"""
    result = [[None] * NUM_SQUARE for _ in range(NUM_SQUARE)]
    for y in range(NUM_SQUARE):
        for x in range(NUM_SQUARE):
            cell = board[y][x]
            if cell is not None:
                result[y][x] = cell["color"]
    return result


def sim_get_reverse_list(board_colors, x, y, player_color, opponent_color):
    """シミュレーション用: ひっくり返せる石のリストを取得"""
    if board_colors[y][x] is not None:
        return []

    reverse_list = []
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            tx, ty = x + dx, y + dy
            temp = []
            while 0 <= tx < NUM_SQUARE and 0 <= ty < NUM_SQUARE:
                cell = board_colors[ty][tx]
                if cell is None:
                    break
                if cell == opponent_color:
                    temp.append((tx, ty))
                elif cell == player_color:
                    reverse_list.extend(temp)
                    break
                else:
                    break
                tx += dx
                ty += dy
    return reverse_list


def sim_get_placable_list(board_colors, player_color, opponent_color):
    """シミュレーション用: 置ける場所のリストを取得"""
    lst = []
    for y in range(NUM_SQUARE):
        for x in range(NUM_SQUARE):
            if board_colors[y][x] is None:
                if sim_get_reverse_list(board_colors, x, y, player_color, opponent_color):
                    lst.append((x, y))
    return lst


def sim_place(board_colors, x, y, player_color, opponent_color):
    """シミュレーション用: 石を置いてひっくり返した新しい盤面を返す"""
    new_board = [row[:] for row in board_colors]
    reverse_list = sim_get_reverse_list(new_board, x, y, player_color, opponent_color)
    new_board[y][x] = player_color
    for rx, ry in reverse_list:
        new_board[ry][rx] = player_color
    return new_board


def evaluate_board(board_colors, com_color, you_color, weights):
    """盤面を評価する (COMから見たスコア)"""
    score = 0
    com_count = 0
    you_count = 0
    empty_count = 0

    for y in range(NUM_SQUARE):
        for x in range(NUM_SQUARE):
            cell = board_colors[y][x]
            if cell == com_color:
                score += weights[y][x]
                com_count += 1
            elif cell == you_color:
                score -= weights[y][x]
                you_count += 1
            else:
                empty_count += 1

    # モビリティ(手数)の評価
    com_moves = len(sim_get_placable_list(board_colors, com_color, you_color))
    you_moves = len(sim_get_placable_list(board_colors, you_color, com_color))
    score += (com_moves - you_moves) * 2

    # 終盤は石の数を重視
    total_stones = com_count + you_count
    if total_stones > 50:
        score += (com_count - you_count) * 3

    return score


def minimax(board_colors, depth, alpha, beta, maximizing, com_color, you_color, weights):
    """Minimax with alpha-beta pruning"""
    if maximizing:
        current_color = com_color
        opponent_color = you_color
    else:
        current_color = you_color
        opponent_color = com_color

    placable = sim_get_placable_list(board_colors, current_color, opponent_color)

    # 終端条件: 深さ0またはゲーム終了
    if depth == 0:
        return evaluate_board(board_colors, com_color, you_color, weights), None

    if not placable:
        # パス: 相手のターンを確認
        opponent_placable = sim_get_placable_list(board_colors, opponent_color, current_color)
        if not opponent_placable:
            # 両者置けない = ゲーム終了
            return evaluate_board(board_colors, com_color, you_color, weights), None
        # パスして相手のターン
        score, _ = minimax(board_colors, depth - 1, alpha, beta,
                           not maximizing, com_color, you_color, weights)
        return score, None

    best_move = None

    if maximizing:
        max_eval = float('-inf')
        for x, y in placable:
            new_board = sim_place(board_colors, x, y, current_color, opponent_color)
            eval_score, _ = minimax(new_board, depth - 1, alpha, beta,
                                    False, com_color, you_color, weights)
            if eval_score > max_eval:
                max_eval = eval_score
                best_move = (x, y)
            alpha = max(alpha, eval_score)
            if beta <= alpha:
                break
        return max_eval, best_move
    else:
        min_eval = float('inf')
        for x, y in placable:
            new_board = sim_place(board_colors, x, y, current_color, opponent_color)
            eval_score, _ = minimax(new_board, depth - 1, alpha, beta,
                                    True, com_color, you_color, weights)
            if eval_score < min_eval:
                min_eval = eval_score
                best_move = (x, y)
            beta = min(beta, eval_score)
            if beta <= alpha:
                break
        return min_eval, best_move


# ===== 自己学習エンジン =====

def self_play_game(weights, epsilon=0.1):
    """GUIなしでCOM vs COMの1ゲームを実行し、各プレイヤーが置いた場所を記録"""
    board = [[None] * NUM_SQUARE for _ in range(NUM_SQUARE)]
    mid = NUM_SQUARE // 2

    # 初期配置 (blackが先手)
    board[mid - 1][mid - 1] = "white"
    board[mid][mid] = "white"
    board[mid - 1][mid] = "black"
    board[mid][mid - 1] = "black"

    black_color = "black"
    white_color = "white"
    current_color = black_color
    opponent_color = white_color

    black_moves = []
    white_moves = []
    pass_count = 0

    while pass_count < 2:
        placable = sim_get_placable_list(board, current_color, opponent_color)

        if not placable:
            pass_count += 1
            current_color, opponent_color = opponent_color, current_color
            continue

        pass_count = 0

        # epsilon-greedy: 探索多様性のためにランダムな手を選ぶことがある
        if random.random() < epsilon:
            best_move = random.choice(placable)
        else:
            # depth=2 で探索 (学習速度と品質のバランス)
            _, best_move = minimax(board, 2, float('-inf'), float('inf'),
                                   True, current_color, opponent_color, weights)

            if best_move is None:
                best_move = random.choice(placable)

        x, y = best_move
        board = sim_place(board, x, y, current_color, opponent_color)

        if current_color == black_color:
            black_moves.append((x, y))
        else:
            white_moves.append((x, y))

        current_color, opponent_color = opponent_color, current_color

    # 石数を計算
    black_count = sum(1 for y in range(NUM_SQUARE) for x in range(NUM_SQUARE) if board[y][x] == black_color)
    white_count = sum(1 for y in range(NUM_SQUARE) for x in range(NUM_SQUARE) if board[y][x] == white_color)

    return black_count, white_count, black_moves, white_moves


def run_self_learning(num_games=100, progress_callback=None):
    """自己学習を実行し、重みテーブルを更新する"""
    learned = load_learned_weights()
    if learned is None:
        weights = [row[:] for row in DEFAULT_EVAL_WEIGHTS]
    else:
        weights = [row[:] for row in learned]

    learning_rate = 0.5
    weight_min = -50.0
    weight_max = 50.0

    for game_idx in range(num_games):
        black_count, white_count, black_moves, white_moves = self_play_game(weights, epsilon=0.1)

        # 勝者の手の位置の重みを増加、敗者の手の位置の重みを減少
        if black_count > white_count:
            winner_moves = black_moves
            loser_moves = white_moves
        elif white_count > black_count:
            winner_moves = white_moves
            loser_moves = black_moves
        else:
            # 引き分けの場合は更新しない
            if progress_callback:
                progress_callback(game_idx + 1, num_games)
            continue

        for x, y in winner_moves:
            weights[y][x] = min(weight_max, weights[y][x] + learning_rate)
        for x, y in loser_moves:
            weights[y][x] = max(weight_min, weights[y][x] - learning_rate)

        if progress_callback:
            progress_callback(game_idx + 1, num_games)

    # 重みを保存
    save_learned_weights(weights)
    return weights

window = tk.Tk()
window.title("reversi")
window.geometry("700x500")

# 難易度の状態変数(tkinter IntVar は後で初期化)
difficulty_var = None

# ジャンケンロジック
def open_janken():
    janken_win = tk.Toplevel(window)
    janken_win.title("ジャンケン")
    janken_win.geometry("360x360")

    result_label = tk.Label(janken_win, text="", font=("Arial", 16))
    result_label.pack(pady=10)

    # 画像を保持するリスト
    janken_win.images = []

    janken_win.protocol("WM_DELETE_WINDOW", lambda: window.destroy())

    def load_image(path):
        path = os.path.normpath(path)
        img = Image.open(path).resize((80, 80))
        photo = ImageTk.PhotoImage(img)
        janken_win.images.append(photo)
        return photo

    rock_img = load_image(os.path.join(IMG_DIR, "rock.png"))
    scissors_img = load_image(os.path.join(IMG_DIR, "scissors.png"))
    paper_img = load_image(os.path.join(IMG_DIR, "paper.png"))

    # UI構成
    hand_frame = tk.Frame(janken_win)
    hand_frame.pack(pady=10)
    tk.Label(hand_frame, text="YOU", font=("Arial", 12)).grid(row=0, column=0, padx=40)
    tk.Label(hand_frame, text="COM", font=("Arial", 12)).grid(row=0, column=1, padx=40)

    you_hand_label = tk.Label(hand_frame)
    you_hand_label.grid(row=1, column=0)
    com_hand_label = tk.Label(hand_frame)
    com_hand_label.grid(row=1, column=1)

    def clear_hands():
        you_hand_label.config(image="")
        com_hand_label.config(image="")
        result_label.config(text="あいこで...")

    # ジャンケン判定
    def judge(player_hand):
        com_hand = random.choice([ROCK, SCISSORS, PAPER])
        imgs = {ROCK: rock_img, SCISSORS: scissors_img, PAPER: paper_img}
        you_hand_label.config(image=imgs[player_hand])
        com_hand_label.config(image=imgs[com_hand])

        # 勝敗判定
        if player_hand == com_hand:
            result = "あいこ"
            janken_win.after(1000, clear_hands)
            result_label.config(text=result)
            return
        
        if (player_hand == ROCK and com_hand == SCISSORS) or \
           (player_hand == SCISSORS and com_hand == PAPER) or \
           (player_hand == PAPER and com_hand == ROCK):
            result = "YOU WIN"
        else:
            result = "YOU LOSE"

        result_label.config(text=f"YOU : {player_hand}\nCOM : {com_hand}\n\n{result}")

        # ジャンケン結果表示
        if result == "YOU WIN":
            janken_win.after(RESULT_DISPLAY_TIME, lambda: finish_janken(True))
        elif result == "YOU LOSE":
            janken_win.after(RESULT_DISPLAY_TIME, lambda: finish_janken(False))

    # ジャンケン後処理
    def finish_janken(you_win):
        global YOUR_COLOR, COM_COLOR

        if you_win:
            YOUR_COLOR, COM_COLOR = "black", "white"
            first_player = YOU
        else:
            YOUR_COLOR, COM_COLOR = "white", "black"
            first_player = COM

        janken_win.destroy()
        start_othello_game(first_player)

    # ボタン設置
    btn_frame = tk.Frame(janken_win)
    btn_frame.pack(pady=10)

    tk.Button(btn_frame,image=rock_img,command=lambda: judge(ROCK)).grid(row=0, column=0, padx=10)
    tk.Button(btn_frame,image=scissors_img,command=lambda: judge(SCISSORS)).grid(row=0, column=1, padx=10)
    tk.Button(btn_frame,image=paper_img,command=lambda: judge(PAPER)).grid(row=0, column=2, padx=10)

# 盤面を初期化してゲーム開始
def start_othello_game(first_player):
    othello.color = {YOU: YOUR_COLOR, COM: COM_COLOR}
    othello.reset_game(first_player)
    if first_player == COM:
        window.after(500, othello.com)

# オセロメインロジック
class Othello:
    def __init__(self, master):
        self.master = master
        self.square = CANVAS_SIZE // NUM_SQUARE
        self.canvas = tk.Canvas(master,width=CANVAS_SIZE,height=CANVAS_SIZE + INFO_HEIGHT,bg=BOARD_COLOR,highlightthickness=0)
        self.canvas.pack()
        self.last_move = None
        self.player = YOU
        self.animating = False
        self.color = {YOU: YOUR_COLOR, COM: COM_COLOR}

    # 上部UI表示
    def draw_info_background(self):
        self.canvas.create_rectangle(0, 0,CANVAS_SIZE, INFO_HEIGHT,fill=INFO_BG_COLOR,outline="",tags="info_bg")
        self.canvas.create_line(0, INFO_HEIGHT,CANVAS_SIZE, INFO_HEIGHT,fill="gray")
        self.canvas.tag_lower("info_bg")

    # プレイヤーとCOMの石の色を表示
    def show_color_info(self):
        self.canvas.delete("color_info")

        you_color = self.color[YOU]
        com_color = self.color[COM]

        you_mark = "●" if you_color == "black" else "○"
        com_mark = "●" if com_color == "black" else "○"

        self.canvas.create_text(CANVAS_SIZE // 4, 18,text=f"YOU : {you_mark} {you_color.upper()}",fill=INFO_TEXT_COLOR,font=("Arial", 14, "bold"),tags="color_info")
        self.canvas.create_text(CANVAS_SIZE * 3 // 4, 18,text=f"COM : {com_mark} {com_color.upper()}",fill=INFO_TEXT_COLOR,font=("Arial", 14, "bold"),tags="color_info")
    
    # 石が置ける場所の表示
    def draw_placable(self):
        if not SHOW_GUIDE:
            self.canvas.delete("guide")
            return
        
        self.canvas.delete("guide")

        if self.animating:
            return
        if self.player != YOU:
            return

        placable_list = self.get_placable_list(YOU)
        for x, y in placable_list:
            cx = (x + 0.5) * self.square
            cy = INFO_HEIGHT + (y + 0.5) * self.square
            self.canvas.create_oval(cx - 5, cy - 5,cx + 5, cy + 5,fill="yellow",outline="orange",tags="guide")

    # 初期化
    def reset_game(self, first_player):
        self.canvas.delete("all")
        self.player = first_player
        self.animating = False
        self.color = {YOU: YOUR_COLOR, COM: COM_COLOR}
        self.draw_info_background()
        self.init_board()
        self.draw_board()
        self.init_stones()
        self.show_color_info()
        self.draw_placable()
        self.last_move = None
        self.canvas.bind("<ButtonPress>", self.click)

    def init_board(self):
        self.board = [[None] * NUM_SQUARE for _ in range(NUM_SQUARE)]

    # 盤面の格子線を描画
    def draw_board(self):
        self.canvas.delete("grid")
        for y in range(NUM_SQUARE):
            for x in range(NUM_SQUARE):
                xs = x * self.square
                ys = INFO_HEIGHT + y * self.square
                xe = xs + self.square
                ye = ys + self.square
                self.canvas.create_rectangle(xs, ys, xe, ye, tags="grid")

    # 中央の初期石を設置
    def init_stones(self):
        mid = NUM_SQUARE // 2
        self.drawDisk(mid - 1, mid - 1, COM)
        self.drawDisk(mid, mid, COM)
        self.drawDisk(mid - 1, mid, YOU)
        self.drawDisk(mid, mid - 1, YOU)

    # 指定された場所に石を配置し、内部データ(self.board)を更新
    def drawDisk(self, x, y, player):
        cx = (x + 0.5) * self.square
        cy = INFO_HEIGHT + (y + 0.5) * self.square
        r = self.square * 0.4
        disk_id = self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r,fill=self.color[player])
        self.board[y][x] = {"color": self.color[player], "id": disk_id}

    
    def highlight_flash(self):
        self.draw_last_move()
        self.canvas.after(400, lambda: self.canvas.delete("last_move"))

    # COMが置いた石の強調
    def draw_last_move(self):
        self.canvas.delete("last_move")

        if not self.last_move:
            return

        x, y = self.last_move
        cx = (x + 0.5) * self.square
        cy = INFO_HEIGHT + (y + 0.5) * self.square
        self.canvas.create_oval(cx - 18, cy - 18,cx + 18, cy + 18,outline="red",width=3,tags="last_move")

    # 石をひっくり返すアニメーション
    def animate_flip(self, x, y, step=0,new_color=None):
        disk = self.board[y][x]
        disk_id = disk["id"]

        cx = (x + 0.5) * self.square
        cy = INFO_HEIGHT + (y + 0.5) * self.square
        r = self.square * 0.4

        scale = abs(1 - step / 5)
        self.canvas.coords(disk_id,cx - r * scale, cy - r,cx + r * scale, cy + r)

        # 半分ひっくり返ったタイミングで色を変更
        if step == 5:
            disk["color"] = new_color
            self.canvas.itemconfig(disk_id, fill=new_color)

        if step < 10:
            self.master.after(30,lambda: self.animate_flip(x, y, step + 1, new_color))

    def animate_reverse_rotate(self, lst, index=0,flip_color=None, callback=None):
        if index >= len(lst):
            if callback:
                callback()
            return

        x, y = lst[index]
        self.animate_flip(x, y, new_color=flip_color)
        self.master.after(120,lambda: self.animate_reverse_rotate(lst, index + 1,flip_color, callback))

    # 挟まれてひっくり返せる石のリスト取得
    def get_reverse_list(self, x, y,player):
        if self.board[y][x] is not None:
            return []

        reverse_list = []
        other = COM if player == YOU else YOU

        # 8方向をチェック
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue

                tx, ty = x + dx, y + dy
                temp = []
                while 0 <= tx < NUM_SQUARE and 0 <= ty < NUM_SQUARE:
                    cell = self.board[ty][tx]
                    if cell is None:break
                    if cell["color"] == self.color[other]:
                        temp.append((tx, ty))
                    elif cell["color"] == self.color[player]:
                        reverse_list.extend(temp)
                        break
                    else:break

                    tx += dx
                    ty += dy

        return reverse_list

    def checkPlacable(self, x, y,player=None):
        if player is None:
            player = self.player

        if self.board[y][x] is not None:
            return False

        return bool(self.get_reverse_list(x, y,player))

    def get_placable_list(self,player=None):
        if player is None:
            player = self.player

        lst = []
        for y in range(NUM_SQUARE):
            for x in range(NUM_SQUARE):
                if self.checkPlacable(x, y,player):
                    lst.append((x, y))
        return lst

    # 盤面の石の数を集計
    def count_stones(self):
        black = 0
        white = 0

        for y in range(NUM_SQUARE):
            for x in range(NUM_SQUARE):
                cell = self.board[y][x]
                if cell is None:
                    continue
                if cell["color"] == "black":
                    black += 1
                elif cell["color"] == "white":
                    white += 1

        return black, white

    # 置ける場所があるか判定
    def has_placable(self, player):
        return bool(self.get_placable_list(player))

    # クリック時の処理
    def click(self, event):
        if self.animating or self.player != YOU:
            return

        if event.y < INFO_HEIGHT:
            return

        x, y = event.x // self.square,  (event.y - INFO_HEIGHT) // self.square

        if 0 <= x < NUM_SQUARE and 0 <= y < NUM_SQUARE:
            if self.checkPlacable(x, y):
                self.place(x, y)
    
    # 石を置き、ターンを進行する共通処理
    def place(self, x, y):
        self.canvas.delete("guide")
        self.animating = True
        if sound_put: sound_put.play()
        reverse_list = self.get_reverse_list(x, y, self.player)
        self.last_move = (x, y)
        flip_color = self.color[self.player]
        self.drawDisk(x, y, self.player)
        self.animate_reverse_rotate(reverse_list,flip_color=flip_color,callback=self.after_animation)
    
    def start_turn(self, player):
        self.player = player

        # 石が置けるか判定
        if not self.has_placable(player):
            # 両者とも置けない → 終了
            opponent = COM if player == YOU else YOU
            if not self.has_placable(opponent):
                self.show_result()
                return

            # 片方だけ置けない → PASS
            self.show_pass(player)
            self.player = opponent
            return

        # 置ける場合
        if player == COM:
            self.master.after(500, self.com)
        else:
            self.draw_placable()

    # ターンの交代と終了判定
    def change_turn(self):
        next_player = COM if self.player == YOU else YOU
        self.start_turn(next_player)

    # アニメーション終了後の状態チェック
    def after_animation(self):
        self.animating = False
        self.change_turn()

    # パス時のメッセージ
    def show_pass(self, player):
        name = "YOU" if player == YOU else "COM"
        self.canvas.delete("pass")
        self.animating = True

        text = f"{name} PASS"
        self.canvas.create_text(CANVAS_SIZE // 2,INFO_HEIGHT + CANVAS_SIZE // 2,text=text,fill="red",font=("Arial", 36, "bold"),tags="pass")

        def clear_pass():
            self.canvas.delete("pass")
            self.animating = False
            self.start_turn(self.player)

        self.master.after(1200, clear_pass)

    # 最終スコアの集計と勝敗表示
    def show_result(self):
        black, white = self.count_stones()

        # 勝者を判定
        if black > white:
            winner = "YOU" if self.color[YOU] == "black" else "COM"
        elif white > black:
            winner = "YOU" if self.color[YOU] == "white" else "COM"
        else:
            winner = "DRAW"

        # 判定された結果に基づいて音を鳴らす
        if winner == "YOU":
            if sound_win: sound_win.play()
        elif winner == "COM":
            if sound_lose: sound_lose.play()

        # 勝敗表示
        msg = f"黒: {black}\n白: {white}\n\n結果: {winner}"
        tk.messagebox.showinfo("ゲーム終了", msg)

    # COMの思考処理
    def com(self):
        if self.animating or self.player != COM:
            return

        self.canvas.delete("guide")
        placable = self.get_placable_list(COM)

        if not placable:
            return

        # 難易度に応じた探索深さと重みを選択
        depth = self.get_com_depth()
        weights = self.get_com_weights()

        com_color = self.color[COM]
        you_color = self.color[YOU]

        # 盤面の色情報を取得
        board_colors = get_board_colors(self.board)

        # Minimaxで最善手を探索
        _, best_move = minimax(board_colors, depth, float('-inf'), float('inf'),
                               True, com_color, you_color, weights)

        if best_move is None:
            # フォールバック: ランダム選択
            best_move = random.choice(placable)

        x, y = best_move
        self.place(x, y)
        self.highlight_flash()

    def get_com_depth(self):
        """現在の難易度に応じた探索深さを返す"""
        global difficulty_var
        if difficulty_var is None:
            return DIFFICULTY_BEGINNER
        level = difficulty_var.get()
        return level

    def get_com_weights(self):
        """現在の難易度に応じた重みテーブルを返す"""
        global difficulty_var
        if difficulty_var is None:
            return DEFAULT_EVAL_WEIGHTS
        level = difficulty_var.get()
        if level == DIFFICULTY_ADVANCED:
            learned = load_learned_weights()
            if learned is not None:
                return learned
        elif level == DIFFICULTY_MEDIUM:
            # 中級: 学習済み重みを50%ブレンド(デフォルトと学習済みの中間)
            learned = load_learned_weights()
            if learned is not None:
                blended = []
                for y in range(NUM_SQUARE):
                    row = []
                    for x in range(NUM_SQUARE):
                        val = (DEFAULT_EVAL_WEIGHTS[y][x] + learned[y][x]) / 2.0
                        row.append(val)
                    blended.append(row)
                return blended
        return DEFAULT_EVAL_WEIGHTS

# メイン
window.title("Othello")
top_frame = tk.Frame(window)
top_frame.pack(fill="x")

# 難易度選択
difficulty_var = tk.IntVar(value=DIFFICULTY_BEGINNER)

difficulty_frame = tk.Frame(top_frame)
difficulty_frame.pack(side="left", padx=10, pady=5)

tk.Label(difficulty_frame, text="難易度:", font=("Arial", 10)).pack(side="left")
tk.Radiobutton(difficulty_frame, text="初級", variable=difficulty_var,
               value=DIFFICULTY_BEGINNER, font=("Arial", 10)).pack(side="left")
tk.Radiobutton(difficulty_frame, text="中級", variable=difficulty_var,
               value=DIFFICULTY_MEDIUM, font=("Arial", 10)).pack(side="left")
tk.Radiobutton(difficulty_frame, text="上級", variable=difficulty_var,
               value=DIFFICULTY_ADVANCED, font=("Arial", 10)).pack(side="left")

start_button = tk.Button(top_frame, text="START", font=("Arial", 14, "bold"), command=open_janken)
start_button.pack(side="left", padx=10, pady=5)

# 学習モードボタンと処理
def start_learning_mode():
    """学習モードを開始する(バックグラウンドスレッドで実行)"""
    num_games = 100
    learn_btn.config(state="disabled")
    progress_label.config(text="学習中: 0/" + str(num_games))

    def learning_thread():
        """バックグラウンドで学習を実行するスレッド"""
        run_self_learning(num_games=num_games, progress_callback=progress_callback)
        # 完了後UIスレッドで後処理
        window.after(0, learning_complete)

    def progress_callback(current, total):
        # UIの更新はメインスレッドで行う
        window.after(0, lambda c=current, t=total: progress_label.config(text=f"学習中: {c}/{t}"))

    def learning_complete():
        progress_label.config(text="学習完了!")
        learn_btn.config(state="normal")
        messagebox.showinfo("学習モード", f"{num_games}ゲームの自己学習が完了しました。\n重みデータを保存しました。")
        progress_label.config(text="")

    thread = threading.Thread(target=learning_thread, daemon=True)
    thread.start()

learn_btn = tk.Button(top_frame, text="学習モード", font=("Arial", 10), command=start_learning_mode)
learn_btn.pack(side="left", padx=10, pady=5)

progress_label = tk.Label(top_frame, text="", font=("Arial", 10))
progress_label.pack(side="left", padx=5)

game_frame = tk.Frame(window)
game_frame.pack()

othello = Othello(game_frame)
othello.reset_game(YOU)
window.mainloop()
pygame.mixer.quit()