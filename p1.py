import tkinter as tk
from tkinter import ttk
import numpy as np
import pandas as pd
from tkinter import filedialog
import matplotlib.pyplot as plt
import seaborn as sns
from PIL import Image, ImageTk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.animation as animation
import threading
window = tk.Tk()
window.configure(bg="black")
image_path = "logo.jpg"
original_image = Image.open(image_path)
resized_image = original_image.resize((450, 400))
image = ImageTk.PhotoImage(resized_image)
image_label = tk.Label(window, image=image, bg="black")
image_label.pack()
image_path1 = "glowtext.png"
original_image1 = Image.open(image_path1)
resized_image1 = original_image1.resize((1200, 80))
image1 = ImageTk.PhotoImage(resized_image1)
original_image1 = Image.open(image_path)
image_label1 = tk.Label(window, image=image1, bg="black")
image_label1.pack()
window.title("Valorant Esports Data Analysis")
def load_data():
    file_paths = filedialog.askopenfilenames(filetypes=[("CSV files", "*.csv")])
    if file_paths:
        for file_path in file_paths:
            if "Players" in file_path:
                global players
                players = pd.read_csv(file_path)  
            elif "Teams" in file_path:
                global teams
                teams = pd.read_csv(file_path)  
            else:
                print("Unknown CSV file")
        load_data_button.pack_forget()  
        players_data_button.pack(side="top", padx=10)
        teams_data_button.pack(side="top", pady=10)

def display_top_teams():
    if 'teams' in globals():
        table_window = tk.Toplevel(window)
        table_window.title("Top 10 Teams")
        top_teams = teams.head(10)
        tree = ttk.Treeview(table_window, columns=list(top_teams.columns), show='headings')
        for col in top_teams.columns:
            tree.heading(col,text=col)
            tree.column(col, anchor=tk.CENTER)
        for index, row in top_teams.iterrows():
            tree.insert('', 'end', values=row.tolist())
        tree.pack()
        t1=pd.read_csv("Teams.csv")
        display_table = ttk.Treeview(window,columns=list(t1.columns), show='headings')
        for col in t1.columns:
            display_table.heading(col, text=col)

def display_s_tier_teams():
    if 'teams' in globals():
        team = teams[['Team', 'Rank', 'S Tier']]
        s_tier = team[team['S Tier'] >= 1]
        table_window = tk.Toplevel()
        table_window.title("Teams That Won S-Tier Events")
        tree = ttk.Treeview(table_window,columns=list(s_tier.columns),show='headings',height=12)
        for col in s_tier.columns:
            tree.heading(col, text=col)
        for index, row in s_tier.iterrows():
            values = row.tolist()
            tree.insert('', 'end', values=values)
        for col in s_tier.columns:
            tree.column(col, anchor=tk.CENTER)
        tree.pack()

def display_teams_with_most_medals_plot():
    if 'teams' in globals():
        teams['medals_total'] = teams['Gold'] + teams['Silver'] + teams['Bronze']
        teams_with_most_medals = teams.sort_values(by='medals_total', ascending=False).head(10)
        graph_window = tk.Toplevel()
        graph_window.title('Teams With Most Medals Bar Plot')
        fig, ax = plt.subplots(figsize=(15,6))
        sns.barplot(data=teams_with_most_medals, x='medals_total', y='Team', ax=ax)
        ax.set(title='Teams With Most Medals')
        canvas = FigureCanvasTkAgg(fig, master=graph_window)
        canvas.draw()
        canvas.get_tk_widget().pack()

def display_teams_with_most_gold_medals_plot():
    if 'teams' in globals():
        teams_with_most_gold_medals = teams.sort_values(by='Gold', ascending=False).head(10)
        graph_window = tk.Toplevel()
        graph_window.title('Players With Most Gold Medals Bar Plot')
        fig, ax = plt.subplots(figsize=(15,6))
        sns.barplot(data=teams_with_most_gold_medals, x='Gold', y='Team', ax=ax)
        ax.set(title='Teams With Most Gold Medals')
        canvas = FigureCanvasTkAgg(fig, master=graph_window)
        canvas.draw()
        canvas.get_tk_widget().pack()

def display_teams_with_most_silver_medals_plot():
    if 'teams' in globals():
        teams_with_most_silver_medals = teams.sort_values(by='Silver', ascending=False).head(10)
        graph_window = tk.Toplevel()
        graph_window.title('Players With Most Silver Medals Bar Plot')
        fig, ax = plt.subplots(figsize=(15,6))
        sns.barplot(data=teams_with_most_silver_medals, x='Silver', y='Team', ax=ax)
        ax.set(title='Teams With Most Silver Medals')
        canvas = FigureCanvasTkAgg(fig, master=graph_window)
        canvas.draw()
        canvas.get_tk_widget().pack()

