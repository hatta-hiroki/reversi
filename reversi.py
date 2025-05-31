import numpy as np
import tkinter as tk
import tkinter.messagebox
import tkinter.ttk as ttk
import random
from PIL import ImageTk, Image

#COMの選択する手
list = ["rock", "scissors", "paper"]

#プレイヤーを示す値
YOU = 1
COM = 2

#キャンバスのサイズ（px）
CANVAS_SIZE = 400

#横方向・縦方向のマスの数
NUM_SQUARE = 8

#色の設定
BOARD_COLOR = 'green'       #盤面の背景色
YOUR_COLOR = 'black'        #あなたの石の色
COM_COLOR = 'white'         #相手の石の色
PLACABLE_COLOR = 'yellow'   #次に石を置ける場所を示す色

count_max = 0

window = tk.Tk()
window.title("reversi")
window.geometry("600x500")

sub_win = tk.Toplevel()
sub_win.geometry("500x450")
sub_win.title("ジャンケン")
sub_win.withdraw()

#先行決めジャンケン実行
def janken():
    janken_initialize()
    sub_win.deiconify()
    sub_win.attributes("-topmost", True)

#ジャンケン初期化
def janken_initialize():
    #CPUの手を非表示
    canvas_cpu.place_forget()
    #メッセージを非表示
    label_draw.place_forget()
    label_lose.place_forget()
    label_win.place_forget()
    #自分の手を全て表示
    button_rock.place(x=50, y=250)
    button_scissors.place(x=200, y=250)
    button_paper.place(x=350, y=250)
    cpu_hand()

def rock_click():
    player_hand = 'rock'
    button_scissors.place_forget()
    button_paper.place_forget()
    canvas_cpu.place(x=200, y=50)
    canvas_cpu.create_image(10, 10, image=cpu, anchor=tk.NW)
    judge(player_hand)

def scissors_click():
    player_hand = 'scissors'
    button_rock.place_forget()
    button_paper.place_forget()
    canvas_cpu.place(x=200, y=50)
    canvas_cpu.create_image(10, 10, image=cpu, anchor=tk.NW)
    judge(player_hand)

def paper_click():
    player_hand = 'paper'
    button_rock.place_forget()
    button_scissors.place_forget()
    canvas_cpu.place(x=200, y=50)
    canvas_cpu.create_image(10, 10, image=cpu, anchor=tk.NW)
    judge(player_hand)

def judge(player_hand):
    global YOU, COM, YOUR_COLOR, COM_COLOR
    if player_hand == com:
        label_draw.place(x=160, y=390)
        sub_win.after(1000, janken_initialize)
    elif player_hand == 'rock' and com == 'scissors':
        label_win.place(x=220, y=390)
        YOU = 1
        COM = 2
        sub_win.after(1000,lambda:sub_win.withdraw())
    elif player_hand == 'scissors' and com == 'paper':
        label_win.place(x=220, y=390)
        YOU = 1
        COM = 2
        sub_win.after(1000, lambda:sub_win.withdraw())
    elif player_hand == 'paper' and com == 'rock':
        label_win.place(x=220, y=390)
        YOU = 1
        COM = 2
        sub_win.after(1000, lambda:sub_win.withdraw())
    else:
        label_lose.place(x=220, y=390)
        YOU = 2
        COM = 1
        YOUR_COLOR = 'white'
        COM_COLOR = 'black'
        sub_win.after(1000, lambda:sub_win.withdraw())
        othello.com()

def cpu_hand():
    #グローバル変数へ再代入
    global com, image_cpu, image_cpu_resize, cpu, canvas_cpu
    #コンピューターの手をランダムで決定
    com = random.choice(list)
    image_cpu = Image.open("./image/" + com + ".png")
    image_cpu_resize = image_cpu.resize((100, 100))
    cpu = ImageTk.PhotoImage(image_cpu_resize)
    canvas_cpu = tk.Canvas(sub_win, bg='white', height=110, width=110, relief='raised', bd=2)

