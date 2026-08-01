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

# アニメーション速度設定
ANIM_SPEED_FAST = 1
ANIM_SPEED_NORMAL = 2
ANIM_SPEED_SLOW = 3

# アニメーション速度に対応するタイミング値 (step_ms, between_ms)
ANIM_TIMING = {
    ANIM_SPEED_FAST: (15, 60),
    ANIM_SPEED_NORMAL: (30, 120),
    ANIM_SPEED_SLOW: (60, 240),
}

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

# BGMの再生設定(読み込みのみ、再生は後でtkinter変数初期化後に開始)
bgm_path = os.path.join(SOUND_DIR, "bgm.mp3")
bgm_loaded = False
if os.path.exists(bgm_path):
    pygame.mixer.music.load(bgm_path)
    pygame.mixer.music.set_volume(0.2)
    bgm_loaded = True

# サウンド・アニメーション速度のグローバル変数（tkinter変数は後で初期化）
sound_enabled_var = None
animation_speed_var = None

def play_sound(sound):
    """サウンドが有効な場合のみ再生するヘルパー関数"""
    global sound_enabled_var
    if sound_enabled_var is not None and not sound_enabled_var.get():
        return
    if sound:
        sound.play()

def toggle_bgm():
    """サウンド設定に応じてBGMを再生/停止"""
    global sound_enabled_var, bgm_loaded
    if sound_enabled_var is None:
        return
    if not bgm_loaded:
        return
    if sound_enabled_var.get():
        pygame.mixer.music.unpause()
    else:
        pygame.mixer.music.pause()

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
window.minsize(500, 550)  # 盤面が完全に表示される最小サイズ

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
    # ゲーム開始時に難易度をスナップショット(ゲーム中の変更を防止)
    othello.game_depth = difficulty_var.get() if difficulty_var is not None else DIFFICULTY_BEGINNER
    set_difficulty_controls_state("disabled")
    othello.reset_game(first_player)
    if first_player == COM:
        window.after(500, othello.com)

