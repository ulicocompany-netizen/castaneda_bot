# English texts of the Raven
STALKING_TASKS = [
    "Today your prey is your words. Notice every time you say «I have to» or «I'm forced to». Don't change it. Just catch yourself and ask: «Who is speaking? Warrior or victim?»\n\nWrite below how many times you fell into this trap today, or describe one such moment.",
    "Your task today is to stalk your self-pity. Every time you start thinking «poor me, how unlucky I am» — stop. Record that moment.\n\nWrite how many times you caught yourself, or describe one case.",
    "Today watch your inner dialogue. When you start arguing with yourself, justifying or scolding yourself — notice it. Those are moths buzzing.\n\nWrite when you heard them loudest.",
    "Your prey today is your reactions. When someone stings you — don't react at once. Count to three. Then decide whether to answer.\n\nWrite how many times you managed to stop, and how many times you got hooked.",
    "Today stalk your self-importance. Every time you think «what will they think of me» or «I must show that I...» — notice it. That is the crown you carry.\n\nWrite how many times you caught yourself."
]
SHIFT_TASKS = [
    "🌀 The assemblage point shifts where habit breaks.\n\nToday do one habitual action with your non-dominant hand. Brush your teeth, open a door, take a cup. Feel how the world becomes strange and new for a second. That is magic.",
    "🌀 Your tonal is used to looking at the ground.\n\nToday, on a familiar road, look only up. At branches, clouds, rooflines. Don't look at the asphalt. Notice how many details you usually ignore.",
    "🌀 Do something deliberately slowly today.\n\nSomething you usually do in a hurry (eating, walking, replying). Stretch the time. Feel the resistance of your rushing mind. Stop it.",
    "🌀 Dreaming is the shift of the assemblage point in sleep.\n\nTonight before sleep, intend to see your hands in a dream. Tell yourself: «I will see my hands». In the morning, write down whether it happened.",
    "🌀 Your perception is used to certain routes.\n\nToday go home by a different road. Even if it takes longer. Feel how the world becomes new.",
    "🌀 You are used to saying «yes» or «no» automatically.\n\nToday pause for 2 seconds before each answer. Feel how it changes the conversation."
]
MAGIC_PHRASES = [
    "🔮 Death stands at your left shoulder. Walk today as if it were your last dance. Light and impeccable.",
    "🔮 Your intention for today: don't feed importance. Not once. Not even in small things.",
    "🔮 Today you will see a sign. Don't try to solve it with your mind. Just notice it and walk on.",
    "🔮 A path with heart is the one where you don't drag yourself. If something feels heavy today, ask: «Does this path have a heart?»",
    "🔮 Tonight, look at the stars. Remember how small you are in this universe. It doesn't humiliate. It frees.",
    "🔮 Your intention: to act, not to prepare to act. Take one step you've been postponing.",
    "🔮 Today don't seek the easy path. Seek the warrior's path. It isn't easier, but it is yours.",
    "🔮 Remember: you are not what you think. You are what you do when you don't think.",
    "🔮 Today your advisor is silence. Listen to it more often than to your mind.",
    "🔮 Don't fear losing what you never chose. A crown you never put on is not yours."
]
DON_JUAN_QUOTES = [
    "Death is the only wise advisor. When life feels heavy, ask it. It will answer: nothing matters except its touch.",
    "Impeccability is not morality. It is the economy of power.",
    "A warrior takes responsibility for his actions, even the smallest.",
    "Erasing personal history frees you from others' expectations.",
    "The world is incomprehensible. It is a mystery. And you are a mystery in it.",
    "A path with heart is easy; it takes no effort to love it.",
    "To act without expecting reward — that is the warrior's doing.",
    "Self-pity is the heaviest burden. Drop it, and you will feel lightness.",
    "The assemblage point shifts when the warrior stops talking to himself.",
    "Not-doing is the key to stopping the world.",
    "Power doesn't demand faith. It demands attention.",
    "You are not the story of your thoughts. You are the attention that watches them."
]
PS_LINES = [
    "P.S. Good. You did it. Walk on.",
    "P.S. I see you trying. Don't be hard on yourself.",
    "P.S. The moths have gone quiet? Good.",
    "P.S. Death nods. You were honest today.",
    "P.S. Don't tell anyone about this. Power loves silence."
]
PS_NAME_LINES = [
    "P.S. {name}, the moths have gone quiet? Good.",
    "P.S. {name}, power doesn't ask your name. It asks your intention.",
    "P.S. {name}, you are here again. That is already a path."
]
DIAGNOSE_QUESTION = "🦅 Power doesn't vanish without a trace. It leaks where you feed your importance or indulge.\n\nLook inside right now. Which of this resonates in you the strongest?"
DIAGNOSE_LABELS = {
    "diagnose_anger": "irritation and anger",
    "diagnose_apathy": "apathy and emptiness",
    "diagnose_rush": "rush and racing thoughts",
    "diagnose_prove": "the need to prove something"
}
DIAGNOSE_ANSWERS = {
    "diagnose_anger": "Irritation is a wall. You build it because you fear your importance will be touched.\nBut the wall also takes power to maintain.\nLower it. Look at what angers you simply as a fact. Like a stone on the road. Without judgment. Power returns as soon as you stop fighting it.",
    "diagnose_apathy": "You think you are losing power. But emptiness is not the absence of power. It is the silence before the shift.\nThe mistake is trying to fill this silence with noise, scrolling or rush.\nDon't run from it. Stay in it. That is the very stopping of the world you seek.",
    "diagnose_rush": "The moths are buzzing. You try to control what cannot be controlled — your mind.\nThe harder you try to drive them away, the fatter they become.\nLet go of the reins. Let thoughts spin like leaves in the wind, but don't catch them. Just watch them fly by.",
    "diagnose_prove": "You spend the most expensive currency on an imaginary spectator.\nRemind yourself: death stands at your left shoulder. It doesn't care whether you are right or wrong, approved or not.\nAct only for yourself. Everything else is food for the moths."
}
INDULGI_QUESTIONS = [
    {"text": "When your plans collapse, your first reaction is:", "options": [
        {"text": "I look for someone to blame, or pity myself", "score": 2, "callback": "indulgi_q1_a"},
        {"text": "I get angry, but quickly pull myself together", "score": 1, "callback": "indulgi_q1_b"},
        {"text": "I calmly change tactics. These are just new circumstances", "score": 0, "callback": "indulgi_q1_c"}]},
    {"text": "How often do you make promises you don't keep (even to yourself)?", "options": [
        {"text": "Often. Circumstances are always stronger", "score": 2, "callback": "indulgi_q2_a"},
        {"text": "Sometimes, but I find an excuse", "score": 1, "callback": "indulgi_q2_b"},
        {"text": "Almost never. My word is my power", "score": 0, "callback": "indulgi_q2_c"}]},
    {"text": "When criticized, you:", "options": [
        {"text": "Defend myself or get offended", "score": 2, "callback": "indulgi_q3_a"},
        {"text": "Pretend I don't care, but boil inside", "score": 1, "callback": "indulgi_q3_b"},
        {"text": "Listen. If useful — I take it; if not — I cut it off", "score": 0, "callback": "indulgi_q3_c"}]},
    {"text": "Do you feel the world «owes» you fairness or understanding?", "options": [
        {"text": "Yes, constantly", "score": 2, "callback": "indulgi_q4_a"},
        {"text": "Sometimes, when it's hard", "score": 1, "callback": "indulgi_q4_b"},
        {"text": "No. The world owes me nothing. I take what I can", "score": 0, "callback": "indulgi_q4_c"}]},
    {"text": "Your tiredness at the end of the day is most often:", "options": [
        {"text": "The result of endless inner dialogues and anxieties", "score": 2, "callback": "indulgi_q5_a"},
        {"text": "A mix of real tasks and emotional shaking", "score": 1, "callback": "indulgi_q5_b"},
        {"text": "The result of real but impeccable actions. I am calm", "score": 0, "callback": "indulgi_q5_c"}]}
]