class Othello():
    def __init__(self,master):
        '''コンストラクタ'''

        self.master = master    #親ウィジェット
        self.player = YOU       #次に置く石の色
        self.board = None       #盤面上の石を管理する２次元リスト
        self.color = {          #石の色を保持する辞書
            YOU : YOUR_COLOR,
            COM : COM_COLOR
        }

        #ウィジェットの作成
        self.createWidgets()

        #イベントの設定
        self.setEvents()

        #オセロゲームの初期化
        self.initOthello()

    def createWidgets(self):
        '''ウィジェットを作成・配置する'''

        #キャンバスの作成
        self.canvas = tkinter.Canvas(
            self.master,
            bg = BOARD_COLOR,
            width = CANVAS_SIZE + 1,
            height = CANVAS_SIZE + 1,
            highlightthickness = 0
        )
        self.canvas.pack(padx=10, pady=10)

    def setEvents(self):
        '''イベントを設定する'''

        #キャンバス上のマウスクリックを受け付ける
        self.canvas.bind('<ButtonPress>', self.click)

    def initOthello(self):
        '''ゲームの初期化を行う'''

        #盤面上の石を管理する２次元リストを作成（最初は全てNone）
        self.board = [[None] * NUM_SQUARE for i in range(NUM_SQUARE)]

        #1マスのサイズ(px)を計算
        self.square_size = CANVAS_SIZE // NUM_SQUARE

        #マスを描画
        for y in range(NUM_SQUARE):
            for x in range(NUM_SQUARE):
                #長方形の開始・終了座標を計算
                xs = x * self.square_size
                ys = y * self.square_size
                xe = (x + 1) * self.square_size
                ye = (y + 1) * self.square_size

                #長方形を描画
                tag_name = 'square_' + str(x) + '_' + str(y)
                self.canvas.create_rectangle(
                    xs, ys,
                    xe, ye,
                    tag = tag_name
                )

        #黒石の描画位置を計算
        your_init_pos_1_X = NUM_SQUARE // 2
        your_init_pos_1_y = NUM_SQUARE // 2
        your_init_pos_2_X = NUM_SQUARE // 2 - 1
        your_init_pos_2_y = NUM_SQUARE // 2 - 1

        your_init_pos = (
            (your_init_pos_1_X, your_init_pos_1_y),
            (your_init_pos_2_X, your_init_pos_2_y)
        )

        #計算した描画位置に石(円)を描画
        for x, y in your_init_pos:
            self.drawDisk(x, y, self.color[YOU])

        #白石の描画位置を計算
        com_init_pos_1_X = NUM_SQUARE // 2 - 1
        com_init_pos_1_y = NUM_SQUARE // 2
        com_init_pos_2_X = NUM_SQUARE // 2
        com_init_pos_2_y = NUM_SQUARE // 2 - 1

        com_init_pos = (
            (com_init_pos_1_X, com_init_pos_1_y),
            (com_init_pos_2_X, com_init_pos_2_y)
        )

        #計算した描画位置に石(円)を描画
        for x, y in com_init_pos:
            self.drawDisk(x, y, self.color[COM])

        #最初に置くことができる石の位置を取得
        placable = self.getPlacable()

        #その位置を盤面に表示
        self.showPlacable(placable)

    def drawDisk(self, x, y, color):
        '''(x,y)に色がcolorの石を置く(円を描画する)'''

        #(x,y)のマスの中心座標を計算
        center_x = (x + 0.5) * self.square_size
        center_y = (y + 0.5) * self.square_size

        #中心座標から円の開始座標と終了座標を計算
        xs = center_x - (self.square_size * 0.8) // 2
        ys = center_y - (self.square_size * 0.8) // 2
        xe = center_x + (self.square_size * 0.8) // 2
        ye = center_y + (self.square_size * 0.8) // 2

        #円を描画する
        tag_name = 'disk_' + str(x) + '_' + str(y)
        self.canvas.create_oval(
            xs, ys,
            xe, ye,
            fill = color,
            tag = tag_name
        )

        #描画した円の色を管理リストに記憶させておく
        self.board[y][x] = color

    def getPlacable(self):
        '''次に置くことが出来る石の位置を取得'''

        placable = []

        for y in range(NUM_SQUARE):
            for x in range(NUM_SQUARE):
                #(x,y)の位置のマスに石が置けるかどうかをチェック
                if self.checkPlacable(x, y):
                    #置けるならその座標をリストに追加
                    placable.append((x, y))

        return placable

    def checkPlacable(self, x, y):
        '''(x,y)に石が置けるかどうかをチェック'''

        #その場所に石が置かれていれば置けない
        if self.board[y][x] != None:
            return False

        if self.player == YOU:
            other = COM
        else:
            other = YOU

        #(x,y)座標から縦横斜め全方向に対して相手の石が裏返せるかどうかを確認
        for j in range(-1, 2):
            for i in range(-1, 2):

                #真ん中方向はチェックしてもしょうがないので次の方向に移る
                if i == 0 and j == 0:
                    continue

                #その方向が盤面外になる場合も次の方向に移る
                if x + i < 0 or x + i >= NUM_SQUARE or y + j < 0 or y + j >= NUM_SQUARE:
                    continue

                #隣が相手の色で無ければその方向に石を置いても裏返せない
                if self.board[y + j][x + i] != self.color[other]:
                    continue

                #置こうとしているマスから遠い方向へ1マスずつ確認
                for s in range(2, NUM_SQUARE):
                    #盤面外のマスはチェックしない
                    if x + i * s >= 0 and x + i * s < NUM_SQUARE and y + j * s >= 0 and y + j * s < NUM_SQUARE:

                        if self.board[y + j * s][x + i * s] == None:
                            #自分の石が見つかる前に空きがある場合
                            #この方向の石は裏返せないので次の方向をチェック
                            break

                        #その方向に自分の石の色があれば石が裏返る
                        if self.board[y + j * s][x + i * s] == self.color[self.player]:
                            return True

        #裏返せる石がなかったので(x,y)に石は置けない
        return False

    def showPlacable(self, placable):
        '''placableに格納された次に石が置けるマスの色を変更する'''

        for y in range(NUM_SQUARE):
            for x in range(NUM_SQUARE):

                #fillを変更して石が置けるマスの色を変更
                tag_name = 'square_' + str(x) + '_' + str(y)
                if (x, y) in placable:
                    self.canvas.itemconfig(
                        tag_name,
                        fill = PLACABLE_COLOR
                    )
                else:
                    self.canvas.itemconfig(
                        tag_name,
                        fill = BOARD_COLOR
                    )

    def click(self, event):
        '''盤面がクリックされた時の処理'''

        if self.player != YOU:
            #COMが石を置くターンの時は何もしない
            return

        #クリックされた位置がどのマスであるかを計算
        x = event.x // self.square_size
        y = event.y // self.square_size

        if self.checkPlacable(x, y):
            #次に石を置けるマスであれば石を置く
            self.place(x, y, self.color[self.player])

    def place(self, x, y, color):
        '''(x,y)に色がcolorの石を置く'''

        #(x,y)に石が置かれた時に裏返る石を裏返す
        self.reverse(x, y)

        #(x,y)に石を置く(円を描画する)
        self.drawDisk(x, y, color)

        #次に石を置くプレイヤーを決める
        before_player = self.player
        self.nextPlayer()

        if before_player == self.player:
            #前と同じプレイヤーであればスキップされたことになるのでそれを表示
            if self.player != YOU:
                tkinter.messagebox.showinfo('結果', 'あなたのターンをスキップしました')
            else:
                tkinter.messagebox.showinfo('結果', 'COMのターンをスキップしました')
        elif not self.player:
            #次に石が置けるプレイヤーがいない場合はゲーム終了
            self.showResult()
            return

        #次に石が置ける位置を取得して表示
        placable = self.getPlacable()
        self.showPlacable(placable)

        if self.player == COM:
            #次のプレイヤーがCOMの場合は1秒後にCOMに石を置く場所を決めさせる
            self.master.after(1000, self.com)

    def reverse(self, x, y):
        '''(x,y)に石が置かれた時に裏返す必要のある石を裏返す'''

        if self.board[y][x] != None:
            #(x,y)に既に石が置かれている場合は何もしない
            return

        if self.player == COM:
            other = YOU
        else:
            other = COM

        for j in range(-1, 2):
            for i in range(-1, 2):
                #真ん中方向はチェックしても意味が無いので次の方向の確認に移る
                if i == 0 and j == 0:
                    continue

                if x + i < 0 or x + i >= NUM_SQUARE or y + j < 0 or y + j >= NUM_SQUARE:
                    continue

                #隣が相手の色で無ければその方向で裏返せる石はない
                if self.board[y + j][x + i] != self.color[other]:
                    continue

                #置こうとしているマスから遠い方向へ1マスずつ確認
                for s in range(2, NUM_SQUARE):
                    #盤面外のマスはチェックしない
                    if x + i * s >= 0 and x + i * s < NUM_SQUARE and y + j * s >= 0 and y + j * s < NUM_SQUARE:

                        if self.board[y + j * s][x + i * s] == None:
                            #自分の石が見つかる前に空きがある場合
                            #この方向の石は裏返せないので次の方向をチェック
                            break

                        #その方向に自分の色の石があれば石が裏返せる
                        if self.board[y + j * s][x + i * s] == self.color[self.player]:
                            for n in range(1, s):
                                #盤面の石の管理リストを石を裏返した状態に更新
                                self.board[y + j * n][x + i * n] = self.color[self.player]

                                #石の色を変更することで石の裏返しを実現
                                tag_name = 'disk_' + str(x + i * n) + '_' + str(y + j * n)
                                self.canvas.itemconfig(
                                    tag_name,
                                    fill = self.color[self.player]
                                )

                            break

    def nextPlayer(self):
        '''次に石を置くプレイヤーを決める'''

        before_player = self.player

        #石を置くプレイヤーを切り替える
        if self.player == YOU:
            self.player = COM
        else:
            self.player = YOU

        #切り替え後のプレイヤーが石を置けるかどうかを確認
        placable = self.getPlacable()

        if len(placable) == 0:
            #石が置けないのであればスキップ
            self.player = before_player

            #スキップ後のプレイヤーが石を置けるかどうかを確認
            placable = self.getPlacable()

            if len(placable) == 0:
                #それでも置けないのであれば両者とも石を置けないということ
                self.player = None
                self.showResult()

    def showResult(self):
        '''ゲーム終了時の結果を表示する'''

        #それぞれの色の石の数を数える
        num_your = 0
        num_com = 0

        for y in range(NUM_SQUARE):
            for x in range(NUM_SQUARE):
                if self.board[y][x] == YOUR_COLOR:
                    num_your += 1
                elif self.board[y][x] == COM_COLOR:
                    num_com += 1

        start_button['state'] = "normal"

        #結果をメッセージボックスで表示する
        if str(num_your) > str(num_com):
            tkinter.messagebox.showinfo('結果', 'あなた' + str(num_your) + ' , ' + 'COM' + str(num_com) + '\nあなたの勝ちです')
        elif str(num_your) < str(num_com):
            tkinter.messagebox.showinfo('結果', 'あなた' + str(num_your) + ' , ' + 'COM' + str(num_com) + '\nCOMの勝ちです')
        else:
            tkinter.messagebox.showinfo('結果', 'あなた' + str(num_your) + ' , ' + 'COM' + str(num_com) + '\n引き分けです')

        #初期化
        self.clear_self_data()
        #self.canvas.delete("all")
        self.initOthello()

    def clear_self_data(self):
        self.__dict__.clear()

    def com(self):
        '''COMに石を置かせる'''

        #石が置けるマスを取得
        original_placable = self.getPlacable()

        current_list = []

        #現在のマスの状況を保存
        for i in self.board:
            for j in i:
                current_list.append(j)

        current = tuple(current_list)

        #石が置けるマス全てを繰り返し処理
        for temporaryHand in range(len(original_placable)):

            current_list = np.array(current).reshape(8, 8).tolist()

            self.board = current_list

            cpu_hand_x = original_placable[temporaryHand][0]
            cpu_hand_y = original_placable[temporaryHand][1]

            #(cpu_hand_x,cpu_hand_y)に石が置かれた時に裏返る石を裏返す
            self.reverse(cpu_hand_x, cpu_hand_y)

            self.board[cpu_hand_y][cpu_hand_x] = COM_COLOR

            #次に石を置くプレイヤーを決める
            self.nextPlayer()

            #次に石が置ける位置を取得して表示
            next_placable = self.getPlacable()
            self.showPlacable(next_placable)

            COM_count = []

            #盤面を記録している2次元配列を1次元配列に置き換え
            for i in self.board:
                for j in i:
                    COM_count.append(j)

            before_count = 0

            first_move_list = []

            for i in self.board:
                for j in i:
                    first_move_list.append(j)

            first_move = tuple(first_move_list)

            for j in range(len(next_placable)):

                first_move_list = np.array(first_move).reshape(8, 8).tolist()

                self.board = first_move_list

                player_hand_x = next_placable[j][0]
                player_hand_y = next_placable[j][1]

                self.reverse(player_hand_x, player_hand_y)

                self.board[player_hand_y][player_hand_x] = YOUR_COLOR

                YOUR_count = []

                #盤面を記録している2次元配列を1次元配列に置き換え
                for i in self.board:
                    for j in i:
                        YOUR_count.append(j)

                count = YOUR_count.count(COM_COLOR)

                if before_count < count:
                    global count_max
                    before_count = count
                    count_max = temporaryHand

        self.player = COM

        current_list = np.array(current).reshape(8, 8).tolist()

        self.board = current_list

        for i in range(NUM_SQUARE):
            for j in range(NUM_SQUARE):

                if self.board[j][i] != None:
                    tag_name = 'disk_' + str(i) + '_' + str(j)
                    stone_color = self.board[j][i]

                    self.canvas.itemconfig(
                        tag_name,
                        fill = stone_color
                    )

        #石が置けるマスを取得
        original_placable = self.getPlacable()

        x, y = original_placable[count_max]

        #石を置く
        self.place(x, y, COM_COLOR)

