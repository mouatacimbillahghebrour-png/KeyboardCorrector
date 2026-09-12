import os
import re
import sys
import time
import ctypes
import threading
import socket
from ctypes import wintypes

import pyperclip
import mouse
import keyboard
import tkinter as tk
from tkinter import ttk, messagebox

import win32gui

try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError as e:
    print("Missing dependency for the system tray feature:", e)
    print("Install the required packages with:")
    print("    pip install pystray pillow")
    raise

# =========================================================
# Keyboard Layouts (unchanged mapping tables)
# =========================================================

ENGLISH_TO_ARABIC = {
    "q": "ض", "w": "ص", "e": "ث", "r": "ق", "t": "ف",
    "y": "غ", "u": "ع", "i": "ه", "o": "خ", "p": "ح",
    "[": "ج", "]": "د",
    "a": "ش", "s": "س", "d": "ي", "f": "ب", "g": "ل",
    "h": "ا", "j": "ت", "k": "ن", "l": "م", ";": "ك",
    "'": "ط",
    "z": "ئ", "x": "ء", "c": "ؤ", "v": "ر", "b": "لا",
    "n": "ى", "m": "ة", ",": "و", ".": "ز", "/": "ظ",
    "`": "ذ",
    "\\": "ذ",
}

ARABIC_TO_ENGLISH = {arabic: english for english, arabic in ENGLISH_TO_ARABIC.items()}

ENGLISH_TO_FRENCH = {
    'q': 'a', 'w': 'z', 'e': 'e', 'r': 'r', 't': 't', 'y': 'y', 'u': 'u', 'i': 'i', 'o': 'o', 'p': 'p',
    'a': 'q', 's': 's', 'd': 'd', 'f': 'f', 'g': 'g', 'h': 'h', 'j': 'j', 'k': 'k', 'l': 'l', ';': 'm',
    'z': 'w', 'x': 'x', 'c': 'c', 'v': 'v', 'b': 'b', 'n': 'n', 'm': ',',
    'Q': 'A', 'W': 'Z', 'E': 'E', 'R': 'R', 'T': 'T', 'Y': 'Y', 'U': 'U', 'I': 'I', 'O': 'O', 'P': 'P',
    'A': 'Q', 'S': 'S', 'D': 'D', 'F': 'F', 'G': 'G', 'H': 'H', 'J': 'J', 'K': 'K', 'L': 'L', ';': 'M',
    'Z': 'W', 'X': 'X', 'C': 'C', 'V': 'V', 'B': 'B', 'N': 'N', 'M': '?',
    ',': ';', '.': ':', '/': '!', "'": 'ù', '?': 'M',
    '[': '^', ']': '$', '\\': '*', '`': '²', '-': ')', '=': '=',
    '!': '!', '@': '"', '#': '£', '$': '$', '%': 'ù', '^': '¨', '&': '&', '*': '*', '(': '(', ')': ')',
    '_': '°', '+': '=', '{': '¨', '}': '£', '|': 'µ', ':': ':', '"': '%', '<': '>', '>': '<', '~': ' ',
}

FRENCH_TO_ENGLISH = {french: english for english, french in ENGLISH_TO_FRENCH.items()}

FRENCH_TO_ARABIC = {}
for _en, _fr in ENGLISH_TO_FRENCH.items():
    _ar = ENGLISH_TO_ARABIC.get(_en.lower())
    if _ar:
        FRENCH_TO_ARABIC[_fr] = _ar
        FRENCH_TO_ARABIC[_fr.upper()] = _ar
FRENCH_TO_ARABIC['m'] = 'ك'
FRENCH_TO_ARABIC['M'] = 'ك'

ARABIC_TO_FRENCH = {}
for _en, _ar in ENGLISH_TO_ARABIC.items():
    _fr = ENGLISH_TO_FRENCH.get(_en)
    if _fr:
        ARABIC_TO_FRENCH[_ar] = _fr
        ARABIC_TO_FRENCH[_ar.upper()] = _fr

# =========================================================
# Supported Languages & Detection
# =========================================================

LANGUAGES = {"en": "English", "ar": "Arabic", "fr": "French"}
lang_codes = ["en", "ar", "fr"]

SUPPORTED_CONVERSIONS = {(s, t) for s in lang_codes for t in lang_codes if s != t}

def is_conversion_supported(src, tgt):
    return (src, tgt) in SUPPORTED_CONVERSIONS

# =========================================================
# 1000+ word dictionaries per language
# Words found in the TARGET language dictionary are left unconverted.
# =========================================================

