import random

class card:
    suits: str
    ranks: str
    value: int
    def __init__(self, suits: str, ranks: str, value: int):
        self.suits = suits
        self.ranks = ranks
        self.value = value

class deck:
    cards: list[card] = []

    def __init__(self):
        self.cards: list[card] = []
        suits = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
        ranks = {
            '2': 2, '3': 3, '4': 4, '5': 5, '6': 6,
            '7': 7, '8': 8, '9': 9, '10': 10,
            'Jack': 11, 'Queen': 12, 'King': 13, 'Ace': 1
        }
        for suit in suits:
            for rank, value in ranks.items():
                self.cards.append(card(suit, rank, value))

    def shuffle(self):
        random.shuffle(self.cards)

class user:
    user_id: int
    user_nickname: str = ""
    def __init__(self, user_id: int, user_nickname: str):
        self.user_id = user_id
        self.user_nickname = user_nickname
        self.hand: list[card] = []
    
    def add_card(self, card: card):
        self.hand.append(card)
    
    def calculate_hand_value(self):
        value = sum(card.value for card in self.hand)
        # Adjust for Aces
        aces = sum(1 for card in self.hand if card.ranks == 'Ace')
        while value > 21 and aces:
            value -= 10
            aces -= 1
        return value
    
class blackjack:
    deck: deck
    def __init__(self):
        self.deck = deck()
        self.deck.shuffle()
        self.players: dict[int, user] = {}
        self.started: bool = False
        self.ended: bool = False
        self.round_id: int = 0
        self.this_round_player: int | None = None
        self.stopped_players: set[int] = set()

    def add_player(self, user_id: int, user_nickname: str):
        if user_id not in self.players and len(self.players) < 5 and not self.started:
            self.players[user_id] = user(user_id, user_nickname)

    def start_game(self):
        if self.started or len(self.players) <= 1:
            return False
        self.started = True
        players = list(self.players.keys())
        self.this_round_player = players[-1]
        return True
    
    def deal_card(self, user_id: int):
        if self.started and user_id in self.players and user_id not in self.stopped_players:
            deal = self.deck.cards.pop()
            player = self.players[user_id]
            player.add_card(deal)
            if player.calculate_hand_value() > 21:
                self.stopped_players.add(user_id)
            elif player.calculate_hand_value() == 21:
                self.stopped_players.add(user_id)
            return deal
        return None
    
    def stop_player(self, user_id: int):
        if self.started and user_id in self.players and user_id not in self.stopped_players:
            self.stopped_players.add(user_id)
            print(self.stopped_players)
    
    def returnThisRoundInfo(self):
        info = f"Round {self.round_id} Info:"
        for player in self.players.values():
            hand_description = ', '.join([f"{c.ranks} of {c.suits}" for c in player.hand])
            hand_value = player.calculate_hand_value()
            info += f"\n玩家[{player.user_nickname}]的手牌: {hand_description} (总值: {hand_value})"
        return info
    
    def next_player(self):
        player_ids = list(self.players.keys())
        current_index = player_ids.index(self.this_round_player)
        print(self.stopped_players)
        print(self.players)
        if len(self.stopped_players) >= len(self.players):
            info = "所有玩家均已停牌，游戏结束!\n"
            info += self.returnThisRoundInfo()
            result, winner = self.end_game()
            info += result
            return info, winner
        elif self.this_round_player in self.stopped_players:
            next_index = current_index % len(player_ids)
        else:
            next_index = (current_index + 1) % len(player_ids)
        player_ids = [pid for pid in player_ids if pid not in self.stopped_players]
        self.this_round_player = player_ids[next_index]
        self.round_id += 1
        info = f"Round {self.round_id}:\n 轮到玩家[{self.players[self.this_round_player].user_nickname}]行动[{self.players[self.this_round_player].calculate_hand_value()}]\n[要牌请输入“要牌”，不要牌请输入“停牌”]"
        return info, None
    
    def end_game(self):
        self.started = False
        self.ended = True
        winner: user = None
        info = "\n游戏结束！最终结果:"
        for player in self.players.values():
            hand_value = player.calculate_hand_value()
            if hand_value <= 21:
                if winner is None or hand_value > winner.calculate_hand_value():
                    winner = player
        if winner is None:
            info += "\n所有玩家均爆点，无获胜者。"
            winner = None
        else:
            info += f"\n获胜者是玩家[{winner.user_nickname}]，手牌总值为{winner.calculate_hand_value()}！"
            winner = str(winner.user_id)
        return info, winner
    
    def returnJoinerInfo(self):
        info = "当前加入21点游戏的玩家有:"
        for player in self.players.values():
            info += f"\n玩家[{player.user_nickname}]"
        return info