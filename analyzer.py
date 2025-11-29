class Analyzer:
    def __init__(self):
        self.model_ready = False

    def train_model(self, data):
        self.model_ready = True

    def predict_outcome(self, match_data):
        if not self.model_ready:
            raise Exception("Модель не обучена.")

        team1_score = match_data['team1_goals'] + match_data['shots'] * 0.1 + match_data['possession'] * 0.02
        team2_score = match_data['team2_goals'] + match_data['shots'] * 0.05 + (100 - match_data['possession']) * 0.02

        total = team1_score + team2_score

        prob1 = (team1_score / total) * 100
        prob2 = (team2_score / total) * 100

        return {
            "Команда 1": prob1,
            "Команда 2": prob2
        }