COMMON_WORDS = {
    "en": {
        "a", "able", "about", "above", "absolutely", "accept", "accomplish", "account", "accountant", 
        "achieve", "across", "active", "actor", "actress", "actually", "add", "admit", "afraid", 
        "after", "afternoon", "again", "against", "ago", "agree", "air", "airplane", "airport", "all", 
        "allow", "almost", "along", "already", "although", "always", "am", "among", "an", "and", 
        "angry", "ankle", "another", "answer", "ant", "any", "apologize", "appear", "apple", 
        "application", "approve", "april", "are", "area", "argue", "arm", "around", "arrive", "art", 
        "artist", "as", "ashamed", "ask", "at", "august", "aunt", "autumn", "available", "baby", 
        "back", "bag", "bake", "ball", "banana", "bank", "barber", "basically", "basket", "basketball", 
        "bathroom", "battery", "be", "beach", "bear", "beautiful", "because", "become", "bed", 
        "bedroom", "bee", "beef", "been", "beer", "before", "begin", "behind", "being", "believe", 
        "belong", "below", "belt", "best", "between", "beyond", "bicycle", "bike", "bill", "bird", 
        "birth", "black", "blanket", "blood", "blue", "board", "boat", "body", "boil", "bone", "book", 
        "bored", "borrow", "boss", "both", "bottle", "bowl", "box", "brain", "brave", "bread", "break", 
        "breakfast", "bridge", "bright", "bring", "brother", "brown", "budget", "build", "builder", 
        "building", "burn", "bus", "business", "businessman", "businesswoman", "but", "butter", 
        "butterfly", "buy", "by", "cabbage", "cake", "calculate", "call", "calm", "camel", "camera", 
        "can", "car", "card", "careful", "carefully", "careless", "carpenter", "carrot", "carry", 
        "case", "cash", "cat", "catch", "ceiling", "celebrate", "century", "certain", "certainly", 
        "chair", "change", "charger", "cheap", "check", "cheese", "chef", "chest", "chicken", "child", 
        "chin", "chocolate", "choose", "church", "cinema", "city", "class", "classmate", "classroom", 
        "clean", "cleaning", "clear", "clearly", "climb", "clock", "clothes", "cloud", "cloudy", 
        "coach", "coat", "code", "coffee", "coin", "cold", "colleague", "collect", "college", 
        "combine", "come", "communicate", "community", "company", "compare", "competition", "complete", 
        "completely", "computer", "confess", "confident", "confused", "congratulate", "consider", 
        "continue", "contract", "contrast", "control", "conversation", "cook", "cookie", "cooking", 
        "cool", "copy", "corn", "cost", "couch", "could", "count", "country", "cousin", "cow", "crawl", 
        "create", "credit", "cruel", "cry", "cup", "curious", "current", "currently", "curved", 
        "customer", "cut", "dance", "dancer", "dancing", "dangerous", "dark", "data", "daughter", 
        "day", "deal", "death", "debit", "debt", "decade", "december", "decide", "deep", "deer", 
        "definitely", "degree", "delete", "deliver", "deny", "depart", "describe", "desert", "design", 
        "desk", "despite", "destroy", "develop", "device", "did", "die", "difficult", "dinner", 
        "diploma", "dirty", "disagree", "discuss", "divide", "divorce", "do", "doctor", "does", "dog", 
        "dolphin", "donkey", "door", "down", "download", "dozen", "drawing", "dress", "drive", 
        "driver", "drop", "dry", "duck", "dull", "during", "each", "eagle", "ear", "early", "ears", 
        "earth", "easily", "easy", "education", "egg", "eggs", "eight", "eighteen", "eighth", "eighty", 
        "elbow", "electrician", "elephant", "eleven", "email", "embarrassed", "embassy", "employ", 
        "employee", "employer", "empty", "end", "enemy", "engine", "engineer", "enter", "entirely", 
        "especially", "evening", "eventually", "every", "exactly", "exam", "except", "excited", 
        "exercise", "exist", "exit", "expect", "expensive", "explain", "eye", "eyes", "face", "fact", 
        "factory", "fail", "fall", "family", "farm", "farmer", "fast", "fat", "father", "february", 
        "feel", "feet", "few", "field", "fifteen", "fifth", "fifty", "file", "finally", "find", 
        "finger", "finish", "fire", "first", "fish", "five", "fix", "flat", "floor", "flower", "fly", 
        "folder", "follow", "foot", "football", "for", "force", "forest", "forget", "forgive", "fork", 
        "forty", "four", "fourteen", "fourth", "fox", "free", "freeze", "friday", "friend", "friendly", 
        "frog", "from", "fruit", "fry", "fuel", "full", "funeral", "funny", "game", "garden", "gas", 
        "gather", "generally", "generous", "gentle", "geography", "get", "girl", "give", "glass", 
        "glove", "gloves", "go", "goal", "goat", "gold", "good", "goodbye", "goose", "government", 
        "grade", "graduate", "grandfather", "grandmother", "grandparent", "grape", "grass", "gray", 
        "great", "green", "greet", "grey", "group", "grow", "guarantee", "guess", "guest", "guy", 
        "gym", "had", "hair", "half", "hand", "handle", "handsome", "happen", "happy", "hard", "has", 
        "hat", "hate", "have", "he", "head", "health", "healthy", "hear", "heart", "heavy", "hello", 
        "help", "her", "hers", "herself", "highway", "hill", "him", "himself", "hip", "hire", "his", 
        "history", "hold", "home", "homework", "honest", "honey", "horse", "hospital", "host", "hot", 
        "hotel", "hour", "house", "hundred", "husband", "i", "ice", "idea", "if", "ill", "immediately", 
        "improve", "in", "include", "income", "information", "insect", "insert", "install", "internet", 
        "into", "introduce", "invest", "invite", "is", "island", "issue", "it", "its", "itself", 
        "jacket", "january", "jealous", "jeans", "job", "join", "journalist", "journey", "judge", 
        "juice", "july", "jump", "jumping", "june", "keep", "key", "keyboard", "kid", "kids", "kill", 
        "kind", "kitchen", "knee", "knife", "know", "knowledge", "lake", "lamp", "land", "language", 
        "laptop", "last", "late", "later", "laugh", "law", "lawyer", "lazy", "lead", "leaf", "learn", 
        "leave", "leg", "lemon", "lend", "lesson", "let", "letter", "level", "library", "life", "lift", 
        "light", "like", "likely", "line", "lion", "literature", "little", "live", "loan", "local", 
        "lock", "lonely", "long", "look", "lose", "loss", "lot", "loud", "love", "low", "lower", 
        "lunch", "lung", "mainly", "make", "mall", "man", "manage", "manager", "manufacture", "many", 
        "march", "market", "marriage", "match", "math", "may", "maybe", "me", "meal", "mean", 
        "measure", "meat", "mechanic", "meet", "meeting", "melt", "member", "mention", "message", 
        "midnight", "might", "milk", "million", "mine", "minute", "mirror", "moment", "monday", 
        "money", "monkey", "month", "moon", "morning", "mosque", "most", "mostly", "mother", 
        "motorcycle", "mountain", "mouse", "mouth", "move", "much", "multiply", "muscle", "museum", 
        "musician", "must", "my", "myself", "name", "narrow", "nation", "near", "nearly", "neck", 
        "need", "neighbor", "neighborhood", "nephew", "nervous", "network", "never", "new", "niece", 
        "night", "nine", "nineteen", "ninety", "ninth", "no", "noon", "nor", "normally", "nose", 
        "notebook", "notice", "november", "now", "number", "nurse", "obviously", "ocean", "october", 
        "of", "off", "offer", "office", "often", "oil", "old", "on", "once", "one", "onion", "onto", 
        "open", "or", "orange", "organize", "other", "others", "our", "ours", "ourselves", "out", 
        "oven", "over", "owl", "own", "painting", "pajamas", "pan", "pants", "paper", "parent", 
        "parents", "park", "part", "particularly", "partly", "partner", "party", "passenger", 
        "password", "paste", "patient", "pause", "pay", "payment", "pen", "pencil", "people", "pepper", 
        "perhaps", "person", "personal", "phone", "photo", "photographer", "picture", "pig", "pillow", 
        "pilot", "pink", "place", "plan", "plane", "plate", "play", "player", "playing", "please", 
        "plumber", "point", "police", "polite", "poor", "pork", "possible", "possibly", "pot", 
        "potato", "power", "practice", "prepare", "president", "pretty", "price", "print", "printer", 
        "probably", "problem", "produce", "product", "profit", "program", "promise", "proud", "pull", 
        "purple", "push", "put", "quarter", "question", "quickly", "quiet", "quit", "quite", "rabbit", 
        "race", "radio", "rain", "rainy", "raise", "rarely", "rat", "rather", "reach", "read", 
        "reading", "real", "realize", "really", "reason", "receive", "recently", "recipe", "recognize", 
        "red", "refrigerator", "refuse", "reject", "relative", "relaxed", "remain", "remember", 
        "remind", "remove", "rent", "repair", "repeat", "replace", "research", "resign", "restaurant", 
        "result", "retire", "return", "rice", "rich", "ride", "right", "river", "road", "robot", 
        "rock", "roof", "room", "rough", "round", "rude", "run", "running", "sad", "safe", "salad", 
        "salary", "salesman", "salt", "sand", "saturday", "save", "say", "scared", "scarf", "school", 
        "science", "scientist", "score", "scream", "screen", "sea", "season", "second", "secretary", 
        "see", "seem", "sell", "send", "separate", "september", "serious", "serve", "service", "set", 
        "seven", "seventeen", "seventh", "seventy", "shall", "shallow", "share", "shark", "sharp", 
        "she", "sheep", "shine", "ship", "shirt", "shoes", "shop", "shopping", "short", "shorts", 
        "should", "shoulder", "shout", "show", "shy", "sibling", "sick", "side", "silver", "similar", 
        "simple", "simply", "since", "sing", "singer", "singing", "sink", "sister", "sit", "six", 
        "sixteen", "sixth", "sixty", "skin", "skirt", "sky", "slow", "slowly", "smile", "smooth", 
        "snack", "snake", "snow", "snowy", "so", "soccer", "socks", "sofa", "software", "soldier", 
        "solve", "some", "sometimes", "son", "soon", "sorry", "soup", "speak", "special", "spend", 
        "spider", "spoon", "sport", "spring", "square", "stadium", "stairs", "stand", "star", "start", 
        "state", "station", "stay", "still", "stomach", "stone", "stop", "store", "storm", "story", 
        "stove", "straight", "stranger", "street", "strict", "strong", "struggle", "student", "study", 
        "subject", "subtract", "succeed", "such", "suddenly", "sugar", "suggest", "suit", "summer", 
        "sun", "sunday", "sunny", "sure", "surprised", "survive", "sweater", "swim", "swimming", 
        "system", "table", "tailor", "take", "talk", "tall", "tax", "taxi", "tea", "teach", "teacher", 
        "team", "teammate", "teeth", "telephone", "television", "tell", "temperature", "temple", "ten", 
        "tennis", "tenth", "test", "than", "thank", "thanks", "that", "the", "theater", "their", 
        "theirs", "them", "themselves", "these", "they", "thin", "think", "third", "thirteen", 
        "thirty", "this", "those", "though", "thousand", "threaten", "three", "through", "throw", 
        "thumb", "thursday", "ticket", "tie", "tiger", "time", "tired", "to", "today", "toe", "tomato", 
        "tomorrow", "tongue", "tooth", "totally", "toward", "towel", "tower", "town", "trade", 
        "traffic", "train", "translate", "travel", "traveling", "tree", "trip", "trousers", "truck", 
        "try", "tuesday", "turn", "turquoise", "turtle", "twelve", "twenty", "twice", "two", "ugly", 
        "uncle", "under", "understand", "underwear", "uninstall", "university", "unless", "unlike", 
        "until", "up", "update", "upgrade", "upload", "upon", "us", "use", "usually", "valley", 
        "vegetable", "very", "video", "village", "violet", "visit", "waist", "wait", "waiter", "walk", 
        "walking", "wall", "want", "war", "warm", "warn", "was", "wash", "watch", "water", "way", "we", 
        "weak", "weather", "website", "wedding", "wednesday", "week", "welcome", "were", "wet", 
        "whale", "what", "wheel", "whether", "which", "while", "whisper", "white", "who", "whole", 
        "whom", "whose", "wide", "wife", "wifi", "will", "win", "wind", "window", "windy", "wine", 
        "winter", "with", "within", "without", "wolf", "woman", "wonder", "word", "work", "worker", 
        "world", "worm", "worried", "would", "write", "writer", "writing", "yard", "year", "yellow", 
        "yes", "yesterday", "yet", "you", "your", "yours", "yourself", "yourselves", "zero", 
    },
    "fr": {
        "a", "abeille", "absolument", "accepter", "accomplir", "accord", "accorder", "accueillir", 
        "acheter", "acteur", "actif", "actrice", "actuel", "actuellement", "addition", "admettre", 
        "affaire", "agrafeuse", "agriculteur", "ai", "aider", "aigle", "ail", "aimer", "air", 
        "ajouter", "algèbre", "aller", "allez", "allons", "ambassade", "ami", "amical", "amour", 
        "améliorer", "animal", "année", "août", "appareil", "appel", "appeler", "application", 
        "apprendre", "approuver", "après", "après-midi", "araignée", "arbre", "arc-en-ciel", "argent", 
        "argumenter", "armoire", "arriver", "arrêter", "art", "artiste", "as", "assez", "assiette", 
        "attendre", "attraper", "au", "aubergine", "aujourd'hui", "aura", "aurai", "auras", "aurez", 
        "aurons", "auront", "autobus", "automne", "autoroute", "autre", "aux", "avaient", "avais", 
        "avait", "avant", "avec", "avertir", "avez", "aviez", "avion", "avions", "avocat", "avoir", 
        "avons", "avril", "aéroport", "bactérie", "bain", "baisser", "balai", "baleine", "ballon", 
        "banane", "banque", "bas", "basketball", "basse", "bateau", "batterie", "beau", "beau-frère", 
        "beau-père", "belle", "belle-fille", "belle-mère", "belle-soeur", "beurre", "bibliothèque", 
        "bicyclette", "bientôt", "bienvenue", "billet", "biscuit", "bière", "blanc", "bleu", "boeuf", 
        "boire", "bol", "bon", "bonjour", "bonne", "bonsoir", "bouche", "bouteille", "boutique", 
        "boîte", "bras", "brillant", "briller", "brouillard", "brun", "bruyant", "brûler", "budget", 
        "bureau", "but", "bâtiment", "bébé", "café", "cahier", "calculer", "calme", "camarade", 
        "camion", "camionnette", "canapé", "canard", "candidature", "car", "carburant", "carotte", 
        "carré", "carte", "casserole", "ce", "ceinture", "cent", "centre", "cerf", "certain", 
        "certainement", "cerveau", "ces", "cet", "cette", "chaise", "chambre", "chameau", "champ", 
        "champignon", "changement", "changer", "chant", "chanter", "chanteur", "chapeau", "chargeur", 
        "chat", "chaud", "chauffeur", "chaussettes", "chaussures", "chef", "chemise", "cher", 
        "chercher", "cheval", "cheveux", "cheville", "chez", "chien", "chirurgie", "chocolat", 
        "choisir", "chou", "chou-fleur", "chuchoter", "chèvre", "ciel", "cinq", "cinquante", 
        "cinquième", "cinéma", "circulation", "ciseaux", "citron", "clair", "clairement", "classe", 
        "classeur", "clavier", "client", "clé", "cochon", "code", "coeur", "coiffeur", "collation", 
        "colle", "collecter", "coller", "colline", "collège", "collègue", "colère", "combiner", 
        "comme", "commencer", "commerce", "commercial", "communiquer", "comparer", "complètement", 
        "compléter", "comprendre", "comptable", "compte", "compétition", "concevoir", "concombre", 
        "conduire", "confiant", "confiture", "confus", "connaissance", "connaître", "constructeur", 
        "construire", "continuer", "contrat", "contre", "contrôler", "conversation", "copier", "corps", 
        "costume", "cou", "coucher", "coude", "couleur", "cour", "courageux", "courbé", "courgette", 
        "courir", "courriel", "course", "cousin", "couteau", "couverture", "coéquipier", "coût", 
        "cravate", "crayon", "crier", "croient", "croire", "crois", "croit", "croyez", "croyons", 
        "cruel", "crème", "crédit", "créer", "cuillère", "cuire", "cuisine", "cuisiner", "cuisinier", 
        "cuisinière", "curieux", "curriculum", "célébrer", "côté", "d'affaires", "dangereux", "dans", 
        "danse", "danser", "danseur", "dauphin", "de", "demain", "demander", "demi-frère", 
        "demi-soeur", "dent", "dents", "depuis", "dernier", "des", "descendre", "dessert", "dessin", 
        "dette", "deux", "deuxième", "devenir", "devez", "devoir", "devoirs", "devons", "devra", 
        "devrai", "devras", "difficile", "différent", "dimanche", "diplôme", "diplômé", "dira", 
        "dirai", "diras", "dire", "directeur", "dis", "discuter", "disent", "disons", "disponible", 
        "dit", "dites", "diviser", "division", "divorce", "dix", "dix-huit", "dix-neuf", "dix-sept", 
        "dixième", "doigt", "dois", "doit", "doivent", "donc", "donner", "données", "dont", "dormir", 
        "dos", "dossier", "doux", "douzaine", "douze", "droit", "drôle", "du", "dès", "débit", 
        "décembre", "décennie", "décider", "défaite", "définitivement", "déjeuner", "déjà", 
        "démissionner", "désert", "désolé", "détendu", "détester", "détruire", "développer", "dîner", 
        "eau", "effrayé", "elle", "elles", "embaucher", "employeur", "employé", "emprunter", "en", 
        "encore", "endroit", "enfant", "enfants", "ennemi", "ennuyé", "ensoleillé", "entier", 
        "entièrement", "entraîneur", "entre", "entreprise", "entrer", "entretien", "envoyer", "es", 
        "escalier", "espèces", "essayer", "essence", "est", "estomac", "et", "exactement", "examen", 
        "excité", "excusez-moi", "exercice", "exister", "expliquer", "facile", "facilement", "faible", 
        "faire", "fais", "faisons", "fait", "faites", "falloir", "famille", "farine", "fatigué", 
        "femme", "fenêtre", "fera", "ferai", "feras", "ferez", "ferme", "fermer", "ferons", "feront", 
        "feu", "feuille", "fier", "fille", "fils", "fin", "finalement", "finir", "fleur", "fois", 
        "fondre", "font", "football", "force", "former", "fort", "forte", "forêt", "four", 
        "fourchette", "fourmi", "frais", "froid", "fromage", "fruit", "frère", "funérailles", "fusée", 
        "féliciter", "février", "gagner", "gant", "gants", "garantir", "gare", "garçon", "geler", 
        "gelée", "gendre", "genou", "gentil", "gentille", "glace", "gomme", "gouvernement", "grand", 
        "grand-mère", "grand-père", "grande", "grenouille", "grimper", "gris", "gros", "groupe", 
        "guerre", "gymnase", "gâteau", "généralement", "généreux", "géographie", "géométrie", "gérer", 
        "gêné", "habituellement", "hanche", "haut", "haute", "herbe", "heure", "heureux", "hibou", 
        "hier", "histoire", "hiver", "homme", "honnête", "honteux", "horloge", "hors", "huile", "huit", 
        "huitième", "humide", "hélicoptère", "hôpital", "hôte", "hôtel", "idée", "il", "ils", 
        "immédiatement", "impoli", "important", "imprimante", "imprimer", "imprudent", "impôt", 
        "infirmière", "information", "ingénieur", "inquiet", "insecte", "internet", "investir", 
        "inviter", "invité", "ira", "irai", "iras", "irez", "irons", "iront", "jaloux", "jamais", 
        "jambe", "janvier", "jardin", "jaune", "je", "jean", "jeter", "jeu", "jeudi", "jeune", "joli", 
        "jolie", "jouer", "joueur", "jour", "journaliste", "juge", "juillet", "juin", "jupe", "jus", 
        "la", "lac", "laid", "laisser", "lait", "lampe", "langue", "lapin", "laquelle", "large", 
        "laver", "le", "lecture", "lent", "lentement", "lequel", "les", "lesquelles", "lesquels", 
        "lettre", "leur", "leurs", "lever", "leçon", "libre", "ligne", "lion", "lire", "lisse", "lit", 
        "littérature", "livre", "livrer", "logiciel", "loi", "long", "longue", "lorsque", "louer", 
        "loup", "lourd", "lui", "lumière", "lundi", "lune", "lutter", "léger", "légume", "ma", 
        "magasin", "mai", "main", "maintenant", "mais", "maison", "malade", "malgré", "manger", 
        "manteau", "marche", "marcher", "marché", "mardi", "mari", "mariage", "marron", "mars", 
        "match", "matelas", "mathématiques", "matin", "matière", "mauvais", "mauvaise", "maïs", "me", 
        "meilleur", "membre", "menacer", "mentionner", "menton", "menuisier", "mer", "merci", 
        "mercredi", "mes", "message", "mesurer", "met", "mets", "mettent", "mettez", "mettons", 
        "mettre", "microbe", "midi", "miel", "mille", "million", "mince", "minuit", "minute", "miroir", 
        "moi", "mois", "moitié", "moment", "mon", "monde", "montagne", "monter", "montrer", "mort", 
        "mosquée", "mot", "moteur", "moto", "mourir", "mouton", "multiplication", "multiplier", "mur", 
        "muscle", "musicien", "musée", "mère", "mécanicien", "médecin", "médicament", "métier", 
        "météo", "même", "nager", "naissance", "natation", "nation", "navire", "naître", "neige", 
        "neigeux", "nerveux", "net", "nettoyage", "nettoyer", "neuf", "neuvième", "neveu", "nez", "ni", 
        "nier", "niveau", "nièce", "noir", "nom", "nombre", "non", "normalement", "nos", "note", 
        "notre", "nous", "nouveau", "nouvelle", "novembre", "nuage", "nuageux", "nuit", "octobre", 
        "océan", "oeil", "oeils", "oeuf", "oeufs", "offrir", "oie", "oignon", "oiseau", "on", "oncle", 
        "ont", "onze", "or", "orange", "ordinateur", "ordonnance", "oreille", "oreiller", "oreilles", 
        "organiser", "orteil", "os", "ou", "oublier", "oui", "ours", "ouvert", "ouvrir", "où", 
        "paiement", "pain", "panier", "pantalon", "papier", "papillon", "par", "parc", "pardon", 
        "pardonner", "parent", "parents", "paresseux", "parfois", "parler", "parmi", "pars", "part", 
        "partager", "partenaire", "partent", "partez", "parti", "particulièrement", "partie", 
        "partiellement", "partir", "partons", "passager", "passe", "passer", "patient", "patron", 
        "pauvre", "payer", "pays", "peau", "peinture", "pendant", "penser", "perdre", "permettre", 
        "personne", "personnel", "perte", "petit", "petit-déjeuner", "petite", "peu", "peut", 
        "peut-être", "peuvent", "peux", "photo", "photographe", "pied", "pieds", "pierre", "pilote", 
        "pilule", "pièce", "place", "plafond", "plage", "planifier", "plat", "plaît", "plein", 
        "pleurer", "plombier", "pluie", "plus", "plutôt", "pluvieux", "poisson", "poitrine", "poivre", 
        "poivron", "poli", "police", "pomme", "pont", "porc", "portable", "porte", "porter", 
        "possible", "possiblement", "posséder", "poubelle", "pouce", "poulet", "poumon", "pour", 
        "pourra", "pourrai", "pourras", "pousser", "pouvez", "pouvoir", "pouvons", "poêle", 
        "pratiquer", "premier", "prend", "prendra", "prendrai", "prendras", "prendre", "prends", 
        "prenez", "prennent", "prenons", "presque", "principalement", "printemps", "prix", 
        "probablement", "problème", "prochain", "produire", "produit", "professeur", "profession", 
        "profit", "profond", "promettre", "propre", "prudent", "préparer", "présenter", "président", 
        "prêt", "public", "puisque", "pull", "pyjama", "pâte", "pâtes", "père", "quand", "quarante", 
        "quart", "quartier", "quatorze", "quatre", "quatre-vingt-dix", "quatre-vingts", "quatrième", 
        "que", "question", "qui", "quinze", "quitter", "quoi", "quoique", "radio", "raisin", "raison", 
        "rapide", "rapidement", "rappeler", "rarement", "rat", "recette", "recevoir", "refuser", 
        "regarder", "rejeter", "rejoindre", "remercier", "remplacer", "renard", "rendre", "repas", 
        "requin", "restaurant", "rester", "revenu", "revoir", "riche", "rideau", "rire", "rivière", 
        "riz", "robe", "robot", "roche", "rond", "rose", "rosée", "roue", "rouge", "route", "rue", 
        "rugueux", "règle", "récemment", "réfrigérateur", "région", "réparer", "répondre", "répéter", 
        "réseau", "résoudre", "résultat", "réunion", "réussir", "s'il", "sa", "sable", "sac", "sain", 
        "sais", "saison", "sait", "salade", "salaire", "sale", "salle", "saluer", "salut", "samedi", 
        "sang", "sans", "santé", "saura", "saurai", "sauras", "saut", "sauter", "sauvegarder", 
        "savent", "savez", "savoir", "savons", "sciences", "scientifique", "score", "se", "sec", 
        "seconde", "secrétaire", "seize", "sel", "selon", "semaine", "sembler", "sentir", "sept", 
        "septembre", "septième", "sera", "serai", "seras", "serez", "serons", "seront", "serpent", 
        "serrure", "serveur", "service", "serviette", "ses", "seul", "shopping", "short", "si", 
        "silencieux", "similaire", "simple", "simplement", "singe", "site", "six", "sixième", "siècle", 
        "soeur", "soi", "soigneusement", "soir", "soixante", "soixante-dix", "sol", "soldat", "soleil", 
        "sombre", "sommes", "son", "sont", "sors", "sort", "sortent", "sortez", "sortir", "sortons", 
        "soudainement", "soupe", "sourire", "souris", "sous", "sous-vêtements", "soustraction", 
        "soustraire", "souvent", "sport", "spécial", "stade", "strict", "stylo", "sucre", "suggérer", 
        "suis", "suivre", "supprimer", "sur", "surpris", "surtout", "survivre", "système", "séparer", 
        "sérieux", "sûr", "ta", "table", "tableau", "taille", "tailleur", "tante", "tapis", "tard", 
        "tasse", "taxi", "te", "temple", "temps", "température", "tempête", "tenez", "tenir", "tennis", 
        "tenons", "terre", "tes", "test", "tester", "thé", "théâtre", "tiennent", "tiens", "tient", 
        "tigre", "timide", "tirer", "tiroir", "tiède", "toi", "toit", "tomate", "tomber", "ton", 
        "tonnerre", "tortue", "totalement", "toujours", "tour", "traduire", "train", "traiter", 
        "travail", "travailler", "travailleur", "treize", "trente", "triste", "trois", "troisième", 
        "trouver", "très", "tu", "turquoise", "téléphone", "télévision", "tête", "tôt", "un", "une", 
        "unique", "université", "usine", "va", "vaccin", "vache", "vais", "vallée", "vas", "vendeur", 
        "vendre", "vendredi", "venez", "venir", "venons", "vent", "venteux", "ventre", "ver", "verra", 
        "verrai", "verras", "verre", "vers", "vert", "veste", "veulent", "veut", "veux", "viande", 
        "victoire", "vide", "vidéo", "vie", "vieille", "viendra", "viendrai", "viendras", "viennent", 
        "viens", "vient", "vieux", "village", "ville", "vin", "vingt", "violet", "virus", "visage", 
        "visiter", "vitae", "vivre", "voient", "voile", "voir", "vois", "voisin", "voit", "voiture", 
        "voler", "vont", "vos", "votre", "voudra", "voudrai", "voudras", "voulez", "vouloir", 
        "voulons", "vous", "voyage", "voyager", "voyez", "voyons", "vrai", "vraiment", "vélo", 
        "vélomoteur", "vérifier", "vêtements", "web", "wifi", "yaourt", "zéro", "à", "âne", "écharpe", 
        "échouer", "éclair", "école", "écouter", "écran", "écrire", "écriture", "écrivain", 
        "éducation", "église", "électricien", "éléphant", "épargner", "épaule", "épice", "éponge", 
        "équation", "équipe", "étagère", "étaient", "étais", "était", "état", "étiez", "étions", 
        "étoile", "étranger", "étroit", "étude", "étudiant", "été", "éventuellement", "évidemment", 
        "évier", "êtes", "être", "île", 
    },
    "ar": {
        "آخر", "آسف", "آكل", "آمن", "أب", "أبدا", "أبريل", "أبيض", "أتى", "أجاب", "أجرة", "أحب", 
        "أحتاج", "أحد", "أحمر", "أحيانا", "أخ", "أخت", "أخذ", "أخرى", "أخضر", "أخير", "أخيرا", "أدار", 
        "أدب", "أذن", "أذنان", "أذهب", "أراد", "أرادوا", "أربعة", "أربعون", "أرجواني", "أردت", "أردنا", 
        "أرز", "أرض", "أرضية", "أرنب", "أريد", "أريكة", "أزرق", "أسبوع", "أستطيع", "أسد", "أسنان", 
        "أسود", "أشرب", "أصبح", "أصفر", "أصلح", "أضاف", "أطفال", "أعطى", "أعمال", "أغسطس", "أغلق", 
        "أفضل", "أقارب", "أقرأ", "أكتب", "أكتوبر", "أكل", "أكلت", "أكلنا", "أكلوا", "أكمل", "ألف", 
        "أم", "أمام", "أمة", "أمس", "أنا", "أنت", "أنتج", "أنتم", "أنتن", "أنتِ", "أنجز", "أنف", 
        "أنفسنا", "أنكر", "أهلا", "أو", "أول", "أولئك", "أي", "إبهام", "إجابة", "إذ", "إذا", "إسفنجة", 
        "إصبع", "إلكتروني", "إلى", "إنترنت", "إنفاق", "إوزة", "ائتمان", "ابن", "ابنة", "اثنا", "اثنان", 
        "اجتماع", "احتاج", "احتفل", "اختبار", "ادخار", "استبدل", "استثمار", "استطاع", "استقال", 
        "استقبل", "استمر", "اسم", "اشترى", "اعتذر", "اعترف", "اعتقد", "الآن", "الأحد", "الأربعاء", 
        "الأول", "الاثنين", "التاسع", "التي", "الثالث", "الثامن", "الثاني", "الثلاثاء", "الجمعة", 
        "الخامس", "الخميس", "الخير", "الذي", "الذين", "الرابع", "السابع", "السادس", "السبت", "العاشر", 
        "القدم", "اللواتي", "الليل", "النهاية", "اليوم", "امتحان", "امرأة", "انتظر", "انتهى", "انضم", 
        "بائع", "باب", "باذنجان", "بارد", "باع", "بالتأكيد", "بالضبط", "بالفعل", "بالكامل", "ببساطة", 
        "ببطء", "بحث", "بحر", "بحيرة", "بدأ", "بدلة", "بدون", "برتقالي", "برج", "برق", "برنامج", 
        "بريد", "بسرعة", "بسكويت", "بسهولة", "بسيط", "بشكل", "بصل", "بطارية", "بطاطا", "بطاطس", 
        "بطاقة", "بطانية", "بطة", "بطن", "بطيء", "بعد", "بعناية", "بعيد", "بقر", "بقرة", "بقي", 
        "بكتيريا", "بكى", "بل", "بلد", "بناء", "بنت", "بنطال", "بنفسجي", "بنك", "بنى", "بني", "بوضوح", 
        "بوظة", "بومة", "بيانات", "بيت", "بيجامة", "بيرة", "بيض", "بيضة", "بيع", "بين", "تأشيرة", 
        "تأكل", "تجارة", "تجاري", "تحت", "تحتاج", "تحدث", "تذكرة", "تذهب", "ترك", "تركوازي", "تريد", 
        "تستطيع", "تسعة", "تسعون", "تسوق", "تشرب", "تصبح", "تطبيق", "تعلم", "تعليم", "تغيير", "تفاح", 
        "تقرأ", "تقريبا", "تكتب", "تكلفة", "تكلم", "تلة", "تلفزيون", "تلك", "تلوين", "تماما", "تمرين", 
        "تنس", "تنظيف", "تنورة", "توابل", "توظيف", "توقف", "ثانية", "ثبت", "ثعبان", "ثعلب", "ثقيل", 
        "ثلاثة", "ثلاثون", "ثلاجة", "ثلج", "ثم", "ثمانون", "ثمانية", "ثوم", "جاء", "جاد", "جار", "جاف", 
        "جامعة", "جانب", "جبر", "جبل", "جبن", "جد", "جدا", "جدار", "جدة", "جديد", "جراحة", "جرذ", 
        "جري", "جزء", "جزئيا", "جزر", "جزيرة", "جسر", "جسم", "جغرافيا", "جلد", "جلس", "جمع", "جمل", 
        "جميل", "جنازة", "جندي", "جهاز", "جوارب", "جواز", "جوي", "جيد", "جينز", "حاد", "حار", "حاسوب", 
        "حافلة", "حالي", "حاليا", "حاول", "حب", "حبة", "حتى", "حجر", "حدث", "حديقة", "حذاء", "حذر", 
        "حذف", "حر", "حرارة", "حرب", "حركة", "حزام", "حزب", "حزين", "حساء", "حساب", "حسن", "حشرة", 
        "حصان", "حفظ", "حق", "حقا", "حقق", "حقل", "حقيبة", "حقيقي", "حكومة", "حل", "حلاق", "حلوى", 
        "حليب", "حمار", "حمام", "حمل", "حوت", "حوض", "حول", "حي", "حيا", "حياة", "حيوان", "خائف", 
        "خاص", "خاصة", "خال", "خالة", "خبز", "خجول", "خدمة", "خرج", "خروف", "خريج", "خريف", "خزانة", 
        "خسارة", "خسر", "خشن", "خصر", "خضار", "خط", "خطط", "خطير", "خفيف", "خفيفة", "خلال", "خلف", 
        "خمسة", "خمسون", "خنزير", "خيار", "خياط", "خير", "دائما", "داخلية", "دافئ", "دب", "دباسة", 
        "دبلوم", "دجاجة", "دخل", "دراجة", "دراسة", "درب", "درج", "درجة", "درس", "دزينة", "دعا", "دفتر", 
        "دفع", "دقيقة", "دم", "دماغ", "دمر", "دواء", "دودة", "دولة", "دولفين", "دولية", "ديسمبر", 
        "دين", "ذئب", "ذاتية", "ذراع", "ذرة", "ذقن", "ذكي", "ذلك", "ذهب", "ذهبت", "ذهبنا", "ذهبوا", 
        "ذهبي", "رأس", "رأى", "رئة", "رئيس", "رئيسي", "راتب", "راديو", "راقص", "راكب", "ربح", "ربطة", 
        "ربع", "ربما", "ربيع", "رجع", "رجل", "رحب", "رحلة", "رخيص", "رد", "رسالة", "رسم", "رصاص", 
        "رضيع", "رطب", "رعد", "رف", "رفض", "رقبة", "رقص", "رقمية", "ركب", "ركبة", "رمادي", "رمز", 
        "رمل", "رمى", "روبوت", "رياح", "رياضة", "رياضيات", "رياضية", "زار", "زبادي", "زبدة", "زجاجة", 
        "زميل", "زهرة", "زواج", "زوج", "زوجة", "زيت", "سأذهب", "سأل", "سؤال", "سائق", "ساعة", "ساعد", 
        "سافر", "ساق", "سامح", "سباحة", "سباق", "سباك", "سبب", "سبتمبر", "سبعة", "سبعون", "سبورة", 
        "ستارة", "ستة", "سترة", "ستون", "سجادة", "سحابة", "سرير", "سريع", "سعر", "سعيد", "سفارة", 
        "سفر", "سفينة", "سقف", "سكر", "سكرتير", "سكن", "سكين", "سلة", "سلحفاة", "سلطة", "سلم", "سماء", 
        "سماعات", "سمع", "سمك", "سمين", "سن", "سنة", "سهل", "سوق", "سيء", "سيارة", "سيدة", "سيرة", 
        "سيطر", "سينما", "شاب", "شاحن", "شاحنة", "شارع", "شاشة", "شاطئ", "شاهد", "شاي", "شبكة", "شتاء", 
        "شجاع", "شجرة", "شخص", "شخصي", "شراء", "شراعية", "شرب", "شربت", "شربنا", "شربوا", "شرح", 
        "شرطة", "شركة", "شريك", "شعر", "شكر", "شكرا", "شمس", "شهادة", "شهر", "شورت", "شوكة", 
        "شوكولاتة", "صاحب", "صاخب", "صادق", "صار", "صارم", "صاروخ", "صالة", "صباح", "صبور", "صحة", 
        "صحراء", "صحفي", "صحن", "صحي", "صحيح", "صخرة", "صدر", "صديق", "صرخ", "صعب", "صغير", "صف", 
        "صفر", "صفقة", "صقيع", "صمم", "صندوق", "صنع", "صورة", "صيانة", "صيدلي", "صيف", "ضباب", "ضحك", 
        "ضحل", "ضرب", "ضريبة", "ضعيف", "ضفدع", "ضمن", "ضوء", "ضيف", "ضيق", "طائر", "طائرة", "طاب", 
        "طابعة", "طالب", "طاهي", "طاولة", "طباخ", "طبخ", "طبع", "طبيب", "طبية", "طحين", "طرح", "طريق", 
        "طفل", "طقس", "طلاق", "طلب", "طماطم", "طور", "طويل", "طيار", "ظن", "ظهر", "ظهيرة", "عائلة", 
        "عاد", "عادة", "عاش", "عاصف", "عاصفة", "عالج", "عالم", "عالي", "عام", "عامل", "عبر", "عجلة", 
        "عدد", "عدو", "عرف", "عسل", "عشاء", "عشب", "عشر", "عشرة", "عشرون", "عصبي", "عصير", "عضلة", 
        "عضو", "عظم", "عقد", "علم", "علوم", "على", "عم", "عمة", "عمل", "عملة", "عموما", "عميق", "عميل", 
        "عن", "عنب", "عنق", "عنكبوت", "عين", "عينان", "عيون", "غائم", "غابة", "غادر", "غاضب", "غالبا", 
        "غالي", "غدا", "غداء", "غراء", "غرفة", "غريب", "غزال", "غسل", "غناء", "غنى", "غني", "غيور", 
        "فأر", "فأرة", "فاتورة", "فارغ", "فاز", "فاكهة", "فبراير", "فتح", "فجأة", "فخور", "فراشة", 
        "فرن", "فريق", "فستان", "فشل", "فصل", "فضلك", "فضولي", "فضي", "فطر", "فطور", "فعل", "فعليا", 
        "فقد", "فقير", "فكرة", "فلفل", "فم", "فن", "فناء", "فنان", "فندق", "فهم", "فورا", "فوز", "فوق", 
        "في", "فيديو", "فيروس", "فيل", "قاد", "قادم", "قارب", "قاسي", "قاضي", "قال", "قانون", "قبعة", 
        "قبل", "قبيح", "قدر", "قدم", "قدمان", "قديم", "قرأ", "قرأت", "قرأنا", "قرأوا", "قراءة", "قرد", 
        "قرش", "قرض", "قرن", "قرنبيط", "قريب", "قريبا", "قرية", "قزح", "قسمة", "قصة", "قطار", "قطة", 
        "قفاز", "قفز", "قفل", "قلب", "قلق", "قلم", "قمر", "قميص", "قهوة", "قوة", "قوس", "قوي", "قيادة", 
        "كأس", "كاتب", "كاحل", "كامل", "كاميرا", "كان", "كبير", "كتاب", "كتابة", "كتب", "كتبت", 
        "كتبنا", "كتبوا", "كتف", "كرة", "كرر", "كرسي", "كره", "كريم", "كريمة", "كسر", "كسول", "كعكة", 
        "كلب", "كلمة", "كلية", "كليل", "كما", "كنزة", "كنيسة", "كهربائي", "كوب", "كوسا", "كي", "لأن", 
        "لا", "لاحقا", "لاسلكي", "لاعب", "لحظة", "لحم", "لسان", "لصق", "لطيف", "لعب", "لعبة", "لغة", 
        "لقاح", "لكن", "لو", "لوحة", "لوحي", "ليل", "ليمون", "مؤخرا", "ما", "ماء", "مائة", "مات", 
        "مادة", "مارس", "ماعز", "مال", "مايو", "مباراة", "مبكرا", "مبنى", "متأخر", "متأكد", "متاح", 
        "متجر", "متحف", "متحمس", "متسخ", "متعب", "متهور", "مثلج", "مجلد", "مجموعة", "محادثة", "محاسب", 
        "محامي", "محرج", "محرك", "محطة", "محقق", "محمول", "محيط", "مختلف", "مدرب", "مدرسة", "مدير", 
        "مدينة", "مرآة", "مربع", "مربى", "مربي", "مرة", "مرتبة", "مرتبك", "مرتين", "مرحبا", "مرفق", 
        "مركز", "مرور", "مريض", "مزارع", "مزرعة", "مساء", "مستدير", "مسترخي", "مستشار", "مستشفى", 
        "مستقيم", "مستوى", "مسجد", "مسرح", "مسطح", "مسطرة", "مشابه", "مشرق", "مشكلة", "مشمس", "مشي", 
        "مصباح", "مصنع", "مصور", "مضحك", "مضيف", "مطار", "مطبخ", "مطر", "مطعم", "مظلم", "مع", "معادلة", 
        "معبد", "معرفة", "معطف", "معكرونة", "معلم", "معلومات", "معين", "مغني", "مفاتيح", "مفتاح", 
        "مفتوح", "مقص", "مقعد", "مقلاة", "مكالمة", "مكان", "مكتب", "مكتبة", "مكنسة", "ملابس", "ملح", 
        "ملعب", "ملعقة", "ملف", "ملفوف", "ملل", "مليون", "ممتلئ", "ممثل", "ممثلة", "ممحاة", "ممرض", 
        "ممرضة", "ممطر", "ممكن", "من", "منافسة", "منتج", "منتصف", "منحني", "منخفض", "مندهش", "منذ", 
        "منشفة", "منطقة", "مهذب", "مهم", "مهملات", "مهنة", "مهندس", "موت", "موز", "موسيقي", "موظف", 
        "موقد", "موقع", "ميدان", "ميزانية", "ميكانيكي", "ميكروب", "نأكل", "نادرا", "نادل", "نار", 
        "نارية", "ناعم", "نافذة", "نام", "نبيذ", "نتيجة", "نجار", "نجح", "نجمة", "نحتاج", "نحلة", 
        "نحن", "نحيف", "ندى", "نذهب", "نريد", "نزل", "نستطيع", "نسخ", "نسر", "نشرب", "نشيط", "نصف", 
        "نظام", "نظر", "نظف", "نظم", "نظيف", "نعم", "نفسك", "نفسه", "نفسها", "نفسي", "نقد", "نقرأ", 
        "نكتب", "نمر", "نملة", "نهاية", "نهر", "نوفمبر", "نوم", "هؤلاء", "هاتف", "هادئ", "هدد", "هدف", 
        "هدم", "هذا", "هذه", "هليكوبتر", "هم", "همس", "هن", "هنأ", "هندسة", "هو", "هواء", "هوائية", 
        "هي", "و", "واثق", "واجب", "واحد", "وادي", "واسع", "واضح", "وافق", "والد", "والدة", "وجبة", 
        "وجد", "وجه", "وحيد", "وداعا", "ودود", "وردي", "ورق", "ورقة", "ورك", "وسادة", "وسيم", "وشاح", 
        "وصفة", "وصل", "وضع", "وظف", "وعاء", "وعد", "وقت", "وقح", "وقف", "وقود", "ولادة", "ولد", 
        "يأكل", "يحتاج", "يد", "يذهب", "يريد", "يزال", "يستطيع", "يشرب", "يقرأ", "يكتب", "يكون", 
        "يناير", "يوليو", "يوم", "يومك", "يونيو", 
    },
}