# オセロメインロジック
class Othello:
    def __init__(self, master):
        self.master = master
        self.board_size = CANVAS_SIZE
        self.square = self.board_size // NUM_SQUARE
        self.x_offset = 0
        self.canvas = tk.Canvas(master, width=CANVAS_SIZE, height=CANVAS_SIZE + INFO_HEIGHT,
                                bg="#d9d9d9", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.last_move = None
        self.player = YOU
        self.animating = False
        self.color = {YOU: YOUR_COLOR, COM: COM_COLOR}
        self._resize_after_id = None
        self._canvas_width = CANVAS_SIZE
        self.game_depth = None
        self.canvas.bind("<Configure>", self._on_configure)

    # リサイズイベントハンドラ（デバウンス付き）
    def _on_configure(self, event):
        # キャンバスのサイズ変更時のみ処理
        if event.widget != self.canvas:
            return
        new_w = event.width
        new_h = event.height - INFO_HEIGHT
        new_board_size = min(new_w, new_h)
        if new_board_size < 80:
            return
        if abs(new_board_size - self.board_size) < 4 and abs(new_w - self._canvas_width) < 4:
            return
        self._canvas_width = new_w
        # デバウンス: 短時間に複数回呼ばれるのを防ぐ
        if self._resize_after_id is not None:
            self.master.after_cancel(self._resize_after_id)
        self._resize_after_id = self.master.after(100, lambda: self._do_resize(new_board_size, new_w))

    def _do_resize(self, new_board_size, canvas_width):
        self._resize_after_id = None
        if self.animating:
            # アニメーション中はリサイズを遅延
            self._resize_after_id = self.master.after(200, lambda: self._do_resize(new_board_size, canvas_width))
            return
        self.board_size = new_board_size
        self.square = self.board_size // NUM_SQUARE
        self.x_offset = (canvas_width - self.board_size) // 2
        self.redraw_all()

    def redraw_all(self):
        """現在の盤面状態を新しいサイズで再描画"""
        if not hasattr(self, 'board'):
            return
        self.canvas.delete("all")
        self.draw_info_background()
        self.draw_board()
        # 既存の石を再描画
        for y in range(NUM_SQUARE):
            for x in range(NUM_SQUARE):
                cell = self.board[y][x]
                if cell is not None:
                    cx = self.x_offset + (x + 0.5) * self.square
                    cy = INFO_HEIGHT + (y + 0.5) * self.square
                    r = self.square * 0.4
                    disk_id = self.canvas.create_oval(
                        cx - r, cy - r, cx + r, cy + r,
                        fill=cell["color"])
                    cell["id"] = disk_id
        self.show_color_info()
        self.draw_placable()
        self.draw_last_move()

    # 上部UI表示
    def draw_info_background(self):
        self.canvas.create_rectangle(self.x_offset, 0,
                                     self.x_offset + self.board_size, INFO_HEIGHT,
                                     fill=INFO_BG_COLOR, outline="", tags="info_bg")
        self.canvas.create_line(self.x_offset, INFO_HEIGHT,
                                self.x_offset + self.board_size, INFO_HEIGHT, fill="gray")
        self.canvas.tag_lower("info_bg")

    # プレイヤーとCOMの石の色を表示
    def show_color_info(self):
        self.canvas.delete("color_info")

        you_color = self.color[YOU]
        com_color = self.color[COM]

        you_mark = "\u25cf" if you_color == "black" else "\u25cb"
        com_mark = "\u25cf" if com_color == "black" else "\u25cb"

        # フォントサイズを盤面サイズに応じて調整（はみ出し防止）
        font_size = max(7, min(12, self.board_size // 35))

        # 盤面が小さい場合は短縮表示で文字の重なりを防止
        if self.board_size < 300:
            you_text = f"YOU:{you_mark}"
            com_text = f"COM:{com_mark}"
        else:
            you_text = f"YOU : {you_mark} {you_color.upper()}"
            com_text = f"COM : {com_mark} {com_color.upper()}"

        # 左寄せ(anchor=w)と右寄せ(anchor=e)で重ならないように配置
        self.canvas.create_text(self.x_offset + 10, 18,
                                text=you_text,
                                fill=INFO_TEXT_COLOR, font=("Arial", font_size, "bold"),
                                anchor="w", tags="color_info")
        self.canvas.create_text(self.x_offset + self.board_size - 10, 18,
                                text=com_text,
                                fill=INFO_TEXT_COLOR, font=("Arial", font_size, "bold"),
                                anchor="e", tags="color_info")
    
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
        guide_r = max(3, self.square * 0.1)
        for x, y in placable_list:
            cx = self.x_offset + (x + 0.5) * self.square
            cy = INFO_HEIGHT + (y + 0.5) * self.square
            self.canvas.create_oval(cx - guide_r, cy - guide_r,
                                    cx + guide_r, cy + guide_r,
                                    fill="yellow", outline="orange", tags="guide")

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
        self.update_stone_count()

    def init_board(self):
        self.board = [[None] * NUM_SQUARE for _ in range(NUM_SQUARE)]

    # 盤面の格子線を描画
    def draw_board(self):
        self.canvas.delete("grid")
        for y in range(NUM_SQUARE):
            for x in range(NUM_SQUARE):
                xs = self.x_offset + x * self.square
                ys = INFO_HEIGHT + y * self.square
                xe = xs + self.square
                ye = ys + self.square
                self.canvas.create_rectangle(xs, ys, xe, ye, fill=BOARD_COLOR, tags="grid")

    # 中央の初期石を設置 (標準リバーシ配置: 色で固定)
    def init_stones(self):
        mid = NUM_SQUARE // 2
        # 標準リバーシ初期配置: (3,3)=白, (4,4)=白, (3,4)=黒, (4,3)=黒
        black_player = YOU if self.color[YOU] == "black" else COM
        white_player = YOU if self.color[YOU] == "white" else COM
        self.drawDisk(mid - 1, mid - 1, white_player)  # (3,3) = white
        self.drawDisk(mid, mid, white_player)            # (4,4) = white
        self.drawDisk(mid - 1, mid, black_player)        # (3,4) = black
        self.drawDisk(mid, mid - 1, black_player)        # (4,3) = black

    # 指定された場所に石を配置し、内部データ(self.board)を更新
    def drawDisk(self, x, y, player):
        cx = self.x_offset + (x + 0.5) * self.square
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
        cx = self.x_offset + (x + 0.5) * self.square
        cy = INFO_HEIGHT + (y + 0.5) * self.square
        highlight_r = self.square * 0.36
        self.canvas.create_oval(cx - highlight_r, cy - highlight_r,
                                cx + highlight_r, cy + highlight_r,
                                outline="red", width=3, tags="last_move")

    # 石をひっくり返すアニメーション
    def animate_flip(self, x, y, step=0,new_color=None):
        disk = self.board[y][x]
        disk_id = disk["id"]

        cx = self.x_offset + (x + 0.5) * self.square
        cy = INFO_HEIGHT + (y + 0.5) * self.square
        r = self.square * 0.4

        scale = abs(1 - step / 5)
        self.canvas.coords(disk_id,cx - r * scale, cy - r,cx + r * scale, cy + r)

        # 半分ひっくり返ったタイミングで色を変更
        if step == 5:
            disk["color"] = new_color
            self.canvas.itemconfig(disk_id, fill=new_color)

        if step < 10:
            step_ms = self._get_anim_step_ms()
            self.master.after(step_ms,lambda: self.animate_flip(x, y, step + 1, new_color))

    def animate_reverse_rotate(self, lst, index=0,flip_color=None, callback=None):
        if index >= len(lst):
            if callback:
                callback()
            return

        x, y = lst[index]
        self.animate_flip(x, y, new_color=flip_color)
        between_ms = self._get_anim_between_ms()
        self.master.after(between_ms,lambda: self.animate_reverse_rotate(lst, index + 1,flip_color, callback))

    def _get_anim_step_ms(self):
        """現在のアニメーション速度設定に応じたステップ間隔(ms)を返す"""
        global animation_speed_var
        if animation_speed_var is None:
            return 30
        speed = animation_speed_var.get()
        return ANIM_TIMING.get(speed, ANIM_TIMING[ANIM_SPEED_NORMAL])[0]

    def _get_anim_between_ms(self):
        """現在のアニメーション速度設定に応じた石間隔(ms)を返す"""
        global animation_speed_var
        if animation_speed_var is None:
            return 120
        speed = animation_speed_var.get()
        return ANIM_TIMING.get(speed, ANIM_TIMING[ANIM_SPEED_NORMAL])[1]

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

        x, y = (event.x - self.x_offset) // self.square, (event.y - INFO_HEIGHT) // self.square

        if 0 <= x < NUM_SQUARE and 0 <= y < NUM_SQUARE:
            if self.checkPlacable(x, y):
                self.place(x, y)
    
    # 石を置き、ターンを進行する共通処理
    def place(self, x, y):
        self.canvas.delete("guide")
        self.animating = True
        play_sound(sound_put)
        reverse_list = self.get_reverse_list(x, y, self.player)
        self.last_move = (x, y)
        flip_color = self.color[self.player]
        self.drawDisk(x, y, self.player)
        # Update board state immediately (before animation) to fix race condition
        for rx, ry in reverse_list:
            self.board[ry][rx]["color"] = flip_color
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
        self.update_stone_count()
        self.change_turn()

    # 石数リアルタイム表示を更新
    def update_stone_count(self):
        """盤面の石数を集計して下部ラベルに反映"""
        global stone_count_label
        if not hasattr(self, 'board'):
            return
        black, white = self.count_stones()
        if stone_count_label is not None:
            stone_count_label.config(text=f"\u25cf {black}    \u25cb {white}")

    # パス時のメッセージ
    def show_pass(self, player):
        name = "YOU" if player == YOU else "COM"
        self.canvas.delete("pass")
        self.animating = True

        # フォントサイズを盤面サイズに応じて調整（はみ出し防止）
        pass_font_size = max(16, min(36, self.board_size // 10))

        text = f"{name} PASS"
        self.canvas.create_text(self.x_offset + self.board_size // 2,
                                INFO_HEIGHT + self.board_size // 2,
                                text=text, fill="red",
                                font=("Arial", pass_font_size, "bold"), tags="pass")

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
            play_sound(sound_win)
        elif winner == "COM":
            play_sound(sound_lose)

        # ゲーム終了時に難易度ラジオボタンを再有効化
        set_difficulty_controls_state("normal")

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

        # 思考中表示
        self.show_thinking()
        # canvasを更新してからminimax実行(ブロッキング回避)
        self.master.after(10, lambda: self._com_compute(placable))

    def _com_compute(self, placable):
        """minimax探索を別スレッドで実行し、結果をメインスレッドに返す"""
        # 難易度に応じた探索深さと重みを選択
        depth = self.get_com_depth()
        weights = self.get_com_weights()

        com_color = self.color[COM]
        you_color = self.color[YOU]

        # 盤面の色情報を取得
        board_colors = get_board_colors(self.board)

        def compute():
            # バックグラウンドスレッドでminimax探索を実行
            _, best_move = minimax(board_colors, depth, float('-inf'), float('inf'),
                                   True, com_color, you_color, weights)

            if best_move is None:
                best_move_final = random.choice(placable)
            else:
                best_move_final = best_move

            # メインスレッドに結果を返す
            self.master.after(0, lambda: self._com_apply_move(best_move_final))

        thread = threading.Thread(target=compute, daemon=True)
        thread.start()

    def _com_apply_move(self, best_move):
        """メインスレッドでCOMの手を盤面に反映する"""
        # 思考中表示を消す
        self.hide_thinking()

        x, y = best_move
        self.place(x, y)
        self.highlight_flash()

    def show_thinking(self):
        """COMの思考中テキストをcanvasに表示"""
        self.canvas.delete("thinking")
        font_size = max(12, min(24, self.board_size // 16))
        self.canvas.create_text(
            self.x_offset + self.board_size // 2,
            INFO_HEIGHT + self.board_size // 2,
            text="\u8003\u3048\u4e2d...",
            fill="#333333", font=("Arial", font_size, "bold"),
            tags="thinking")

    def hide_thinking(self):
        """COMの思考中テキストを削除"""
        self.canvas.delete("thinking")

    def get_com_depth(self):
        """ゲーム開始時にスナップショットした探索深さを返す"""
        if hasattr(self, 'game_depth') and self.game_depth is not None:
            return self.game_depth
        global difficulty_var
        if difficulty_var is None:
            return DIFFICULTY_BEGINNER
        level = difficulty_var.get()
        return level

    def get_com_weights(self):
        """ゲーム開始時の難易度に応じた重みテーブルを返す"""
        level = self.get_com_depth()
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

# グローバル変数
stone_count_label = None

# === トップバー ===
top_frame = tk.Frame(window)
top_frame.pack(fill="x")

# 歯車(設定)ボタン - 左側
settings_btn = tk.Button(top_frame, text="\u2699", font=("Arial", 16),
                         relief="flat", cursor="hand2")
settings_btn.pack(side="left", padx=10, pady=5)

# STARTボタン - 中央に配置するためのフレーム
center_frame = tk.Frame(top_frame)
center_frame.pack(side="left", expand=True)

start_button = tk.Button(center_frame, text="START", font=("Arial", 14, "bold"),
                         command=open_janken, bg="#4CAF50", fg="white",
                         activebackground="#45a049", padx=20, pady=2)
start_button.pack()

# ヘルプボタン - 右側
help_btn = tk.Button(top_frame, text="\u2753", font=("Arial", 14),
                     relief="flat", cursor="hand2")
help_btn.pack(side="right", padx=10, pady=5)

# === 設定パネル（折りたたみ式） ===
settings_frame = tk.Frame(window, bg="#f0f0f0", relief="groove", bd=1)
settings_visible = tk.BooleanVar(value=False)

# 難易度選択
difficulty_var = tk.IntVar(value=DIFFICULTY_BEGINNER)

# アニメーション速度
animation_speed_var = tk.IntVar(value=ANIM_SPEED_NORMAL)

# サウンドON/OFF
sound_enabled_var = tk.BooleanVar(value=True)

def toggle_settings():
    if settings_visible.get():
        settings_frame.pack_forget()
        settings_btn.config(text="\u2699")
        settings_visible.set(False)
    else:
        # 相互排他: ヘルプが開いていたら閉じる
        if help_visible.get():
            help_frame.pack_forget()
            help_btn.config(text="\u2753")
            help_visible.set(False)
        settings_frame.pack(fill="x", after=top_frame)
        settings_btn.config(text="\u2699 \u25bc")
        settings_visible.set(True)

settings_btn.config(command=toggle_settings)

# 設定パネル内容
settings_inner = tk.Frame(settings_frame, bg="#f0f0f0")
settings_inner.pack(fill="x", padx=10, pady=8)

# 難易度設定
diff_frame = tk.Frame(settings_inner, bg="#f0f0f0")
diff_frame.pack(fill="x", pady=2)
tk.Label(diff_frame, text="COM\u30ec\u30d9\u30eb:", font=("Arial", 10), bg="#f0f0f0").pack(side="left")
diff_rb_beginner = tk.Radiobutton(diff_frame, text="\u521d\u7d1a", variable=difficulty_var,
               value=DIFFICULTY_BEGINNER, font=("Arial", 10), bg="#f0f0f0")
diff_rb_beginner.pack(side="left", padx=5)
diff_rb_medium = tk.Radiobutton(diff_frame, text="\u4e2d\u7d1a", variable=difficulty_var,
               value=DIFFICULTY_MEDIUM, font=("Arial", 10), bg="#f0f0f0")
diff_rb_medium.pack(side="left", padx=5)
diff_rb_advanced = tk.Radiobutton(diff_frame, text="\u4e0a\u7d1a", variable=difficulty_var,
               value=DIFFICULTY_ADVANCED, font=("Arial", 10), bg="#f0f0f0")
diff_rb_advanced.pack(side="left", padx=5)

difficulty_radio_buttons = [diff_rb_beginner, diff_rb_medium, diff_rb_advanced]

def set_difficulty_controls_state(state):
    """難易度ラジオボタンの有効/無効を切り替える"""
    for rb in difficulty_radio_buttons:
        rb.config(state=state)

# アニメーション速度設定
anim_frame = tk.Frame(settings_inner, bg="#f0f0f0")
anim_frame.pack(fill="x", pady=2)
tk.Label(anim_frame, text="\u30a2\u30cb\u30e1\u901f\u5ea6:", font=("Arial", 10), bg="#f0f0f0").pack(side="left")
tk.Radiobutton(anim_frame, text="\u901f\u3044", variable=animation_speed_var,
               value=ANIM_SPEED_FAST, font=("Arial", 10), bg="#f0f0f0").pack(side="left", padx=5)
tk.Radiobutton(anim_frame, text="\u666e\u901a", variable=animation_speed_var,
               value=ANIM_SPEED_NORMAL, font=("Arial", 10), bg="#f0f0f0").pack(side="left", padx=5)
tk.Radiobutton(anim_frame, text="\u9045\u3044", variable=animation_speed_var,
               value=ANIM_SPEED_SLOW, font=("Arial", 10), bg="#f0f0f0").pack(side="left", padx=5)

# サウンドON/OFF設定
sound_frame = tk.Frame(settings_inner, bg="#f0f0f0")
sound_frame.pack(fill="x", pady=2)

sound_label_var = tk.StringVar(value="\ud83d\udd0a \u30b5\u30a6\u30f3\u30c9 ON")

def on_sound_toggle():
    """サウンドトグル時にラベル更新とBGM制御"""
    if sound_enabled_var.get():
        sound_label_var.set("\ud83d\udd0a \u30b5\u30a6\u30f3\u30c9 ON")
    else:
        sound_label_var.set("\ud83d\udd07 \u30b5\u30a6\u30f3\u30c9 OFF")
    toggle_bgm()

tk.Checkbutton(sound_frame, textvariable=sound_label_var,
               variable=sound_enabled_var, font=("Arial", 10), bg="#f0f0f0",
               command=on_sound_toggle).pack(side="left")

# === ヘルプパネル（折りたたみ式） ===
help_frame = tk.Frame(window)
help_visible = tk.BooleanVar(value=False)

help_text = (
    "\u3010\u904a\u3073\u65b9\u3011\n"
    "1. START\u30dc\u30bf\u30f3\u3092\u62bc\u3057\u3066\u30b8\u30e3\u30f3\u30b1\u30f3\u3067\u5148\u653b/\u5f8c\u653b\u3092\u6c7a\u5b9a\n"
    "2. \u9ec4\u8272\u3044\u4e38(\u30ac\u30a4\u30c9)\u304c\u7f6e\u3051\u308b\u5834\u6240\u3067\u3059\n"
    "3. \u76f8\u624b\u306e\u77f3\u3092\u631f\u3081\u308b\u5834\u6240\u306b\u30af\u30ea\u30c3\u30af\u3057\u3066\u77f3\u3092\u7f6e\u304d\u307e\u3059\n"
    "4. \u7f6e\u3051\u308b\u5834\u6240\u304c\u306a\u3044\u5834\u5408\u306f\u81ea\u52d5\u3067\u30d1\u30b9\u306b\u306a\u308a\u307e\u3059\n"
    "5. \u5168\u30de\u30b9\u57cb\u307e\u308b\u304b\u4e21\u8005\u7f6e\u3051\u306a\u304f\u306a\u3063\u305f\u3089\u7d42\u4e86\n"
    "6. \u77f3\u304c\u591a\u3044\u65b9\u306e\u52dd\u3061\u3067\u3059"
)

help_content = tk.Label(help_frame, text=help_text, font=("Arial", 9),
                        justify="left", anchor="w", bg="#fffde6",
                        relief="groove", padx=8, pady=5)

def toggle_help():
    if help_visible.get():
        help_frame.pack_forget()
        help_btn.config(text="\u2753")
        help_visible.set(False)
    else:
        # 相互排他: 設定パネルが開いていたら閉じる
        if settings_visible.get():
            settings_frame.pack_forget()
            settings_btn.config(text="\u2699")
            settings_visible.set(False)
        help_frame.pack(fill="x", after=top_frame)
        help_content.pack(fill="x", padx=10, pady=5)
        help_btn.config(text="\u2753 \u25bc")
        help_visible.set(True)

help_btn.config(command=toggle_help)

# === 石数表示(盤面下部) ===
# bottom_frameを先にpackすることで、ウィンドウ縮小時も常に表示される
bottom_frame = tk.Frame(window)
bottom_frame.pack(fill="x", side="bottom")

# === ゲームフレーム ===
game_frame = tk.Frame(window)
game_frame.pack(fill="both", expand=True, side="top")

stone_count_label = tk.Label(bottom_frame, text="\u25cf 2    \u25cb 2",
                             font=("Arial", 14, "bold"), pady=5)
stone_count_label.pack()

othello = Othello(game_frame)
othello.reset_game(YOU)

# BGM再生開始(tkinter変数初期化後に開始し、ミュート状態を尊重)
if bgm_loaded and sound_enabled_var.get():
    pygame.mixer.music.play(-1)

window.mainloop()
pygame.mixer.quit()