def display_teams_with_most_bronze_medals_plot():
    if 'teams' in globals():
        teams_with_most_bronze_medals = teams.sort_values(by='Bronze', ascending=False).head(10)
        graph_window = tk.Toplevel()
        graph_window.title('Players With Most bronze Medals Bar Plot')
        fig, ax = plt.subplots(figsize=(15,6))
        sns.barplot(data=teams_with_most_bronze_medals, x='Bronze', y='Team', ax=ax)
        ax.set(title='Teams With Most Bronze Medals')
        canvas = FigureCanvasTkAgg(fig, master=graph_window)
        canvas.draw()
        canvas.get_tk_widget().pack()

def display_teams_earnings_vs_rank_plot():
    image_window = tk.Toplevel()
    image_window.title("Image Display")
    image_path = "re2.png" 
    png_image = Image.open(image_path)
    png_photo = ImageTk.PhotoImage(png_image)
    image_label = tk.Label(image_window, image=png_photo)
    image_label.image = png_photo 
    image_label.pack() 
        
def teams_earnings_vs_tier_heatmap():
    image_window = tk.Toplevel()
    image_window.title("Image Display")
    image_path = "hm2.png" 
    png_image = Image.open(image_path)
    png_photo = ImageTk.PhotoImage(png_image)
    image_label = tk.Label(image_window, image=png_photo)
    image_label.image = png_photo 
    image_label.pack()         
     
def show_buttons():
    top_teams_window = tk.Toplevel()
    top_teams_window.title("Teams Data Analysis")
    top_teams_window.configure(bg="black")
    top_teams_button = tk.Button(top_teams_window, text="Display Top Teams", command=display_top_teams,bg='red', fg='black')
    s_tier_teams_button = tk.Button(top_teams_window, text="Display S-Tier Teams", command=display_s_tier_teams,bg='red', fg='black')
    teams_with_most_medals_button = tk.Button(top_teams_window, text="Display Teams with Most Medals", command=display_teams_with_most_medals_plot,bg='red', fg='black')
    teams_with_most_gold_medals_button = tk.Button(top_teams_window, text="Display Teams with Most Gold Medals", command=display_teams_with_most_gold_medals_plot,bg='red', fg='black')
    teams_with_most_silver_medals_button = tk.Button(top_teams_window, text="Display Teams with Most Silver Medals", command=display_teams_with_most_silver_medals_plot,bg='red', fg='black')
    teams_with_most_bronze_medals_button = tk.Button(top_teams_window, text="Display Teams with Most Bronze Medals", command=display_teams_with_most_bronze_medals_plot,bg='red', fg='black')
    earnings_vs_rank_plot_button = tk.Button(top_teams_window, text="Display Earnings vs. Rank Plot", command=display_teams_earnings_vs_rank_plot,bg='red', fg='black')
    earnings_vs_tier_heatmap_button = tk.Button(top_teams_window, text="Display Earnings vs. Tier Heatmap", command=teams_earnings_vs_tier_heatmap,bg='red', fg='black')
    top_teams_button.pack(pady=20)
    s_tier_teams_button.pack(pady=20)
    teams_with_most_medals_button.pack(pady=20)
    teams_with_most_gold_medals_button.pack(pady=20)
    teams_with_most_silver_medals_button.pack(pady=20)
    teams_with_most_bronze_medals_button.pack(pady=20)
    earnings_vs_rank_plot_button.pack(pady=20)
    earnings_vs_tier_heatmap_button.pack(pady=20)

def display_top_players():
    if 'players' in globals():
        table_window = tk.Toplevel(window)
        table_window.title("Top 10 Players")
        top_players = players.head(10)
        tree = ttk.Treeview(table_window, columns=list(top_players.columns), show='headings')
        for col in top_players.columns:
            tree.heading(col,text=col)
            tree.column(col, anchor=tk.CENTER)
        for index, row in top_players.iterrows():
            tree.insert('', 'end', values=row.tolist())
        tree.pack()
        t2=pd.read_csv("Players.csv")
        display_table1 = ttk.Treeview(window,columns=list(t2.columns), show='headings')
        for col1 in t2.columns:
            display_table1.heading(col1, text=col1)

def display_s_tier_players():
    if 'players' in globals():
        s_tier_players=players[players['S Tier'] >= 1]
        table_window = tk.Toplevel()
        table_window.title("Players That Won S-Tier Events")
        tree = ttk.Treeview(table_window,columns=list(s_tier_players.columns),show='headings',height=12)
        for col in s_tier_players.columns:
            tree.heading(col, text=col)
        for index, row in s_tier_players.iterrows():
            values = row.tolist()
            tree.insert('', 'end', values=values)
        for col in s_tier_players.columns:
            tree.column(col, anchor=tk.CENTER)
        tree.pack()

def display_players_with_most_medals_plot():
    if 'players' in globals():
        players['medals_total'] = players['Gold'] + players['Silver'] + players['Bronze']
        players_with_most_medals = players.sort_values(by='medals_total', ascending=False).head(10)
        graph_window = tk.Toplevel()
        graph_window.title('Players With Most Medals Bar Plot')
        fig, ax = plt.subplots(figsize=(15,6))
        sns.barplot(data=players_with_most_medals, x='medals_total', y='Player', ax=ax)
        ax.set(title='Players With Most Medals')
        canvas = FigureCanvasTkAgg(fig, master=graph_window)
        canvas.draw()
        canvas.get_tk_widget().pack()