FRENCH_COMMON_WORDS = COMMON_WORDS["fr"]  # kept for backward compatibility with detect_language

def detect_language(text, lang1=None, lang2=None):
    arabic_count = sum(1 for char in text if "\u0600" <= char <= "\u06FF")
    if arabic_count > 0:
        return "ar"
    french_chars = set("éèêëàâçùûüôîï")
    french_count = sum(1 for char in text.lower() if char in french_chars)
    if french_count > 0:
        return "fr"
    words = re.findall(r"\w+", text.lower())
    french_word_count = sum(1 for word in words if word in FRENCH_COMMON_WORDS)
    if french_word_count > 0:
        return "fr"
    if lang1 is not None and lang2 is not None:
        if ("fr" in (lang1, lang2)) and ("en" not in (lang1, lang2)):
            return "fr"
    return "en"

_STRIP_CHARS = ".,;:!?()[]{}'\"-،؛؟"

def is_correct_word(word, target_lang):
    if target_lang not in COMMON_WORDS:
        return False
    stripped = word.strip(_STRIP_CHARS)
    return stripped.lower() in COMMON_WORDS[target_lang] or stripped in COMMON_WORDS[target_lang]

def convert_text(text, source_lang, target_lang):
    if not text or source_lang == target_lang or not is_conversion_supported(source_lang, target_lang):
        return text
    tokens = re.findall(r"\S+|\s+", text)
    result_tokens = []
    for token in tokens:
        if token.isspace():
            result_tokens.append(token)
            continue
        if is_correct_word(token, target_lang):
            result_tokens.append(token)
            continue
        converted_token = ""
        for char in token:
            if char.isdigit():
                converted_token += char
                continue
            if source_lang == "fr" and target_lang == "ar":
                converted_token += FRENCH_TO_ARABIC.get(char, char)
            elif source_lang == "ar" and target_lang == "fr":
                converted_token += ARABIC_TO_FRENCH.get(char, char)
            elif source_lang == "en" and target_lang == "ar":
                converted_token += ENGLISH_TO_ARABIC.get(char.lower(), char)
            elif source_lang == "ar" and target_lang == "en":
                converted_token += ARABIC_TO_ENGLISH.get(char, char)
            elif source_lang == "en" and target_lang == "fr":
                converted_token += ENGLISH_TO_FRENCH.get(char, char)
            elif source_lang == "fr" and target_lang == "en":
                converted_token += FRENCH_TO_ENGLISH.get(char, char)
            else:
                converted_token += char
        result_tokens.append(converted_token)
    return "".join(result_tokens)

