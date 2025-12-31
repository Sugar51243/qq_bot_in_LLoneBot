import os
from src.classify.game.blackjack import blackjack
try:
    from OneBotConnecter.MessageType import MessageChain, AtMessage
except:
    os.system("pip install OneBotConnecter")
    exec("from OneBotConnecter.MessageType import MessageChain, AtMessage")
try:
    from config_io import Config
except:
    os.system("pip install config-io")
    exec("from config_io import Config")


blackjack_group = {} #groupid: blackjack instance

async def gameMode(bot, message, raw_message, be_at):
    try:
        await blackjackMode(bot, message, raw_message, be_at)
    except Exception as e:
        group_id = message['group_id']
        await bot.send_group_msg(
            group_id=group_id,
            message=MessageChain(f"游戏模块出现错误: {str(e)}")
        )
        del blackjack_group[group_id]
        traceback.print_exc()

async def blackjackMode(bot, message, raw_message, be_at):
    group_id = message['group_id']

    if raw_message == "21点":
        if group_id not in blackjack_group:
            blackjack_group[group_id] = blackjack()
            await bot.send_group_msg(
                group_id=group_id,
                message=MessageChain(f"21点游戏已创建！发送“加入21点”加入游戏，最多4人。")
            )
        else:
            await bot.send_group_msg(
                group_id=group_id,
                message=MessageChain(f"当前已有21点游戏进行中，发送“加入21点”加入游戏。")
            )

    if raw_message == "加入21点":
        user_id = message['user_id']
        nickname = message['sender']['nickname']
        if group_id in blackjack_group and not blackjack_group[group_id].started:
            game = blackjack_group[group_id]
            game.add_player(user_id, nickname)
            await bot.send_group_msg(
                group_id=group_id,
                message=MessageChain(game.returnJoinerInfo())
            )
        else:
            await bot.send_group_msg(
                group_id=group_id,
                message=MessageChain(f"当前没有可加入的21点游戏。")
            )
    
    if raw_message == "开始21点":
        if group_id in blackjack_group:
            game = blackjack_group[group_id]
            if not game.started:
                if game.start_game():
                    await bot.send_group_msg(
                        group_id=group_id,
                        message=MessageChain(f"21点游戏开始！")
                    )
                    #首轮自动为所有玩家抽取1张卡牌
                    for player in game.players.values():
                        card = game.deal_card(player.user_id)
                    #整合当前所有玩家手牌信息并展示
                    await bot.send_group_msg(
                        group_id=group_id,
                        message=MessageChain(game.returnThisRoundInfo())
                    )
                    result, winner = game.next_player()
                    await bot.send_group_msg(
                        group_id=group_id,
                        message=MessageChain(result)
                    )
                else:
                    await bot.send_group_msg(
                        group_id=group_id,
                        message=MessageChain(f"无法开始游戏，可能是因为玩家不足2人。")
                    )
            else:
                await bot.send_group_msg(
                    group_id=group_id,
                    message=MessageChain(f"游戏已开始，无法重复开始。")
                )
        else:
            await bot.send_group_msg(
                group_id=group_id,
                message=MessageChain(f"当前没有可开始的21点游戏。")
            )
    
    if group_id in blackjack_group:
        game = blackjack_group[group_id]
        if game.ended:
            del blackjack_group[group_id]
        if game.started:
            user_id = message['user_id']
            if user_id == game.this_round_player:
                if raw_message == "要牌":
                    card = game.deal_card(user_id)
                    player = game.players[user_id]
                    hand_value = player.calculate_hand_value()
                    response = f"玩家[{player.user_nickname}]抽到: {card.ranks} of {card.suits} (手牌总值: {hand_value})\n"
                    if hand_value > 21:
                        response += f"玩家[{player.user_nickname}]爆点！\n"
                    elif hand_value == 21:
                        response += f"玩家[{player.user_nickname}]已满值！\n"
                    await bot.send_group_msg(
                        group_id=group_id,
                        message=MessageChain(response)
                    )
                    result, winner = game.next_player()
                    await bot.send_group_msg(
                        group_id=group_id,
                        message=MessageChain(result)
                    )
                elif raw_message == "停牌":
                    game.stop_player(user_id)
                    response = f"玩家[{game.players[user_id].user_nickname}]选择停牌。\n"
                    await bot.send_group_msg(
                        group_id=group_id,
                        message=MessageChain(response)
                    )
                    result, winner = game.next_player()
                    await bot.send_group_msg(
                        group_id=group_id,
                        message=MessageChain(result)
                    )
                if winner != None:
                    await add_scroes(bot = bot, msg = message, score = 5)
                    msg = MessageChain([AtMessage(int(winner))])
                    msg.add(f" 获得 {5} 积分！")
                    await bot.send_group_msg(int(message["group_id"]), msg)
                    del blackjack_group[group_id]

async def add_scroes(bot, msg, score = 0, add_type: str = "sp"):
    old_rank = -1
    user_id = msg["sender"]["user_id"]
    if user_id is not str:
        user_id = str(user_id)
    #读取文件
    users = Config.load_from_file("data/classify/general/guess_scores.json")
    try:
        data = users[user_id]
    except:
        data = {"scores": 0.0, "chart": 0, "card": 0, "sp": 0.0, "name": msg["sender"]["nickname"], "cards": [], "use_card": True, "time": 0}
    #计算排名
    try:
        user_list = list(users.keys())
        user_list.sort(key=lambda uid: users[uid]["scores"], reverse=True)
        old_rank = user_list.index(user_id)
    except: pass
    #更新数据
    if data["use_card"] and score > 0:
        card_bonus = 1
        if len(data["cards"]) > 0:
            card_bonus = 1 + data["cards"].pop(0)
        score = score * card_bonus
        if card_bonus > 1:
            message = MessageChain([f"\n使用卡牌加成 x{1+card_bonus}，本次获得积分提升至 {int(score)} 分！"])
            await bot.reply_to_message(msg, message)
    data["scores"] += score
    if add_type == "sp":
        data["sp"] += score
    else:
        data[add_type] += 1
    users[user_id] = data
    #写入文件
    users.dump_to_file("data/classify/general/guess_scores.json")
    #计算排名
    user_list = list(users.keys())
    user_list.sort(key=lambda uid: users[uid]["scores"], reverse=True)
    rank = user_list.index(user_id)
    #输出信息
    if rank > (old_rank) or old_rank == -1:
        message = MessageChain([f"恭喜你！你的总分提升到第 {rank+1} 名！"])
        await bot.reply_to_message(msg, message)