def display_players_with_most_gold_medals_plot():
    if 'players' in globals():
        players_with_most_gold_medals = players.sort_values(by='Gold', ascending=False).head(10)
        graph_window = tk.Toplevel()
        graph_window.title('Players With Most Gold Medals Bar Plot')
        fig, ax = plt.subplots(figsize=(15,6))
        sns.barplot(data=players_with_most_gold_medals, x='Gold', y='Player', ax=ax)
        ax.set(title='Players With Most Gold Medals')
        canvas = FigureCanvasTkAgg(fig, master=graph_window)
        canvas.draw()
        canvas.get_tk_widget().pack()

def display_players_with_most_silver_medals_plot():
    if 'players' in globals():
        players_with_most_silver_medals = players.sort_values(by='Silver', ascending=False).head(10)
        graph_window = tk.Toplevel()
        graph_window.title('Players With Most Gold Medals Bar Plot')
        fig, ax = plt.subplots(figsize=(15,6))
        sns.barplot(data=players_with_most_silver_medals, x='Silver', y='Player', ax=ax)
        ax.set(title='Players With Most Silver Medals')
        canvas = FigureCanvasTkAgg(fig, master=graph_window)
        canvas.draw()
        canvas.get_tk_widget().pack()

def display_players_with_most_bronze_medals_plot():
    if 'players' in globals():
        players_with_most_bronze_medals = players.sort_values(by='Bronze', ascending=False).head(10)
        graph_window = tk.Toplevel()
        graph_window.title('Players With Most Gold Medals Bar Plot')
        fig, ax = plt.subplots(figsize=(15,6))
        sns.barplot(data=players_with_most_bronze_medals, x='Bronze', y='Player', ax=ax)
        ax.set(title='Players With Most Bronze Medals')
        canvas = FigureCanvasTkAgg(fig, master=graph_window)
        canvas.draw()
        canvas.get_tk_widget().pack()

def player_earnings_vs_tier_heatmap():
    image_window = tk.Toplevel()
    image_window.title("Image Display")
    image_path = "hm1.png" 
    png_image = Image.open(image_path)
    png_photo = ImageTk.PhotoImage(png_image)
    image_label = tk.Label(image_window, image=png_photo)
    image_label.image = png_photo 
    image_label.pack()  

def display_players_earnings_vs_rank_plot():
    image_window = tk.Toplevel()
    image_window.title("Image Display")
    image_path = "re1.png" 
    png_image = Image.open(image_path)
    png_photo = ImageTk.PhotoImage(png_image)
    image_label = tk.Label(image_window, image=png_photo)
    image_label.image = png_photo 
    image_label.pack() 

def show_buttons1():
    top_players_window = tk.Toplevel()
    top_players_window.title("Players Data Analysis")
    top_players_window.configure(bg="black")
    top_players_button = tk.Button(top_players_window, text="Display Top Players", command=display_top_players,bg='red', fg='black')
    s_tier_players_button = tk.Button(top_players_window, text="Display S-Tier Players", command=display_s_tier_players,bg='red', fg='black')
    players_with_most_medals_button = tk.Button(top_players_window, text="Display Players with Most Medals", command=display_players_with_most_medals_plot,bg='red', fg='black')
    players_with_most_gold_medals_button = tk.Button(top_players_window, text="Display Players with Most Gold Medals", command=display_players_with_most_gold_medals_plot,bg='red', fg='black')
    players_with_most_silver_medals_button = tk.Button(top_players_window, text="Display Players with Most Silver Medals", command=display_players_with_most_silver_medals_plot,bg='red', fg='black')
    players_with_most_bronze_medals_button = tk.Button(top_players_window, text="Display Players with Most Bronze Medals", command=display_players_with_most_bronze_medals_plot,bg='red', fg='black')
    earnings_vs_rank_plot_button = tk.Button(top_players_window, text="Display Player Earnings vs. Rank Plot", command=display_players_earnings_vs_rank_plot,bg='red', fg='black')
    earnings_vs_tier_heatmap_button = tk.Button(top_players_window, text="Display Player Earnings vs. Tier Heatmap", command=player_earnings_vs_tier_heatmap,bg='red', fg='black')
    top_players_button.pack(pady=20)
    s_tier_players_button.pack(pady=20)
    players_with_most_medals_button.pack(pady=20)
    players_with_most_gold_medals_button.pack(pady=20)
    players_with_most_silver_medals_button.pack(pady=20)
    players_with_most_bronze_medals_button.pack(pady=20)
    earnings_vs_rank_plot_button.pack(pady=20)
    earnings_vs_tier_heatmap_button.pack(pady=20)

load_data_button = tk.Button(window, text="Load Data", width=20, height=3, bg='red', fg='black', command=load_data)
load_data_button.pack(side="top")
players_data_button = tk.Button(window, text="Players Data", width=20, height=3, bg='green', fg='black',command=show_buttons1)
teams_data_button = tk.Button(window, text="Teams Data", width=20, height=3, bg='blue', fg='black',command=show_buttons)
window.mainloop()