# =========================================================
# Copy / Paste helpers
#
# IMPORTANT BUGFIX: these previously used keyboard.press_and_release
# ("ctrl+c" / "ctrl+v"). The `keyboard` library resolves hotkeys to raw
# SCAN CODES, and scan-code interpretation is keyboard-layout dependent.
# Because this app constantly switches the active input layout between
# English/Arabic/French, the scan code the library sent for "c" would
# occasionally be interpreted by Windows as the Volume Down key instead
# of the letter C (0xAE is the extended scan code for Volume Down, and
# under certain non-US layouts / extended-key flag states the library
# could emit it ambiguously). That's what caused "the system volume
# goes down instead of the app working" randomly.
#
# The fix: send Ctrl and C/V using raw VIRTUAL-KEY codes instead of scan
# codes. Virtual-key codes for Ctrl and letters are layout-independent
# by design (this is exactly why Ctrl+C means "copy" in literally every
# app no matter what keyboard layout is active) so there is no scan-code
# ambiguity and no chance of it being reinterpreted as a media key.
# =========================================================

user32 = ctypes.windll.user32

VK_CONTROL = 0x11
VK_C = 0x43
VK_V = 0x56

KEYEVENTF_KEYUP = 0x0002
INPUT_KEYBOARD = 1

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]

class INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("hi", HARDWAREINPUT)]

class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("union", INPUT_UNION)]

def _send_vk(vk, key_up=False):
    """Sends a single virtual-key event via SendInput, deliberately with
    wScan=0 so Windows never has to translate a scan code -> no
    layout-dependent ambiguity, no accidental media-key interpretation."""
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.union.ki.wVk = vk
    inp.union.ki.wScan = 0
    inp.union.ki.dwFlags = KEYEVENTF_KEYUP if key_up else 0
    inp.union.ki.time = 0
    inp.union.ki.dwExtraInfo = None
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

def send_ctrl_c():
    _send_vk(VK_CONTROL)
    _send_vk(VK_C)
    _send_vk(VK_C, key_up=True)
    _send_vk(VK_CONTROL, key_up=True)
    time.sleep(0.02)

def send_ctrl_v():
    _send_vk(VK_CONTROL)
    _send_vk(VK_V)
    _send_vk(VK_V, key_up=True)
    _send_vk(VK_CONTROL, key_up=True)
    time.sleep(0.02)

def probe_selected_text():
    """Checks whether there is an active text selection in the current
    foreground window, without disturbing the user's clipboard.

    Works by temporarily clearing the clipboard, issuing a copy, and
    seeing whether anything new arrived. The original clipboard content
    is always restored before returning, whether or not a selection was
    found. Returns the selected text, or "" if nothing is selected.
    """
    old_clipboard = ""
    try:
        old_clipboard = pyperclip.paste()
    except Exception:
        old_clipboard = ""

    try:
        pyperclip.copy("")
    except Exception:
        pass
    time.sleep(0.05)

    send_ctrl_c()

    selected_text = ""
    for _ in range(20):
        time.sleep(0.02)
        try:
            selected_text = pyperclip.paste()
        except Exception:
            selected_text = ""
        if selected_text:
            break

    try:
        pyperclip.copy(old_clipboard)
    except Exception:
        pass

    return selected_text