#ランダムにリストから選択
com = random.choice(list)

#画像読み込み
image_cpu = Image.open("./image/" + com + ".png")
image_rock = Image.open("./image/rock.png")
image_scissors = Image.open("./image/scissors.png")
image_paper = Image.open("./image/paper.png")

#画像サイズ調整
image_cpu_resize = image_cpu.resize((100, 100))
image_rock_resize = image_rock.resize((100, 100))
image_scissors_resize = image_scissors.resize((100, 100))
image_paper_resize = image_paper.resize((100, 100))

#画像表示
cpu = ImageTk.PhotoImage(image_cpu_resize)
rock = ImageTk.PhotoImage(image_rock_resize)
scissors = ImageTk.PhotoImage(image_scissors_resize)
paper = ImageTk.PhotoImage(image_paper_resize)

#ボタン作成
button_rock = tk.Button(sub_win, image=rock, compound="none", command=rock_click)
button_scissors = tk.Button(sub_win, image=scissors, compound="none", command=scissors_click)
button_paper = tk.Button(sub_win, image=paper, compound="none", command=paper_click)

#キャンバス作成
canvas_cpu = tk.Canvas(sub_win, bg='white', height=110, width=110, relief='raised', bd=2)

#ラベル内容
label_draw = tk.Label(sub_win, text='あいこです。もう一度手を選択して下さい。')
label_win = tk.Label(sub_win, text='あなたの勝ちです。')
label_lose = tk.Label(sub_win, text='CPUの勝ちです。')

#ラベル表示
label_draw.place_forget()
label_win.place_forget()
label_lose.place_forget()

#ボタン表示位置
button_rock.place(x=50, y=250)
button_scissors.place(x=200, y=250)
button_paper.place(x=350, y=250)

othello = Othello(window)

start_button = ttk.Button(window, text="スタート", width=15, padding=[5,10], command=janken)
start_button.place(x=250, y=430)

window.mainloop()