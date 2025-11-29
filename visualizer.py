import matplotlib.pyplot as plt

class Visualizer:
    def plot_team_stats(self, data):
        if "goals" not in data.columns:
            print("Нет колонки 'goals'.")
            return

        plt.hist(data["goals"], bins=10)
        plt.xlabel("Голы")
        plt.ylabel("Количество матчей")
        plt.title("Распределение голов по матчам")
        plt.show()