# =========================================================
# Target Window functions
# =========================================================

target_window = None

def remember_target_window():
    global target_window
    try:
        target_window = win32gui.GetForegroundWindow()
    except Exception:
        target_window = None

def correct_selected_text():
    print("Correct command received")
    try:
        close_menu()

        global target_window
        target_window = win32gui.GetForegroundWindow()

        lang1 = lang1_var.get()
        lang2 = lang2_var.get()

        old_clipboard = pyperclip.paste()
        pyperclip.copy("")
        time.sleep(0.1)

        send_ctrl_c()

        selected_text = ""
        for _ in range(60):
            time.sleep(0.02)
            try:
                selected_text = pyperclip.paste()
            except Exception:
                selected_text = ""
            if selected_text:
                break

        if not selected_text:
            print("No text selected.")
            pyperclip.copy(old_clipboard)
            return

        detected = detect_language(selected_text, lang1, lang2)
        if detected == lang1:
            src_lang, tgt_lang = lang1, lang2
        elif detected == lang2:
            src_lang, tgt_lang = lang2, lang1
        else:
            messagebox.showwarning("Notice", "Selected text is neither of the chosen languages.")
            pyperclip.copy(old_clipboard)
            return

        corrected_text = convert_text(selected_text, src_lang, tgt_lang)
        print(f"Converted ({src_lang}->{tgt_lang}): {selected_text} -> {corrected_text}")

        pyperclip.copy(corrected_text)
        time.sleep(0.1)

        send_ctrl_v()
        time.sleep(0.2)

        pyperclip.copy(old_clipboard)

    except Exception as e:
        print("Correction error:", e)

def copy_selected_text():
    try:
        close_menu()
        global target_window
        target_window = win32gui.GetForegroundWindow()
        send_ctrl_c()
        print("Text copied.")
    except Exception as e:
        print("Copy error:", e)

def stop_program():
    print("Stopping Keyboard Corrector...")
    try:
        mouse.unhook_all()
    except Exception:
        pass
    try:
        keyboard.unhook_all()
    except Exception:
        pass
    try:
        if tray_icon is not None:
            tray_icon.stop()
    except Exception:
        pass
    try:
        _single_instance_socket.close()
    except Exception:
        pass
    try:
        root.destroy()
    except Exception:
        pass
    os._exit(0)

def on_close():
    # The X button no longer quits the app -- it hides the window to
    # the System Tray. The app only fully exits via the tray's "Exit".
    hide_to_tray()

def correct_from_button():
    root.withdraw()
    root.after(200, _run_correction_and_restore)

def _run_correction_and_restore():
    """Runs the correction while the window is hidden, then guarantees
    the window is brought back no matter what happens (success, no
    selection, or an unexpected error)."""
    try:
        correct_selected_text()
    except Exception as e:
        print("Correction from button failed:", e)
    finally:
        try:
            root.deiconify()
            root.attributes("-topmost", True)
            root.lift()
            root.focus_force()
        except Exception as e:
            print("Could not restore window:", e)

# =========================================================
# Single-instance enforcement
#
# Uses a TCP socket bound to the local loopback address (127.0.0.1) as
# both a lock and a simple same-machine IPC channel. This never talks
# to the network or the internet -- 127.0.0.1 traffic never leaves the
# machine, it's just how two local processes signal each other.
#
# If binding succeeds, this is the first/only instance: keep the
# socket open and listen for a "SHOW" message from any later launch.
# If binding fails, another instance is already running: tell it to
# show its window, then exit immediately without creating any UI,
# tray icon, or hooks.
# =========================================================

SINGLE_INSTANCE_HOST = "127.0.0.1"
SINGLE_INSTANCE_PORT = 51973

def _try_acquire_single_instance_lock():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        s.bind((SINGLE_INSTANCE_HOST, SINGLE_INSTANCE_PORT))
        s.listen(5)
        return s
    except OSError:
        try:
            s.close()
        except Exception:
            pass
        return None

def _notify_existing_instance():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1.5)
        s.connect((SINGLE_INSTANCE_HOST, SINGLE_INSTANCE_PORT))
        s.sendall(b"SHOW")
        s.close()
    except Exception as e:
        print("Could not reach the already-running instance:", e)

_single_instance_socket = _try_acquire_single_instance_lock()
if _single_instance_socket is None:
    print("Keyboard Corrector is already running -- showing the existing window instead.")
    _notify_existing_instance()
    sys.exit(0)

def _single_instance_listener(server_socket):
    """Runs on a background thread for the life of the app. Whenever a
    second launch connects and sends "SHOW", bring the real window to
    the foreground on the main thread via root.after()."""
    while True:
        try:
            conn, _addr = server_socket.accept()
        except OSError:
            break
        try:
            data = conn.recv(64)
            if data == b"SHOW":
                root.after(0, show_window)
        except Exception:
            pass
        finally:
            try:
                conn.close()
            except Exception:
                pass

# =========================================================
# Manual launch vs. Windows-Startup launch
#
# The Windows Startup entry (registry Run key / Startup folder
# shortcut / installer-created shortcut) should launch the app with
# a "--startup" argument, e.g.:  KeyboardCorrector.exe --startup
# A normal manual double-click has no such argument, so the window
# opens as usual.
# =========================================================

LAUNCHED_FROM_STARTUP = any(
    arg.lower() in ("--startup", "--minimized", "/startup") for arg in sys.argv[1:]
)

# =========================================================
# Tkinter GUI
# =========================================================

root = tk.Tk()
root.title("Keyboard Corrector")
root.geometry("400x320")
root.resizable(False, False)
root.attributes("-topmost", True)
root.attributes("-alpha", 0.93)

# ---------------------------------------------------------
# Icon loading: works both when run directly with Python and
# when packaged into an EXE with PyInstaller. Never crashes
# the app if the icon cannot be found/loaded.
# ---------------------------------------------------------

def resource_path(filename):
    try:
        if getattr(sys, "frozen", False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, filename)
    except Exception:
        return filename

def load_icon():
    candidates = [
        r"C:\Users\mouha\Desktop\KeyboardCorrector\Icon.ico",
        resource_path("Icon.ico"),
    ]
    for path in candidates:
        try:
            if path and os.path.exists(path):
                root.iconbitmap(path)
                return
        except Exception as e:
            print(f"Icon load failed for '{path}':", e)
    print("Icon not loaded: no valid Icon.ico found in known locations.")

load_icon()

# ---------------------------------------------------------
# System Tray support (pystray)
#
# The app now runs primarily from the tray: the main window starts
# hidden, closing it with the X hides it to the tray instead of
# quitting, and the only way to fully exit is the tray menu's "Exit".
# All existing correction / hook / menu / hotkey functionality is
# untouched -- it already works whether the window is visible or not.
# ---------------------------------------------------------

def load_tray_icon_image():
    """Loads the same Icon.ico used for the window for the tray icon.
    Falls back to a simple generated icon so the tray icon always has
    something valid to show, even if Icon.ico can't be found."""
    candidates = [
        r"C:\Users\mouha\Desktop\KeyboardCorrector\Icon.ico",
        resource_path("Icon.ico"),
    ]
    for path in candidates:
        try:
            if path and os.path.exists(path):
                return Image.open(path)
        except Exception as e:
            print(f"Tray icon load failed for '{path}':", e)
    # Fallback: a simple generated placeholder icon (a filled circle).
    try:
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse((4, 4, 60, 60), fill=(60, 140, 216, 255))
        return img
    except Exception as e:
        print("Could not build fallback tray icon:", e)
        return None

def show_window():
    try:
        root.deiconify()
        root.attributes("-topmost", True)
        root.lift()
        root.focus_force()
    except Exception as e:
        print("Could not show window:", e)

def hide_to_tray():
    try:
        root.withdraw()
    except Exception as e:
        print("Could not hide window:", e)

def on_tray_open(icon, item):
    root.after(0, show_window)

def on_tray_exit(icon, item):
    try:
        icon.stop()
    except Exception:
        pass
    root.after(0, stop_program)

tray_icon = None

def start_tray_icon():
    global tray_icon
    image = load_tray_icon_image()
    menu = pystray.Menu(
        pystray.MenuItem("Open Keyboard Corrector", on_tray_open, default=True),
        pystray.MenuItem("Exit", on_tray_exit),
    )
    tray_icon = pystray.Icon("KeyboardCorrector", image, "Keyboard Corrector", menu)
    tray_thread = threading.Thread(target=tray_icon.run, daemon=True)
    tray_thread.start()

# ---------------------------------------------------------
# Best-effort Windows 11 rounded window corners via DWM.
# Silently ignored on Windows versions that don't support it.
# ---------------------------------------------------------

def apply_rounded_corners():
    try:
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        DWMWA_WINDOW_CORNER_PREFERENCE = 33
        DWMWCP_ROUND = 2
        value = ctypes.c_int(DWMWCP_ROUND)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_WINDOW_CORNER_PREFERENCE, ctypes.byref(value), ctypes.sizeof(value)
        )
    except Exception as e:
        print("Rounded corners not applied (unsupported on this OS):", e)

root.after(50, apply_rounded_corners)

lang1_var = tk.StringVar(value="en")
lang2_var = tk.StringVar(value="ar")
dark_mode_var = tk.BooleanVar(value=False)

style = ttk.Style()
style.theme_use("clam")

# ---------------------------------------------------------
# "Aero glass" color palette
# ---------------------------------------------------------

PALETTE = {
    "light": {
        "bg": "#DCEBFA",
        "panel": "#EAF4FE",
        "panel_border": "#BBDCF7",
        "panel_highlight": "#FFFFFF",
        "text": "#12324D",
        "accent": "#3C8CD8",
        "accent_hover": "#2C6FB0",
        "field_bg": "#FFFFFF",
        "field_border": "#9FC7EC",
    },
    "dark": {
        "bg": "#101826",
        "panel": "#182234",
        "panel_border": "#28405C",
        "panel_highlight": "#2E4A6B",
        "text": "#E8F1FB",
        "accent": "#3C8CD8",
        "accent_hover": "#5AA6EC",
        "field_bg": "#1E2B40",
        "field_border": "#33506F",
    },
}

def current_palette():
    return PALETTE["dark"] if dark_mode_var.get() else PALETTE["light"]

# ---------------------------------------------------------
# Rounded "glass" panel drawn on a Canvas
# ---------------------------------------------------------

def create_rounded_rect(canvas, x1, y1, x2, y2, radius=18, **kwargs):
    points = [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)

bg_canvas = tk.Canvas(root, highlightthickness=0, bd=0)
bg_canvas.pack(fill="both", expand=True)

glass_panel_id = None
glass_highlight_id = None

content_frame = ttk.Frame(root, padding=18)
content_window_id = bg_canvas.create_window(200, 160, window=content_frame, width=372, height=292)

def redraw_glass_background():
    global glass_panel_id, glass_highlight_id
    p = current_palette()
    bg_canvas.configure(bg=p["bg"])
    bg_canvas.delete("glass")
    w = int(root.winfo_width()) or 400
    h = int(root.winfo_height()) or 320
    glass_panel_id = create_rounded_rect(
        bg_canvas, 10, 10, w - 10, h - 10, radius=22,
        fill=p["panel"], outline=p["panel_border"], width=1.5, tags="glass",
    )
    # subtle glossy highlight strip near the top, classic Aero touch
    glass_highlight_id = create_rounded_rect(
        bg_canvas, 16, 14, w - 16, h * 0.32, radius=16,
        fill=p["panel_highlight"], outline="", tags="glass",
    )
    bg_canvas.itemconfig(glass_highlight_id, stipple="gray25")
    bg_canvas.tag_lower("glass")
    bg_canvas.coords(content_window_id, w / 2, h / 2)
    bg_canvas.itemconfig(content_window_id, width=w - 40, height=h - 40)

def apply_theme():
    p = current_palette()
    redraw_glass_background()

    style.configure(".", background=p["panel"], foreground=p["text"])
    style.configure("TFrame", background=p["panel"])
    style.configure("TLabel", background=p["panel"], foreground=p["text"])

    style.configure(
        "TButton", background=p["field_bg"], foreground=p["text"],
        borderwidth=1, relief="flat", padding=6,
    )
    style.map(
        "TButton",
        background=[("active", p["accent_hover"]), ("!active", p["field_bg"])],
        foreground=[("active", "#FFFFFF")],
    )

    style.configure(
        "Accent.TButton", background=p["accent"], foreground="#FFFFFF",
        borderwidth=0, relief="flat", padding=(14, 8), font=("Segoe UI", 10, "bold"),
    )
    style.map("Accent.TButton", background=[("active", p["accent_hover"])])

    style.configure(
        "TCombobox", fieldbackground=p["field_bg"], background=p["field_bg"],
        foreground=p["text"], bordercolor=p["field_border"], relief="flat",
        arrowsize=14, padding=4,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", p["field_bg"])],
        selectbackground=[("readonly", p["field_bg"])],
        selectforeground=[("readonly", p["text"])],
        bordercolor=[("focus", p["accent"])],
    )

    style.configure("TCheckbutton", background=p["panel"], foreground=p["text"])
    style.map("TCheckbutton", background=[("active", p["panel"])])

root.bind("<Configure>", lambda e: redraw_glass_background() if e.widget == root else None)

# =========================================================
# Build UI (placed inside the glass content_frame)
# =========================================================

lbl_title = ttk.Label(content_frame, text="Keyboard Corrector", font=("Segoe UI", 15, "bold"))
lbl_title.grid(row=0, column=0, columnspan=2, pady=(0, 18))

lbl_lang1 = ttk.Label(content_frame, text="Language 1:")
lbl_lang1.grid(row=1, column=0, sticky="w", pady=6)
lang1_combo = ttk.Combobox(content_frame, state="readonly", width=22)
lang1_combo.grid(row=1, column=1, sticky="w", pady=6)

lbl_lang2 = ttk.Label(content_frame, text="Language 2:")
lbl_lang2.grid(row=2, column=0, sticky="w", pady=6)
lang2_combo = ttk.Combobox(content_frame, state="readonly", width=22)
lang2_combo.grid(row=2, column=1, sticky="w", pady=6)

btn_correct = ttk.Button(
    content_frame, text="Correct Text", command=correct_from_button, style="Accent.TButton",
)
btn_correct.grid(row=3, column=0, columnspan=2, pady=22, sticky="w")

chk_dark = ttk.Checkbutton(
    content_frame, text="Dark Mode", variable=dark_mode_var, command=apply_theme,
)
chk_dark.grid(row=4, column=0, columnspan=2, pady=(0, 5), sticky="w")

# =========================================================
# About window (Help -> About)
# =========================================================

APP_NAME = "Keyboard Corrector"
APP_VERSION = "1.0"
APP_DEVELOPER = "Gheberour Mouatacim Billah"
APP_COPYRIGHT_YEAR = "2026"

def show_about_window():
    p = current_palette()

    about = tk.Toplevel(root)
    about.title(f"About {APP_NAME}")
    about.resizable(False, False)
    about.transient(root)
    about.attributes("-topmost", True)
    try:
        about.attributes("-alpha", 0.97)
    except Exception:
        pass
    about.configure(bg=p["bg"])

    # Reuse the same icon-loading approach as the main window.
    try:
        about.iconbitmap(r"C:\Users\mouha\Desktop\KeyboardCorrector\Icon.ico")
    except Exception:
        try:
            about.iconbitmap(resource_path("Icon.ico"))
        except Exception:
            pass

    width, height = 360, 230

    about_canvas = tk.Canvas(about, width=width, height=height, highlightthickness=0, bd=0, bg=p["bg"])
    about_canvas.pack(fill="both", expand=True)
    create_rounded_rect(
        about_canvas, 8, 8, width - 8, height - 8, radius=18,
        fill=p["panel"], outline=p["panel_border"], width=1.5,
    )

    about_frame = ttk.Frame(about_canvas, padding=16)
    about_canvas.create_window(width / 2, height / 2, window=about_frame, width=width - 34, height=height - 30)
    label_wrap = width - 60

    ttk.Label(about_frame, text=APP_NAME, font=("Segoe UI", 13, "bold")).pack(pady=(2, 2))
    ttk.Label(about_frame, text=f"Version {APP_VERSION}").pack()
    ttk.Label(
        about_frame, text=f"Developed by {APP_DEVELOPER}",
        wraplength=label_wrap, justify="center",
    ).pack(pady=(10, 0))
    ttk.Label(
        about_frame, text=f"Copyright \u00A9 {APP_COPYRIGHT_YEAR} {APP_DEVELOPER}", font=("Segoe UI", 9),
        wraplength=label_wrap, justify="center",
    ).pack(pady=(14, 0))
    ttk.Label(about_frame, text="All Rights Reserved.", font=("Segoe UI", 9)).pack()

    ttk.Button(about_frame, text="OK", style="Accent.TButton", command=about.destroy).pack(pady=(16, 0))

    about.update_idletasks()
    root.update_idletasks()
    x = root.winfo_x() + (root.winfo_width() - width) // 2
    y = root.winfo_y() + (root.winfo_height() - height) // 2
    about.geometry(f"{width}x{height}+{x}+{y}")
    about.grab_set()
    about.focus_set()

menubar = tk.Menu(root)
help_menu = tk.Menu(menubar, tearoff=False)
help_menu.add_command(label="About", command=show_about_window)
menubar.add_cascade(label="Help", menu=help_menu)
root.config(menu=menubar)

# =========================================================
# Language combo functions (reliable display via .current())
# =========================================================

def get_code_from_display(display_name):
    for code, name in LANGUAGES.items():
        if name == display_name:
            return code
    return None

def sync_combo_displays():
    names = [LANGUAGES[c] for c in lang_codes]
    lang1_combo["values"] = names
    lang2_combo["values"] = names
    lang1_combo.current(lang_codes.index(lang1_var.get()))
    lang2_combo.current(lang_codes.index(lang2_var.get()))

def on_lang1_selected(event=None):
    code = get_code_from_display(lang1_combo.get())
    if code is None:
        return
    lang1_var.set(code)
    if lang2_var.get() == code:
        for c in lang_codes:
            if c != code:
                lang2_var.set(c)
                break
    sync_combo_displays()

def on_lang2_selected(event=None):
    code = get_code_from_display(lang2_combo.get())
    if code is None:
        return
    lang2_var.set(code)
    if lang1_var.get() == code:
        for c in lang_codes:
            if c != code:
                lang1_var.set(c)
                break
    sync_combo_displays()

lang1_combo.bind("<<ComboboxSelected>>", on_lang1_selected)
lang2_combo.bind("<<ComboboxSelected>>", on_lang2_selected)

# =========================================================
# Right-click context menu
# =========================================================

menu = tk.Menu(root, tearoff=False)
menu.add_command(label="Cancel", command=lambda: close_menu())
menu.add_separator()
menu.add_command(label="Correct Keyboard Text", command=correct_selected_text)

menu_visible = False

def close_menu(event=None):
    global menu_visible
    if menu_visible:
        try:
            menu.unpost()
        except Exception:
            pass
        menu_visible = False

def get_menu_rect():
    try:
        mx = menu.winfo_rootx()
        my = menu.winfo_rooty()
        mw = menu.winfo_width()
        mh = menu.winfo_height()
        if mw <= 1 or mh <= 1:
            return None
        return mx, my, mw, mh
    except Exception:
        return None

def show_menu(x=None, y=None):
    global menu_visible
    close_menu()
    try:
        if x is None or y is None:
            x, y = mouse.get_position()
        menu.update_idletasks()
        menu_width = menu.winfo_reqwidth() or 160
        # Appear to the LEFT of the cursor instead of the right
        popup_x = max(0, x - menu_width)
        popup_y = y
        menu_visible = True
        menu.tk_popup(popup_x, popup_y)
        menu.update_idletasks()
    finally:
        menu.grab_release()

def _handle_left_click_close(x, y):
    if not menu_visible:
        return
    rect = get_menu_rect()
    if rect:
        mx, my, mw, mh = rect
        if mx <= x <= mx + mw and my <= y <= my + mh:
            return  # click landed inside the menu, let tkinter handle it
    close_menu()

# NOTE: the `mouse` and `keyboard` libraries invoke these callbacks on a
# background hook thread, NOT the Tkinter main thread. Tkinter is not
# thread-safe, so every callback below only reads the raw mouse position
# (safe, no Tk calls) and then schedules the actual Tk/menu work with
# root.after(0, ...) so it always runs on the main thread. Without this,
# calls like menu.winfo_rootx() from the hook thread can silently fail or
# behave unreliably, which was why outside clicks weren't closing the menu.

def on_global_right_down():
    x, y = mouse.get_position()
    remember_target_window()
    root.after(0, lambda: _handle_right_click(x, y))

def _handle_right_click(x, y):
    # Close any menu that might already be open first (so a right-click
    # always closes-then-reopens rather than stacking menus).
    close_menu()
    selected = probe_selected_text()
    if selected.strip():
        show_menu(x, y)
    # else: nothing is selected, so we deliberately do nothing further
    # and let the right-click pass through normally to the app underneath.

def on_global_left_down():
    x, y = mouse.get_position()
    root.after(0, lambda: _handle_left_click_close(x, y))

def on_escape_pressed(event=None):
    root.after(0, close_menu)

mouse.on_button(on_global_right_down, buttons=("right",), types=("down",))
mouse.on_button(on_global_left_down, buttons=("left",), types=("down",))
keyboard.on_press_key("esc", lambda e: on_escape_pressed())

# also close on Escape / focus-out when the menu itself has focus
menu.bind("<Unmap>", lambda e: close_menu())

# =========================================================
# Start
# =========================================================

print("========================================")
print("Keyboard Corrector is running.")
print("Right Click -> Cancel / Correct Keyboard Text")
print("========================================")

sync_combo_displays()
apply_theme()

root.protocol("WM_DELETE_WINDOW", on_close)

threading.Thread(target=_single_instance_listener, args=(_single_instance_socket,), daemon=True).start()

start_tray_icon()

if LAUNCHED_FROM_STARTUP:
    # Started automatically by Windows: stay hidden in the tray.
    root.withdraw()
else:
    # Manual launch: open the window normally; the tray icon is still available.
    show_window()

root.mainloop()

stop_program()